#!/usr/bin/env bash
# 真机测试统一入口 —— 强制「先预热守护进程，再跑目标」这个顺序。
#
# 为什么必须是脚本而不是每次手敲命令：
#   本机实测（iPhone 13 / iOS 26.7 / 网络配对无 USB）发现，直接跑 UI 测试会
#   以两种形态失败，而且**都不是代码问题**：
#     ① Early unexpected exit ... exited with code 74
#        [DTXConnection] Connection peer refused channel request for
#          "dtxproxy:XCTestDriverInterface:XCTestManager_IDEInterface"
#     ② The test runner failed to initialize for UI testing.
#        (Timed out while enabling automation mode.)
#
#   判别实验：同设备同会话先只跑单元测试 → 5/5 通过。
#   说明 testmanagerd 本身健康，缺的是 UI automation 通道的初始化时机。
#   先跑一次设备侧测试把守护进程拉起来，UI 测试立刻通过
#   （Setting up automation session ≈ 3.7s）。
#
#   旁证（说明为什么它无法自愈）：
#     · xctrace list devices 把该机列为 Devices Offline
#     · ~/Library/Developer/Xcode/DeviceSupport 为空，从未为该设备准备
#     · 设备 iOS 26.7 (23H24) 比 Xcode SDK 26.4 (23E252) 更新
#     · 设备为网络配对（*.coredevice.local），Xcode 无法经 USB 准备 DeviceSupport
#
#   顺序约定如果只写在文档里，迟早有人直接跑 UI 目标而重现 exit 74。
#   所以把它固化成脚本：**没有预热就不允许进入 UI 阶段**。
#
# 用法：
#   .apm/tools/device-test.sh                 # 预热 + 完整真机套件
#   .apm/tools/device-test.sh ui              # 预热 + 只跑 UI 套件
#   .apm/tools/device-test.sh unit            # 只跑单元套件（仍先预热）
#   .apm/tools/device-test.sh one <Target/Class/test>   # 预热 + 单个用例
#   APM_DEVICE=<UDID> .apm/tools/device-test.sh         # 换设备
#
# 退出码：0 全绿；1 有失败；2 环境前置不满足（设备锁屏/未连接等）

set -euo pipefail

SCHEME="${APM_SCHEME:-Duiyi}"
PROJECT="${APM_PROJECT:-Duiyi.xcodeproj}"
CONFIG="${APM_CONFIG:-Debug}"
DEVICE="${APM_DEVICE:-REDACTED_CORE_DEVICE_ID}"
# 预热目标：故意选一组又快又稳的纯单元测试，它的作用不是测覆盖率，而是把
# testmanagerd 拉起来。换成任何设备侧可跑目标都行。
WARMUP="${APM_WARMUP:-DuiyiTests/TaskStoreTests}"

MODE="${1:-all}"
ONLY="${2:-}"

command -v mobilebuildmcp >/dev/null || { echo "⛔ 缺少 mobilebuildmcp（npm i -g mobilebuildmcp）"; exit 2; }

# ── 环境前置检查 ─────────────────────────────────────────
echo "═══════ 真机测试 ═══════"
echo "  设备:   $DEVICE"
echo "  工程:   $PROJECT / $SCHEME / $CONFIG"
echo "  模式:   $MODE${ONLY:+ $ONLY}"
echo

lock_json=$(mktemp -t apm-lock.XXXXXX)
if ! xcrun devicectl device info lockState --device "$DEVICE" --timeout 30 \
      --json-output "$lock_json" --quiet >/dev/null 2>&1; then
  echo "⛔ 连不上设备 $DEVICE —— 确认已连接并已信任这台 Mac"
  rm -f "$lock_json"; exit 2
fi
passcode=$(python3 -c "
import json,sys
print(json.load(open('$lock_json')).get('result',{}).get('passcodeRequired'))
" 2>/dev/null || echo "unknown")
rm -f "$lock_json"
if [ "$passcode" = "True" ]; then
  echo "⛔ 设备处于锁屏状态。UI 测试会被系统拒绝，请解锁后重跑。"
  exit 2
fi
echo "  ✓ 设备已解锁"

# ── 预热 ────────────────────────────────────────────────
# 这一步不是可选的。缺它，UI 阶段会以 exit 74 / automation 超时失败。
run_test() {
  local label="$1"; shift
  local extra_json="$1"; shift
  local out; out=$(mktemp -t apm-test.XXXXXX)
  echo "  → $label"
  local -a args=(
    device test --project-path "$PROJECT" --scheme "$SCHEME"
    --device-id "$DEVICE" --configuration "$CONFIG" --output json
  )
  if [ -n "$extra_json" ]; then args+=(--json "$extra_json"); fi
  set +e
  mobilebuildmcp "${args[@]}" >"$out" 2>/dev/null
  set -e
  python3 - "$out" "$label" <<'PY'
import json, sys
path, label = sys.argv[1], sys.argv[2]
try:
    data = json.load(open(path)).get("data", {})
except Exception as exc:
    print(f"    ⛔ 无法解析输出：{exc}")
    sys.exit(1)
summary = data.get("summary", {}) or {}
counts = summary.get("counts", {}) or {}
status = summary.get("status", "UNKNOWN")
print(f"    {label}: {status}  passed={counts.get('passed', 0)} "
      f"failed={counts.get('failed', 0)} skipped={counts.get('skipped', 0)} "
      f"({summary.get('durationMs', 0) / 1000:.0f}s)")
for f in (data.get("diagnostics", {}) or {}).get("testFailures", []) or []:
    print(f"      ✗ {f.get('test') or f.get('suite')}: {str(f.get('message'))[:160]}")
xcr = (data.get("artifacts", {}) or {}).get("xcresultPath")
if xcr:
    print(f"      xcresult: {xcr}")
sys.exit(0 if status == "SUCCEEDED" else 1)
PY
}

echo
# 注意：变量紧邻中文全角标点时必须写成 ${VAR}。
# "$VAR（说明）" 里的（不是变量名分隔符，bash 会去找一个叫 "VAR（说明）" 的变量，
# 在 set -u 下直接报「未绑定的变量」。本项目文档全角标点很多，这个坑很容易踩。
echo "  [1/2] 预热 testmanagerd（${WARMUP}）"
if ! run_test "warmup" "{\"extraArgs\":[\"-only-testing:${WARMUP}\"]}"; then
  echo
  echo "⛔ 预热失败 —— 先修环境，不要继续跑 UI。"
  echo "   · 确认设备已解锁、Developer Mode 已开、已信任这台 Mac"
  echo "   · 确认安装的 App 没超过免费 provisioning 的数量上限"
  exit 1
fi
echo "  ✓ 守护进程已就绪"

echo
echo "  [2/2] 目标测试"
case "$MODE" in
  warm) echo "  （--warm：只预热）"; exit 0 ;;
  ui)   extra='{"extraArgs":["-only-testing:DuiyiUITests"]}' ;;
  unit) extra='{"extraArgs":["-only-testing:DuiyiTests"]}' ;;
  all)  extra='' ;;
  one)  [ -n "$ONLY" ] || { echo "⛔ one 模式需要给出 Target/Class/test"; exit 2; }
        extra="{\"extraArgs\":[\"-only-testing:$ONLY\"]}" ;;
  *)    echo "⛔ 未知模式：${MODE}（可选 all / ui / unit / one / warm）"; exit 2 ;;
esac

if run_test "$MODE" "$extra"; then
  echo
  echo "✅ 真机测试通过"
else
  echo
  echo "❌ 真机测试失败"
  cat <<'HINT'

排查顺序（按本机实测的证据强度排序）：
  1. 若报 exit 74 或 "Timed out while enabling automation mode"
     → 守护进程没就绪。确认本脚本的预热步骤已执行（不要跳过它直接跑 UI）。
  2. 若报 "Free provisioning requires at most 10 apps"
     → 设备上安装的 App 超限，清理后重跑。
  3. 若 UI 测试反复起不来
     → 用 USB 连接设备并保持解锁，让 Xcode 为该 OS 版本准备 DeviceSupport
        （网络配对时 Xcode 无法完成这一步）。
        设备 OS 比 Xcode SDK 更新时尤其容易卡在这里。
HINT
  exit 1
fi

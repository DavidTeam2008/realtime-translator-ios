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
#   APM_DEVICE=<CoreDevice ID> .apm/tools/device-test.sh # 换设备
#
# 退出码：0 全绿；1 有失败；2 环境前置不满足（设备锁屏/未连接等）

set -euo pipefail

SCHEME="${APM_SCHEME:-Duiyi}"
PROJECT="${APM_PROJECT:-Duiyi.xcodeproj}"
CONFIG="${APM_CONFIG:-Debug}"
DEVICE="${APM_DEVICE:-}"
if [ -z "$DEVICE" ]; then
  echo "⛔ 缺少 APM_DEVICE（设备 CoreDevice ID）" >&2
  echo "   查看：xcrun devicectl list devices / mobilebuildmcp device list" >&2
  echo "   本机值写 AGENTS.local.md，或：APM_DEVICE=<id> .apm/tools/device-test.sh" >&2
  exit 2
fi
# 预热目标：故意选一组又快又稳的纯单元测试，它的作用不是测覆盖率，而是把
# testmanagerd 拉起来。换成任何设备侧可跑目标都行。
WARMUP="${APM_WARMUP:-DuiyiTests/TaskStoreTests}"

MODE="${1:-all}"
ONLY="${2:-}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EVIDENCE_TOOL="$ROOT/tools/evidence.py"
# Xcode 版本只作为 evidence 的 environment 字段；没有 Xcode 时测试本身会先失败。
XCODE_VERSION=""
if command -v xcodebuild >/dev/null 2>&1; then
  XCODE_VERSION="$(xcodebuild -version 2>/dev/null | head -n 1 || true)"
fi

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
# summary_path（第 3 参数，可选）：目标测试的机器可读摘要，供 evidence 使用。
run_test() {
  local label="$1"; shift
  local extra_json="${1:-}"; shift || true
  local summary_path="${1:-}"
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
  python3 - "$out" "$label" "$summary_path" <<'PY'
import json, sys
path, label = sys.argv[1], sys.argv[2]
summary_path = sys.argv[3] if len(sys.argv) > 3 else ""
try:
    data = json.load(open(path)).get("data", {}) or {}
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
if summary_path:
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump({
            "label": label,
            "status": status,
            "counts": counts,
            "durationMs": summary.get("durationMs", 0),
            "xcresultPath": xcr,
        }, fh, ensure_ascii=False)
sys.exit(0 if status == "SUCCEEDED" else 1)
PY
}

# ── 证据与 skip 断言（Phase 1）────────────────────────────────
# 目标测试完成后自动写 .apm/evidence/；skipped 必须等于真机预期（基线读自
# .apm/test-baseline.json）。证据写入失败不覆盖测试结论，但会显式告警。
write_evidence() {
  local mode="$1" summary="$2"
  [ -s "$summary" ] || { echo "  （无测试摘要，跳过 evidence）"; return 0; }
  [ -f "$EVIDENCE_TOOL" ] || { echo "  ⚠️ 缺少 ${EVIDENCE_TOOL}，跳过 evidence"; return 0; }
  local draft; draft=$(mktemp -t apm-evidence.XXXXXX)
  if ! python3 - "$ROOT" "$mode" "$summary" "$XCODE_VERSION" "$CONFIG" >"$draft" <<'PY'
import json, sys
from pathlib import Path

root, mode = Path(sys.argv[1]), sys.argv[2]
summary_path, xcode, config = Path(sys.argv[3]), sys.argv[4].strip() or None, sys.argv[5]
claims = {"all": "device-tests-pass", "ui": "ui-tests-pass", "unit": "unit-tests-pass"}
claim = claims.get(mode)
if claim is None:
    sys.exit(0)
baseline = json.loads((root / ".apm/test-baseline.json").read_text(encoding="utf-8"))
summary = json.loads(summary_path.read_text(encoding="utf-8"))
counts = summary.get("counts") or {}
status = summary.get("status", "UNKNOWN")
passed = int(counts.get("passed", 0) or 0)
failed = int(counts.get("failed", 0) or 0)
skipped = int(counts.get("skipped", 0) or 0)
floors = {
    "all": int(baseline["unit"]["floor"]) + int(baseline["ui"]["floor"]),
    "ui": int(baseline["ui"]["floor"]),
    "unit": int(baseline["unit"]["floor"]),
}
expected_skipped = int(baseline["expectedSkipped"]["device"])
verdict = "PASS" if (
    status == "SUCCEEDED"
    and failed == 0
    and passed >= floors[mode]
    and skipped == expected_skipped
) else "FAIL"
draft = {
    "claim": claim,
    "command": f".apm/tools/device-test.sh {mode}",
    "environment": {
        "xcode": xcode,
        "simulator": None,
        "device": "physical",
        "build": config,
    },
    "result": {
        "status": status,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "durationSec": round(float(summary.get("durationMs") or 0) / 1000, 1),
        "xcresultPath": summary.get("xcresultPath"),
    },
    "verdict": verdict,
    "notes": f"mode={mode}；设备 ID 不写入证据；skipped 期望={expected_skipped}",
}
print(json.dumps(draft, ensure_ascii=False))
PY
  then
    echo "  ⚠️ evidence 草稿生成失败（不覆盖测试结论）"
    rm -f "$draft"
    return 0
  fi
  if [ ! -s "$draft" ]; then
    rm -f "$draft"
    return 0
  fi
  local evidence_path=""
  if evidence_path=$(python3 "$EVIDENCE_TOOL" write --from-json "$draft" --root "$ROOT"); then
    echo "  evidence: ${evidence_path}"
  else
    echo "  ⚠️ evidence 写入失败（不覆盖测试结论；修好后重跑可重新生成）"
  fi
  rm -f "$draft"
}

# skipped 断言：真机预期 0（白名单）；不符按失败处理（不静默变绿）。
check_skipped() {
  local summary="$1"
  [ -s "$summary" ] || return 0
  python3 - "$ROOT" "$summary" <<'PY'
import json, sys
from pathlib import Path

root, summary_path = Path(sys.argv[1]), Path(sys.argv[2])
summary = json.loads(summary_path.read_text(encoding="utf-8"))
counts = summary.get("counts") or {}
skipped = int(counts.get("skipped", 0) or 0)
baseline = json.loads((root / ".apm/test-baseline.json").read_text(encoding="utf-8"))
expected = int(baseline["expectedSkipped"]["device"])
if skipped != expected:
    print(f"    ⛔ skipped={skipped} 与真机预期 {expected} 不符（skip 白名单漂移，按失败处理）")
    sys.exit(1)
PY
}

echo
# 注意：变量紧邻中文全角标点时必须写成 ${VAR}。
# "$VAR（说明）" 里的（不是变量名分隔符，bash 会去找一个叫 "VAR（说明）" 的变量，
# 在 set -u 下直接报「未绑定的变量」。本项目文档全角标点很多，这个坑很容易踩。
echo "  [1/2] 预热 testmanagerd（${WARMUP}）"
if ! run_test "warmup" "{\"extraArgs\":[\"-allowProvisioningUpdates\",\"-only-testing:${WARMUP}\"]}" ""; then
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
  ui)   extra='{"extraArgs":["-allowProvisioningUpdates","-only-testing:DuiyiUITests"]}' ;;
  unit) extra='{"extraArgs":["-allowProvisioningUpdates","-only-testing:DuiyiTests"]}' ;;
  all)  extra='{"extraArgs":["-allowProvisioningUpdates"]}' ;;
  one)  [ -n "$ONLY" ] || { echo "⛔ one 模式需要给出 Target/Class/test"; exit 2; }
        extra="{\"extraArgs\":[\"-allowProvisioningUpdates\",\"-only-testing:$ONLY\"]}" ;;
  *)    echo "⛔ 未知模式：${MODE}（可选 all / ui / unit / one / warm）"; exit 2 ;;
esac

SUMMARY_JSON=$(mktemp -t apm-summary.XXXXXX)
TARGET_OK=0
if run_test "$MODE" "$extra" "$SUMMARY_JSON"; then
  TARGET_OK=1
fi

# Phase 1：自动写证据 + skipped 断言。unit/ui/all 才写；one/warm 不写证据。
SKIP_OK=1
case "$MODE" in
  unit|ui|all)
    write_evidence "$MODE" "$SUMMARY_JSON"
    if ! check_skipped "$SUMMARY_JSON"; then
      SKIP_OK=0
    fi
    ;;
esac
rm -f "$SUMMARY_JSON"

if [ "$TARGET_OK" -eq 1 ] && [ "$SKIP_OK" -eq 1 ]; then
  echo
  echo "✅ 真机测试通过"
else
  echo
  echo "❌ 真机测试失败"
  if [ "$TARGET_OK" -eq 1 ] && [ "$SKIP_OK" -eq 0 ]; then
    echo "   原因：测试本身 SUCCEEDED，但 skipped 数不符合真机预期 → 按失败处理。"
  fi
  cat <<'HINT'

排查顺序（按本机实测的证据强度排序）：
  1. 若报 exit 74 或 "Timed out while enabling automation mode"
     → 先确认本脚本的预热步骤已执行（不要跳过它直接跑 UI）。
     → 仍失败时看手机是否停在「为 “XCTest” 输入 iPhone 密码 /
       Enable UI Automation」。iOS 15+ 真机 UI 测试要求输入一次
       锁屏密码，设备重启后会再次要求；设备没有密码时无法完成。
  2. 若报 "Free provisioning requires at most 10 apps"
     → 设备上安装的 App 超限，清理后重跑。
  3. 若报 No profiles for '...xctrunner'
     → 脚本已带 -allowProvisioningUpdates；仍失败时确认 Team 和设备
       都在当前开发者账号下。
  4. 若 UI 测试反复起不来
     → 用 USB 连接设备并保持解锁，让 Xcode 为该 OS 版本准备 DeviceSupport
        （网络配对时 Xcode 无法完成这一步）。
        设备 OS 比 Xcode SDK 更新时尤其容易卡在这里。
HINT
  exit 1
fi

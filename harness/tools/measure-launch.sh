#!/usr/bin/env bash
# 冷启动耗时测量（真机）—— 闭环里「测量」这一步的唯一入口。
#
# 为什么必须是脚本而不是每次手敲命令：
#   铁律 3 要求「与基线完全相同的口径」。口径包括：同设备、同构建类型、
#   同测量命令、同样本量。手敲必然会漂移，脚本才能保证可比。
#
# 用法：
#   harness/tools/measure-launch.sh [次数] [输出文件]
# 默认 5 次，输出 harness/runs/<时间戳>/metrics.json

set -euo pipefail

UDID="${APM_UDID:-}"
if [ -z "$UDID" ]; then
  echo "⛔ 缺少 APM_UDID（硬件 UDID）" >&2
  echo "   查看：xcrun devicectl list devices" >&2
  echo "   本机值写 AGENTS.local.md，或：APM_UDID=<udid> harness/tools/measure-launch.sh" >&2
  exit 2
fi
BID="${APM_BUNDLE_ID:-com.david.Duiyi}"
N="${1:-5}"
RUN_DIR="${2:-harness/runs/$(date +%Y%m%d-%H%M%S)-launch}"
APP="${APM_APP:-/tmp/duiyi-t1/Build/Products/Release-iphoneos/Duiyi.app}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EVIDENCE_TOOL="$ROOT/tools/evidence.py"
# Xcode 版本只作为 evidence 的 environment 字段；没有 Xcode 时留空（测量本身会先失败）。
XCODE_VERSION=""
if command -v xcodebuild >/dev/null 2>&1; then
  XCODE_VERSION="$(xcodebuild -version 2>/dev/null | head -n 1 || true)"
fi
SECONDS=0

mkdir -p "$RUN_DIR/raw"
RAW="$RUN_DIR/raw/samples.txt"
: > "$RAW"

echo "═══════ 冷启动测量 ═══════"
echo "  设备: $UDID"
echo "  样本: $N 次"
echo "  产物: $RUN_DIR"
echo

# 预热一次（安装后首启受 dyld/缓存影响，不计入样本）
echo "  预热中…"
xcrun devicectl device install app --device "$UDID" "$APP" >/dev/null 2>&1 || true
sleep 2
timeout 30 xcrun devicectl device process launch --device "$UDID" --terminate-existing "$BID" >/dev/null 2>&1 || true
sleep 6

for i in $(seq 1 "$N"); do
  rm -f /tmp/apm_sys.txt
  ( timeout 25 idevicesyslog -u "$UDID" 2>/dev/null \
      | grep --line-buffered -aE "first-frame|Launch stages|EARLY pre-main|STORE open" > /tmp/apm_sys.txt ) &
  LP=$!
  sleep 3
  timeout 30 xcrun devicectl device process launch --device "$UDID" --terminate-existing "$BID" >/dev/null 2>&1
  sleep 8
  kill $LP 2>/dev/null; pkill -f "idevicesyslog -u $UDID" 2>/dev/null || true
  wait 2>/dev/null || true

  ms=$(grep -aoE "first-frame: [0-9]+ms" /tmp/apm_sys.txt | tail -1 | grep -oE "[0-9]+" || true)
  stages=$(grep -a "Launch stages" /tmp/apm_sys.txt | tail -1 | sed 's/.*Launch stages (since\/+delta ms): //' || true)
  premain=$(grep -aoE "pre-main: [0-9]+ ms" /tmp/apm_sys.txt | tail -1 | grep -oE "[0-9]+" || true)

  printf "  #%d  first-frame=%sms  pre-main=%sms\n" "$i" "${ms:-?}" "${premain:-?}"
  # 成对记录 —— 分层分析需要 pre-main 与 first-frame 一一对应
  [ -n "$ms" ] && [ -n "$premain" ] && echo "$premain $ms" >> "$RUN_DIR/raw/paired.txt"
  [ -n "$stages" ] && echo "$stages" >> "$RUN_DIR/raw/stages.txt"
done

python3 - "$RUN_DIR" "$N" "$XCODE_VERSION" "$SECONDS" <<'PY'
import json, statistics as st, subprocess, sys
from pathlib import Path

run = Path(sys.argv[1])
requested = int(sys.argv[2])
xcode = sys.argv[3].strip() or None
duration = float(sys.argv[4])
pairs = []
p = run/"raw"/"paired.txt"
if p.exists():
    for line in p.read_text().splitlines():
        a = line.split()
        if len(a) == 2 and a[0].isdigit() and a[1].isdigit():
            pairs.append((int(a[0]), int(a[1])))          # (premain, firstFrame)
if not pairs:
    print("\n⛔ 未采集到任何样本"); sys.exit(1)

# ── 分层：pre-main 是「进程启动环境冷热」的代理指标 ──────────────
# 实测发现冷启动呈双峰，且与 pre-main 同向（pre-main 小 → 全程快）。
# 直接比中位数会被两峰的混合比例左右 —— 所以按 pre-main 分层，
# 只比同层样本，A/B 才可比。
FAST_MAX = 20
fast = [ff for pm, ff in pairs if pm <= FAST_MAX]
slow = [ff for pm, ff in pairs if pm >  FAST_MAX]

def line(name, xs):
    if not xs: return None
    med = st.median(xs)
    cv = (st.stdev(xs)/st.mean(xs)*100) if len(xs) > 1 else 0.0
    return f"  {name:<10} 中位数 {med:>5.0f}ms   n={len(xs):<3} CV={cv:>5.1f}%"

try:
    commit = subprocess.run(["git","rev-parse","--short","HEAD"],
                            capture_output=True, text=True).stdout.strip()
except Exception:
    commit = "unknown"

allff = [ff for _, ff in pairs]
metrics = [
    {"name":"startup.cold.first_frame","unit":"ms","direction":"lower_is_better",
     "samples":allff, "minEffect":30},
    {"name":"startup.premain","unit":"ms","direction":"lower_is_better",
     "samples":[pm for pm, _ in pairs], "minEffect":5},
]
# 分层指标：A/B 对比应当用这两个，而不是上面的混合口径
if len(fast) >= 2:
    metrics.append({"name":"startup.cold.fast_env","unit":"ms","direction":"lower_is_better",
                    "samples":fast, "minEffect":30})
if len(slow) >= 2:
    metrics.append({"name":"startup.cold.slow_env","unit":"ms","direction":"lower_is_better",
                    "samples":slow, "minEffect":30})

(run/"metrics.json").write_text(json.dumps({
    "context": {
        "commit": commit,
        "device": "iPhone 13 (iPhone14,5) / iOS 26.7 / 真机",
        "build": "Release",
        "command": "harness/tools/measure-launch.sh",
        "method": "terminate + launch, idevicesyslog 抓 first-frame（延迟一个 runloop）",
        "stratify": f"按 pre-main 分层：fast_env ≤ {FAST_MAX}ms，slow_env > {FAST_MAX}ms",
    },
    "metrics": metrics,
}, ensure_ascii=False, indent=2), encoding="utf-8")

print("\n  ────────────────────────────────────────")
print("  ⚠️ 冷启动呈双峰，且与 pre-main 同向 —— 直接比混合中位数会被比例左右。")
print("     下面的**分层**口径才是可比的：")
for l in (line("fast_env", fast), line("slow_env", slow)):
    if l: print(l)
print(f"  混合口径    中位数 {st.median(allff):>5.0f}ms   n={len(allff)}")
print(f"  → {run/'metrics.json'}")

# Phase 1：evidence 草稿（摘要：n/CV/context/metrics 路径）。由外层 shell 调
# tools/evidence.py write --from-json 落盘；这里只产出草稿，避免脚本耦合 git 状态判定。
n_valid = len(allff)
cv_all = (st.stdev(allff) / st.mean(allff) * 100) if n_valid > 1 else 0.0
verdict = "PASS" if n_valid >= 10 and cv_all <= 10.0 else "UNVERIFIED"
draft = {
    "claim": "perf-measurement",
    "command": f"harness/tools/measure-launch.sh {requested} {run.as_posix()}",
    "environment": {
        "xcode": xcode,
        "simulator": None,
        "device": "physical",
        "build": "Release",
    },
    "result": {
        "status": "SUCCEEDED",
        "passed": n_valid,
        "failed": max(0, requested - n_valid),
        "skipped": 0,
        "durationSec": round(duration, 1),
        "xcresultPath": None,
        "metricsPath": (run / "metrics.json").as_posix(),
    },
    "verdict": verdict,
    "notes": (
        f"n={n_valid} CV={cv_all:.1f}%；PASS 仅表示测量可用且 context 一致，"
        "A/B 显著性/最小效应属后续阶段；分层口径与 docs/case-startup-performance.md 的结论存在差异（已知项）"
    ),
}
(run / "evidence-draft.json").write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
PY

# Phase 1：写 evidence 摘要（原始产物仍在 harness/runs/，不入库；本文件是 1–3KB 摘要）。
DRAFT="$RUN_DIR/evidence-draft.json"
if [ -f "$DRAFT" ] && [ -f "$EVIDENCE_TOOL" ]; then
  if EV_PATH=$(python3 "$EVIDENCE_TOOL" write --from-json "$DRAFT" --root "$ROOT"); then
    echo "  evidence: ${EV_PATH}"
  else
    echo "  ⚠️ evidence 写入失败（测量结果不受影响；修好后可重跑生成）"
  fi
  rm -f "$DRAFT"
fi

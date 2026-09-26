#!/usr/bin/env bash
# 冷启动耗时测量（真机）—— 闭环里「测量」这一步的唯一入口。
#
# 为什么必须是脚本而不是每次手敲命令：
#   铁律 3 要求「与基线完全相同的口径」。口径包括：同设备、同构建类型、
#   同测量命令、同样本量。手敲必然会漂移，脚本才能保证可比。
#
# 用法：
#   .apm/tools/measure-launch.sh [次数] [输出文件]
# 默认 5 次，输出 .apm/runs/<时间戳>/metrics.json

set -euo pipefail

UDID="${APM_UDID:-REDACTED_UDID}"
BID="${APM_BUNDLE_ID:-com.david.Duiyi}"
N="${1:-5}"
RUN_DIR="${2:-.apm/runs/$(date +%Y%m%d-%H%M%S)-launch}"
APP="${APM_APP:-/tmp/duiyi-t1/Build/Products/Release-iphoneos/Duiyi.app}"

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

python3 - "$RUN_DIR" <<'PY'
import json, statistics as st, subprocess, sys
from pathlib import Path

run = Path(sys.argv[1])
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
        "command": ".apm/tools/measure-launch.sh",
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
PY

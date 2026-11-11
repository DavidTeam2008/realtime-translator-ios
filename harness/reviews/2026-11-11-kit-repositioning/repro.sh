#!/usr/bin/env bash
# 复现 2026-11-11 harness-kit 重定位评估的校验点（只读；不提交、不联网）。
set -euo pipefail
cd "$(dirname "$0")/../../.."   # repo root
ENV_INFO="$(python3 --version 2>&1) / $(git rev-parse --short HEAD 2>/dev/null || echo no-git)"
echo "[env] $ENV_INFO"
echo "[sha256] 核对冻结副本..."
fail=0
while read -r expected name; do
  actual="$(shasum -a 256 "harness/reviews/2026-11-11-kit-repositioning/$name" | cut -d' ' -f1)"
  if [ "$actual" != "$expected" ]; then
    echo "[FAIL] sha256 mismatch: $name"
    fail=1
  fi
done <<'EOF'
18e7bc2d6431b563d3fce328a07095132faf43fb4df6aff97d65dd0e46c82a72 report.md
a5aacb6d37d548229314eb58e8340f9765d2766e3c63a4998361ad81bcb42768 positioning-audit.md
b9aa1e177b30084069a9e2fd8fb4a1d0fa45e061eef99f8b174de574c782a0ac research-ecosystem.md
0f52aceb26f2db0329d2540549c6a87275ec3b7ee0b8e5084493acda5b0c1e63 usability-audit.md
ab9d82d68019767bc6b956496c1d818dd11e5b6d449dd3e3f1dead52f4e21542 dsh-extensibility.md
de37e83ead0d45ca383b1eabded5dbc506a0d77e15d3aabcf9b509a998881823 review-instructions.md
c8ae17c9de0383d2007d18788efceacc77c139a5ed2ba5c522768b771c8fa79e review-quality.md
EOF
[ "$fail" -eq 0 ] && echo "[OK] sha256 全部一致"
echo "[test] kit 测试："
(cd harness-kit && python3 -m unittest discover -s tests -q)
echo "[test] 伪造 PASS 证据回归（无 artifact 必须被拒）："
(cd harness-kit && python3 -m unittest tests.test_core_plan_evidence_claim.KitCoreTest.test_verify_claim_rejects_forged_pass_without_artifact -q)
exit "$fail"

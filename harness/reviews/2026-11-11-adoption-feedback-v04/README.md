# v0.4.0 接入反馈收口 · 方案 / 审查 / 验证（冻结）

> 输入：外部存量仓 `harness/reports/2026-11-11-harness-kit-feedback.md`（kit 0.3.0，standard 档）。
> 输出：kit `v0.4.0`（15 项反馈 + 红队 P0/P1 回应，见 `plan.md` §8）。

## 文件

| 文件 | sha256 |
| --- | --- |
| `plan.md` | 4a40a1b837e8fa00e187925feb1b0c5863326093f5e3d80df994a26e382e3dcd |
| `red-team-plan-review.md` | 26b096b1464578b7a43f058750f8e6bc819f6433e8280dcc3c0f01fc660d5286 |
| `barra-validation.md` | b5a689537644a043e88f1fd635e9885aaba73e51680363535ea8cae4bdcf8aed |

- `plan.md`：冻结方案（P0×6 / P1×6 / P2×3 + 决策 V1–V12 + 红队逐条回应 §8）。
- `red-team-plan-review.md`：独立红队审查（P0×5 / P1×11 / P2×10 + 12 条最小验证清单）。
- `barra-validation.md`：真实接入仓只读复验与 /tmp 迁移路径实测。

## 复现

```bash
# kit 全量
cd harness-kit && python3 -m unittest discover -s tests -q
# 真实仓只读复验（不修改目标仓）
python3 harness-kit/core/tools/check_layers.py --root <barra>
python3 harness-kit/core/tools/verify_claim.py --all --root <barra>
python3 harness-kit/core/tools/check_plan.py --root <barra>          # 日常：归档问题 WARN
python3 harness-kit/core/tools/check_plan.py check --strict --root <barra>  # strict：归档问题 FAIL
```

不改写历史：`plan.md` 在实现后只追加 §8 回应；审查报告保持原样（含对冻结稿 sha256 的引用）。

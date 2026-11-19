# harness 评分卡 · 2026-11-19

> 草稿：由 `make scorecard`（`tools/scorecard.py --generate`）生成；「自评」与「独立复评」两列需人工填写，生成器只提供门禁快照，不自动打分。
> **自评不是认证**；「独立复评」列为 TBD 时，本评分卡不算完成证据。
> 每次大改后重新生成；`make check` 会对过期评分卡给出 WARN（不阻断）。

- checkedAt: 2026-11-19T05:32:57Z
- commit: 83e35b3
- kitVersion: 0.5.5
- evidence: unit-tests-pass=20261119T052625Z-unit-tests-pass（PASS）；ui-tests-pass=20261119T052843Z-ui-tests-pass（PASS）；ui-device-tests-pass=（无证据）（UNVERIFIED）；device-tests-pass=（无证据）（UNVERIFIED）；docs-pass=20261116T055240Z-docs-pass（PASS）
- 测试基线：floor=144 expectedSkipped=0（harness/test-baseline.json）
- 文档计数：17 篇（docs/ + references/ + rootDocs 中现有文件）

## 1. 门禁快照（自动）

| 命令 | exit | 关键输出 |
| --- | --- | --- |
| `python3 tools/check_docs.py` | 0 | [OK] 相对链接：175 条全部存在；[OK] 代码围栏：66 篇文档成对；[OK] docs 索引：docs/README.md 已登记 16 个目标；[OK] 公开文档：根目录 md 白名单 6 项，公开文档 10 篇（上限 10）；[OK] token 预算：AGENTS.md ≈1620/1650（余 30） |
| `python3 tools/check_agents.py` | 0 | [OK] 指令文件：7 个存在（nestedMaxBytes=8192, nestedMaxTokens=2000）；[OK] 嵌套指令 token：docs/AGENTS.md ≈805/2000（余 1195）；[OK] 嵌套指令 token：harness/AGENTS.md ≈640/2000（余 1360）；[OK] 嵌套指令 token：Duiyi/Services/AGENTS.md ≈1090/2000（余 910）；[OK] 嵌套指令 token：Duiyi/Features/AGENTS.md ≈894/2000（余 1106） |
| `python3 tools/check_plan.py check --lenient-uncommitted` | 0 | [OK]  harness/plans/2026-11-18-ai-delivery-phase2.md  status=active；[WARN] 证据位于 _archive（归档历史，不参与当前判定）：20261119T042907Z-unit-tests-pass；[WARN] 证据位于 _archive（归档历史，不参与当前判定）：20261119T043007Z-ui-tests-pass；[WARN] 证据位于 _archive（归档历史，不参与当前判定）：20261119T051131Z-unit-tests-pass；[WARN] 证据位于 _archive（归档历史，不参与当前判定）：20261119T042907Z-unit-tests-pass |
| `python3 tools/check_hygiene.py` | 0 | [SKIP] 未配置 hygiene（harness/config.json），跳过宿主卫生检查 |
| `python3 tools/check_layers.py` | 0 | [SKIP] 未配置 layers（harness/config.json），跳过分层检查 |
| `python3 tools/verify_claim.py --all` | 0 | CLAIM 20261119T051131Z-unit-tests-pass: SUPERSEDED — 已被 20261119T052625Z-unit-tests-pass 取代；CLAIM 20261119T051240Z-ui-tests-pass: SUPERSEDED — 已被 20261119T052843Z-ui-tests-pass 取代；结论：PASS（3 PASS / 0 FAIL / 0 UNVERIFIED） |

## 2. 五子系统评分（自评 / 独立复评）

| 子系统 | 关注点 | 自评（1–5） | 独立复评（1–5） | 证据 |
| --- | --- | --- | --- | --- |
| Instructions | 根 / 嵌套指令、预算、引用可解析 | TBD | TBD | make check / check_agents |
| State | 计划状态机、handoff、唯一 active、证据绑定 | TBD | TBD | check_plan / verify_claim |
| Verification | 静态 / 动态门禁、证据三值、skip 白名单 | TBD | TBD | 门禁快照 / verify_claim |
| Scope | 改动范围声明、越界拦截、DoD | TBD | TBD | check_plan / scope.allow |
| Session Lifecycle | 冷启动、健康检查、收尾与交接 | TBD | TBD | make status / handoff |

## 3. 未验证 / 待人工

- 五子系统分数为 TBD：需人工按 1–5 口径（1 缺失 / 3 有规则不可机检 / 5 有门禁+证据+定期复核）自评；
- 自评不是认证；独立复评列为 TBD 时本卡不算完成证据（release 门禁可另行强制）。
- 独立复评需由未参与实现的人/Agent 只读仓库后填写；自评与独立复评分列，不互相替代。
- 门禁快照只证明「命令跑了、退出码如此」，不证明行为正确；动态/真机/性能仍需项目自己的证据。

## 4. 复现

```bash
make scorecard          # 重新生成本文件
make verify-static      # 静态门禁
make selftest           # 负向注入自检（证明门禁会红）
make verify-claim       # 证据三值判定
```

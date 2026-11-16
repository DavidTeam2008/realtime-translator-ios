# harness 评分卡 · 2026-11-16

> 草稿：由 `make scorecard`（`tools/scorecard.py --generate`）生成；「自评」与「独立复评」两列需人工填写，生成器只提供门禁快照，不自动打分。
> **自评不是认证**；「独立复评」列为 TBD 时，本评分卡不算完成证据。
> 每次大改后重新生成；`make check` 会对过期评分卡给出 WARN（不阻断）。

- checkedAt: 2026-11-16T05:51:03Z
- commit: 414ae10（dirty 文件 37 个）
- kitVersion: 0.5.3
- evidence: unit-tests-pass=20261109T133618Z-unit-tests-pass（PASS）；ui-tests-pass=20261107T062205Z-ui-tests-pass（PASS）；device-tests-pass=20261109T142307Z-device-tests-pass（PASS）；docs-pass=（无证据）（UNVERIFIED）
- 测试基线：floor=120 expectedSkipped=0（harness/test-baseline.json）
- 文档计数：16 篇（docs/ + references/ + rootDocs 中现有文件）

## 1. 门禁快照（自动）

| 命令 | exit | 关键输出 |
| --- | --- | --- |
| `python3 tools/check_docs.py` | 0 | [OK] 相对链接：157 条全部存在；[OK] 代码围栏：47 篇文档成对；[OK] docs 索引：docs/README.md 已登记 15 个目标；[OK] 公开文档：根目录 md 白名单 6 项，公开文档 9 篇（上限 10）；[OK] token 预算：AGENTS.md ≈1576/1650（余 74） |
| `python3 tools/check_agents.py` | 0 | [OK] 指令文件：7 个存在（nestedMaxBytes=8192, nestedMaxTokens=2000）；[OK] 嵌套指令 token：docs/AGENTS.md ≈805/2000（余 1195）；[OK] 嵌套指令 token：harness/AGENTS.md ≈640/2000（余 1360）；[OK] 嵌套指令 token：Duiyi/Services/AGENTS.md ≈1069/2000（余 931）；[OK] 嵌套指令 token：Duiyi/Features/AGENTS.md ≈894/2000（余 1106） |
| `python3 tools/check_plan.py check --lenient-uncommitted` | 0 | [OK]  harness/plans/2026-11-06-benchmark-opensource.md  status=active；[WARN] [daily-warn] git 有未提交改动但计划未声明：.dsh/skills/handoff/SKILL.md；[WARN] [daily-warn] git 有未提交改动但计划未声明：.dsh/skills/red-team/SKILL.md；[WARN] [daily-warn] git 有未提交改动但计划未声明：.dsh/skills/verify-change/SKILL.md；[WARN] [daily-warn] git 有未提交改动但计划未声明：.githooks/pre-push |
| `python3 tools/check_hygiene.py` | 0 | [SKIP] 未配置 hygiene（harness/config.json），跳过宿主卫生检查 |
| `python3 tools/check_layers.py` | 0 | [SKIP] 未配置 layers（harness/config.json），跳过分层检查 |
| `python3 tools/verify_claim.py --all` | 2 | CLAIM 20261109T142307Z-device-tests-pass: UNVERIFIED — artifact 不存在：~/Library/Developer/MobileBuildMCP/workspaces/realtimeTranslatorOptimize-8df963897d87/result-bundles/test_device_2026-11-09T14-20-15-134Z_pid84104_cbb31087.xcresult；artifact 不存在：~/Library/Developer/MobileBuildMCP/workspaces/realtimeTranslatorOptimize-8df963897d87/result-bundles/test_device_2026-11-09T14-20-15-134Z_pid84104_cbb31087.xcresult（CI 无法复核）；CLAIM docs-pass: UNVERIFIED — 缺少当前证据（config.claims.required）；结论：UNVERIFIED（0 PASS / 0 FAIL / 8 UNVERIFIED） |

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

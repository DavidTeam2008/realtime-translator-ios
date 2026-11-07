# 文档索引

> **唯一文档索引。** 代码、测试与最新证据是事实源；文档解释事实，冲突时以代码/证据为准。
> 新增或迁移文档必须登记到本页，否则 `make check` 失败（`tools/check-docs.py` 机检）。

## 先读哪几篇

| 你的目的 | 阅读顺序 |
| --- | --- |
| 第一次来 / 判断值不值得看 | [`../README.md`](../README.md) → [`../HARNESS.md`](../HARNESS.md) |
| 跑起来 / 配环境 / 签名 | [`../CONTRIBUTING.md`](../CONTRIBUTING.md) → [`../references/verification.md`](../references/verification.md) |
| 理解产品与架构 | [`01-product-design.md`](01-product-design.md) → [`02-architecture.md`](02-architecture.md) |
| 改语音/翻译/音频/持久化 | [`02-architecture.md`](02-architecture.md) → [`../references/contracts.md`](../references/contracts.md) |
| 查问题、排期与验收 | [`04-roadmap.md`](04-roadmap.md)（唯一排期源） |
| 查决策 | [`decisions.md`](decisions.md)（唯一决策源） |
| 查启动性能结论 | [`case-startup-performance.md`](case-startup-performance.md)（负结果完整案例） |
| AI Agent 接手 | [`../AGENTS.md`](../AGENTS.md) → [`../HARNESS.md`](../HARNESS.md) → active 计划（`harness/plans/`） |

## 当前规范（现行）

| 文档 | 内容 |
| --- | --- |
| [`01-product-design.md`](01-product-design.md) | 三模块行为、任务生命周期、引导/设置、总结/导出、视觉与无障碍 |
| [`02-architecture.md`](02-architecture.md) | 分层、依赖、启动、音频/听写/翻译/持久化全链路、并发、测试、风险摘要 |
| [`03-tech-choices.md`](03-tech-choices.md) | 系统框架选型、理由、强制约束、明确不选、权衡与缺口 |
| [`04-roadmap.md`](04-roadmap.md) | P0–P3 问题、代码依据、**验收标准与排期（唯一真源）** |
| [`decisions.md`](decisions.md) | **唯一决策表**：D1–D7 + 2026-11 开源标杆化决策 |

## 参考（Agent 细则）

- [`../references/contracts.md`](../references/contracts.md)：架构契约与铁律细则；
- [`../references/verification.md`](../references/verification.md)：验证矩阵、测试计数、真机坑与性能口径（计数唯一源）；
- [`../references/workflow.md`](../references/workflow.md)：L0/L1/L2、计划、红队与状态归属；
- 项目规则入口：[`../AGENTS.md`](../AGENTS.md)；harness 系统地图：[`../HARNESS.md`](../HARNESS.md)。

## 案例（带证据，非规范）

| 文档 | 内容 |
| --- | --- |
| [`case-startup-performance.md`](case-startup-performance.md) | 启动 200ms 目标证伪：口径区分、真机 A/B、空壳对照、分段归因、排除方向与可复核线索；启动微优化已暂停 |
| [`harness-scorecard.md`](harness-scorecard.md) | 五子系统评分卡：分数、证据、与改造前对比、独立复评记录、评分局限 |

> 早期过程记录（原 `docs/14`–`docs/21`）已蒸馏/删除；原始全文可从 git 历史取回（`git log --diff-filter=D -- docs/`）。

## 档案与工具

| 路径 | 内容 |
| --- | --- |
| [`../harness/`](../harness/) | Agent 工作区：计划、证据、真机脚本；`runs/` 不入库（2026-11 由 APM 目录更名） |
| [`../harness/README.md`](../harness/README.md) | 工作区索引：目录职责、入库规则、与 `docs/` 的边界 |
| [`../harness/evidence/`](../harness/evidence/README.md) | 可复核证据 schema/模板/摘要；`make evidence`、`make verify-claim` |
| [`../harness/plans/`](../harness/plans/) | 跨会话计划；active 唯一，done 归档 |
| [`AGENTS.md`](AGENTS.md) | `docs/` 目录级写作规则（当前规范 / 历史 / 新增与索引 / 验证） |
| [`../tools/check-docs.py`](../tools/check-docs.py) | 文档链接/围栏/索引/token 预算/公开文档白名单 |
| [`../Makefile`](../Makefile) | 测试、构建、真机、门禁、计划、证据命令入口 |
| [`../harness-kit/`](../harness-kit/README.md) | 与项目无关的 harness 模板：minimal/standard/strict、`harness-init` 脚手架、端到端验收（`make kit-check`）；独立仓 <https://github.com/DavidTeam2008/harness-kit> |
| [`../.dsh/skills/`](../.dsh/skills/) | 6 个项目级 Agent skills（按需加载的动作卡） |

## 维护约定

- 一个事实只在一个真源维护；其他位置只引用（链接或 ID），不复制。
- 测试计数只在 [`../references/verification.md`](../references/verification.md)；决策只在 [`decisions.md`](decisions.md)；排期只在 [`04-roadmap.md`](04-roadmap.md)。
- 过程/历史文档只进 `harness/` 档案区；`docs/` 不新增过程记录。已完成修复写"发现 → 红测 → 修复 → 绿测 → follow-up"。
- 新规则/工具/门禁要同时登记到本页与对应 `make check-*` 入口。
- 文档里的行号/数字漂移时顺手修正；未验证的推断标注"待验证"。

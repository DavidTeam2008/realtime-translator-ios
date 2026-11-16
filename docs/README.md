# 文档索引

> **唯一文档索引。** 代码、测试与最新证据是事实源；文档解释事实，冲突以代码/证据为准。
> 新增或迁移文档必须登记本页，否则 `make check` 失败（`tools/check_docs.py` 机检）。

## 先读哪几篇

| 目的 | 阅读顺序 |
| --- | --- |
| 第一次来 | [`../README.md`](../README.md) → [`../HARNESS.md`](../HARNESS.md) |
| 跑起来 / 配环境 / 签名 | [`../CONTRIBUTING.md`](../CONTRIBUTING.md) → [`../references/verification.md`](../references/verification.md) |
| 理解产品与架构 | [`01-product-design.md`](01-product-design.md) → [`02-architecture.md`](02-architecture.md) |
| 改语音/翻译/音频/持久化 | [`02-architecture.md`](02-architecture.md) → [`../references/contracts.md`](../references/contracts.md) |
| 查问题、排期与验收 | [`04-roadmap.md`](04-roadmap.md)（唯一排期源） |
| 查决策 | [`decisions.md`](decisions.md)（唯一决策源） |
| 查启动性能结论 | [`case-startup-performance.md`](case-startup-performance.md)（负结果案例） |
| AI Agent 接手 | [`../AGENTS.md`](../AGENTS.md) → [`../HARNESS.md`](../HARNESS.md) → active 计划 |

## 当前规范（现行）

| 文档 | 内容 |
| --- | --- |
| [`01-product-design.md`](01-product-design.md) | 三模块行为、任务生命周期、引导/设置、总结/导出、视觉与无障碍 |
| [`02-architecture.md`](02-architecture.md) | 分层、依赖、启动、音频/听写/翻译/持久化链路、并发、测试、风险摘要 |
| [`03-tech-choices.md`](03-tech-choices.md) | 框架选型、理由、强制约束、明确不选、权衡与缺口 |
| [`04-roadmap.md`](04-roadmap.md) | P0–P3 问题、代码依据、**验收标准与排期（唯一真源）** |
| [`decisions.md`](decisions.md) | **唯一决策表**：D1–D7 + 2026-11 开源标杆化决策 |
| [`harness-scorecard.md`](harness-scorecard.md) | 五子系统评分口径与固定入口；生成物在 `../harness/reviews/` |

## 参考（Agent 细则）

- [`../references/contracts.md`](../references/contracts.md)：架构契约与铁律细则；
- [`../references/verification.md`](../references/verification.md)：验证矩阵、测试计数、真机坑与性能口径（计数唯一源）；
- [`../references/workflow.md`](../references/workflow.md)：L0/L1/L2、计划、红队与状态归属；
- 规则入口 [`../AGENTS.md`](../AGENTS.md)；harness 系统地图 [`../HARNESS.md`](../HARNESS.md)。

## 案例（带证据，非规范）

| 文档 | 内容 |
| --- | --- |
| [`case-startup-performance.md`](case-startup-performance.md) | 启动 200ms 目标证伪：口径区分、真机 A/B、空壳对照、分段归因与可复核线索；启动微优化已暂停 |

## 文档目录规则

- 只放「现行规范」与「带证据案例」；过程记录进 `../harness/reviews/`，历史快照进 `../harness/plans/_archive/`。
- 目录级规则见 [`AGENTS.md`](AGENTS.md)；公开文档白名单与数量上限见 `../harness/config.json`（`docs.publicWhitelist`）。

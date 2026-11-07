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
| AI Agent 接手 | [`../AGENTS.md`](../AGENTS.md) → [`../HARNESS.md`](../HARNESS.md) → active 计划（`.apm/plans/`） |

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

## 历史记录（只读，勿作为当前规范）

以下文档是带日期的过程记录，结论可能仍有效，但数字/行号按当时口径；不重写历史，只做链接维护。第二批文档治理会将其蒸馏后归档。

| 文档 | 内容 |
| --- | --- |
| [`14-device-test-iphone13.md`](14-device-test-iphone13.md) | 真机安装、Instruments/XCUITest 性能、英→中抽测 |
| [`15-startup-optimization.md`](15-startup-optimization.md) | 启动优化方案与二进制重排（收益已被实测推翻） |
| [`16-startup-measurement-verification.md`](16-startup-measurement-verification.md) | 真机 A/B：无显著差异；模拟器结论不能用 |
| [`17-startup-optimization-paused.md`](17-startup-optimization-paused.md) | 暂停决定与已排除方向（当前结论：不再投入） |
| [`18-startup-feasibility-verification.md`](18-startup-feasibility-verification.md) | 200ms 目标不可达证明（control p50=210ms） |
| [`19-ended-translation-persistence-fix.md`](19-ended-translation-persistence-fix.md) | 已结束任务译文回填修复（已合入） |
| [`20-ui-test-hittable-fix.md`](20-ui-test-hittable-fix.md) | UI 测试不可点击/权限/模拟器能力/真机预热闭环（已合入） |
| [`21-cross-session-handoff.md`](21-cross-session-handoff.md) | 跨会话计划与交接 SOP（与 skills/计划重复，待归档） |

## 档案与工具

| 路径 | 内容 |
| --- | --- |
| [`../.apm/`](../.apm/) | Agent 工作区：计划、证据、审查、真机脚本；`runs/` 不入库（第二批将更名为 `harness/`） |
| [`../.apm/evidence/`](../.apm/evidence/README.md) | 可复核证据 schema/模板/摘要；`make evidence`、`make verify-claim` |
| [`../.apm/plans/`](../.apm/plans/) | 跨会话计划；active 唯一，done 归档 |
| [`AGENTS.md`](AGENTS.md) | `docs/` 目录级写作规则（当前规范 / 历史 / 新增与索引 / 验证） |
| [`../tools/check-docs.py`](../tools/check-docs.py) | 文档链接/围栏/索引/token 预算/公开文档白名单 |
| [`../Makefile`](../Makefile) | 测试、构建、真机、门禁、计划、证据命令入口 |
| [`../.dsh/skills/`](../.dsh/skills/) | 6 个项目级 Agent skills（按需加载的动作卡） |

## 维护约定

- 一个事实只在一个真源维护；其他位置只引用（链接或 ID），不复制。
- 测试计数只在 [`../references/verification.md`](../references/verification.md)；决策只在 [`decisions.md`](decisions.md)；排期只在 [`04-roadmap.md`](04-roadmap.md)。
- 过程/历史文档只进 `.apm/` 档案区；`docs/` 不新增过程记录。已完成修复写"发现 → 红测 → 修复 → 绿测 → follow-up"。
- 新规则/工具/门禁要同时登记到本页与对应 `make check-*` 入口。
- 文档里的行号/数字漂移时顺手修正；未验证的推断标注"待验证"。

# 文档索引

> **代码是事实来源。** 文档与代码/测试冲突时，以代码和最新验证为准。
> 2026-11-02 完成一次合并：当前文档只保留 01–04；05–13 已退休（内容并入 01–04，git 历史可追溯）。

## 先读哪几篇

| 你的目的 | 阅读顺序 |
| --- | --- |
| 刚接手项目 | [`../HANDOFF.md`](../HANDOFF.md) → 本页 → [`02`](02-architecture.md) → [`04`](04-roadmap.md) |
| 了解产品行为 | [`01`](01-product-design.md) |
| 改语音/翻译链路 | [`02`](02-architecture.md) §3–§6 → [`03`](03-tech-choices.md) §2–§5 → [`04`](04-roadmap.md) |
| 跑真机/补 UI 测试 | [`../HANDOFF.md`](../HANDOFF.md) §3 → [`20`](20-ui-test-hittable-fix.md) → [`../references/verification.md`](../references/verification.md) |
| 跨会话任务 / 换 Agent | [`21`](21-cross-session-handoff.md)：谁维护、四个动作、命令与示例 |
| 做启动/性能 | [`17`](17-startup-optimization-paused.md) → [`18`](18-startup-feasibility-verification.md) → [`16`](16-startup-measurement-verification.md)；**先看结论，方向已暂停** |

## 当前文档（01–04）

| 文档 | 内容 | 维护要求 |
| --- | --- | --- |
| [`01-product-design.md`](01-product-design.md) | 三模块行为、任务生命周期、引导/设置、总结/导出、视觉与无障碍 | 产品行为变化时同步 |
| [`02-architecture.md`](02-architecture.md) | 分层、依赖、启动、音频/听写/翻译/持久化全链路、并发、测试、风险摘要 | 改数据链路或依赖时同步 |
| [`03-tech-choices.md`](03-tech-choices.md) | 系统框架选型、理由、强制约束、明确不选、权衡与缺口 | 换框架/API 或推翻决策时同步 |
| [`04-roadmap.md`](04-roadmap.md) | 当前 P0–P3 问题、代码依据、**验收标准与排期（唯一真源）**；待确认决策见 HANDOFF §6 D1–D7 | 问题状态变化时更新；完成后移入“已完成” |

## 历史与证据（14–21）

这些是**带日期的记录**，不是当前规范；结论仍有效，但数字/行号按当时口径。

| 文档 | 内容 | 状态 |
| --- | --- | --- |
| [`14-device-test-iphone13.md`](14-device-test-iphone13.md) | iPhone 13 真机安装、Instruments/XCUITest 性能、英→中抽测 | 历史报告；工具限制仍有效 |
| [`15-startup-optimization.md`](15-startup-optimization.md) | 启动优化方案与二进制重排 | 历史；开头有“收益被实测推翻”订正 |
| [`16-startup-measurement-verification.md`](16-startup-measurement-verification.md) | 真机 A/B：280ms→279ms，p=0.605 | 历史证据 |
| [`17-startup-optimization-paused.md`](17-startup-optimization-paused.md) | 暂停决定与已排除方向 | 当前结论：不再投入 |
| [`18-startup-feasibility-verification.md`](18-startup-feasibility-verification.md) | 200ms 目标不可达证明（control p50=210ms） | 当前结论 |
| [`19-ended-translation-persistence-fix.md`](19-ended-translation-persistence-fix.md) | 已结束任务译文回填修复 | 已合入；含导出 follow-up |
| [`20-ui-test-hittable-fix.md`](20-ui-test-hittable-fix.md) | UI 测试不可点击、权限、模拟器能力、真机预热 | 已合入；真机入口说明仍有效 |
| [`21-cross-session-handoff.md`](21-cross-session-handoff.md) | 跨会话计划与交接的人读 SOP | 当前流程 |

## Agent 规则

人读入口是 [`../HANDOFF.md`](../HANDOFF.md)；`AGENTS.md` 是 Agent 冷启动入口。
**真源优先级只在本页维护**：代码与测试 > `docs/01`–`04` > `HANDOFF.md` > `references/`（规则视图）> 历史文档。
唯一决策表是 [`HANDOFF.md` §6 的 D1–D7](../HANDOFF.md)，其他文件只引用编号。

门禁：`make check` = 文档（`check-docs`）+ 架构铁律（`check-arch`）+ 测试计数（`check-tests`）+ 指令层（`check-harness`）+ 计划状态（`check-plan`）；`make verify-static` 在 `check` 之上再加证据 schema 校验（`check-evidence`）、harness 脚本单测（`test-tools`）与脚本语法。证据与三值判定见 [`HARNESS.md`](../HARNESS.md) §5。
规则层 token 预算（`tools/token_estimate.py` 口径：CJK 汉字 / CJK 标点 / 全角字符各按 1 token，其余按 4 字符/token）：`AGENTS.md` ≤1600；每个 `references/*.md` ≤950；超预算先删重复，不删有效规则。

| 文件 | 用途 |
| --- | --- |
| [`../AGENTS.md`](../AGENTS.md) | Agent 冷启动入口：铁律、命令、验证矩阵、项目级覆盖 |
| [`../HARNESS.md`](../HARNESS.md) | harness 系统地图：guides/sensors 矩阵、运行手册、证据政策、月度审计、DSH 用户级配置建议 |
| [`AGENTS.md`](AGENTS.md) | `docs/` 目录级规则：01–04 当前规范 / 14–21 历史、登记与真源优先级 |
| [`../references/contracts.md`](../references/contracts.md) | 架构契约与铁律细则 |
| [`../references/verification.md`](../references/verification.md) | 测试 / 真机 / 性能验证矩阵 |
| [`../references/workflow.md`](../references/workflow.md) | L0/L1/L2、长任务、红队 |
| [`../tools/check-docs.py`](../tools/check-docs.py) | 文档链接 / 围栏 / 索引 / token 预算；`make check-docs` |
| [`../tools/check-arch.py`](../tools/check-arch.py) | 架构铁律 R1–R6 静态扫描；`make check-arch` |
| [`../tools/check-test-baseline.py`](../tools/check-test-baseline.py) | 测试计数 / skip 白名单门禁（基线 `.apm/test-baseline.json`）；`make check-tests` |
| [`../tools/check-harness.py`](../tools/check-harness.py) | 指令层机检：预算 / § 引用 / 嵌套 AGENTS / skills / 敏感路径；`make check-harness` |
| [`../tools/plan.py`](../tools/plan.py) | 跨会话计划：新建 / 最新 / 交接摘要 / check / resume / end；`make plan` / `handoff` / `resume` / `end` |
| [`../tools/doctor.py`](../tools/doctor.py) | 环境检查：Xcode / 模拟器 runtime / 真机工具 / 模板仓；`make doctor` |
| [`../tools/evidence.py`](../tools/evidence.py) | 证据读写：`ls` / `show` / `validate` / `write`；`make evidence` |
| [`../tools/verify-claim.py`](../tools/verify-claim.py) | 完成声明三值判定 PASS / FAIL / UNVERIFIED；`make verify-claim` |
| [`../.github/workflows/verify.yml`](../.github/workflows/verify.yml) | CI：ubuntu 静态门禁 + 可选 self-hosted macOS 单测（`MACOS_CI_ENABLED=true`） |
| [`../.githooks/pre-push`](../.githooks/pre-push) | push 前跑 `make verify-static`；`make hooks-install` 安装 |
| [`../Makefile`](../Makefile) | 测试 / 构建 / 真机 / 门禁 / 计划 / 证据命令入口 |

## 原型与图

- 可交互原型：[`../prototype/index.html`](../prototype/index.html)、[`simultaneous.html`](../prototype/simultaneous.html)、[`platform.html`](../prototype/platform.html)。
  均为 2026-08 视觉稿，**只作布局/视觉参考**，与代码冲突时以 [`01`](01-product-design.md) 为准。
- 架构图（2026-08 视觉稿）：[`diagrams/system-architecture.svg`](diagrams/system-architecture.svg)、[`data-pipeline.svg`](diagrams/data-pipeline.svg)、[`platform-layers.svg`](diagrams/platform-layers.svg)、[`platform-modules.svg`](diagrams/platform-modules.svg)、[`screen-layout.svg`](diagrams/screen-layout.svg)、[`si-pipeline.svg`](diagrams/si-pipeline.svg)、[`si-system.svg`](diagrams/si-system.svg)。只表达分层与链路概念，类型名/细节可能滞后，**以 [`02`](02-architecture.md) 为准**。

## 证据与工具（`.apm/`）

`.apm/` 不是运行时依赖，是**计划 / 证据 / 审查 / 工具的唯一工作区**（项目自定的 Agent 工作区，目录名沿用早期启动性能测量演练）；原始产物不入库，入库的只有摘要与结论。

| 路径 | 内容 |
| --- | --- |
| [`.apm/AGENTS.md`](../.apm/AGENTS.md) | `.apm/` 目录级协议：计划状态机、验证证据四列、红队/审查输入输出 |
| [`.apm/evidence/`](../.apm/evidence/README.md) | 可复核证据：schema / 模板 / 摘要 JSON；`make evidence`；无 evidence id 即未验证 |
| `.apm/tools/device-test.sh` | 真机测试唯一入口：先预热 `testmanagerd`，再跑单元/UI；成功自动写证据 |
| `.apm/tools/measure-launch.sh` | 真机冷启动测量：固定命令、warmup、分层口径；完成写证据摘要 |
| `.apm/baseline/README.md` | 哪个 baseline 可用、哪个已作废 |
| `.apm/issues/` | 问题单（根因、证据、修复状态） |
| [`.apm/plans/`](../.apm/plans/) | 跨会话任务执行计划；front matter `status`、同一时间一个 active、done 移入 `_archive/` |
| `.apm/reviews/` | 独立审查报告；结论与作者回应写入对应计划 |
| `.apm/runs/` | 历次测量原始数据（gitignore，可由脚本重建） |
| `.apm/report.md` | 启动 200ms 演练的完整复盘（历史，已被 17/18 结论取代） |
| [`HARNESS.md`](../HARNESS.md)（仓库根） | harness 系统地图：guides/sensors、运行手册、证据政策、审计清单、DSH 用户级配置建议 |
| [`.dsh/skills/`](../.dsh/skills/) | 6 个项目级 skills（DSH 原生；其他 agent 工具可当动作卡读，不保证自动加载） |

## 维护约定

- 当前规范只维护 01–04；新事实优先补进对应文档，不再恢复 05–13 的编号。
- 已完成的修复写“发现 → 红测 → 修复 → 绿测 → 未混入本次的 follow-up”。
- 性能结论必须写清口径（设备、构建、样本量、起止点），否则视为无效。
- 未验证的推断要标注“待验证”，不要把设计意图写成已实现事实。
- 新增 `docs/*.md` 必须登记到本页，否则 `make check` 失败；新增工具/门禁要同时登记上方表并配 `make check-*` 入口。

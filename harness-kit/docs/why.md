# 为什么是「项目管理工具」，而不是又一个脚手架

> 本文回答三个问题：它到底是什么、为什么不用单个 Agent（如 Claude Code）自己管、它凭什么值得存在。
> 事实源：`README.md`（能力）、`SPEC.md`（内部契约）、`docs/adoption.md`（接入）、`docs/playbook.md`（操作）。

## 1. 定位

**harness-kit 是给 AI Coding Agent 用的 Harness Engineering 项目管理工具（项目治理层）**：
把 Instructions / State / Verification / Scope / Session Lifecycle 五子系统落成仓库里的规则、状态与门禁，并提供 Agent 可自助执行的统一入口（`tools/harness.py`、kit 侧升级工具）。

- 脚手架只是它的**接入方式**，不是产品身份；
- 它不调度 Agent、不替代 Agent，解决的是"**多个 Agent / 模型 / 人怎么在同一个项目上接力、分工、互相信得过**"。

## 2. 现实问题

典型场景：复杂项目按模型能力分层——

- 架构、技术攻关、Code Review 用 Claude Code + 强推理模型；
- 日常开发用 DeepSeek Harness + 高吞吐/成本更优的模型；
- 项目周期长、交接多、发布需要可追溯。

问题不在"Agent 会不会写代码"，而在：

1. 两个 Agent 的会话各活各的：做到哪、谁验证过、下一步给谁，全靠人转述；
2. "完成/已验证"是自述，仓库里没有可复核记录；
3. 换 Agent / 换模型 / 换人就要重新解释一遍上下文；
4. 多 Agent 同时改，写作用域与合并顺序没有协议。

## 3. 为什么不用单个 Agent 自己管

Claude Code（或任何单个 Agent）是**执行面**，不是**跨厂商项目控制面**：

| 维度 | 单个 Agent 原生（以 Claude Code 为例） | harness-kit |
| --- | --- | --- |
| 会话恢复 / fork | 本机会话状态，不跨机器、不跨厂商 | 项目状态是仓库文件，任意 Agent 可读 |
| 规则 / 记忆 | CLAUDE.md / AGENTS.md + 本机 memory | AGENTS 单源 + 预算/引用门禁 + 嵌套路由 |
| 完成判定 | 模型自述 + LLM review | 证据三值 + clean tree + commit 绑定 + 可重算 artifact（v0.2.12 起） |
| 生命周期 | 会话级 resume/fork/compact | 项目级：接入/需求验收/计划/发布/交接/归档 |
| 多 Agent | 同一运行时的 subagents/worktrees | 跨运行时/跨厂商的写作用域与交接协议（v0.4.x 规划） |
| 锁定与退出 | 绑定厂商生态 | 模型无关；kit 产物可整体退出，不成为运行时依赖 |

一句话：**Agent 让模型更能干；kit 让 Agent 的成果可接手、可复核、可跨厂商复用。**
两者是"执行器 vs 治理层"的关系，不是竞品——你仍然用最顺手的 Agent 写代码，kit 负责让交接和完成声明可信。

## 4. 它凭什么值得存在（卖点，按成熟度诚实标注）

| # | 价值 | 现状 |
| --- | --- | --- |
| M1 | **跨 Agent / 模型的可移植项目状态** | 已有机制（计划/证据/handoff/统一入口）；无 active 时回读归档计划（v0.4）；跨厂商交接实测在 v0.4.x |
| M2 | **完成声明强制可复核** | 证据三值 + commit 祖先/clean tree + JUnit XML 独立重算（v0.2.12）；v0.4 追加证据/artifact 入库、必需 claim、归档接管、submitted scope 审计；不承诺防伪造，只提高说谎成本 |
| M3 | **多 Agent 分层协作协议** | 当前串行接力 + 角色/评审留痕；并发门禁在 v0.3.2，未交付前不夸大 |
| M4 | **项目生命周期状态机** | 接入 → 需求验收 → 计划 → 实现 → 验证 → 评审 → 发布 → 交接 → 归档；done 未验证项需清零/豁免，归档可回读（v0.4） |
| M5 | **反臃肿：不拖累模型** | 计算型优先、指令预算、渐进披露、删除优先、可退出；kit 自身也有测试与审计 |
| M6 | **自进化** | 版本 manifest + 只读升级检查 + 门禁自测 + 评分卡（v0.4）；行为级 A/B 在 v0.4.x/v0.5 |

**不是卖点**：一键脚手架（可被复制）；"模型会更强"（未做 A/B，不声称）。

## 5. 边界（不做什么）

- 不做 Agent 编排运行时（DSH Agent Teams、Claude Code subagents 已做得更好）；
- 不替代产品管理（PRD/优先级在外部工具；kit 从"可验收"开始，用 `harness intake` 接收需求卡）；
- 不做权限 / 工单 / 审批系统（在 Git/CI/团队系统）；
- 不覆盖线上运维 / 监控 / SLO；
- 不成为运行时依赖，不 import 进业务代码。
- **不做 DSH 插件（v0.5.0 决策）**：DSH 已原生发现 `.dsh/skills`、`.agents/skills`、`~/.agents/skills` 等 skill 根，入口 skill 用 `harness-skill --scope user` 一次安装即可覆盖发现与分发；插件只增加安装/版本维护面，不改善门禁与证据。复访条件：需要跨项目自动更新、或需要工具级/MCP 集成。

## 6. 什么时候不该用

- 一次性脚本、没有测试也不打算长期维护的仓库；
- 单 Agent / 单模型 / 短周期 / 无交接、无发布审计的个人项目（CLAUDE.md + 简单 Makefile 足够）；
- 无法产出机读测试结果、无 git、无任何 CI 且不愿维护证据的项目；
- 想要"自动写代码"、不想要任何过程约束的项目。

## 7. 当前版本 vs 路线图

- **已交付**（v0.4.0）：五子系统模板/门禁、证据可复核（含伪造回归）、manifest 升级基线、只读升级检查、统一入口 `tools/harness.py`、router skill（显式安装，默认不启用）、真实存量仓反馈收口（submitted scope/归档回读/证据入库/JUnit 脱敏/claim 环境/scorecard/selftest 目标）。
- **已交付**（v0.5.0 / v0.5.1）：入口 skill 优先（`--scope user` 一次安装 `~/.agents/skills` + `~/.claude/skills`、任意仓库会话可见；`--scope project` 供团队 pin 版本；`uninstall`/漂移检查）、提示词降级为兜底、skill 自足 adopt 流程；门禁/`tools/`/config 无行为变更。
- **路线图**：v0.5.x 行为级 A/B（skill vs 提示词，衡量人工操作数与协议遵守）；v0.4.x 跨 Agent 真实交接演练 + 多 Agent 并发门禁（顺延）。DSH 插件明确不做（见 §5）。
- **不承诺**：接入后模型表现提升 X%；多 Agent 并发已受门禁保护；绝对防伪造。
- **不承诺**：接入后模型表现提升 X%；多 Agent 并发已受门禁保护；绝对防伪造。

## 8. 对外话术

- 10 秒：**Agent 换、模型换，项目不散；完成不是自述，要有可复核证据。**
- 30 秒：Claude Code 做设计、DeepSeek Harness 做日常开发——两边读写同一份仓库状态，谁接手都能继续；任何"完成"都要留有可复核记录，拿不出证据就是未验证。

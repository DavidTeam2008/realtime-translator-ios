> 冻结副本：来源 `harness/runs/kit-eval/research-ecosystem.md`（2026-11-11）；原始命令输出仍在 gitignored 的 `harness/runs/kit-eval/`。
> 本文件为提案/评审冻结稿，实施记录见 `harness/plans/2026-11-06-benchmark-opensource.md` 与 `harness-kit/CHANGELOG.md`。

# 生态研究：Agent Skills / Claude Code / 竞品 —— 对 harness-kit 封装与卖点的含义

> 研究日期：2026-11-11（抓取时点）。工作区：Duiyi iOS 仓（内含 `harness-kit/` v0.2.11）。方法：web_search + web_fetch/raw curl + GitHub API；本地只读查看 kit。
> 置信度：**高**=官方文档/一手仓库原文；**中**=二手报道/README 自述/可推导；**低**=仅搜索摘要或站点被拦截；**未证实**=没找到证据，明确不当作事实。
> 说明：Claude Code 文档页无发布日期，统一按 2026-11-11 抓取；页面内容提及 Claude Code v2.1.3xx。

## A. Claude Code 现状（2026-11）

### A1. Agent Skills：格式、触发、多 skill、与旧命令/插件的关系

| claim | 来源 | 日期 | conf |
|---|---|---|---|
| skill = 目录内 `SKILL.md`（YAML frontmatter + Markdown），可带 `scripts/references/assets`；Claude Code skill 遵循 Agent Skills 开放标准并做扩展（invocation control、fork 执行、动态上下文注入） | code.claude.com/docs/en/skills.md | 2026-11-11 | 高 |
| 位置：企业 / 个人 `~/.claude/skills` / 项目 `.claude/skills` / 嵌套子目录（按需加载）/ `--add-dir` 目录 / 插件 `<plugin>/skills` / claude.ai 同步；嵌套与同名有优先级规则 | 同上 | 同上 | 高 |
| frontmatter：标准字段 `name`、`description` 必填（标准里 name/description 必填、name 须匹配目录名）；Claude Code 另有 `when_to_use`、`argument-hint`、`arguments`、`disable-model-invocation`、`user-invocable`、`allowed-tools`、`disallowed-tools`、`model`、`effort`、`context: fork`、`agent`、`background`、`hooks`、`paths`、`shell`、`metadata`、`license`、`compatibility`（后两者仅接受不执行） | skills.md；agentskills docs/specification.mdx | 同上 | 高 |
| 触发：启动时把每个 skill 的 name+description 预载入上下文（渐进披露第 1 层），Claude 按 description 语义决定是否读全文；用户可用 `/skill-name` 直接调用；`paths` 可按文件 glob 限定自动激活 | skills.md；Anthropic 工程博客（渐进披露三阶段） | 同上 | 高 |
| **多 skill**：交互终端一条消息可“堆叠” skill——第一个 + 最多 5 个（共 6），尾随文本作为 `$ARGUMENTS` 传给每个；`claude -p`/Agent SDK 只加载第一个；同为 `/plugin` 插件的 skill 用 `/plugin:skill` 命名 | skills.md（“Stack several skills in one message”） | 同上 | 高 |
| 旧 custom slash commands 已**并入 skills**：`.claude/commands/deploy.md` 与 `.claude/skills/deploy/SKILL.md` 都产生 `/deploy`，旧文件继续可用；skill 额外支持目录资源/frontmatter 控制/自动触发 | skills.md（NOTE） | 同上 | 高 |
| 插件 = 可含 skills/agents/hooks/MCP 的目录 + `.claude-plugin/plugin.json`，由 marketplace 分发，`/plugin` 安装；插件 skill 命名空间为 `/plugin-name:skill-name`；插件启用后其 name+description 每轮都在上下文 | plugins.md | 同上 | 高 |
| 多 skill 的**冲突/优先级**：文档只给同名解析（企业>个人>项目、插件名命名空间、嵌套按目录）和叠加顺序，未定义“多个 skill 同时生效时如何协调/冲突” | skills.md | 同上 | 高（缺失本身是一手事实） |
| **上下文税**：每个可用 skill 的 name+description 每轮都在上下文（描述与 when_to_use 合计截断 1536 字符）；`/skill-doctor` 可查每个 skill 的 token 成本与使用率，从未调用过的会被标出 | skills.md（Find unused skills） | 同上 | 高 |

### A2. 原生能力清单与边界（哪些落仓库、哪些只是会话状态）

| claim | 来源 | 日期 | conf |
|---|---|---|---|
| `/init`：分析仓库生成 CLAUDE.md 起点；已存在则建议改进；`CLAUDE_CODE_NEW_INIT=1` 时为交互多阶段（CLAUDE.md、skills、hooks）；还会吸收 Cursor/Copilot 等旧规则文件 | memory.md | 2026-11-11 | 高 |
| 会话：`--continue`/`--resume`/`/resume`/`--fork-session`/`/branch`；transcript 存本机 `~/.claude/projects/<project>/<session-id>.jsonl`；恢复对话、模型、agent、权限模式、active goal、未过期定时任务；**不恢复**后台 subagent/Bash/workflow 的未完成工作，也需重传 `--mcp-config`/`--settings`/`--plugin-dir`/`--add-dir` | sessions.md | 同上 | 高 |
| 跨会话/跨机器：session 按项目目录存本机；同机可按 ID 跨目录 resume；启用了 cross-session messaging 的会话可向“本机或更远”的会话发消息（子 agent 文档所述）；**本地 session 文件不跨机器同步** | sessions.md；sub-agents.md | 同上 | 高 |
| Subagents：`.claude/agents/*.md` + frontmatter（`description/tools/model/skills/permissionMode/hooks/...`）；独立上下文；可 `isolation: worktree`；后台运行；`SendMessage` 可 resume；同 session 内最多 20 并发（可配）；agent teams 是“多会话团队” | sub-agents.md | 同上 | 高 |
| Subagent 可**预载多个 skill**：frontmatter `skills` 字段把多个 skill 全文预载；这是“一个任务带一整套 skill”的官方机制 | sub-agents.md（Preloaded skills） | 同上 | 高 |
| Hooks：`SessionStart/UserPromptSubmit/PreToolUse/PostToolUse/Stop/SubagentStart/SubagentStop/SessionEnd/PreCompact/...`；可 command/HTTP/MCP-tool/prompt/agent 五类 handler；可 block 或返回 `additionalContext` 注入上下文；定义位置含 `.claude/settings.json`（可入库）、插件、skill frontmatter、subagent frontmatter | hooks.md | 同上 | 高 |
| Workflows：动态 workflow = Claude 写的 JS 脚本编排大量 subagent，后台运行/`/workflows` 查看/可暂停恢复；保存到**仓库** `.claude/workflows/` 或用户目录，成为 `/name` 命令；可随插件分发 | workflows.md | 同上 | 高 |
| Code Review：`/code-review` 本地对分支审查（任意 plan）；托管 Code Review 在 Anthropic 基础设施审 GitHub PR（Team/Enterprise，只读、不阻塞合并） | code-review.md | 同上 | 高 |
| Memory：`CLAUDE.md`/`AGENTS.md`（v2.1.277+ 原生读 AGENTS.md，通过 setting 选 CLAUDE.md 或二者）+ `.claude/rules/`（可 `paths` 限定）+ auto memory（Claude 自己写，存本机 `~/.claude/projects/<project>/memory/`，**不跨机器**） | memory.md | 同上 | 高 |
| Sandbox/权限：Bash sandbox 默认关，OS 级限制（macOS Seatbelt/Linux bubblewrap），限制文件写与网络域；默认工作目录可写；hooks/MCP/文件工具不在 sandbox 内；另有 permission modes / `deny/ask` 规则 | sandboxing.md | 同上 | 高 |
| **落仓库 vs 会话态**：落仓库=`.claude/skills|commands|agents|rules|workflows`、`CLAUDE.md/AGENTS.md`、`.claude/settings.json`、`.claude-plugin/`、hooks 配置；会话态=对话/压缩/权限授权/plan mode/后台任务；用户级=`~/.claude/*`、plugins、auto memory | 上述各页综合 | 同上 | 高 |
| **落仓库 vs 会话态** 总结：能跨会话恢复的只有文件与 transcript；后台任务、临时 flags 不恢复 | sessions.md | 同上 | 高 |

### A3. “Harness” 表述

| claim | 来源 | 日期 | conf |
|---|---|---|---|
| Anthropic 工程文章大量使用“harness”概念：长任务 harness（initializer+coding agent）、harness design（planner/generator/evaluator），并把 Claude Agent SDK 称为 “general-purpose agent harness” | anthropic.com/engineering/effective-harnesses-for-long-running-agents；.../harness-design-long-running-apps | 2026（抓取于 11-11） | 高 |
| Claude Code 官方文档（上述各页）**没有**给出 “Agent = Model + Harness” 这一公式；它用 skills/plugins/hooks/subagents 等具体机制表达同一层含义 | code.claude.com/docs/*（已读页） | 2026-11-11 | **未证实**（公式）/ 高（无公式） |
| “harness” 已成行业通用词：Kiro 文档有 “Choose an agent harness” 页；OpenAI 有 “Harness engineering” 文章（2026-02-11）；DSH 官方定义（二手转述）Agent = Model + Environment + Tools + State | kiro.dev/docs/cli/agent-harness/；openai.com/index/harness-engineering/；DSH breakdown | 各自页面 | 高/中 |
| Anthropic 对 skills 的定位：把 expertise/流程“打包成可组合资源”（capability packaging），以渐进披露（discovery→activation→execution）解决上下文膨胀 | anthropic.com/engineering/equipping-agents...；agentskills README | 同上 | 高 |

## B. Agent Skills 开放标准 / 生态

| claim | 来源 | 日期 | conf |
|---|---|---|---|
| 标准规范：skill=目录+`SKILL.md`；frontmatter 必填 `name`（1–64、小写字母数字连字符、匹配目录名）与 `description`（≤1024）；可选 `license`、`compatibility`、`metadata`、`allowed-tools`（实验） | raw.githubusercontent.com/agentskills/agentskills/main/docs/specification.mdx | 2026-11-11 | 高 |
| 渐进披露三阶段（Discovery 只载 name/description；Activation 读 SKILL.md；Execution 按需读 scripts/references） | agentskills README；同上 | 同上 | 高 |
| 2026-10-22 Anthropic 把 Agent Skills 捐给 Linux Foundation 下的 Agentic AI Foundation（AAIF），含名称/logo/GitHub 组织/agentskills.io 域名；Anthropic、Google、OpenAI 等工程师以个人身份维护；路线图含版本化、正式提案流程、安全指南 | anthropic.com/news/donating-agent-skills-to-the-agentic-ai-foundation；mixed-news.com（报道 “announced on October 22”，10-23） | 2026-10-22 | 高（一手+二手互证） |
| 官方称 70+ agent 平台已集成，含 ChatGPT、Cursor、GitHub Copilot、VS Code；自报 100 万 skill、2.8 亿安装（Anthropic 口径，非独立核实） | 同上 donation 新闻；mixed-news | 2026-10 | 中（数字为厂商口径） |
| 官方 client 列表（仓库 snippets/clients.jsx，摘录）：Claude Code、Claude、ChatGPT & Codex、Cursor、Gemini CLI、GitHub Copilot、VS Code、Kiro、OpenCode、OpenHands、Goose、Junie、Amp、Roo Code、TRAE、Qodo、Factory、pi、Hermes Agent…（共 40+ 条目） | raw.../agentskills/main/docs/snippets/clients.jsx；agentskills.io/clients（列表页） | 2026-11-11 | 高（列表本身）/ 中（70+ 为新闻口径） |
| **DSH 不在** Agent Skills 官方 client 列表中；但 DSH 原生支持 SKILL.md：项目根 `.dsh/skills`（rank 100）、`.agents/skills`（rank 200）、用户级 roots（400/500），支持 `<name>/SKILL.md` 与平铺 `<name>.md`、kebab-case name、`whenToUse`、`disable-model-invocation`/`user-invocable`，catalog 只暴露 name+description、正文按需 `skill({name})` 加载 | raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/docs/subsystems/skills.md；本机 app.asar `dsh-skill-filesystem` README（0.2.1-rc.5） | 同上 | 高（能力）/ **未证实**（是否宣称遵循 agentskills 标准） |
| 可移植性差异：标准只保证 6 个 frontmatter 字段；Claude Code 扩展字段（`disable-model-invocation`、`paths`、`context`、`hooks`、`!` 命令注入等）在标准工具中不可用；反之 claude.ai 上传只接受 6 字段且多字段会硬报错 | skills.md（Using skill frontmatter outside Claude Code） | 同上 | 高 |
| 各 agent 的目录/触发差异：Claude Code `.claude/skills` + 自动触发/`/name`；Kiro `.kiro/skills` + `/name`、workspace 优先 global、custom agent 需 `skill://` 显式引用；DSH `.dsh/skills` + `.agents/skills` + 模型 catalog 自动/用户命令；均对齐 SKILL.md 形态但不保证行为一致 | skills.md；kiro.dev/docs/skills/；DSH skills.md | 同上 | 高 |

## C. 竞品/同类方案（GitHub stars 为 2026-11-11 API 快照）

| 项目 | 定位 | 交付形态 | 跨 agent | 状态/证据管理 | stars / 活跃 | 明显缺口 |
|---|---|---|---|---|---|---|
| **GitHub Spec Kit** | SDD 工具包：specify→plan→tasks→implement→converge，另有 bug/idea 流程 | `uv tool install specify-cli` + 各 agent 的 `/speckit-*` skills；extensions/presets/workflows/bundles | 是（集成多种 agent） | 产物在 `.specify/`；有 converge/verification 步骤，但无 claim 三值验证（README 未提） | 149,224★，pushed 2026-11-10 | 流程重、模板/扩展层复杂；无“完成声明可证伪”的证据 JSON |
| **OpenSpec** | 轻量 spec-driven：`/opsx:explore/propose/apply/archive`，spec delta 为真源 | npm CLI `@fission-ai/openspec` + skills/commands | 是（面向 AI coding assistants） | `openspec/changes|specs` 落仓库；Stores（beta）做跨仓共享 | 74,563★，pushed 2026-11-11 | 无门禁/证据校验；小改动也走流程；stores 尚 beta |
| **BMAD-METHOD** | Agile AI-Driven Development 方法：persona 角色 + 交付循环（clarify/plan/build/learn） | npm 安装器；v6.12 稳定，v7 preview alpha 转 skills | 需支持 skills 的 agent | 产物为 brief/spec/architecture 文档；无证据链 | 55,241★，pushed 2026-11-11 | 角色/流程重，v7 破坏性变更；无机械校验 |
| **Superpowers** | 完整开发方法论（brainstorm→plan→subagent 开发→TDD→review→finish） | 插件（Claude Code/Codex/Cursor/Gemini/Copilot 等 15+ harness），skills 库 | 是（跨 harness 插件） | worktree + subagent-driven + 强制 TDD；无证据 JSON | 315,816★，pushed 2026-11-03 | skill 触发可靠性需自诊断（自带 diagnosing-superpowers）；方法论侵入强 |
| **Kiro（AWS）** | 规格驱动 IDE/CLI/Web：requirements/design/tasks、steering、hooks、Agent Skills、自定义 agent、任务并行波次 | 商业产品（IDE/CLI/Web/Crew） | 产物可带走，但执行绑定 Kiro | `.kiro/specs`+`.kiro/skills`；任务状态内置 | 非 OSS（无 stars） | 厂商锁定；无跨 agent 可执行门禁/证据标准 |
| **Conductor** | 在 Mac 上并行运行多个 coding agent（隔离工作区） | Mac GUI 应用 | 以 agent 配置为准 | 工作区隔离（细节未证实） | 站点 403（Cloudflare） | **低/未证实**：未能读官方文档 |
| **Taskmaster** | AI 任务管理系统（PRD→tasks，多编辑器集成） | CLI/npm + MCP/规则集成 | 是（Cursor 等） | tasks 文件；无门禁/证据 | 28,344★，pushed 2026-04-28 | 近 6 个月未更新；无 harness 层 |
| **Tessl** | agent skills 的包管理器/registry：build/evaluate/distribute/optimize 全生命周期 | 商业 registry/CLI | 以 skills 标准为载体 | 评测/分发层（细节未证实） | 商业产品（无 stars） | 厂商 registry；**低/未证实**定价与深度 |
| （补充）Agent OS | 把代码库标准“注入”给 agent，做更好的 spec | 文件/命令注入 | Claude Code/Cursor/Antigravity | specs/standards 文件 | 5,592★，pushed 2026-10-07 | 门禁弱、生态小 |

## D. 关键判断素材：“多 skill 不能同时用”与跨工作流解法

| claim | 来源 | 日期 | conf |
|---|---|---|---|
| “一个会话只能用/激活一个 skill”的旧说法**在 Claude Code 当前文档下不成立**：catalog 常驻全部 name+desc，可按需加载多个；一条消息最多堆叠 6 个；subagent 可预载多个；插件可捆绑多个 | skills.md；sub-agents.md；plugins.md | 2026-11-11 | 高 |
| 但“同时自动生效并互相协调”**没有官方语义**：自动路由按 description 语义选择，文档未定义多 skill 冲突/顺序/组合协议；堆叠是显式用户行为，非自动编排 | skills.md | 同上 | 高 |
| 跨工作流的业界解法（有一手证据）：① **入口/路由 skill**——Superpowers 用 `using-superpowers` bootstrap（SessionStart 注入）让 agent 先加载方法论入口；Kiro/DSH 用 catalog+按需加载 | superpowers README；kiro.dev/docs/skills；DSH skills.md | 同上 | 高（Superpowers）/中（其他） |
| ② **插件捆绑多 skill**：Claude Code plugin 把 skills/agents/hooks/MCP 作为一单元分发（`/plugin`） | plugins.md | 同上 | 高 |
| ③ **subagent 各自带 skill**：frontmatter `skills` 预载多个全文，隔离上下文执行 | sub-agents.md | 同上 | 高 |
| ④ **hooks 自动注入**：`UserPromptSubmit` 等返回 `additionalContext`，把项目规则/状态注入每次请求 | hooks.md | 同上 | 高 |
| ⑤ **workflow/保存命令**：把编排写成 `.claude/workflows/*.js` 可复用/可恢复 | workflows.md | 同上 | 高 |
| ⑥ DSH 侧：所有 skills 进 catalog，模型按需 `skill({name})` 逐个加载（多次加载累积在历史中）；无“堆叠/多选”语法，多 skill 协作需靠提示/编排（推断） | DSH skills.md；本机 app.asar | 同上 | 中（推断） |

## E. 与 kit 相关的影响（供封装决策）

- **核心资产可跨 agent 复用的是 AGENTS.md 指令树 + 确定性门禁脚本**；Agent Skills 是最佳“第二分发格式”，但标准只保证 name/description 等 6 字段，kit 生成的 skill 应只依赖标准字段。
- **竞品矩阵里没有人把“可执行门禁 + 证据三值判定 + 负向注入”做成主打**（Spec Kit/OpenSpec/BMAD 是流程与产物，Superpowers 是方法论）→ kit 的差异化卖点应选“完成声明可被机械否证”，而不是“又一个 SDD 流程”。
- **“多 skill 不能同时用”不应再作为 kit 的立论**：正确立论是“skill 是渐进披露的指令包，不是编排系统；跨工作流需要 router/plugin/subagent/hooks 组合”，kit 可提供“入口 skill + 子动作 skills + 确定性门禁 hooks”的分层包。
- **DSH 插件化**：DSH 原生 skill 宿主（`.dsh/skills` rank 100 / `.agents/skills` rank 200）且事件管线可挂 hook；kit 作为 DSH 插件应封装“门禁工具 + skills 包”，但 profile 安装是用户级动作（仓库内只能放 `.dsh/skills`），需双轨分发。
- **kit 当前适配层偏薄**：`harness-kit/adapters/manifest.json` 中 claude-code 只给 CLAUDE.md/hooks 示例/red-team agent；`dsh` 适配为空（预留）→ 封装 Agent Skills 是补强适配层的自然一步，且能同时服务 Claude Code/Codex/Cursor/Kiro/Gemini 等 client 列表中的工具。
- **风险**：Agent Skills 生态已标准化（AAIF）且竞品/大厂都在做流程封装；若 kit 只输出文件模板而无“验证闭环”，会与 Spec Kit/OpenSpec 同质化。
- **风险**：Claude Code 原生能力（`/init`、hooks、plugins、workflows）持续内建化，kit 的 adapters 必须跟踪，否则“薄适配”会被官方能力替代。
- **skill 有上下文税**：catalog 每轮载入所有 skill 的 name+description（描述截断 1536 字符），数量越多常驻成本越高；kit 封装的 skills 应控制在少数高价值动作卡，并支持按 profile 裁剪。
- **机会**：kit 的 AGENTS.md token 预算/指令机检/§ 引用校验与 Agent Skills 的 progressive disclosure 天然互补——可做成“skill 负责动作、AGENTS.md 负责约束、脚本负责证据”的三层包。

## F. 未证实清单（不得当事实引用）

1. Claude Code 官方是否使用 “Agent = Model + Harness” 公式——未找到；仅有 engineering 文章的 harness 概念。
2. DSH 是否正式声明兼容/加入 agentskills.io 标准与 client 列表——官方 docs 有 SKILL.md 能力，但标准成员身份未证实。
3. Conductor 官方功能细节（站点 Cloudflare 403）；Tessl 的具体定价/评测能力（只读到 blog intro）。
4. 各竞品“状态/证据/门禁”能力仅基于 README/文档自述，未逐项实测；Spec Kit/OpenSpec/BMAD 是否有 evidence 校验未证实。
5. “多个 skill 自动组合/冲突语义”——官方文档未定义，属开放问题。
6. Anthropic “70+ 平台、100 万 skill、2.8 亿安装”为厂商口径，未独立核实。
7. Kiro 规格产物能否在非 Kiro agent 中无损执行——未证实。
8. stars/pushed 为 2026-11-11 GitHub API 单次快照，会变化。

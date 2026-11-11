> 冻结副本：来源 `harness/runs/kit-eval/positioning-audit.md`（2026-11-11）；原始命令输出仍在 gitignored 的 `harness/runs/kit-eval/`。
> 本文件为提案/评审冻结稿，实施记录见 `harness/plans/2026-11-06-benchmark-opensource.md` 与 `harness-kit/CHANGELOG.md`。

# 定位审计：从「项目脚手架」到「Harness Engineering 项目管理工具」

> 日期：2026-11-11｜对象：`harness-kit/` v0.2.11（README / SPEC / docs / prompts / profiles / adapters）｜方法：只读审计（未改仓库文件、未复跑 kit 测试；测试数引用 CHANGELOG/治理自述）。
> 新定位（审计基准）：支持多 AI Coding Agent（Claude Code + Opus 做架构/评审/攻关，DeepSeek Harness + DeepSeek 模型做日常开发）按同一规范协作、覆盖项目全生命周期、**给 Agent 用**、零学习成本、不拖累模型能力、可自我进化。

## 1. 现状盘点：旧「脚手架」措辞 vs 新定位

| 位置 | 原文关键句 | 与「脚手架」旧定位绑定 | 与新定位的关系 | 建议改写（一句话） |
| --- | --- | --- | --- | --- |
| README.md:3 | 「**Harness Engineering 项目脚手架**：…生成与项目无关的模板、门禁与证据链」 | 生成器/一次性骨架 | 冲突：新定位是持续使用的管理工具 | 「Harness Engineering **项目管理工具**：用五子系统约束多 Agent 协作与项目全生命周期」 |
| README.md:5 | 「不是框架，也不是依赖；**生成物可整目录删除**」 | 可退出的一次性产物 | 部分可沿用（可退出性）；「可删除」弱化持续管理价值 | 「不是运行时框架或依赖；规则与产物可整体移除，但管理方法与证据持续生效」 |
| README.md:13,15 | 「它是什么：Harness Engineering 脚手架」「**可生成、可改造、可验证**的脚手架」 | 生成/改造动作 | 冲突 | 「它是什么：项目管理工具——规则、状态、验证、协作规范都在仓库里」 |
| README.md:25 | 「**脚手架能力矩阵**」 | 以生成动作组织能力 | 冲突 | 「全生命周期能力矩阵」（按阶段 × 资产列） |
| README.md:29-31 | 新项目初始化 / 存量改造 / 版本升级（生成骨架、不自动重写） | 以「kit 生成什么」组织 | 机制可沿用，组织方式需改为生命周期阶段 | 按阶段重排：需求→架构→计划→开发→验证→评审→发布→交接→收尾 |
| README.md:32 | 「不提供**权限 / 工单 / 审批系统**」 | 旧边界（只管仓库内生成物） | 与新「全生命周期管理」冲突；边界需重新定义 | 「团队治理（权限/审批/工单/分支保护）在 Git/飞书等外部系统；kit 管规范、门禁与证据」 |
| README.md:45-56 | 「适合谁 / 不适合谁」「只想要自动写代码…不适合」 | 面向人类做选型 | 与新「给 Agent 用、零学习成本」冲突（入口仍是人评估） | 前置「Agent 60 秒自检并给接入建议」，人只确认结论 |
| README.md:58-64 | 「接入路径：**AI coding Agent 优先**」 | 可沿用（最接近新定位） | 可沿用并升级 | 「多 Agent 协作入口：同一规范，不同角色/模型」 |
| README.md:145-147 | 「真实案例：接入前后**五子系统评分**」 | 接入案例（单 Agent 视角） | 可沿用；缺多 Agent 协作案例 | 增「Claude 设计 → DSH 实现 → Claude 评审」的角色分工与交接案例 |
| SPEC.md:5 | 「抽成…可在任意项目 10 分钟接入的 **Harness Engineering 项目脚手架**」 | 目标 = 抽模板 | 冲突 | 「抽成项目无关的 Harness Engineering **项目管理工具**（五子系统 + 多 Agent 协作契约）」 |
| SPEC.md:9-12 §0 | 「不是通用 CI 平台/Agent 框架；不做语言封装；不是代码迁移器」 | 部分可沿用 | 缺新边界：不替代产品管理、不做 Agent 调度/编排、不做权限系统 | 补三条非目标（产品管理 / Agent 编排运行时 / 权限审批） |
| docs/adoption.md:3 | 「主要使用者是 **AI coding Agent**…接入、日常任务、计划、分工、交接、收尾都以 Agent 为主路径」 | 可沿用（与新定位一致） | 可沿用；但正文仍有大量人工步骤 | 保留 Agent 主路径，显式标出「仅人可决策」的少数决策点 |
| docs/adoption.md:21,57 | 「**脚手架能力**覆盖五子系统」「按 Agent 能力分层接入」 | 前半旧、后半新 | 分层表可沿用；升级为「角色/能力分层 + 多模型分工」 | 增加角色矩阵：架构/实现/评审/攻关各自的最小输入输出 |
| docs/playbook.md:1,3 | 「采用 playbook：五步改造法（五子系统落地）…操作手册」 | 接入手册（旧主路径） | 可沿用但应降级为操作附录；新主路径应是提示词/Agent | 定位为「Agent 操作参考」，主入口指向 adoption/agent-prompts |
| docs/governance.md:3,57,134 | 「让 kit 跟上模型与 Agent」；行为级评估尚未实现；140 测试 | 演化机制（最接近自进化） | 可沿用；是自进化的最大现有资产 | 从「结构审计」补到「行为级 A/B + agent capability probe」 |
| docs/agent-prompts.md:3 | 「主要使用者是 AI coding Agent…覆盖接入、开发、评审、发布、协作与收尾」 | 可沿用（最接近新定位的资产） | 可沿用；缺角色、跨模型流程、产品需求阶段 | 提示词从「任务场景」扩展为「场景 × 角色 × 模型」三维 |
| adapters/dsh/README.md:4 | 「本适配器**不复制任何文件**——manifest 中 `dsh` 为空列表」 | 以「生成物」衡量适配价值 | 冲突：DSH 是新定位主力 Agent，却零适配资产 | DSH 适配器升级为角色 skills + 交接协议（即使不复制文件） |
| adapters/claude-code/CLAUDE.md.template:3 | 「本文件…**只做转发**，不在此复制」 | 薄适配 | 与「Claude 做架构/评审/攻关」不匹配 | 增 architect/reviewer 角色入口、评审产物契约与跨模型交接示例 |
| profiles/*.json:3 | 「10 分钟接入，不需要测试框架」「适合真实仓库」「适合长期维护」 | 接入档位（生成多少文件） | 与新定位弱相关 | 描述改为「治理强度 / 协作强度」档，接入速度只作次要属性 |
| CHANGELOG.md:3 | 0.2.11：提示词单源生成 + CLI（无定位句） | 进化机制可沿用 | 可沿用；缺定位/兼容性摘要 | 每个 release 增一行「定位变化 / 兼容性 / 迁移」 |
| prompts/_preamble-adopted.md:1-2 | 「你是本仓库的 AI coding Agent，按 Harness Engineering 流程工作」 | 可沿用 | 缺角色/模型身份与输出契约 | 前置支持 `{{ROLE}}` / `{{MODEL}}`，并要求返回「结论 + 证据 + 未验证」 |
| prompts/multi-agent.md:15-18 | 「多个 Agent 并行…独立 branch/worktree；写作用域不重叠」 | 新定位核心，但机制粗 | 可沿用；与「唯一 active 计划」存在张力 | 引入「角色任务卡 + 子计划 + 产物交接」，避免多 active 冲突 |
| prompts/handoff.md:15-18 | 「交接给另一个 Agent 或人；回答 5 问」 | 可沿用 | 缺跨模型/角色状态与未决评审 | 交接补「模型/角色/评审结论/未决决策/下一步」 |

## 2. 全生命周期覆盖矩阵

| 阶段 | 现有覆盖物（prompt / 门禁 / 模板 / skill） | 覆盖强弱 | 缺口 |
| --- | --- | --- | --- |
| 概念 / 产品需求 | 无；`request-feature`（#4）是「已接入后的小需求」，不是发现/PRD | **无** | 没有需求来源、验收判据生成、干系人/范围确认；kit 是否覆盖需先定边界（见下） |
| 方案 / 架构 | `evaluate-options`（#5）、`update-docs`（#12，含 ADR）、`references/contracts` 模板 | 弱 | 无设计评审角色、无架构决策记录模板、无跨模型「设计→实现」交接物 |
| 计划 | `new-plan`（#6）、计划模板、`check_plan`、唯一 active | 强 | 多 Agent 并行时多计划/分支的协调语义未定 |
| 开发 | `request-feature`（#4）、`fix-bug`（#7）、`refactor`（#8）、AGENTS 模板、scope 门禁 | 强 | 角色化实现指引（哪些活给 DSH、哪些给 Opus）缺失 |
| 验证 | `verify-change` skill、`completion-claim`（#20）、evidence/`verify_claim`/`verify-static`/`check-host` | 强 | 行为级验证缺（见 §5） |
| 评审 | `pr-self-check`（#9）、`adversarial-review`（#10）、red-team skill、reviews 模板 | 中强 | 无「评审者 ≠ 作者/不同模型」的机制约束与身份留痕 |
| 发布 | `release-prep`（#15）、`security-self-check`（#14）、`release-check` | 中 | 无部署/回滚/发布后观察；发布审批在外部 |
| 运维 / 迭代 | `upgrade-deps`（#11）、`verify-performance`（#13）仅擦边 | **弱/无** | 无监控、事故/回归、SLO、运行手册、线上问题回写 |
| 交接 | `handoff`（#18）、`end-session`（#17）、`cold-start`（#3）、`plan brief` | 中强 | 跨模型/跨角色的状态与评审结论不结构化 |
| 收尾归档 | `close-stage`（#19）、计划 done + `_archive/`、评分卡 | 中 | 归档后的经验回写（规则/门禁）无闭环模板 |

**产品需求阶段特别回答**：目前**零资产**。新定位要「覆盖全生命周期」，但 kit 不做产品管理更合理——建议把产品需求定义为明确定义的**外挂环节（boundary adapter）**：需求来源（issue/PRD/用户研究）在外部工具，kit 只提供「需求 → 可执行验收判据 + 计划」的衔接资产（1 个 prompt + 1 个需求/验收模板），并在 README 写明「kit 从可验收处开始」。否则全称「全生命周期」会被理解为包含产品管理，反而扩大承诺与学习成本。

## 3. 「谁在用」审计：默认读者是 Agent，还是人？

| 位置/资产 | 文档默认读者 | 需要人判断 / 手工的动作（学习成本） | 应改为 Agent 可执行的动作 |
| --- | --- | --- | --- |
| README.md:34-56,145 | 人（症状/选型/评分） | 判断是否需要 kit、选 profile、看评分表 | Agent 自检仓库状态 → 给「需不需要/用哪档」结论 |
| README.md:68-80、adoption.md:19-32 | 人（粘提示词） | 克隆 kit、记 `<kit>` 路径、复制/粘贴到 Agent UI、补占位符 | 一条 `harness-prompt auto`：探测阶段、选场景、填占位符、输出可直接执行的指令 |
| docs/agent-prompts.md:20,23 | 人（手工复制回退） | `--set` 填占位符、手工贴 0A/0B、判断阶段 | 阶段自动检测已有雏形（`detect_target_stage`），应成默认路径并自动填值 |
| prompts/adopt-*.md、evaluate-options、new-plan | 人（确认闸门） | 「给我确认」「我确认后」：方案/计划/init 均等人 | 保留决策点，但改成结构化「选项 + 风险 + 默认建议」，Agent 可先执行可逆部分 |
| docs/playbook.md:16-108 | 人（逐步命令） | 盘点/选档/init/填规则/接 CI 的 5–7 步手工流程 | Agent 自动盘点与 init；人只看首次失败与越界 |
| docs/adoption.md:82-123 | 人（手动接入） | 不依赖 Agent 的路径 | 保留作为降级路径（Agent 不可用/审计） |
| docs/governance.md:18-83 | 人（维护者） | 九条原则、复杂度预算、淘汰流程 | 固化成 `harness-audit` 的数据与检查项 |
| profiles/*.json:3、README profiles 表 | 人（选档） | 理解三档差异 | Agent 按仓库规模/测试现状推荐，人确认 |
| README.md:295-303、governance.md:114-118 | 人（信任边界） | 阅读未验证项/限制 | Agent 启动时直接读「边界」并主动声明未验证 |

**结论**：文档**声称** Agent-first（adoption.md:3、agent-prompts.md:3），但实际默认读者仍是「有经验的维护者」：选型、阶段判断、粘提示词、升级 diff、评分都靠人。零学习成本只在「提示词内容已写好」这一层成立，不在「Agent 能否自己走完流程」这一层。

## 4. 多 Agent / 多模型协作是否足够？

现有资产：
- 机制层：唯一 active 计划 + `scope.allow/deny` + 证据 commit 绑定 + `plan brief`（governance.md:86-94）；`multi-agent` 提示词（#16）要求独立 branch/worktree、写作用域不重叠；`handoff`（#18）5 问通用交接；`cold-start`（#3）接手。
- 适配层：DSH 走原生 AGENTS（adapters/dsh/README.md:3-4，manifest 空）；Claude Code 走 `CLAUDE.md` 薄转发 + hooks 示例 + red-team 子 agent（adapters/claude-code/）；AGENTS 模板路由到 references/harness（core/templates/AGENTS.md.template:25-34）。

不足以支撑「Claude Code 设计 → DSH 实现 → Claude Code 评审」的现实流程，缺：
1. **角色契约**：没有 architect / implementer / reviewer 三个角色提示词与输入输出规范；`adversarial-review` 是通用评审，不包含「读设计稿 + 验证实现符合设计」。
2. **跨模型交接物**：设计稿/ADR/接口契约/review verdict 没有 schema 或落盘位置，交接靠自然语言；`handoff` 不记录模型/角色/未决评审。
3. **身份与可追溯**：evidence 只有 `verifier` 字符串，无 `agent`/`model`/`harnessVersion`；无法证明「评审者不是作者/不是同模型」，也无跨模型评审门禁。
4. **并发协调**：唯一 active + 多 branch 各自维护计划存在语义冲突；无 ownership/claim 文件或子计划机制；合并顺序/冲突处理仍是人决定。
5. **适配层不对称**：DSH 零适配（主力 Agent 却没有 skills/角色），Claude Code 只有入口转发；没有两端的角色/能力映射与交接模板。
6. **模型能力差异**：文档不说哪类任务适合哪个模型（长上下文/架构推理 vs 高频编码），也没有按模型裁剪提示词或上下文的机制。
7. **评审闭环**：`reviews/` 模板存在（strict），但没有「评审必须引用被评审的 evidence id / design doc」的机检，也没有 review→修复→再评审的状态机。

## 5. 自进化机制：结构可进化，行为不可证

| 机制 | 现状 | 判断 |
| --- | --- | --- |
| 版本 / 契约 / 发布 | `VERSION`+`CHANGELOG`+`SPEC`+tag（governance.md:32-36） | 强；但升级靠人按 playbook 手动 diff（playbook.md:219-236） |
| 版本升级路径 | v0.2.2→v0.2.3 真实 Android 仓验证（playbook.md:229） | 中；仅一次、单语言生态；profile 升级未验证 |
| 漂移 / 门禁自测 | `harness-selftest`（M1–M8）+ tests 140 + adapters-check | 强（结构）；能证明门禁不空转 |
| 月度审计 / 反臃肿 | 评分卡 + `harness/reviews/` + 九条原则 + 删除优先（governance.md:18-82） | 中强；靠人执行，无自动趋势数据 |
| 行为级评估 | **未实现**，明确列 v0.3+（governance.md:57-68） | 缺：无法回答「接入后 Agent 是否更好」 |
| 模型 / Agent 能力复核 | 只有一条人工观察清单（governance.md:46-54） | 弱：无 capability probe、无模型矩阵、无版本 pin 强制 |
| kit 版本 pin | `harness/config.json.kitVersion` 存在，工具不校验/不阻断 | 弱：drift 不影响门禁 |
| 升级建议 | 只有手工 diff + selftest | 缺：`harness-upgrade --plan/--apply`（可逆、生成映射表） |

**结论**：现有机制能保证「kit 自身结构与门禁不腐烂」，但还不能保证「跟上模型与 Agent 变化」——缺的是**Agent 能力探测、模型/角色矩阵、kit 版本 pin 与自动升级建议、行为级 A/B 回归**。这四项是「可自我进化」的最小闭环。

## 6. 结论

### Top 5 定位冲突

1. **脚手架 vs 工具**：README/SPEC 首页三次自称「脚手架」，而新定位要持续管理多 Agent 全生命周期；「生成」是动作，不是定位。
2. **可整目录删除 vs 长期管理**：强调「生成物可删」能证明低风险，但也暗示价值一次性；新定位需要「规则/工件可退出，但方法与证据持续生效」。
3. **不提供治理 vs 全生命周期管理**：旧边界把权限/工单/审批排除在外；新定位说「全生命周期」必须重新定义边界为「治理外挂」，否则承诺与能力不匹配。
4. **Agent-first 文案 vs 人类操作现实**：文档号称 Agent-first，实际流程（选档、粘提示词、升级 diff、评分）默认人来做；「零学习成本」目前不成立。
5. **薄适配/工具无关 vs 多 Agent 协作**：新定位把跨 Agent 协作当核心，但 DSH 适配为空、Claude 适配只做转发、无角色/评审/跨模型交接契约。

### 新 README 开头 3 句话草案

> **harness-kit 是给 AI Coding Agent 用的 Harness Engineering 项目管理工具**：用 Instructions / State / Verification / Scope / Session Lifecycle 五子系统，把多 Agent（如 Claude Code + Opus 做架构/评审，DeepSeek Harness + DeepSeek 做日常开发）约束在同一套规范里。
> 它覆盖项目从需求验收、方案、计划、开发、验证、评审到发布、交接、收尾的全生命周期——**Agent 直接读仓库就能工作，人只做少数风险决策**。
> 不是运行时框架或依赖：规则与工件可整体移除、可自我演化，但「谁在什么证据上声称完成」始终可复核。

### 必须改的文件清单（按优先级）

- **P0**：`README.md`（开头定位、能力矩阵按生命周期、适合谁/接入路径改 Agent 自检）、`SPEC.md`（§0 目标与非目标补多 Agent 边界）、`docs/adoption.md`（Agent 主路径 + 标出人决策点）。
- **P0**：`docs/agent-prompts.md` + `prompts/`（角色维度、跨模型交接、产品需求衔接 1 个模板；同步 `_preamble-*` 加 role/model）。
- **P1**：`adapters/dsh/README.md` + `adapters/claude-code/`（角色入口、评审产物契约、接口/交接最小定义）、`docs/governance.md`（多 Agent 协作 + 自进化四件套：capability probe / 模型矩阵 / 版本 pin / 行为回归）。
- **P1**：`core/templates/harness/evidence/schema.json`（可选 `agent`/`model`/`harnessVersion`）与 review 模板（评审引用 evidence id）。
- **P2**：`profiles/*.json` description（治理/协作强度档）、`docs/playbook.md`（降为操作附录 + 加自动升级建议）、`CHANGELOG.md`（release 摘要加定位/迁移行）。

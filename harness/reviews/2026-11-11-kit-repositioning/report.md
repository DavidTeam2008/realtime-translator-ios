> 冻结副本：来源 `harness/runs/kit-eval/REPORT.md`（2026-11-11）；原始命令输出仍在 gitignored 的 `harness/runs/kit-eval/`。
> 本文件为提案/评审冻结稿，实施记录见 `harness/plans/2026-11-06-benchmark-opensource.md` 与 `harness-kit/CHANGELOG.md`。

# harness-kit 重评估与重构方案（v0.3 提案 · v2 修订版）

> 日期：2026-11-11｜对象：`harness-kit/` v0.2.11（**140 个测试**（单元/fixture/端到端混合）；**24 个提示词文件** = 19 场景 + 2 附加片段 + 2 前置 + 1 文档头）；3 profiles；4 个 kit 脚本。
> 状态：**提案，待用户确认后执行**；本文件不改变已发布 v0.2.11 的任何行为。
> v2 修订说明：经两名独立红队评审（`review-instructions.md` P0×1/P1×4/P2×6；`review-quality.md` P0×2/P1×4/P2×6），已修正 M2 过度承诺、路线图不可验收、数字引用错误、兼容迁移缺失等问题；处置表见 §11。
> 证据源（同目录）：[`positioning-audit.md`](positioning-audit.md)（定位冲突与生命周期矩阵）· [`research-ecosystem.md`](research-ecosystem.md)（Claude Code / Agent Skills / 竞品事实）· [`usability-audit.md`](usability-audit.md)（端到端可用性实测）· [`dsh-extensibility.md`](dsh-extensibility.md)（DSH 插件/ skill 机制事实）· `out-*.txt`（命令原始输出）
> **落盘位置**：已按 D8 移入 tracked 的 [`harness/reviews/2026-11-11-kit-repositioning/`](../../reviews/2026-11-11-kit-repositioning/README.md)；原始命令输出仍留在 gitignored 的 `harness/runs/kit-eval/`；sha256 与复现见该目录 `README.md` / `repro.sh`。

---

## 0. 结论速览

1. **定位**：从「项目脚手架（生成模板/门禁/证据）」改为「**给 AI Coding Agent 用的 Harness Engineering 项目管理工具（项目治理层）**」。脚手架只是"接入方式"，不是产品身份。**对外必须区分已交付与路线图**：v0.3.0 交付"接力 + 分工 + 证据可复核"；**"多 Agent 并行"是 v0.3.2 路线图**，建设前不得写成现状。
2. **形态**：现在是"给有经验维护者用的脚手架 + 24 个提示词文件 + 复制粘贴入口"，对 Agent 不友好。v0.3 改为「**1 个统一 `harness` CLI + 仓库原生状态 + 1 个总控 skill（待 A/B 验证后定）**」：Agent 侧 `@harness + 自然语言`，人侧最多确认一次。
3. **Skill 封装**：合理且可行——Agent Skills 已是中立标准（2026-10-22 捐给 Linux Foundation/AAIF，40+ 客户端；Claude Code 与 DeepSeek Harness 都原生支持 `SKILL.md`）。但正确形态不是"20 个平级 skill"，而是**单入口 + 渐进披露 references + 确定性 CLI**；"多 skill 不能同时用"的旧前提在 Claude Code 上已不成立（一条消息最多堆叠 6 个、subagent 可预载、plugin 可捆绑），但多 skill 自动协调无官方语义。**skill 主入口需先做 A/B（skill vs "AGENTS 一行 + CLI"），无显著收益则只保留 D+A**。
4. **DSH 插件**：技术上完全可行（Cordis bundle / `plugin_manager` / 已有"随包 skill 提供方"先例，可注册 tool/command/skill/GUI/事件），但**暂缓产品化**：插件代码在 workspace sandbox 外执行、安装需 full-access/审批、`engines.dsh` 强耦合（Desktop runtime 仍 `0.2.2-rc.1` 预发布；本机 PATH 上的 `dsh` 是 `0.2.1-rc.5`）、profile 级影响所有项目，与"可退出、不是依赖"冲突。只做隔离 spike，且排到多 Agent 协议之后（v0.4 决策）。
5. **卖点**：不是"一键脚手架"（Spec Kit 149k★、OpenSpec 74.5k★、BMAD 55k★、Superpowers 315.8k★ 占据流程/方法论生态；竞品能力仅 README 自述、未实测；Claude Code 在持续内建 init/hooks/plugins/workflows）。真正的差异化是**跨 Agent 可移植的项目状态 + 完成声明强制可复核（当前不抗伪造，v0.2.12 起加固）+ 多 Agent 协作协议（路线图）+ 模型无关的自进化**。一键搭建是获客点，不是护城河。
6. **诚实前提**：单 Agent、单模型、短周期、无需审计的项目不需要本工具；Claude Code + `CLAUDE.md` + 简单 Makefile 就能覆盖大部分价值。kit 的价值随"Agent 数量 × 模型异构度 × 项目周期 × 完成声明的严肃性"增长。

---

## 1. 现状诊断（证据，不空谈）

### 1.1 已有资产（v0.2.11，扎实）

- 五子系统：Instructions（AGENTS 树 + `check_docs/check_agents`）、State（计划 front matter + 唯一 active + `check_plan`）、Verification（证据三值 + clean-tree/commit 绑定 + `verify_claim` + JUnit 适配）、Scope（`scope.allow/deny` × `git status`）、Session Lifecycle（handoff / verify-change / red-team skills + doctor + 升级路径）。
- 140 个测试（复跑 `Ran 140 tests OK`）；`harness-selftest` 负向注入——**M1–M5 必跑，M6–M8 条件执行**（需 active 计划/证据/hygiene 配置；普通 standard 宿主会 SKIP）——证明"门禁真的会红"，但**不覆盖"伪造 PASS"**（见 §3.7）。
- 3 档 profile；Android/Gradle 与 iOS 两个真实仓试点。
- 设计治理（反臃肿九原则、预算、删除优先、行为级评估路线）写在 `docs/governance.md`——重定位后最值钱的资产之一。

### 1.2 入口与日常成本（实测）

| 项 | 实测 | 证据 |
| --- | --- | --- |
| 从零到第一个动作 | 人至少 2 条命令 + 1 次粘贴；Agent 没有自助发现路径；`copy` 默认剪贴板，**无剪贴板工具时打印到 stdout + WARN**（16 行） | usability-audit §1.1；`out-copy-noclip.txt` |
| 文档面 | 6 文件（README+adoption+agent-prompts+playbook+governance+SPEC）= **1619 行 / ≈35.9k tokens**；不含 SPEC 的 5 文件 = 1356 行 / 29.1k tokens；0B 提示按字面要读 568 行 | usability-audit §1.1；复算：`wc -l` + `python3 tools/token_estimate.py` |
| 入口命令 | 4 个 kit 脚本 + Makefile target + 提示词库 + 3 处重复入门说明（README / adoption / agent-prompts） | 同上 |
| 日常任务 | 8–9 步：plan→改码→check→verify-static→证据 3 步→commit；计划"未提交改动"必须与 `git status` 严格互等，**每步维护第二份状态**（P1 摩擦） | usability-audit §1.3/§2 |
| 首日体验 | scaffold+未填计划时 `make check` 一次报 35 个 error，Agent 易误判"门禁坏了" | `out-check-after-plan.txt` |
| 发布/交接 | standard 无 `release-check`/`doctor`/`resume`/`end`/`handoff` target；strict 才有 `release-check`；`brief` 藏在 README 一行命令里 | usability-audit §1.3；kit tests（standard vs strict Makefile） |

### 1.3 定位冲突（独立审计，Top 5）

1. README/SPEC 首页三次自称"脚手架"——生成是动作，不是定位；新定位要的是持续管理。
2. "生成物可整目录删除"证明低风险，但也暗示价值一次性；应改为"规则与工件可退出，方法与证据持续生效"。
3. 边界仍写"不提供权限/工单/审批"，缺新边界"不替代产品管理、不做 Agent 编排"。
4. 文案 Agent-first，现实默认"有经验的人"：选 profile、判阶段、粘提示词、手工升级 diff、人做评分。
5. 声称工具无关，但 **DSH 适配为空**、Claude Code 适配只有 3 个文件 + skills 哈希同步（`adapters.py`），没有角色/跨模型交接契约——而这条恰是新定位的核心。

**诊断结论：kit 不缺点子，也不缺机制；缺的是"Agent 原生"的产品形态，以及"跨 Agent 协作"从口号变成协议。**

---

## 2. 新定位（问题 1）

### 2.1 定位陈述

**一句话（v0.3 发布口径）**：
> **harness-kit 是给 AI Coding Agent 用的 Harness Engineering 项目管理工具**：让 Claude Code、DeepSeek Harness 等 Agent / 模型在同一仓库上**接力与分工**开发复杂项目——规则、状态、边界、证据都在仓库里，任何 Agent 冷启动即可接手，"完成"要有可复核证据。
> （**多 Agent 并行** = v0.3.2 路线图；发布时不得写成现状。）

**电梯陈述（30 秒）**：
> 你用 Claude Code + Opus 做架构、Code Review 和技术攻关，用 DeepSeek Harness + DeepSeek 做日常开发。问题是：两个 Agent 的会话各活各的，做到哪、谁验证过、下一步给谁，全靠人转述。
> harness-kit 把项目状态、任务边界和验证证据做成仓库里的文件与命令：换 Agent、换模型、换人，下一个只读仓库就能接着做；"完成"必须拿出可复核证据，没有证据就是"未验证"。

**三个不变量（任何版本都不破）**：
1. **真相在仓库，不在会话里**：状态、证据、边界必须是可 diff、可提交、可被任意 Agent 读取的文件。
2. **确定性优先**：能脚本判定的绝不靠模型自觉；门禁必须能变红，且能被负向注入证明没有腐烂。
3. **可退出、不锁定**：不成为运行时依赖，不绑定任何 Agent/模型；删掉 kit 产物，项目本身仍能构建运行。

### 2.2 与旧定位的差异

| 维度 | 旧：项目脚手架 | 新：项目管理工具（治理层） |
| --- | --- | --- |
| 产品身份 | 生成一次性的模板/门禁/证据骨架 | 持续使用的项目状态与协作协议 |
| 主要用户 | 人类维护者（读文档、选 profile、粘提示词） | AI Coding Agent（自助发现、自助执行）；人只做风险决策 |
| 核心问题 | "怎么快速长出五子系统" | "多 Agent/模型怎么不打架、怎么接得住、怎么信完成" |
| 成功标准 | init 很快、门禁很多 | Agent 冷启动 1 次就读懂状态；完成声明可复核；换 Agent 不掉线 |
| 一次性价值 | 生成物可删除 | 方法与证据持续生效；规则可淘汰 |
| 与 Agent 关系 | 适配层（可选、薄） | 控制面：Agent 是执行器，kit 是共享内存与审计层 |

### 2.3 边界：做什么 / 不做什么（写进 README 与 SPEC §0）

**做**
- 项目状态机：接入 → 需求验收 → 计划 → 实现 → 验证 → 评审 → 发布 → 交接 → 收尾归档（下文称"**工程交付生命周期**"，不含产品定义与线上运维）；
- 跨 Agent/模型的交接协议与身份留痕（谁、用什么模型、在哪个 commit 上、验了什么）；
- 多 Agent 协作的写作用域协调与合并前门禁（**v0.3.2**；v0.3.0 只交付串行接力与分工）；
- 确定性门禁 + 证据链 + 门禁自测 + 版本升级/漂移检测；
- 一个薄入口（skill，待 A/B）与一个统一 CLI。

**不做**
- 不做 Agent 编排运行时（DSH Agent Teams、Claude Code subagents/workflows 已经做得更好）；
- 不替代产品管理（PRD/优先级/用户研究在外部工具，kit 从"可验收"开始，通过 intake 契约衔接）；
- 不做权限/工单/审批系统（在 Git/CI/飞书等治理系统）；
- 不做语言/测试框架封装，不解析测试输出（JUnit XML → 证据由宿主提供）；
- 不覆盖线上运维/监控/SLO，不承诺"全生命周期"字面意义；
- 不引入运行时依赖，不 import 进业务代码。

> 边界的作用：**"工程交付生命周期"是可承诺的**；产品定义、线上运维、Agent 编排都是明确定义的外挂环节。

### 2.4 目标场景（用户给的现实场景）

| 角色 | 典型 Agent / 模型 | kit 给什么 | 当前/规划 |
| --- | --- | --- | --- |
| 架构 / 方案 / 技术攻关 | Claude Code + Opus（长上下文、强推理） | 设计产物落 `docs/`（ADR/契约）；task 角色卡；评审证据 | v0.3.2 补齐角色卡 |
| 日常开发 / 批量实现 | DeepSeek Harness + DeepSeek（成本、吞吐、DSH 优化） | 冷启动一屏状态；scope 门禁；按变更类型选验证；证据关联 | v0.3.0 |
| Code Review / 对抗性评审 | Claude Code + Opus（与作者不同模型） | `harness review`：评审引用 commit/证据 id；可配"评审者≠作者/不同模型" | v0.3.2 |
| 人 | 决策者 | 只处理：风险确认、发布/推送、越界与 UNVERIFIED 决策 | 已有 |

关键原则：**kit 不调度 Agent，kit 让任何调度方式写同一份项目状态。** 这样 Claude Code 升级、DSH 新增 Agent Teams、模型换代，都不需要迁移项目状态。

### 2.5 新 README 开头（草案，确认后落地）

```markdown
# harness-engineering-kit

> **给 AI Coding Agent 用的 Harness Engineering 项目管理工具**：让 Claude Code、DeepSeek Harness
> 等 Agent / 模型在同一仓库上接力与分工开发——规则、状态、边界、证据都在仓库里，
> 任何 Agent 冷启动即可接手，「完成」要有可复核证据。
>
> 当前支持：单工作流接力 / 分工 / 证据复核；多 Agent 并行门禁见路线图 v0.3.2。

**Agent 换、模型换，项目不散。** 不是框架，也不是运行时依赖；可退出、可自进化。
```

---

## 3. 核心卖点（问题 3）

### 3.1 先回答：为什么不用 Claude Code + Harness Engineering 自己管？

Claude Code 是**单厂商执行面**，不是**跨厂商项目控制面**。它的 init / resume / fork / subagents / hooks / workflows / code-review 都在回答"这个会话/这个厂商的 Agent 怎么把活干好"，而本工具回答"**多个 Agent / 模型 / 人怎么在同一个项目上不打架、接得住、信得过**"。

| 能力 | Claude Code 原生 | harness-kit | 关系 |
| --- | --- | --- | --- |
| 会话恢复 / fork | 本机 `~/.claude/projects/`，不跨机器、不跨厂商 | 状态在仓库文件，任意 Agent 可读 | 互补（kit 管项目状态，CC 管会话） |
| 记忆 / 规则 | CLAUDE.md / AGENTS.md / auto memory（本机） | AGENTS 单源 + 预算门禁 + § 引用校验 | kit 可给 CC 供料 |
| 完成判定 | 模型自述 + `/code-review`（LLM 判断） | 证据三值 + clean tree + commit 绑定 + 门禁自测；**当前可伪造，v0.2.12 加固** | 开箱提供，非绝对能力 |
| 代码评审 | `/code-review`、subagent 评审 | 评审记录引用 commit/证据；"评审者≠作者"可配门禁 | 互补（评审仍由强模型做） |
| 多 Agent 并行 | subagents（同一运行时）、worktrees | 跨运行时/跨厂商的写作用域与任务认领 | **路线图 v0.3.2**，当前未交付 |
| 生命周期 | 会话级（resume/fork/compact） | 项目级（接入/需求/计划/发布/交接/归档） | 开箱提供（项目级） |
| 模型/厂商锁定 | 绑定 Claude 生态 | 模型无关，删掉 kit 不影响项目 | 开箱提供（可退出） |

一句话：**Claude Code 让 Agent 更能干；harness-kit 让 Agent 的成果更可接手、可复核、可跨厂商复用。** 二者不是竞品，是"执行器 vs 治理层"。

> 注意：Claude Code 的 hooks/scripts/workflows 也能自建确定性检查——kit 的差异不是"别人做不到"，而是**开箱提供、跨厂商可复用、有证据与门禁约定**（见 §3.2 的竞品口径）。

### 3.2 竞品格局（2026-11-11 快照；竞品"证据能力"仅 README 级证据，未实测）

| 项目 | 定位 | 是否跨 Agent | 证据/门禁能力（README 未实测） | 对 kit 的含义 |
| --- | --- | --- | --- | --- |
| GitHub Spec Kit（149k★） | SDD 流程：spec→plan→tasks→implement | 是 | 有 verify 步骤，未见证据三值/门禁 JSON | 流程层已被占位，不做"又一个 SDD" |
| OpenSpec（74.5k★） | 轻量 spec-driven + archive | 是 | 未见门禁校验 | 同上 |
| BMAD-METHOD（55k★） | persona + 交付循环 | 是（skills） | 未见机械校验 | 重流程，不是 kit 对手 |
| Superpowers（315.8k★） | 完整开发方法论 + skills 生态 | 是（15+ harness） | 强制 TDD，未见证据 JSON | 生态强；kit 做"可信层"而非再写方法论 |
| Kiro（AWS） | 规格驱动 IDE | 产物可带走，执行绑 Kiro | 未见跨厂商证据标准 | 厂商锁定，反衬 kit 的中立 |
| Claude Code 原生 | 执行 + skills/plugins/hooks | 否（跨厂商） | 自述 + LLM review；hooks 可自建检查 | 见 3.1 |
| **市场空白（待验证）** | **跨 Agent 的项目治理 + 完成声明强制可复核 + 协作协议** | — | — | **kit 的差异化押注**；竞品未实测，不能断言"无一" |

结论：**不要在同质化红海里卖"流程/模板/规格"**；卖"流程跑完之后的信任问题"——"Agent 说完成了，你能不能 30 秒内核对它是真的"。

### 3.3 六个核心卖点（按"主张 / 依据 / 现状"）

| # | 卖点 | 一句话 | 依据 | 现状 |
| --- | --- | --- | --- | --- |
| M1 | **跨 Agent / 模型的可移植项目状态** | 换 Agent、换模型、换人，下一个只读仓库就接手 | 状态全部是仓库文件；AGENTS/CLI 不绑定厂商 | 机制已有（计划/证据/handoff），**入口太难用**；**跨厂商交接未实测** |
| M2 | **"完成"强制可复核**（不承诺防伪造） | 自述不算数：无证据即 UNVERIFIED；证据三值 + clean tree + commit 绑定 + 门禁自测 | `evidence.py`/`verify_claim.py`/`check_plan.py`/`selftest` | **部分已有，但有 P0 漏洞**：手写 PASS 证据可通过全部门禁；v0.2.12 加固前**不得**对外主打"机械否证/确定性" |
| M3 | **多 Agent 分层协作协议**（架构用 Opus、实现用 DeepSeek、评审换模型） | 角色卡、写作用域、任务认领、评审引用证据、跨模型评审门禁 | 当前仅"唯一 active + multi-agent 提示词"；并发语义缺失 | **v0.3.2 建设**；建设前不得写成现状 |
| M4 | **项目生命周期状态机** | 不止会话 resume：接入/需求验收/计划/发布/交接/归档都是项目状态 | 计划状态机 + 交接摘要 + 归档；生命周期矩阵见 positioning-audit §2 | 中强；缺产品段衔接与发布后阶段（明确外挂） |
| M5 | **反臃肿：不拖累模型** | 计算型优先、指令预算、渐进披露、删除优先、可退出 | governance 九原则 + 140 tests + 预算门禁 | 已有；但 1619 行文档与 24 提示词文件本身已成负担 → 本次收敛**须有预算门禁** |
| M6 | **自进化：跟上 Agent/模型变化** | 薄适配、版本 pin、漂移检测、能力探测、升级路径、行为级回归 | version/CHANGELOG/SPEC + selftest + drift | **部分已有**：capability probe/kitVersion 门禁/upgrade/A-B **均未做**（v0.3+ 交付） |

> M2 的诚实边界：`evidence.py` 由 Agent 自己运行，**恶意 Agent 可以伪造证据 JSON、伪造命令输出**。当前 kit 的 `verify_claim` 信任证据自报的 verdict/counts，commit/dirty 也来自证据自身；质量评审实测"0 测试 + `passed:9999` + 无 artifact"可通过 `verify_claim --all/--fresh --strict` 与 `check_plan check`。**因此 M2 在 v0.2.12 加固前只能表述为"无证据不能通过 + 证据可审计"，不能表述为"机械否证"**；加固方案见 §3.7。

### 3.4 不适用场景（必须写进 README，避免过度承诺）

- 一次性脚本、没有测试也不长期维护的仓库；
- 只用单一 Agent、单一模型、无交接、无发布审计的个人小项目（Claude Code + CLAUDE.md 就够）；
- 只想要"自动写代码"、不想要任何过程约束；
- 需要 kit 替你做产品决策/优先级（kit 不做产品管理）；
- **无法产出机读测试结果 / 无 git / 无任何 CI 的项目**：证据链只能降为 UNVERIFIED，接入收益低；
- **不愿维护证据与门禁的项目**：kit 不是"自动合规"，它要求宿主提供真实命令与产物。

### 3.5 对外话术（三层，M2 加固前加限定）

- **10 秒**："Agent 换、模型换，项目不散；完成不是自述，要有可复核证据。"
- **30 秒**："Claude Code 做设计、DeepSeek Harness 做日常开发——两边读写同一份仓库状态，谁接手都能继续；任何'完成'都要留有可复核记录，拿不出证据就是未验证（防伪造加固中）。"
- **1 分钟**：见 §2.1 电梯陈述 + §3.1 对照表 + §3.3 M2 边界。

### 3.6 卖点排序（定位清晰的关键）

1. **获客点（wedge）**：一键接入 / 一句话触发（简单，但可被复制）；
2. **核心价值**：M1 跨 Agent 可移植状态 + M2 完成声明强制可复核（加固后）；
3. **护城河**：M3 多 Agent 协作协议 + M6 自进化（需要持续投入，难被单厂商内建替代）。

### 3.7 证据可信性威胁模型与加固路线（P0 修复）

**威胁模型**：攻击者 = 能写仓库文件、能提交、能跑 CLI 的 Agent（或人）。攻击面：手写 evidence JSON、伪造 counts/verdict、伪造 commit（`deadbeef` 可被 `--fresh` 抓，但 `--all` 不抓）、伪造 dirty、伪造成约定路径、过期证据复用。

**最小加固（v0.2.12 必做，不做则不得营销 M2）**：
1. **artifact 契约统一**：`evidence_from_junit.py` 输出 `result.artifacts`，但 `verify_claim.py` 只读 `xcresultPath`——先统一字段并写 schema。
2. **默认 `requireArtifact: true`**：test-count 类 claim 必须带 artifact 路径；verifier 校验文件存在，并**从 JUnit XML/xcresult summary 重算 passed/failed/skipped**，与自报值不一致 → FAIL。
3. **commit/dirty 复核**：commit 必须可解析且是 HEAD 祖先；`--fresh`/`--strict` 重新计算工作树 dirty，不信证据自报。
4. **M9 负向测试**：伪造 PASS 证据（0 测试、`passed:9999`、无 artifact、done 计划）必须被 `verify_claim`/`check_plan` 拒绝；现有 selftest M1–M8 只覆盖"缺失/不一致"，不覆盖"伪造 PASS"，需新增 M9 并纳入 kit tests。
5. **可选增强**：CI 生成的证据带 CI run id / OIDC 签名；commit 签名；证据文件哈希写入 commit message/tag。该层为 v0.3+，不阻塞 v0.2.12。
6. **口径**：加固前对外只用"无证据即未验证 / 证据可审计"；加固后再评估是否恢复"可机械否证"表述。
7. **实现边界（2026-11-11 v0.2.12 落地）**：先修 `verify_claim`（本节的 artifact 契约/重算/commit 祖先/dirty/M9 均已实现）；`check_plan` 的完成校验仍只做计划一致性与 evidence id 绑定（委托 `verify_claim` 列入 v0.2.13）；xcresult 不做独立重算（判 UNVERIFIED，先转 JUnit XML）。

**验收（可执行）**：上述伪造 fixture 在加固后 `verify_claim --all` 返回 FAIL/UNVERIFIED 且 `check_plan check` 非 0；真实测试 → JUnit → evidence 路径仍 PASS；两者输出可区分。

---

## 4. Skill 封装评估（问题 2 前半）

### 4.1 结论（附 A/B 前置）

**方向合理、可行，但"是否作为主入口"需先验证。** 推荐架构仍是「**1 个总控 skill + 渐进披露 references + 确定性 CLI 后端**」，但 v0.3.0-alpha 必须先做 **A/B**：
- 变体 A：AGENTS.md 一行入口（`入口：先跑 harness status`）+ 统一 CLI；
- 变体 B：A + router skill。

指标：首次动作步数、触发成功率（10 个任务）、上下文 token、失败恢复步数。**B 相对 A 无显著收益 → 只交付 A（D+A），skill 降级为可选**；这样可省掉 skill 渲染/同步/drift/10 references 的维护成本。

理由：
- Agent Skills 已是中立标准（2026-10-22 捐给 Linux Foundation 下 AAIF；官方 client 40+，含 Claude Code/Codex/Cursor/Gemini CLI/Copilot/Kiro；Anthropic 口径 70+ 平台）——**跨 Agent 分发风险低**；
- Claude Code 与 DeepSeek Harness 都原生支持 `SKILL.md`（DSH：项目 `.dsh/skills` rank100 / `.agents/skills` rank200；catalog 只载 name + 截断 description（默认 500 字符），正文按需加载）；
- 渐进披露可解决"规则塞满上下文"：catalog 常驻成本 ≈ 1 条 name+description；
- 自然语言触发满足"@该 skill + 自然语言"的使用方式。

### 4.2 纠正一个过时前提

"有些 Agent（如 Claude Code）不支持同时使用多个 skill"——**在 2026-11 的 Claude Code 文档下已不成立**：
- catalog 常驻全部 skill 的 name+description，按需加载多个；
- 交互终端一条消息可**堆叠最多 6 个 skill**（第一个 + 最多 5 个）；
- subagent frontmatter 可**预载多个 skill** 全文；
- plugin 可捆绑多个 skill（命名空间 `/plugin:skill`）；
- 但"多个 skill 自动生效后如何协调/冲突"**官方没有定义**——这是真问题，也是 kit 的设计空间。

### 4.3 现实问题与解法

| 现实问题 | 解法 |
| --- | --- |
| 多 skill 同时激活无协调语义 | **不需要同时激活**：1 个 router skill 内部路由到 references；跨工作流靠"仓库产物契约"衔接；需要并行时用 subagent 预载不同 skill |
| 产品需求阶段还要用别的 skill | kit 把产品阶段定义为**外挂环节**：别的 skill/人产出"需求卡 + 验收判据"；`harness intake` 校验后转计划；harness skill 检测到"无验收判据"时**拒绝建计划并提示先补需求**，不自己编 |
| skill 触发不准 | description 覆盖意图关键词（接入/接手/需求/计划/验证/发布/交接/多 Agent）；AGENTS.md 写入口行；保留显式命令 |
| skill 数量膨胀、上下文税 | **只发 1 个 skill**（DSH description 截断 500 字符、Claude Code 1536 字符；控制在 ~500 字内）；references 按需读并设总 token 预算 |
| 不同 Agent 字段不兼容 | skill 只用标准 6 字段（name/description/license/compatibility/metadata/allowed-tools），Agent 私有字段放适配层 |
| skill 无法保证确定性 | skill 只做"读状态→选流程→调 CLI→校验输出"；证据/门禁由 CLI 产生；**但 CLI 产出也可被伪造，见 §3.7** |
| 分发与版本漂移 | 仓库内安装（默认，随项目 pin，可 diff）；全局插件（可选）；`harness upgrade` + `harness status` 检测版本 |
| 不支持 skill 的 Agent | AGENTS.md 入口行 + `harness status` CLI；提示词库降级为 fallback |
| 安全 | skill 是文本指令，不执行代码；CLI 只读/写仓库内文件；插件包无第三方依赖（见 §5） |

### 4.4 形态对比（为什么是 skill + CLI，而不是别的）

| 形态 | 零学习成本 | 确定性 | 跨 Agent | 上下文成本 | 判断 |
| --- | --- | --- | --- | --- | --- |
| 现在的提示词库（24 文件/21 条目） | ❌ 要查、要复制、要粘 | 中（靠模型执行） | 是 | 低（不进上下文） | 保留为 fallback/维护者工具 |
| 纯 skills（多条平级） | 中（能触发） | 低（全靠模型） | 是 | **高**（每个名字+描述常驻） | ❌ |
| 纯 CLI + AGENTS.md | 中（要记命令） | **高** | 是 | 低 | **必选底座（A）** |
| MCP server | 中（要注册） | 高 | 部分（需客户端支持） | 中 | 过度设计，不选 |
| **1 个 router skill + CLI + references** | **高** | **高** | **是** | **低** | ✅ 待 A/B 后决定 |
| Agent 专属插件（DSH bundle / CC plugin） | 高 | 高（薄） | 否（按厂商） | 低 | 可选分发层（§5，暂缓） |

### 4.5 产品需求阶段怎么衔接（不膨胀核心）

生命周期分两段：

```text
[产品定义段]  概念 → PRD/需求 → 优先级/验收判据     ← 外部工具/产品 skill/人（kit 不覆盖）
      │  交接物：需求卡（外部链接或 docs/product/requirements/<id>.md）
      ▼
[工程交付段]  intake → 计划 → 实现 → 验证 → 评审 → 发布 → 交接 → 归档   ← harness-kit 主战场
```

- 需求卡 schema（最小，机检）：`目标` / `非目标` / `验收判据`（每条 = 命令 + 期望结果，或可复核链接 + 复核者）/ `干系人` / `优先级`。
- `harness intake`：校验每条判据可执行或可复核 → 生成计划骨架（含 `acceptance`、`verify`、`scope` 建议）→ 人确认；**缺判据 → 拒绝并给"先补哪三项"**；kit 不替 Agent 编验收标准。
- 可选 `harness-product` addon skill（独立安装、独立版本）：只做"需求 → 验收判据"，供没有产品 skill 的用户；不塞进核心 skill。
- 与别的产品 skill 的关系：**不抢活、不并发激活**；产品 skill 产出文件，harness skill 读文件并接管。多 skill 组合的稳定接口是**仓库产物**，不是会话内的技能栈。

---

## 5. DSH 插件评估（问题 2 后半）

### 5.1 事实：DSH 的可扩展面（Desktop runtime 0.2.2-rc.1 + 官方文档，详见 `dsh-extensibility.md`）

| 事实 | 关键细节 | 置信 |
| --- | --- | --- |
| 可分发单元 = **bundle**（npm 包） | `package.json` 声明 `dsh.bundle.patch`（指向 `cordis.patch.yml`）；可选 `engines.dsh` 版本门槛；profile `dsh.profile.bundles` 有序选择启用哪些 bundle | 高 |
| 安装/升级 | `plugin_manager` / `dsh plugin --profile <p> add <spec>`；spec 支持 npm、本地目录、tarball、git；第三方分发走 experimental 的 custom plugin index（未签名、默认关闭） | 高 |
| 一个包能注册什么 | model tool（`ctx.tools.register`）、人类 slash command（`ctx.commands.register`）、skill（内嵌 `ctx.skills.register` 或 provider `registerProvider`）、GUI slot/panel、后台 service/事件监听、MCP 配置 | 高 |
| **包可携带 skill** | 官方"随包 skill 提供方"先例：`dsh-skill-badge`、`dsh-skill-office`；skill-only bundle `dsh-experimental-badge-skill-bundle` 的唯一 row 即 provider | 高 |
| skill 机制 | 发现根 `.dsh/skills`(rank100) → `.agents/skills`(rank200) → 用户级；只扫一层；frontmatter 必填 name+description，可选 whenToUse；**catalog 只给 name+截断 description（默认 500 字符），whenToUse 不进 catalog**；正文按需加载、每次重读；支持 references/scripts/assets | 高 |
| 插件分发 skill 的作用域 | **profile 级**（对使用该 profile 的所有项目生效），不是仓库级 | 高 |
| 安全模型 | 插件代码在 Host 进程内、workspace sandbox **之外**执行；安装需 full-access/审批；git 安装的 build script 需单独放行；插件 = 可执行任意代码 | 高 |
| 版本兼容 | `engines.dsh` 或 `@deepseek-ai/dsh*` peer 范围强校验；不满足直接拒绝；豁免需 exact 版本对 + `acceptRisk`；本机已见 `incompatible-version` 实例 | 高 |
| 版本来源 | Desktop runtime = 0.2.2-rc.1；本机 PATH 上 `dsh --version` = 0.2.1-rc.5——**两个版本并存，文档/测试必须写清来源** | 高 |
| 标准身份 | DSH 支持 `SKILL.md` 形态，但不在 Agent Skills/AAIF 官方 client 列表（成员身份未证实）；`whenToUse` 与 Claude Code 的 `when_to_use` 拼写不同 | 高/未证实 |

### 5.2 方案对比

| | 形态 | 安装/升级 | 跨 Agent | 能力上限 | 用户成本 | 主要失败模式 |
| --- | --- | --- | --- | --- | --- | --- |
| A 纯 skill 文件 | kit 渲染 `SKILL.md` 到目标仓 | 随项目 init/upgrade，可 diff/pin | 最好 | 仅指令+资源 | 最低 | catalog 只按 description 路由；行为无强制 |
| B 单 router skill + references | 1 个入口 + 按需 references | 同 A | 最好 | 仅指令，但可覆盖工程交付生命周期 | 低 | 路由描述不佳会漏触发；references 需模型主动读 |
| C DSH bundle 插件 | npm 包，可含 skill + tool + command + UI | profile 级安装，`engines.dsh` 强耦合 | **仅 DSH** | 最高（可注册原生 tool/command/UI/service） | 高：需 full-access/审批、装到用户 profile、影响所有项目 | API 预发布漂移；版本不兼容；代码信任风险；破坏"可退出"定位 |
| D CLI-only | 仓库 `tools/harness` | 随项目 | 最好（任何能跑 shell 的 Agent） | 高（确定性执行） | 中（要记命令） | 模型不知道何时跑；输出需结构化 |
| E MCP server | kit 提供 tools | 需起进程/配置 MCP | 较好（MCP 通用） | 仅 tools | 中 | 多一个运行时与生命周期；kit 无需引入 |

### 5.3 结论与推荐

**主形态：D（CLI 为唯一执行体）+ A（AGENTS 入口）为必选；B（单总控 skill）待 A/B 后决定；C 不在 v0.3 主路径。**

理由：
1. kit 的差异化是"完成声明强制可复核"——执行体必须是 CLI/门禁/证据 JSON；skill 只是路由。把逻辑放进插件会把真源拆成两处，违反单一真源。
2. 跨 Agent 与"可退出"是定位与采用门槛：A/B/D 全满足，C 只服务 DSH，且是 profile 级运行时代码，与"不是依赖、可整目录删除"直接冲突。
3. C 的版本耦合真实存在（engines.dsh 强校验 + pre-release 漂移）；当前 DSH 为 `0.2.2-rc.1`，插件的每次升级都可能要求同步返工。
4. C 的安装是 full-access/审批动作，与"零学习成本"的目标用户（普通使用者）不匹配；更适合作为高级用户的可选加速器。
5. 优先级：C 为可选分发，**不得排在 M3（多 Agent 协议）之前**；放 v0.4 实验分支决策。

**如果未来做 C，只允许是薄壳**：
- 只注册 `harness_status` / `harness_check` 两个只读 tool + 可选 `/harness` 命令；全部调用仓库 `tools/harness`，不放门禁逻辑、不联网、不带长文档；
- 自带 skill 用 provider 随包分发；
- 验收必须包含：**不装插件功能完整**、卸载无残留、`engines.dsh` pin 明确、故障降级为"提示安装/使用仓库 CLI"。

**只有插件能做（skill/CLI 做不到）**：模型可直接调用的 tool（带参数 schema/输出渲染/policy）、人类 slash command（不产生 model message）、GUI 面板、Agent 生命周期/工具前后置事件监听、profile 级 skill/能力分发。

### 5.4 最小验证步骤（spike；未实测，安装需 full-access/审批）

1. 建 `kit-plugin-spike/`（不进 kit 发布物）：`package.json`（`dsh.bundle.patch`、`engines.dsh: ">=0.2.2-rc.1 <0.3.0"`、无依赖/build script）+ `cordis.patch.yml` + `index.js`（`harness_check` tool，只读调 `make check`）。
2. 用独立 `DSH_HOME`/非默认 profile 隔离安装（避免污染本机 web/desktop）。
3. 验证：`--dump-config` 出现自己的 layer、新会话工具列表出现 `harness_check` 且能返回 exit code、`/harness` 可执行、卸载后 row/依赖清理干净。
4. 记录未验证项：市场收录、Windows、跨版本矩阵、审批流程。

---

## 6. 新架构 v0.3

### 6.1 分层

```text
┌─────────────────────────────────────────────────────────────┐
│ 入口层（Agent 原生，薄）                                      │
│   AGENTS.md 入口行（必选）+ 1 个 harness skill（待 A/B）+ 可选插件│
│   用户：@harness + "接入这个项目 / 实现这个需求 / 发布"          │
├─────────────────────────────────────────────────────────────┤
│ 执行层（确定性，Python 标准库单入口）                          │
│   tools/harness：status / start / adopt / init / task /      │
│   verify / evidence / review / release / handoff / upgrade / │
│   doctor / skill install                                     │
├─────────────────────────────────────────────────────────────┤
│ 状态与证据层（仓库原生）                                       │
│   AGENTS.md 树 + references/ + harness/{config,plans,tasks,  │
│   evidence,reviews} + Makefile 目标（薄别名）                 │
├─────────────────────────────────────────────────────────────┤
│ 门禁层（可复核）                                              │
│   check_docs/check_agents/check_plan/check_hygiene/check_layers│
│   evidence + verify_claim + selftest + CI/pre-push            │
└─────────────────────────────────────────────────────────────┘
适配层（可选、薄）：DSH bundle（v0.4 决策）/ Claude Code plugin / CI / githooks
```

### 6.2 统一 CLI `harness`（v0.3.0 核心）

现状：4 个 kit 脚本 + Makefile target + `python3 tools/*.py` + `check_plan.py brief` 混用。改为**一个入口**（`tools/harness`，kit 侧 `scripts/harness`），Makefile target 保留为人类/CI 别名。

| 命令 | 作用 | 取代 | 备注 |
| --- | --- | --- | --- |
| `harness status [--json]` | 一屏状态：阶段/profile/版本 pin/active 计划/证据三值/未验证/未提交/下一步 | make resume/brief/手工读计划 | **默认只读**，Agent 冷启动第一命令；版本不一致 exit 3 |
| `harness start [--topic]` | 幂等建计划：自动 owner、scope 含计划自身、未提交段为空、建完即绿 | `make plan` + 手填 front matter | 消除首个 plan 必红 |
| `harness adopt` / `harness init` | 接入（默认 dry-run；`--apply` 显式写） | harness-adopt/harness-init | Agent 需可撤销 |
| `harness intake` | 需求卡 → 计划骨架（校验验收判据） | 无 | 产品阶段衔接 |
| `harness task list/claim/release/done` | 多 Agent 任务卡与认领 | multi-agent 提示词 | v0.3.2 |
| `harness verify [--changed]` | 按变更类型选验证命令 + 写证据 | verify-static/verify-claim/evidence 多步 | 输出 PASS/FAIL/UNVERIFIED；写证据前复核 artifact/commit |
| `harness review new/list` | 评审记录（引用 commit/证据/被评审者） | reviews 模板 + 手写 | 评审者≠作者门禁 |
| `harness release [--check]` | 发布前检查（standard 也有分级 fresh 检查） | strict 专属 release-check | 修正"standard 推荐但无发布门" |
| `harness handoff [--json]` | 交接摘要（结构化） | `check_plan.py brief` + 手写 | 含模型/角色/未决项 |
| `harness plan check` | 计划机检 | make check-plan / check_plan | |
| `harness upgrade [--check/--plan/--apply]` | 版本升级：manifest diff、逐文件回写、selftest | playbook 手工 diff | 依赖 v0.2.13 的 manifest |
| `harness doctor [--agent]` | 环境 + Agent 能力探测 | doctor.py | capability probe（§6.7） |
| `harness skill install --agent dsh,claude-code` | 安装/更新 skill | 无 | 待 A/B；单源渲染 |
| `harness prompt …` | 兼容旧命令（隐藏） | harness-prompt | v0.4 再评估删除 |

输出约定：人读默认精简（≤30 行），`--json` 机器读；错误给"原因 + 修复命令 + 需要谁决策"。

### 6.2.1 根治"计划 ↔ git 双状态对账"（P1 摩擦，不能只靠 CLI 换皮）

现状：计划里的"未提交改动"必须与 `git status` **严格互等**——改码未声明 FAIL、已声明但已提交也 FAIL；Agent 每步要维护第二份状态。这是机制摩擦，入口层解决不了。

设计（v0.3.0-alpha 落地）：
1. **按需计算，不手抄**：`harness status` 动态对比计划声明与 `git status`，输出差异；计划里不再要求 Agent 手工维护清单。
2. **分级校验**：`check_plan` 的严格互等只在 `harness verify`/`harness handoff`/CI 时执行；日常 `make check` 降为 WARN + 修复提示（不阻塞小步提交）。
3. **自动回写**：`harness verify`/`harness handoff` 生成计划"未提交改动"段（可 `--no-write`），Agent 不手抄；写完再校验。
4. **验收**：fixture 仓跑"改码→verify→commit"三步，计划与 git 不再出现假红；selftest 增加 M9（计划与 git 不一致时门禁必须红）。

### 6.3 `harness` skill（router）设计（待 A/B 通过后启用）

```markdown
---
name: harness
description: Harness Engineering 项目管理入口。接入新项目/改造存量项目、接手/继续项目、
  提需求建计划、实现/修 bug/重构、完成前验证与证据、Code Review/对抗评审、发布、
  交接换人或换 Agent、多 Agent 分工、kit 升级与自检——先运行 `harness status` 再按路由执行。
license: MIT
compatibility: 需要目标仓库已接入 harness-kit；未接入时先执行 adopt 流程
metadata: {kit: harness-kit, entry: scripts/harness, min_version: 0.3.0}
---
# harness · 项目入口
0) 先运行 `harness status`（只读）。读不到 → 判断仓库未接入 → 走 references/adopt.md。
1) 按意图路由（表略，含 11 条）。
2) 硬约束：不越 scope；不伪造证据；无证据写未验证；push/发布/删改先问人。
3) 输出固定五段：结论 / 证据（命令+退出码+evidence id）/ 未验证 / 下一步 / 需要人决策。
```

目录（单源 `harness-kit/skills/harness/`，渲染到 `.dsh/skills/harness/` 与 `.claude/skills/harness/`）：

```text
skills/harness/
├── SKILL.md                 # 路由 + 硬约束（≤120 行）
└── references/              # 初版 8 个，总预算 ≤ 1200 行；按需加载
    ├── status.md            # 冷启动/接手（读什么、怎么报告）
    ├── adopt.md             # 新项目/存量接入（profile 建议、角色）
    ├── plan.md              # 计划/需求验收/intake
    ├── build.md             # 实现/修 bug/重构/依赖升级
    ├── verify.md            # 验证矩阵/证据/三值判定/artifact 契约
    ├── review.md            # 自检/对抗评审/跨模型评审
    ├── release.md           # 发布/安全/性能
    └── collaborate.md       # 角色/任务/workstream/交接（v0.3.2 细化）
```

**为什么不是 21 个 skill**：DSH catalog 每轮常驻所有 name+description（默认截断 500 字符）；Claude Code 有 1536 字符截断与上下文税。1 个入口 + 按需 references 是同时满足"覆盖全周期"和"不拖累模型"的形态。21 个提示词条目内容**不删除**，转成 references 与 fallback。

### 6.4 安装 / 升级 / 版本 pin

- 默认（仓库模式）：`harness skill install` 把 skill 渲染进目标仓（可 diff、可 pin），`harness upgrade` 随 kit 升级一起更新；`harness status` 显示 `kitVersion` 与 skill 版本是否一致。
- 版本门禁：config `kitVersion` 从"记录"升级为"门禁校验"——不一致时 `harness status` **exit 3** 并拒绝执行写操作；strict 下 `make check` FAIL。
- **管理面清单**：v0.2.13 引入 `.harness-manifest.json`（path / sha256 / 来源模板 / kitVersion），`harness upgrade --plan` 做三方 diff（manifest hash vs 当前文件 vs 新模板），冲突不覆盖、写 `.new`。
- 回滚：`--apply` 前自动备份到 `.harness-upgrade-backup/<UTC>/`；失败可一键还原。
- 可选（插件模式）：v0.4 决策；当前不承诺。

### 6.5 多 Agent 协作机制（v0.3.2，兑现 M3）

现状：唯一 active 计划隐含"串行集成"，与"多 Agent 同时开发"矛盾。**分两步走，先简后繁**：
1. **先验证是否需要任务板**（更简单方案）：git worktree + 每个 workstream 一个计划文件 + scope 不相交 + 合并前统一 verify；先用 fixture 量冲突率/交接步数，再决定是否上任务卡。
2. 若需要，再引入：
   - **任务卡** `harness/tasks/<id>.md`：`role`（architect/implementer/reviewer）、`owner`、`model`、`scope`、`depends_on`、`acceptance`、`status`、`handoff`；
   - **认领**：`harness task claim` 写入 owner + 时间戳；同任务同时只能一个 owner；过期可回收；**不做实时锁**（Git 冲突用 merge gate 兜底）；
   - **并发语义**：从"唯一 active 计划"升级为"**唯一 active 计划 / workstream**"（默认单 workstream = 行为不变；多 workstream 时 scope 必须不相交）；
   - **证据身份**：evidence 增加可选 `agent`/`model`/`kitVersion`/`reviewedCommits`；review 必须引用被评审 commit 或 evidence id；
   - **跨模型评审门禁**（strict，可选）：L2 改动的 review 必须 `reviewer.model != author.model` 或显式豁免理由；
   - **交接**：`harness handoff --json` 输出角色、模型、进度、证据、未决决策、下一步。

### 6.6 产品阶段衔接（intake）

- 需求卡 schema（最小，机检）：目标 / 非目标 / 验收判据（每条 = 命令 + 期望结果，或可复核链接 + 复核者）/ 干系人 / 优先级。
- `harness intake`：校验判据存在且可执行/可复核 → 生成计划骨架（含 `acceptance`、`verify`、`scope` 建议）→ 人确认。
- 缺判据 → 拒绝并给"先补哪三项"；**kit 不替 Agent 编验收标准**。
- 负向 fixture：模糊判据（"体验好"）必须被拒绝；可执行判据（"`make test` exit 0"）通过。

### 6.7 自进化机制（M6，四件套 + 删除纪律；v0.3+ 交付，标注清楚）

1. **capability probe**（`harness doctor --agent`）：检测信号 = 环境变量（`CLAUDECODE`/`DSH_*`/`CODEX_*` 等）+ 可用 CLI（`--help` 能力自述）+ skill 根是否存在；输出本地 JSON（不入库）：agent、model、skills/hooks/subagents/commands/workflow 可用性；skill/AGENTS 按能力裁剪指引。1–2 天可做。
2. **版本 pin + 漂移门禁**：`kitVersion` 门禁（§6.4）；`harness upgrade --check` 比对 `.harness-manifest.json` 哈希；文档/模板单源渲染 + `--check` 防漂移（已有）。
3. **升级命令**：`harness upgrade --plan` 生成逐文件 diff 与风险提示；`--apply` 只回写 kit 管理面，跑 selftest + verify-static；回滚备份。**承诺下调为"手工升级降到一次 diff 确认"**（不再承诺全自动）。
4. **行为级评估**（v0.4，预注册）：3 个 fixture 任务（修 bug 带红测 / 加功能带验收测试 / 文档改）× 2 条件（有 kit / 无 kit）× 每条件 3 次；主指标 **false-claim acceptance rate**（构造"声称 PASS 但隐藏测试失败"的提交，看门禁是否抓住）+ 越界文件数 + 首次通过率；脚本自动计分；未达阈值不宣称收益。
5. **删除纪律**：每个 release 记录 kit 文件数/配置键/门禁数/指令 token 趋势；Agent 原生能力已覆盖的规则降级或删除；删除也写 CHANGELOG（继续 governance 九原则）。
6. **模型/角色矩阵**（文档 + 提示词）：哪类任务给哪个模型（架构/评审→强推理；批量实现→高吞吐），kit 只给建议，不硬编码。

### 6.8 反臃肿红线（继承 + 新增，**要有门禁**）

继承 governance 九原则；新增三条（红线必须可机检，否则只是愿望）：
- **入口只有 1 个**：用户/Agent 只需记住 `@harness`（或 `harness status`）；
- **skill 只做路由**：skill 里不写验证细节，细节在 references/CLI；
- **文档/技能预算**：README ≤ 200 行、skill ≤ 120 行、references 总计 ≤ 1200 行——**加入 `harness/config.json` 的 budgets 并由 `check_docs` 校验**（不能只写文档）；agent-prompts 降级为 fallback。

---

## 7. 路线图与验收（可执行判据；估时为假设：1 个 Agent、无中断，区间）

| 版本 | 内容 | 可执行验收 | 不做 |
| --- | --- | --- | --- |
| **v0.2.12**（3–5 天）证据链加固 + 定位句 | artifact 契约统一；`requireArtifact` 默认 true；verifier 从 JUnit/xcresult 重算 counts；commit 祖先/dirty 复核；**M9 伪造 PASS 测试**；计划模板补 `submitted:`/`_archive/`；README 定位句替换 | ① 伪造 fixture（0 测试 + `passed:9999` + 无 artifact + done 计划）→ `verify_claim --all` 与 `check_plan check` **非 0**；② 真实 JUnit → evidence → verify **PASS**；③ 140 tests 全绿 + 父仓 `make kit-check`（kit 镜像无 Makefile，需注明） | 不动架构、不做 CLI |
| **v0.2.13**（3–5 天）兼容与升级前置 | `.harness-manifest.json`（path/sha256/模板/kitVersion，init 写）；`kitVersion` 门禁（status exit 3）；`upgrade --plan` 三方 diff（stub 可先输出清单）；旧仓/3 profile fixture 回归；6 个项目 skills 与 router 去重决策 | ① manifest 覆盖所有 kit 管理文件（`harness-init` 后比对清单完整）；② 伪造 kitVersion 的 fixture：`harness status` exit 3；③ Android v0.2.3 风格 fixture 跑 `upgrade --plan`：0 覆盖、输出 conflict 清单；④ 3 profiles `make check` 不变 | 不做后端重构 |
| **v0.3.0-alpha**（5–8 天）入口与状态 | 统一 `harness` CLI（status/start/verify/plan check/handoff/upgrade stub）；AGENTS 入口行；**双状态对账改造**（§6.2.1）；**A/B：AGENTS+CLI vs +skill（10 任务）**；skill 单源（若 B 胜出） | ① `status --json` schema 测试：必需字段齐全、人读 ≤30 行、exit 0；版本不符 exit 3；② 5 场景命令预算（fixture 包装命令计数，基线 6-7/5-6/8-9/7-8/5-6 → 目标 ≤3/3/4/4/3；"一步"=一次工具调用）；③ 冷启动 transcript tool rounds ≤3；④ A/B 指标表落盘，B 无显著收益则只发 A；⑤ 旧命令兼容测试 | 不做多 Agent、不做插件 |
| **v0.3.0**（5–8 天）入口收尾 | skill 安装/升级（仅 A/B 胜出时）；intake；`release` 分级；doctor capability probe；文档重写（README/SPEC/adoption）；预算门禁 | ① 预算门禁：README/skill/references 超限 → `check_docs` FAIL；② intake fixture：模糊判据拒绝、可执行判据通过；③ standard `harness release --check` 在 stale 证据上 FAIL、fresh 上 PASS；④ skill 单源 drift 测试（若启用） | 不删提示词库 |
| **v0.3.1**（5–8 天）跨 Agent 实证 | 真实两 Agent 交接演练（Claude Code 设计 → DSH 实现 → Claude Code 评审）；adapters/dsh 与 claude-code 能力矩阵（修复 DSH 空适配：至少提供 skill 目录与入口说明）；迁移矩阵文档 | ① 演练记录：冷启动动作数/错误/人工转述次数，报告落 `harness/reviews/`；② 两 Agent 都能在 fixture 仓完成"接手→实现→交接"，各自 evidence 可读；③ 未验证项列表 | 不夸大"任意 Agent" |
| **v0.3.2**（1–2 周）多 Agent 协议 | workstream/任务卡/认领/证据身份/跨模型评审（先用 worktree 方案量冲突率，再决定任务板） | ① 两 Agent 并发改不相交 scope → 各自证据可合并、`status` 显示双任务；② 冲突文件/过期 claim/评审者=作者/伪造证据四类负向注入必须变红；③ 交接只需 `harness status`（fixture transcript） | 不做实时锁、不做 Agent 调度 |
| **v0.4**（持续）行为评估与插件决策 | 行为级 A/B 预注册执行；模型/角色矩阵；kit 自身 dogfood；DSH bundle spike（隔离 profile，只读 tool/command）**排在 M3 之后** | ① A/B 报告有基线、脚本、阈值；② spike 有安装/卸载/降级证据，且"不装插件功能完整"；③ 删除清单与趋势数据 | 不声称未测收益；插件不作为主入口 |

每阶段独立发布、可回滚；不改 profile/门禁的行为变化必须进 CHANGELOG。**任一阶段验收不通过 → 不进入下一阶段。**

---

## 8. 兼容与迁移（v0.2.11 → v0.3）

- **命令兼容**：`make check`/`verify-static`/`verify-claim`/`release-check`（strict）保留为 `harness` 子命令别名；现有 `tools/*.py` 继续可用；profiles 结构不变。
- **管理面与版本**：v0.2.13 引入 `.harness-manifest.json` + `kitVersion` 门禁；`harness upgrade --plan` 三方 diff（不覆盖冲突、写 `.new`、自动备份）。旧仓（Android pin v0.2.3）必须先过 v0.2.12/v0.2.13 再升 v0.3，禁止跨版本直跳。
- **技能去重**：现有 strict 3 个 skill（verify-change/handoff/red-team）与项目自有 `.dsh/skills`（本仓 6 个）→ 新 router 只做入口与路由，**不复制**已有 skill 内容；迁移期二选一：保留旧 skill 并在 router 里"委托"，或旧 skill 标 deprecated，v0.4 删除。决定与映射表写入 `docs/adapters/dsh.md`。
- **状态迁移**：唯一 active 计划 → 单 workstream（默认不动）；多 workstream 仅在新版本显式启用；不迁移历史计划文件。
- **提示词库**：保留（`harness prompt`），文档降级为"维护者/无 skill Agent 的 fallback"；v0.4 再评估删除。
- **释放流程不变**：仍走 `kit-check → verify-static → commit → mirror tag → tag clone 测试 → drift`；本次重构不跳过。
- **文档**：README/SPEC/adoption/playbook/governance 重写文案；agent-prompts 标记"生成物/fallback"；新增 `docs/why.md`（定位与卖点）、`docs/adapters/dsh.md`、`docs/adapters/claude-code.md`。

---

## 9. 待确认决策（建议默认）

| # | 决策 | 选项 | 建议默认 |
| --- | --- | --- | --- |
| D1 | 新定位措辞 | "项目管理工具" / "项目治理层" / 两者并用 | **项目管理工具（治理层）** 主句 + 治理层解释 |
| D2 | 是否更名 | 保留 harness-engineering-kit / 改短名 | **保留**（改名成本高，tag/镜像/URL 301 已有） |
| D3 | v0.3 入口 | 先做仓库 skill / 先做 DSH 插件 / 先 AGENTS+CLI | **先 AGENTS 入口 + CLI；skill 经 A/B 后决定** |
| D4 | DSH 插件 | 做产品化 / 暂缓 / 仅 spike | **暂缓**：v0.4 隔离 spike，排在 M3 之后；不作为主入口 |
| D5 | 多 Agent 并发 | 先做 / 后做 | **v0.3.2**；v0.3.0 只交付串行接力；不夸大 |
| D6 | 产品需求阶段 | 外挂 intake / 覆盖产品管理 | **外挂 intake**（不膨胀核心） |
| D7 | 本轮范围 | 只出提案 / 提案+改定位文档 | 确认后：v0.2.12 起按路线图落地；定位句在 v0.2.12 先改 |
| D8 | 提案与证据落盘 | 留在 gitignored runs / 移入 tracked reviews 并冻结 | **已执行**：移入 `harness/reviews/2026-11-11-kit-repositioning/` 并冻结（sha256 + `repro.sh`）；提交由用户确认 |
| D9 | 证据链加固是否阻断后续 | 先加固再重构 / 并行 | **阻断**：v0.2.12 的伪造 PASS 测试通过前，不进入 v0.3.0 |

---

## 10. 风险与未验证（诚实清单）

- **P0 证据可伪造**：当前 `verify_claim`/`check_plan` 信任证据自报；手写 PASS JSON 可通过 `--all`/`--fresh --strict`。v0.2.12 加固前 **M2 不得作为对外主打**。
- **"零学习成本"是目标不是现状**：需 v0.3.0 落地后用陌生 Agent/人实测；当前 usability 实测结论是否定的。
- **跨 Agent 未实测**：DSH 适配为空、Claude Code 未安装实测；"任意 Agent 可接手"需要 v0.3.1 真实演练（CC 设计→DSH 实现→CC 评审）。
- **多 Agent 并发未验证**：workstream/任务卡是设计；v0.3.2 前不对外称"支持并行"。
- **插件 API 不稳定**：DSH 0.2.2-rc 阶段；且本机 Desktop runtime 与 PATH CLI 版本不一致（0.2.2-rc.1 vs 0.2.1-rc.5）。
- **行为级收益未验证**：无 A/B 数据，不声称"接入后模型更强"。
- **确认偏误风险**：本次评估由 kit 作者（AI）主导；已用两名独立红队 + 外部事实对冲；评审本身也有局限（未实测竞品、未装 Claude Code）。
- **安全**：未做外部安全审计；插件分发引入供应链风险。
- **生态事实时效**：Claude Code / DSH / 竞品数据为 2026-11-11 快照。
- **工期不确定**：估时为单 Agent 无中断假设，可能 ±50%；不据此承诺交付日期。

---

## 11. 红队评审处置表（v2 修订记录）

| 评审意见 | 级别 | 处置 |
| --- | --- | --- |
| M2「机械否证」不成立：证据自报、可伪造 PASS | P0 | ✅ 已改口径（§3.3/§3.5）、新增威胁模型与加固路线（§3.7）；v0.2.12 设为阻断阶段（D9） |
| 路线图验收不可机检 | P0 | ✅ §7 全面改为"命令/退出码/fixture/阈值"；增加 A/B、伪造、并发、过渡演练 fixture |
| v0.2.x 旧仓升级/兼容未设计 | P1 | ✅ 新增 v0.2.13（manifest + kitVersion 门禁 + upgrade --plan）与 §8 迁移矩阵 |
| 评审/证据包在 gitignored 区、不可复现 | P1 | ✅ 记录为 D8：确认后移入 tracked `harness/reviews/` + sha256 + repro.sh；raw 留 runs |
| 数字/引用错误（文档行数、copy、CC 适配、prompts 计数、DSH 版本） | P1 | ✅ §1.2/§1.3/§5.1/§7 已逐条修正并补复算方式 |
| M6 四件套缺可落地起点 | P1 | ✅ §6.7 已具体化（probe 信号/JSON、version gate、upgrade 三方 diff、A/B 预注册） |
| M3 并行写成现状 | P1 | ✅ §0/§2.1/§2.3/§3.3/§7 全部标注"v0.3.2 路线图"，发布口径区分已交付/规划 |
| Skill 主入口未 A/B | P1 | ✅ §4.1/§7 增加 A/B 门槛与"无显著收益只发 D+A"的回退 |
| M1「任意 Agent」无跨厂商实测 | P1 | ✅ 标注未验证；v0.3.1 增加真实两 Agent 交接演练与验收 |
| 竞品"独有/空白区"过度绝对 | P2 | ✅ 改为"开箱提供/跨厂商可复用"；竞品能力标"README 未实测" |
| 全生命周期措辞膨胀 | P2 | ✅ 统一为"工程交付生命周期（不含产品定义与线上运维）" |
| selftest 覆盖被高估 | P2 | ✅ §1.1 改为 M1–M5 必跑、M6–M8 条件 SKIP |
| 红线无可机检门禁 | P2 | ✅ §6.8 预算纳入 config budgets 与 check_docs |
| intake 判据不可机检 | P2 | ✅ §6.6 schema + 负向 fixture |
| 不适用场景缺"无机读测试/无 git" | P2 | ✅ §3.4 已补 |
| 工期估算无依据 | P2 | ✅ §7 标注假设与区间；§10 标注 ±50% |

**被采纳的"更简单替代方案"**：
1. 先不引入 skill：AGENTS 入口 + CLI → A/B 证明增量收益后再加（已写入 §4.1/§7）。
2. 多 Agent 先不上任务板：worktree + 每 workstream 计划 + scope 不相交 + merge gate，量冲突率后再决定（已写入 §6.5）。
3. DSH 插件整体推迟到 v0.4 实验分支（已调整 §5.3/§7）。
4. 定位先收窄："当前单 workstream，并行 v0.3.2"（已写入 §0/§2.1）。
5. M2 先做最小可信链（artifact 重算 + commit 祖先/dirty + M9），否则降级话术（已写入 §3.7）。

---

## 附录 A：关键事实来源

- Claude Code skills / plugins / hooks / sessions / subagents / workflows / code-review：`research-ecosystem.md` §A（code.claude.com/docs/*，2026-11-11 抓取）
- Agent Skills 标准与 AAIF 捐赠：`research-ecosystem.md` §B（agentskills.io、Anthropic news，2026-10-22）
- 竞品：`research-ecosystem.md` §C（GitHub API 快照 2026-11-11；stars 抽查一致）
- DSH skill 子系统与随包提供方：DSH 仓库 `docs/subsystems/skills.zh.md`；本机 `plugin_manager list_bundles`/`list_plugins` 输出
- DSH 插件/可扩展面事实（bundle manifest、install spec、tool/command/skill 注册、安全模型、版本门槛、未验证项）：`dsh-extensibility.md`
- kit 现状与定位冲突：`positioning-audit.md` §1/§2/§6
- kit 实测成本：`usability-audit.md` §1–§5 与 `out-*.txt`（复跑 140 tests OK）
- 对抗性评审：`review-instructions.md`（P0×1/P1×4/P2×6）、`review-quality.md`（P0×2/P1×4/P2×6，含伪造证据实测）

# AI Delivery Governance 目标态设计与技术调研

> **类型**：设计输入 + 技术调研（不是 active 计划，不产生第二份任务状态）。
> **日期**：2026-11-18（2026-11-19 更新） ｜ **作者**：lead（DSH） ｜ **状态**：设计已确认；执行以 Phase 2 计划与门禁为准。
> **决策关联**：D-AI1…D-AI11（[decisions.md](../../docs/decisions.md)）；本设计建议新增 D-AI12（原生工具参与与 provenance）与 D-AI13（可移植工具链）。
> **执行计划**：[2026-11-18-ai-delivery-phase2](../plans/2026-11-18-ai-delivery-phase2.md)（本设计获批后再执行）。
> **上游案例**：[case-native-openspec-delivery.md](../../docs/case-native-openspec-delivery.md)。

## 0. 需求、结论与边界

### 0.1 需求原文要点

1. 让 **OpenSpec** 与 **Superpowers** 这两个成熟 AI Coding 工具**直接参与**需求管理流程，而不是只参考它们的方法论、自己另造一套流程。
2. 两款工具的 skill 已安装；在整个需求执行过程中**直接调用**它们的方法，保障 **prompt 质量**与**需求执行流程**。
3. 项目流程管理最终要**抽象成一套工具**，用来管理用户的所有项目。
4. 当前核心缺口不是业务实现，而是 AI 工具链集成：
   - OpenSpec CLI 已硬参与（validate / apply / archive / archived validate），但工件是手工写的，没有用 `openspec new change` 留下 scaffold provenance。
   - Superpowers v7.0.2 已安装可发现，但 L2 执行中没有被显式调用，只是“按纪律手动执行”。
   - 外部 ai-delivery-toolchain v0.3.0 新增 discipline receipt gate，但宿主尚未 pin / 集成。
   - 因此 Superpowers 的 TDD、systematic-debugging、verification-before-completion 还没有成为宿主门禁强制项。

### 0.2 结论（TL;DR）

1. **不要再写第三套流程**。目标是把两款工具变成**可机检的生命周期参与者**：OpenSpec 管行为契约与领域 prompt 模板，Superpowers 管执行纪律，Harness 管执行状态/范围/证据，工具链只做 fail-closed 审计。
2. 三处缺口对应三类新工件：**scaffold provenance 回执**（OpenSpec）、**skill invocation 回执**（Superpowers）、**discipline 回执**（v0.3.0 已实现，需 pin + 接入宿主 profile）。
3. Prompt 质量不能靠“写得认真”，应靠五段式：**CLI 生成 → 回执留痕（模板 provenance）→ 契约 lint → traceability → 独立 review**；回执只证明“用了哪版模板”，不能单独证明质量。
4. 工具抽象采用 **pinned CLI + lock + resolver cache + 宿主薄适配**，复用仓库已有的 openspec/superpowers/harness-kit resolver 模式；第一阶段不做 Dashboard、RBAC、审批流或独立后端（D-AI3）。
5. 分期（2026-11-19 调整）：外部 v0.3.1（版本卫生 + discipline pin）→ 宿主最小 pin/纪律回执 → 外部 v0.4.0（provenance / skill receipts / contract lint / offline）→ 宿主最小接入（回执 + 全量 L1–L11 lint + 一个真实试点）→ lint WARN→ERROR/pre-commit/Record/doctor/portfolio 增量 → 工具链产品化 + 第二项目 → 多仓 Change Set。
6. **诚实边界**：本地回执只能抬高“跳过纪律”的成本，不能证明 Agent 真的读了 skill；最终信任锚仍是 Git 历史 + 独立 review + CI 复算。
7. 建议**先用固定版本**（OpenSpec 2.1.0、Superpowers v7.0.2）跑通首个原生 Change，再评估 OpenSpec store/多仓与 Superpowers 升级。
8. 工具能否“管理所有项目”必须用**真实第二项目**验收，不能在本仓自证。

### 0.3 非目标（本设计的边界）

- 不重写业务代码，不改既有测试断言，不追溯改写已归档的历史 Change。
- 不做中央控制平台、Dashboard、RBAC、审批流、Agent 调度器或独立后端（D-AI3）。
- 不全局安装 Claude Code 插件或上游 hooks；不在项目里创建第二份计划/任务状态。
- 不把 `openspec status.isComplete`、`remaining==0`（无 `total>0`）或任何 ledger 当成完成判据（D-AI11）。
- 不承诺“AI 提效百分比”；只度量机制有效性与流程成本（D-AI10）。

## 1. 现状事实与缺口

### 1.1 已具备的能力

| 能力 | 现状 | 证据 |
| --- | --- | --- |
| 治理内核 | harness-kit 0.5.5，strict profile；计划/证据/范围/生命周期检查可执行 | `python3 tools/harness.py status --json`：kitVersion 0.5.5、0 active plans |
| 静态门禁 | `make check` 2026-11-18 基线 PASS（docs/harness/plan/scorecard/adapters） | 本机运行输出 |
| 证据链 | 单元 139 + UI 2/1 证据 PASS；JUnit + manifest + 提交绑定 | `harness/evidence/`；status claims |
| OpenSpec | 固定 wrapper 2.1.0；validate/archive/archived validate 已在用 | [tools/openspec](../../tools/openspec) |
| Superpowers | 固定 v7.0.2（commit `22f0b46`）缓存；15 个 skill 可读 | `~/.cache/ai-delivery-toolchain/superpowers/22f0b463...` |
| 交付门禁 v0.2.0 | 解析 Delivery Contract、tasks/复选框、scope Base..HEAD、evidence、review、CI、archive-gate | [delivery_check.py](../../tools/delivery_check.py) |
| 外部 v0.3.0 | 已打 annotated tag（`e11ae5c`），discipline receipt 已接入 delivery-check | 外部仓 `git tag` / `delivery.py:575` |
| host 适配 | Claude Code skills 单源同步 + `make doctor-skills`；pre-push 静态门禁 | `tools/adapters.py`、`.githooks/pre-push` |

### 1.2 缺口清单（本次要解决的）

| ID | 缺口 | 事实证据 | 影响 |
| --- | --- | --- | --- |
| G1 | **scaffold provenance 缺失** | 已归档 `fix-transcript-export` 有 `.openspec.yaml`；`cache-language-capabilities` 没有，属手工编写 | 无法证明工件由 `openspec new change` 产生；无法审计 schema/created |
| G2 | **Superpowers 未被显式调用** | skill 是“薄入口 + 人工读”；L2 执行没有调用回执 | TDD/调试/完成前验证仍靠自觉 |
| G3 | **discipline receipt 未 pin** | 宿主 PIN 仍为 v0.2.0（[PIN.json](../../tools/vendor/ai_delivery_toolchain/PIN.json)）；`delivery_check.py` 硬校验 `0.2.0` | v0.3.0 的 discipline gate 在宿主完全不生效 |
| G4 | **prompt/契约质量无门禁** | 只有 `openspec validate --strict`（结构）+ 人工 review | 歧义、不可验证、无 traceability 的工件可以过关 |
| G5 | **完成前验证仅靠证据门禁** | 证据可由旧产物/人工记录绕过（有 freshness 检查但无 skill 回执） | “没跑就说 PASS”只能靠 review 兜底 |
| G6 | **工具链不可移植** | 宿主适配逻辑（profile 构造、PIN、Make 目标）写死在 Duiyi 仓 | 无法低成本管理第二个项目 |
| G7 | **外部仓发布卫生缺陷** | v0.3.0 tag 已存在，但 `pyproject.toml` 与 `cli.TOOLCHAIN_VERSION` 仍是 `0.2.0` | pin 进来的版本元数据不一致，供应链可审计性差 |
| G8 | **无跨项目运营面** | 没有项目注册表、升级检查、组合状态 | “管理所有项目”缺少最小操作面 |

### 1.3 对本项目的含义

- 这不是一次“补工具”的改动，而是**把流程真源从‘人读文档’迁移到‘机检回执’**；因此必须按 L2 处理：完整方案 + 独立对抗审查 + 用户确认后执行。
- 不能只 pin v0.3.0 就宣布完成：v0.3.0 只覆盖 discipline 一致性，仍不覆盖 G1/G4/G5 的 skill 显式调用与 provenance。
- 不能把回执当成“防伪”；回执的价值是**可审计、可复算、可追责**，最终由 Git + review + CI 收口。

## 2. 外部调研：成熟企业如何落地 AI Coding 需求管理

> 调研口径：只引用可复核的官方文档、标准与公开研究；不引用“某公司提效 N%”这类不可复核数字。外链见第 11 节。

### 2.1 三类成熟范式

#### A. 契约优先的 Spec-Driven Development（SDD）

**GitHub Spec Kit**（官方文档，2026）把 SDD 拆成可编排的命令：`constitution → specify → clarify → plan → checklist → tasks → analyze → implement → converge`。关键事实：

- 定位是给 coding agent 的“结构化流程 + 可复用模板 + 可核对结果”，口号是 **intent and evidence ahead of implementation**。
- `clarify` / `checklist` / `analyze` 被明确设计成**质量门禁**：在 plan 前消除歧义、在实现前检查 spec/plan/task 一致性；`analyze` 是只读的跨工件一致性分析。
- 每阶段产出 Markdown 工件并喂给下一阶段，模板、checklist、preset/extension 都可定制；已支持 40+ coding agent 集成。
- 对本项目的含义：**“prompt 质量”可以工程化**——把每个工件的生成 prompt 变成 CLI/模板产物，而不是 Agent 自由发挥。

**AWS Kiro**（官方文档）的 requirements-first 流程：

- `requirements.md` 用 user stories + acceptance criteria，系统行为用 **EARS**（`WHEN ... THE SYSTEM SHALL ...`）；
- 然后 `design.md`、`tasks.md`；配套 **steering**（持久化项目知识）、**hooks**（生命周期事件）、**agent skills**。
- 对本项目的含义：EARS/GWT 是可直接机器 lint 的句式；steering ≈ 我们的 AGENTS.md/迁移规则层。

**OpenSpec**（Fission-AI，官方 README/文档）：

- 哲学明确：*fluid not rigid、iterative not waterfall、brownfield not just greenfield、scalable from personal projects to enterprises*。
- 生命周期：`changes/<id>` 下 proposal / specs delta / design / tasks → apply → archive 合并主 specs；`validate --strict` 检查结构。
- 2.1.0 已提供 `new change`（生成 `.openspec.yaml`）、`instructions`（按工件输出增强 prompt/模板）、`validate`、`archive`、`store/workset`（多仓/多项目 beta）。
- 对本项目的含义：OpenSpec 本身就是**契约 + prompt 生成器**；我们缺的是把它的输出留痕并纳入门禁。

**Superpowers**（obra，v7.0.2 本地固定 checkout）：

- 一套 **skill 组合的软件工程方法论**：brainstorming → design → writing-plans → executing-plans / subagent-driven-development；执行期用 TDD、systematic-debugging、verification-before-completion、requesting/receiving-code-review、using-git-worktrees、finishing-a-development-branch。
- 核心纪律是“铁律”式：TDD `NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST`；完成前验证 `NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE`；调试 `NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST`。
- 上游默认依赖宿主插件/hook 做自动触发（`hooks/hooks.json` 的 SessionStart bootstrap）；我们的宿主没有装插件，所以必须**显式调用 + 留回执**，不能假设自动触发。
- 对本项目的含义：Superpowers 提供的是“执行纪律文本 + 按需脚本”，适合作为**门禁可审计的执行协议**，而不是第二套计划系统。

#### B. 需求工程与质量（企业通用）

- **EARS**（Easy Approach to Requirements Syntax）：Rolls-Royce 提出，Airbus/Bosch/Honeywell/Intel/NASA/Siemens 等使用；约束需求句式（precondition/trigger/system/response），显著降低自然语言歧义。
- **Acceptance Criteria + Given/When/Then**：把“可验收”前置到需求层；DoR/DoD 要求进入实现前判据可验证。
- **需求质量特性**：ISO/IEC/IEEE 29148 要求需求无歧义、完整、一致、可验证、可追溯等；这是 lint 规则的理论依据。
- **Traceability Matrix**：需求 → 设计 → 任务 → 测试 → 证据，逐条可追；企业审计（ISO 9001/DO-178C 等）常用。
- **ADR / Decision Log + Glossary**：决策与术语唯一表，避免多个文档复制结论（本项目已有 D1–D7 / D-AI 系列与 GLOSSARY 实践）。
- 对本项目的含义：把 **DoR/DoD 变成可执行 lint 规则**，把 traceability 变成 Change Record 的机检字段，而不是评审时口头检查。

#### C. 治理、证据与平台化

- **DORA 2025《State of AI-assisted Software Development》**：90% 技术从业者已在工作中使用 AI，80%+ 认为提效；但研究发现 AI 是**放大器**：高绩效组织更强，弱组织问题放大；更高 AI 采用率同时关联吞吐与**不稳定度**上升，创建阶段省下的时间常被**审计与验证**吃掉。DORA AI Capabilities Model 给出 7 个放大能力：清晰的 AI 立场、健康数据生态、AI 可访问内部数据、**强版本控制**、**小批量**、用户中心、**高质量内部平台**。
- **SLSA / in-toto provenance**：provenance 是“关于工件在哪、何时、如何产生的可验证信息”；模型是 buildDefinition + runDetails 的 attestation。对本项目的类比：**receipt 就是本地交付的 attestation**，但信任锚不同（本地 Agent 无受信构建平台，所以靠 Git/CI/review）。
- **NIST AI RMF**（Govern / Map / Measure / Manage）：提供 AI 治理的功能划分，可直接映射为“规则层 / 风险分级 / 度量 / 门禁闭环”。
- **Golden Path / Paved Road / 平台工程**（Backstage Software Templates、internal developer portal 实践）：用**可复制的模板 + 自动检查**降低团队认知负担，而不是靠文档约束。
- **Agent Skills 标准**：`SKILL.md` 目录格式，2026-10 已捐给 Linux Foundation 下的 Agentic AI Foundation；70+ agent 平台接入，100 万 skill、2.8 亿次安装。说明 **skill 作为跨宿主可移植指令包**已是事实标准。
- **AGENTS.md**：被 6 万+ 开源项目使用，作为“给 agent 的 README”，说明**指令层与工具解耦**可行。
- **MCP（Jira/Linear/GitHub Issues 等）**：让 Agent 读取/更新外部需求系统；但对本项目应只做**可替换适配层**，不把外部系统变成第二真源（D-AI3/D-AI5）。

### 2.2 可复用做法清单

| 做法 | 来源 | 本项目落地 |
| --- | --- | --- |
| 每阶段工件由模板/CLI 生成，而非自由发挥 | Spec Kit / Kiro / OpenSpec `instructions` | 捕获 `openspec instructions` 输出为 prompt receipt；lint 检查模板结构 |
| 在 plan 前消除歧义 | Spec Kit `clarify` / Superpowers brainstorming | L2 intake 增加“歧义清单 + 决策记录”；brainstorming receipt |
| 需求质量 checklist 作为门禁 | Spec Kit `checklist` | contract lint + review checklist（机器可读） |
| 跨工件一致性分析 | Spec Kit `analyze` | traceability map：scenario → task → acceptance → evidence |
| 强版本控制 + 小批量 | DORA AI Capabilities Model | pinned toolchain/skills；每 Change 3–7 个任务；trunk-based |
| 证据/来源可复算 | SLSA provenance / 本项目 evidence 链 | receipt JSON + artifact sha256 + commit 祖先绑定 |
| 治理四功能闭环 | NIST AI RMF | 规则（AGENTS/references）/ 分级 / 度量 / 门禁 |
| 模板 + 自动检查替代文档约束 | Backstage templates / golden path | `ai-delivery init` + 门禁；不写“请大家遵守” |
| skill 作为可移植指令包 | Agent Skills 标准 | 固定版本 skill + hash manifest + 宿主适配 |
| 外部系统只做适配 | AGENTS.md / MCP 生态 | 需求卡 ↔ issue 单向同步；文件仍是真源 |

### 2.3 反模式与调研结论

1. **只参考方法论、不直接调用工具**：等于自造一个更差的实现；工具升级也无法受益。
2. **依赖 Agent 自动触发 skill**：不同宿主能力不同（Claude Code 有 hooks，DSH/QoderCN 没有插件），必须把“调用”变成显式命令 + 回执。
3. **把 Agent 自述当证据**：DORA 的“验证时间转移”和 Superpowers 的“evidence before claims”都指向同一结论——**没有新跑的命令输出，就不是 PASS**。
4. **把门禁做成平台**：Dashboard/RBAC/审批流会引入第二真源与运维成本，违背 D-AI3。
5. **一次铺满全部项目**：D-AI4 要求先单仓、再多仓、再第二团队；可移植性必须用真实第二项目验收。

## 3. 设计原则

- **P1 工具原生**：能用 CLI 生成/校验的，不写“请遵循”；能用官方模板的，不自造模板。
- **P2 单一真源**：契约=OpenSpec；执行状态=`tasks.md`/Change Record；证据=Harness；纪律=Superpowers；门禁=Toolchain。
- **P3 fail-closed**：缺字段、缺回执、哈希不符、版本不一致、读取失败一律非零退出，不降级 WARN。
- **P4 回执可复算**：每个回执绑定 commit/路径/sha256/命令/退出码，gate 能独立重算。
- **P5 prompt 可追溯**：每份工件的生成 prompt 有 receipt；工件改动后 validate 回执必须重签。
- **P6 信任分层**：本地回执 → 独立 review → CI 复算；不宣称本地防伪。
- **P7 薄适配**：工具链只提供 schema/校验；宿主规则留仓库；公司私有规则放 Organization Overlay。
- **P8 可移植**：pin + lock + resolver cache；一个 CLI 管理多项目；离线可复算。
- **P9 小批量**：一个 Change 一个行为，3–7 个任务；门禁错误要可操作（给修复命令）。
- **P10 演进可回滚**：先加新门禁后迁移旧工件；保留旧 PIN/旧证据；回滚需同时回退 pin、adapter、schema、证据。

## 4. 目标架构

### 4.1 五层架构

```text
┌─────────────────────────────────────────────────────────────────────┐
│ L5 运营面：ai-delivery CLI（init/adopt/pin/upgrade/doctor/report/   │
│            portfolio；可选 MCP 适配；无后端、无 Dashboard）          │
├─────────────────────────────────────────────────────────────────────┤
│ L4 门禁面：delivery-check / archive-gate / contract-lint /          │
│            provenance-gate / skill-receipt-gate / review/CI schema  │
├─────────────────────────────────────────────────────────────────────┤
│ L3 纪律面：Superpowers 固定版本 skills + phase router + receipts    │
│            TDD / systematic-debugging / verification-before-complete │
├─────────────────────────────────────────────────────────────────────┤
│ L2 契约面：OpenSpec Change（proposal/design/specs/tasks）           │
│            + .openspec.yaml provenance + instructions prompt receipt │
├─────────────────────────────────────────────────────────────────────┤
│ L1 治理内核：harness-kit（计划/证据/范围/生命周期；Change Record）   │
└─────────────────────────────────────────────────────────────────────┘
        ▲ Git 历史 / pre-commit、pre-push / CI（最终信任锚）
```

### 4.2 单一真源与职责

| 事实 | 唯一所有者 | 存放 | 不做什么 |
| --- | --- | --- | --- |
| 行为契约（外部可观察行为） | OpenSpec | `openspec/changes/<id>/` + `openspec/specs/` | 不写实现步骤流水账 |
| 执行计划与任务状态 | `tasks.md` | `openspec/changes/<id>/tasks.md` | 不第二份 checklist/ledger |
| 执行范围/验收/证据/完成判定 | Harness | `harness/records`、`harness/evidence`、`harness/reviews` | 不复制任务状态 |
| 执行纪律文本与执行方法 | Superpowers | 固定 commit 缓存 + 回执 | 不建计划、不改契约 |
| 门禁规则与实现 | ai-delivery-toolchain | 外部仓 + 宿主 PIN | 不存业务状态 |
| 变更生命周期（归档/主 specs） | OpenSpec | `openspec/archive` | 不替代完成门禁 |
| 会话级指令/规则 | AGENTS.md 指令树 + references | 仓库 | 不做机器状态 |

### 4.3 生命周期时序（G0–G8）

| 阶段 | 参与者/命令 | 产物 | 门禁 |
| --- | --- | --- | --- |
| G0 分类 | `/harness` 分级 | L0/L1/L2 结论 | L0/L1 不走 OpenSpec |
| G1 Intake | requirement card → `/harness intake` | 需求卡（目标/非目标/验收判据/干系人） | 验收判据 = 命令+期望 |
| G1.5 需求澄清 | 默认 `/superpowers` brainstorming；高风险/不可逆决策可加 `grilling`（不建第二份 plan） | 问题清单 + 候选方案 + 决策，写入 proposal/design；持久决策进 decisions.md | 触发但无 clarification receipt → lint ERROR；未触发须写一行跳过理由；grill-with-docs 暂不作门禁 |
| G2 Contract | `openspec new change` → `instructions proposal/design/specs` → 编写 | `.openspec.yaml` + 契约工件 + prompt receipts | provenance + contract lint |
| G3 Plan | `instructions tasks` → tasks.md + Delivery Contract | 唯一任务清单 | lint：复选框唯一、traceability、base |
| G4 Execute | `/superpowers` phase router + TDD / debugging | 红→绿代码、测试 | skill receipt + discipline receipt |
| G5 Evidence | Harness `make evidence` / test | JUnit + manifest + claim | evidence fresh/strict + verification skill receipt |
| G6 Review | `/superpowers requesting/receiving-code-review` + 两轴 review + red-team（高风险） | review 报告（Standards / Spec 两轴 + 归一 P0/P1/P2） | Base..Head、P0/P1 关闭 |
| G7 Complete/Archive | `delivery-check archive-gate` → `openspec archive` | 归档 + 主 specs 更新 | all_done + evidence + review + provenance |
| G8 Handoff/Release | `make handoff` / `release-check` | 交接摘要 | 未验证项单列；push/发布单独确认 |

### 4.4 运行方式：CLI 由 Agent 执行，不靠人手粘贴 prompt

先澄清三个概念：

1. `openspec instructions <artifact>` 输出的是**确定性指令块**（任务、约束、模板、检查规则），不是让 LLM 代写一段 prompt；它是当前工件阶段的“工作指令”。
2. Agent 通过自己的 shell/Bash 工具执行 CLI，**输出直接进入 Agent 上下文**；默认没有人工复制粘贴。
3. `prompt receipt` 只是把这个指令块（或其 hash + 输出文件）留痕，供门禁复核“工件是不是按该版本的指令写的”，不是给用户的操作步骤。

**三种运行模式**：

| 模式 | 谁执行 CLI | 指令如何进入 Agent | 回执 | 适用 |
| --- | --- | --- | --- | --- |
| Agent 驱动（默认） | Agent 自己跑 Bash/终端 | 工具结果直接进上下文 | CLI 自动写入 | DSH / Claude Code / Codex / QoderCN 等能执行命令的宿主 |
| 宿主受限 / GUI | 用户或宿主执行 | `--print` 输出由用户粘贴或宿主注入 | CLI 按输出内容生成，hash 不变 | 无 shell 的聊天 UI、受限沙箱 |
| CI / 自动化 | CI/脚本 | job 读取文件或标准输出 | CLI 自动写入 | 构建、审计、dry-run |

**一次 L2 会话中各步由谁执行**：

| 步骤 | 执行者 | Agent 看到什么 | 留痕 |
| --- | --- | --- | --- |
| 分级 / 接手 | Agent | `harness status` / 计划 | — |
| 建 Change | Agent | `openspec new change` 输出 | scaffold receipt |
| 写某个工件前 | Agent | `openspec instructions <artifact>` 指令块 | instruction receipt |
| 写工件 | Agent | 指令块 + 项目规则 + 领域文档 | 工件提交 |
| 校验 | Agent | `validate --strict --json` | validate receipt |
| lint / 执行 | Agent | lint issues、task brief、skill 文本 | lint 结果 / skill receipt |
| 交付完成 | Agent | `delivery-check` 输出 | evidence + review |

**最小 transcript（Agent 视角，示意）**：

```text
# 用户只说需求；Agent 携带 /harness /openspec /superpowers 工作
make resume
make change-new CHANGE=cache-language-capabilities
make change-instructions CHANGE=cache-language-capabilities ARTIFACT=proposal   # 指令块进入上下文 + 回执
# Agent 写 proposal.md
make change-instructions CHANGE=cache-language-capabilities ARTIFACT=specs
# Agent 写 specs/**/spec.md
make change-instructions CHANGE=cache-language-capabilities ARTIFACT=tasks
# Agent 写 tasks.md（含 Delivery Contract）
make change-validate CHANGE=cache-language-capabilities
make change-lint CHANGE=cache-language-capabilities
# 执行阶段
make skill-invoke SKILL=test-driven-development PHASE=tdd CHANGE=cache-language-capabilities TASK=1
# Agent 按固定版本 skill 写红测试 → 最小实现
make delivery-check CHANGE=cache-language-capabilities
# 用户确认后才 archive / commit / push
```

**关键点**：

- 用户不需要背命令、也不需要复制 prompt；命令由携带对应 skill 的 Agent 执行，用户只在质量门禁上确认（需求澄清、L2 方案/契约、例外豁免、archive/提交/推送）。
- “prompt 质量”由三部分组成：CLI 指令块（模板/约束）+ 固定版本 skill 文本 + 由 `tasks.md` 派生的 task brief；三者都有版本/哈希/回执。
- 对 subagent 场景：`ai-delivery task brief` 生成确定性 brief，可作为 subagent 的初始 prompt；receipt 绑定任务，避免“口口相传”。
- 宿主差异只影响“谁执行命令”：DSH 用原生 skill 目录与 shell；Claude Code 用 `make adapters-sync` 生成 `.claude/skills`；Codex/QoderCN 读 `AGENTS.md` + skill 目录。门禁层（Git/CI/CLI）不依赖具体宿主。

### 4.5 原生调用与宿主 wrapper 的边界（避免打折扣）

- **OpenSpec**：`make change-*` 必须是薄透传：stdout/stderr/exit 原样返回，不改变 CLI 参数与 JSON；只额外落回执。加 contract test 对比 direct CLI 与 wrapper 的输出/退出码，防止 wrapper 漂移。
- **Superpowers**：`skill receipt` 不是 skill 调用本身。Agent 必须先通过宿主原生 Skill 机制（或 Read 固定 `SKILL.md`）真正加载并执行纪律；wrapper 只记录来源与宿主实际副本哈希。禁止把 skill 逻辑复制进 Makefile，禁止用 receipt 数量代替内容执行。
- **宿主差异**：Claude Code 等有 hooks 的宿主可由 PostToolUse 自动写 receipt；DSH/QoderCN 无 hooks 时手动写 receipt，流程效果不依赖 hook。
- **原则**：wrapper 越薄越好；任何“包装后改变行为”的实现都按缺陷处理，不按风格问题处理。

## 5. 核心机制设计

### 5.1 OpenSpec 原生参与：scaffold + prompt + validate 三段回执

**流程（L2）**：

1. `openspec new change <id>` 创建目录与 `.openspec.yaml`（`schema`、`created`）。
2. 每个工件写之前，先运行 `openspec instructions <artifact> --change <id> --json`，把输出（含模板/约束）保存为 **prompt receipt**。
3. 写 `proposal.md / design.md / specs/**/spec.md / tasks.md`。
4. `openspec validate <id> --type change --strict --json`，保存 **validate receipt**（含工件树哈希、退出码、issues）。
5. Gate 复算：`.openspec.yaml` 必须被跟踪、`schema` 合法；scaffold receipt 的 `.openspec.yaml` hash 与当前一致；validate receipt 的工件树 hash 与当前一致；`created` 仅作元数据（允许 ±1 天时区差）。**不强制 instructions 回执与工件提交的先后**（同提交无法证明顺序，见 Phase 2 计划「复核处置」R1）；instructions 回执证明“取过该版本模板”，工件质量由 lint / traceability / review 承担。

**回执 schema（建议 v1）**：

```json
{
  "schemaVersion": 1,
  "kind": "openspec-scaffold",
  "change": "cache-language-capabilities",
  "base": "1961368...",
  "command": "openspec new change cache-language-capabilities",
  "exitCode": 0,
  "createdAt": "2026-11-18T10:20:00Z",
  "outputArtifact": "harness/receipts/openspec/<change>/scaffold.log",
  "outputSha256": "<64 hex>",
  "openspecYaml": "openspec/changes/<change>/.openspec.yaml",
  "openspecYamlSha256": "<64 hex>"
}
```

**prompt receipt** 记录 `artifact`、`command`、`stdoutSha256`、`artifactPath`（原始输出）、`createdAt`；**validate receipt** 记录 `artifactsSha256`（排序后的路径+hash 清单）、`validateJson` 路径与 hash。

**Gate 失败模式**（全部 fail-closed）：缺 `.openspec.yaml`；`created` 与 scaffold 回执日期相差超过 1 天；scaffold 回执缺失/哈希不符；instructions 回执缺失或输出 hash 不符；validate 回执早于最后一次工件修改（树哈希失效）；回执 artifact 未跟踪；路径越界。

> 说明：无法证明“没调用过 `new change` 的人不能手工伪造两者”，也无法从同一提交推断“先读模板后写工件”；回执 + 哈希绑定 + validate 树哈希 + review 审计把“伪造”从默认路径变成显式违规路径。

### 5.2 Superpowers 原生参与：phase router + skill receipt + discipline receipt

**Phase → Skill 路由（L2 默认）**：

| 阶段 | 必需/可选 skill | 说明 |
| --- | --- | --- |
| 需求澄清（新行为/跨模块/歧义/多方案） | `brainstorming`（默认，触发时必需）；`grilling`（高风险/不可逆/≥2 未决 tradeoff，进阶可选） | 产出写入 proposal/design，不写第二份 plan；receipt 记录 skill + 固定来源；grill-with-docs 待定 |
| 领域术语/长期决策 | `grill-with-docs`（= grilling + domain-modeling；暂不列门禁） | 默认会创建 GLOSSARY.md / docs/adr/**，与本仓“决策唯一表 + 文档预算”冲突；待 D-AI14 决策 |
| 契约编写 | `using-superpowers`（启动纪律，可选） | 声明使用哪条纪律 |
| 每个实现任务 | `test-driven-development`（必需） | 红测试失败 → 最小实现 → 全绿 |
| 失败/回归排查 | `systematic-debugging`（触发时必需） | 先根因；receipt 记录 `rootCause` |
| 完成前 | `verification-before-completion`（必需） | 必须绑定本轮 evidence ID |
| Review | `requesting-code-review` / `receiving-code-review`（按风险）+ 两轴 schema | 高风险 L2 独立 review；两轴各自给最严重问题、不跨轴排序 |
| 禁用 | `writing-plans` / stock `executing-plans` / SDD ledger | 与 D-AI11 单一计划冲突 |

**skill invocation receipt（建议 v1）**：

```json
{
  "schemaVersion": 1,
  "kind": "skill-invoked",
  "change": "cache-language-capabilities",
  "task": 1,
  "phase": "tdd",
  "skill": "test-driven-development",
  "source": {
    "project": "superpowers",
    "version": "v7.0.2",
    "commit": "22f0b463e7a5e579904dd6211a520321035526f7",
    "path": "skills/test-driven-development/SKILL.md",
    "sha256": "<64 hex>"
  },
  "host": { "name": "dsh", "version": "<host 版本>" },
  "hostSkill": { "path": "<宿主实际加载路径>", "sha256": "<宿主实际 SKILL.md hash>" },
  "invokedAt": "2026-11-18T10:40:00Z",
  "head": "<记录时 HEAD>"
}
```

- 生成方式：Agent 先按宿主原生 Skill 机制（或 Read 固定版本 `SKILL.md`）加载并执行纪律；随后 `ai-delivery skill receipt ...` 打印来源/宿主副本摘要并写回执。**receipt 不替代 skill 调用**；命令建议命名为 `skill-receipt` 以免误解。
- Gate 校验收据 `source.commit/sha256` 等于工具链内置的 **Superpowers pin manifest**（v0.4.0 新增 `skills.manifest.json`，逐 skill sha256），且 `hostSkill.root` 是本机配置声明的 root id（user-cache / claude-skills / dsh-skills 等）、`hostSkill.path` 是相对路径、`hostSkill.sha256` 等于宿主实际加载文件；回执不写绝对路径，仓库/CI 只按 root 映射复算。避免“换了版本/换了副本还声称用过”。若启用第三方 clarifier（`grilling` / `grill-with-docs`），manifest 需扩展为多来源（source repo + commit + folderHash）；当前不作为 Phase 2 强制条件。
- 与 `discipline receipt` 链接：discipline v2 增加 `skills` 引用 invocation receipt id，并补齐 `redCommand`、`redExitCode`、`redOutputSha256`、`greenEvidenceId`（承接 v0.3.0 的 red/green 字段，避免两套回执各说各话）；gate 校验调用回执与 red/green 同 task/change 且 red commit 是 green commit 的祖先。
- **信任边界**：回执是自述，不能证明“读了并遵守了”；和 v0.3.0 一样，由 Git 历史 + 独立 review + CI 复算兜底；门禁的价值是让“不调用”成为可检测的违规。

### 5.3 Prompt / 需求质量门禁（DoR/DoD 机器化）

**五段式**：

1. **Intake（DoR）**：`harness/requirements` 需求卡 → `/harness intake` 生成计划候选；L2 额外要求：非目标、歧义清单（问题/答案/决策）、外部依赖、风险级别。
2. **Prompt provenance**：每个工件写前捕获 `openspec instructions → receipt`；prompt 来自 CLI 而不是 Agent 记忆；回执只证明模板来源，不能替代质量门。
3. **Contract lint（新增 `contract-lint`）**：结构 + 质量规则：

| 规则 | 检查 | 级别 |
| --- | --- | --- |
| L1 | proposal：Why / What Changes / Out of Scope 非空；无 `TBD/TODO/待定/待补充/…` | ERROR |
| L2 | specs：每个 Requirement ≥1 Scenario；Scenario 有 WHEN + THEN；Requirement 含 `SHALL` | ERROR |
| L3 | 禁用词/歧义词（中英：尽量/大概/合理/友好/fast/enough/etc.）命中需人工确认 | WARN→review 记录 |
| L4 | tasks：Delivery Contract 字段齐全；每个 `### Task N:` 恰好 1 个复选框；全文无其他复选框 | ERROR |
| L5 | tasks：每个任务有 Files / 验证命令 / Expected；任务数 3–7（超出 WARN） | ERROR（缺失）/WARN |
| L6 | traceability（分两阶段）：`plan-lint` 只查 A# → claim 名称/任务映射；`delivery-lint` 再查 claim 实际 PASS/新鲜；每个 scenario → 至少一个 task；每个 task → 至少一个 acceptance | ERROR |
| L7 | Base 存在且是 HEAD 祖先；scope allow/deny 与 Contract 一致 | ERROR |
| L8 | design：Decisions / Risks / Verification boundary 有实义内容；≥2 备选或显式“无备选”理由 | ERROR |
| L9 | 工件自最近一次 validate 后未改动（validate receipt 绑定树哈希） | ERROR |
| L10 | 无第二份计划/任务清单（`docs/superpowers/plans`、`.superpowers/sdd`、独立 ledger） | ERROR |
| L11 | 歧义门禁：命中 intake 触发条件却无 clarification receipt（brainstorming，或高风险时的 grilling），或未记录“无需澄清理由” | ERROR |

> **Lint 范围决策（2026-11-19，DD-8）**：用户选 A，宿主接受 v0.4.0 全量 L1–L11，不再收窄为 4 条。v0.4.0 中 ERROR 级规则在 `delivery-check` 硬失败；L3 措辞、L5 任务数、L6 Covers 缺失、L11 澄清在实现中仍为 WARN，由 `make change-lint` 展示并在 review 核对；WARN→ERROR 升级列为后续增量，不在本阶段声称完成。

4. **Traceability Matrix**：由 lint 生成 `change → requirement → scenario → task → acceptance → evidence claim` 表；缺链即失败；表作为 Change Record 附件（只引用，不复制任务状态）。
5. **Review schema（hybrid，2026-11-19 起）**：front matter 不变（`base/head/reviewer/p0/p1/p2/verdict`，`delivery-check` 继续按此门禁）；正文采用两轴：`Standards`（仓库标准 + Fowler smell 基线，仓库标准优先）与 `Spec`（对照 proposal/spec/acceptance/issue）；两轴各自给最严重问题、**不跨轴排序**，但所有发现必须归一为 P0/P1/P2 并记录关闭状态；另保留 `Provenance` / `Skill discipline` / `Traceability` 三段核对。可选 `review_method` 作方法溯源，不参与门禁。执行器政策（2026-11-19 采纳）：**默认 B = mattpocock code-review**（普通代码/Spec review，宿主有 subagent 时并行两轴，快且 Spec 轴更细）；**A = 自定义两轴 prompt 兜底**（无 subagent 时）。**按风险分层**：`tools/**`、`.githooks/**`、`.github/**`、`harness/config.json` 的变更默认 A 或独立 gate-runner（因为 B 试跑未跑 delivery-check）。无论执行器，reviewer 必须复跑关键门禁或明确写“未复跑”，两轴报告不替代验证。Reviewer 独立（高风险 L2 用 red-team 输出）。

### 5.4 Harness / Toolchain 集成面

**宿主 config 扩展（建议，向后兼容）**：

```json
{
  "delivery": {
    "toolchain": "0.4.0",
    "mode": "full",
    "receipts": { "dir": "harness/receipts" },
    "provenance": { "required": true, "dir": "harness/receipts/openspec" },
    "contractLint": { "required": true, "profile": "strict" },
    "discipline": {
      "required": true,
      "dir": "harness/evidence/discipline",
      "requiredSkills": ["test-driven-development", "verification-before-completion"],
      "debuggingSkill": "systematic-debugging"
    }
  },
  "skills": {
    "superpowers": {
      "version": "v7.0.2",
      "commit": "22f0b463e7a5e579904dd6211a520321035526f7",
      "manifest": "tools/vendor/ai_delivery_toolchain/superpowers.manifest.json"
    },
    "openspec": { "version": "2.1.0", "wrapperSha256": "<64 hex>" }
  }
}
```

**Change Record v2**（只增字段，不复制任务状态）：`provenance: {scaffold, instructions, validated}`、`skills: {invocations, required}`、`discipline: {required, dir}`、`lint: {profile, resultHash}`。

**门禁入口**：

- `make change-new CHANGE=<id>`：包装 `openspec new change` + scaffold receipt。
- `make change-instructions CHANGE=<id> ARTIFACT=proposal`：包装 `openspec instructions --json` + prompt receipt。
- `make change-validate CHANGE=<id>`：包装 validate strict + validate receipt。
- `make change-lint CHANGE=<id>`：contract lint。
- `make skill-invoke SKILL=... PHASE=... CHANGE=... TASK=N`：skill receipt。
- `make delivery-check CHANGE=<id>`：v0.4.0 起同时校验 provenance + lint + discipline + skill receipts。
- `make doctor-delivery`：版本/PIN/技能发现/回执能力自检。

**hooks/CI**：

- **pre-commit（新增）**：触发条件 = 存在未归档 `openspec/changes/<id>/tasks.md`（或 active Change Record），且提交路径命中其 `Scope allow`；命中时快速校验必需回执存在、JSON 合法、哈希匹配；无 Change 的 L0/L1 代码提交不拦截（由 review/CI 抽查“该建 Change 却没建”）。绕过必须 `SKIP_AI_DELIVERY=1`，并写 waiver（理由/负责人/到期日/change），gate 可见、review 必须解释。
- **pre-push（已有）**：`make verify-static`；有 active Change 时追加 `make delivery-check`。
- **CI**：静态 job 跑 `verify-static`；PR 触达 Change 时跑 `delivery-check`（含 provenance/lint/discipline）；macOS 动态测试沿用 P0 书面豁免。

### 5.5 工具链抽象：一套工具管理所有项目

**目标形态**：把当前宿主里的“Duiyi 专用接线”抽成通用能力，仓库只保留配置与规则。

**CLI 命令面（`ai-delivery`）**：

| 命令 | 作用 | 备注 |
| --- | --- | --- |
| `init` / `adopt` | 新仓接入 / 存量仓接入（dry-run 默认）；P3 起支持 `--mode full|light-spec|light-agent` | 生成 config、wrapper、skills 适配、hooks、CI 模板 |
| `pin` / `upgrade` | 固定/升级工具链、OpenSpec、Superpowers、skill manifest | annotated tag + 哈希校验；离线 fail-closed |
| `doctor` | python/git/版本/技能发现/PIN/回执能力/当前 mode 自检 | 输出 JSON |
| `change new/instructions/validate/lint` | OpenSpec 原生参与 + 回执 | 宿主薄 wrapper 直接转调 |
| `task brief` | 由 tasks.md 生成确定性任务 brief（含必需 skill 摘要/验证命令）；只作派生视图，不持久化第二计划 | 保证 prompt 来自工件 |
| `skill invoke` / `discipline verify` | Superpowers 回执 / discipline 门禁 | 复用 v0.3.0 能力 |
| `delivery check` / `archive-gate` | 交付门禁 | 现有能力 |
| `report` | 单 Change 度量（门禁失败/返工/回执覆盖率） | 本地 JSON/Markdown |
| `portfolio status` / `upgrade --check` | 多项目聚合（只读；含 mode 与关闭的门禁） | 本地注册表，无服务端 |

**分发与 pin**：

- 工具链仓打 **annotated tag**（`v0.4.0`），发布清单含 `pyproject.toml`/CLI 版本一致性、测试、tag 对象、peeled commit、source tree、逐文件 sha256。
- 每项目保留 `PIN`/`lock`（工具链 tag+commit+file hashes、OpenSpec 2.1.0 wrapper hash、Superpowers commit + 逐 skill sha256）；PIN 校验必须覆盖列举的**全部文件**（含 `*.json`、子包与 wrapper hash），不是只校验顶层 `*.py`。
- 运行解析复用现有模式：`~/.cache/ai-delivery/<commit>` + 离线校验；宿主可选 vendored 以保证 hermetic（当前模式），迁移期两者并存。明确 **offline / online 两种门禁模式**：offline 只复算已落盘 receipt 与哈希、不调用 `npx`；online 才执行 OpenSpec 校验；`doctor` 与 CI 必须声明使用哪种模式，缺网时 fail-closed 并提示切 offline。
- 供应链：先做到“annotated tag + 哈希 + 离线复算”；Sigstore/minisign 作为 P4 可选增强。

**多项目运营**：

- 本地注册表 `~/.config/ai-delivery/projects.json`（不入库）：项目名/路径/工具链版本/最近状态。
- `ai-delivery portfolio status` 输出：active change、最近门禁结果、证据新鲜度、未验证项、PIN 漂移、waiver。
- `ai-delivery upgrade --check` 输出每个项目的升级差异与迁移步骤（不自动改仓库）。

**可选集成（P4+）**：MCP 读取 Jira/Linear/GitHub Issues → 生成 requirement card；只做 intake/状态镜像，OpenSpec/Harness 仍是真源。

### 5.6 信任模型与防伪造边界

- 回执能证明的：**声明存在、版本固定、artifact 哈希、命令/退出码、commit 顺序、evidence 引用**。
- 回执不能证明的：Agent 是否真的读/遵守 skill；人在本地是否手工伪造。
- 残余风险：PIN 的 tag/tree 是自述值、无密码学签名；同一提交下的“先读后写”不可证明；由 review + P4 签名增强承担，不在 P2 假装已解决。
- 收口手段：① 提交必须携带回执（pre-commit）；② 回执与 evidence/commit 交叉绑定（delivery-check）；③ 独立 review 抽查；④ CI 在干净 checkout 复算；⑤ 违规 bypass 留 waiver 并计入度量。
- 结论：这是“**可审计的工程纪律**”，不是“形式化证明”；与 SLSA 的分层信任思路一致，只是本地场景没有受信构建平台。

### 5.7 交付强度模式：full / light-spec / light-agent

> 用户决策（2026-11-18）：方案2/3 不单独作为目标架构，但保留为轻量模式；L0/L1 或单人项目可不接全部门禁。

| 模式 | 面向 | 主流程 | 保留的强制项 | 关闭/降级的门禁 |
| --- | --- | --- | --- | --- |
| `full`（原生） | L2 / 团队 / 多项目 | OpenSpec + Superpowers + Harness | provenance、contract lint、skill/discipline receipts、evidence、review、archive-gate | 无（仅按风险书面豁免） |
| `light-spec`（方案2 轻量） | L1 / 单人 / spec-first | OpenSpec change + tasks → 编码 | `validate --strict`；真实运行验证；不伪造 PASS | provenance / skill receipt / discipline / evidence / delivery-check / archive-gate；保留 git 保护与 changelog |
| `light-agent`（方案3 轻量） | L0/L1 / 原型 / 单人实验 | Superpowers（brainstorming → writing-plans → executing/TDD） | 真实运行验证；不删测试；不泄露密钥；破坏性操作确认 | OpenSpec 契约、tasks.md 单一状态、Harness evidence、delivery-check；允许 stock plan/ledger（此时无竞争状态） |

**模式选择与升级**：

- 项目默认 mode 写配置；change 级 L0/L1 可低于项目默认；**L2 默认必须 full**。
- L2 若在 light 模式执行 → 需要 `mode_waiver`（理由 / 负责人 / 到期日），`status / report / portfolio` 可见；到期未升级即失败。
- **单人项目默认 light**：原型/探索默认 `light-agent`；需要 spec 留痕时用 `light-spec`（项目配置显式选择）；团队/多项目建议 full。
- **light-agent 例外**：允许 stock `writing-plans` / `executing-plans`；该模式不维护 tasks.md，不存在双状态竞争。
- 升级 full 不追溯改写历史 Change。
- 模式不是质量豁免：light 只是不产出过程证据，仍然“未运行 = UNVERIFIED”。

**工具面（P3）**：

- `ai-delivery init --mode full|light-spec|light-agent`
- `ai-delivery doctor` / `portfolio status` 显示 mode 与关闭的门禁
- `ai-delivery report` 记录 mode、L2-in-light 尝试与 waiver
- Phase 2（宿主接入）只实现 full 并显式声明；P3 再引入 light 模式与 mode-aware gates。

## 6. 备选方案与取舍

| 方案 | 做法 | 优点 | 缺点 | 结论 |
| --- | --- | --- | --- | --- |
| A. 只补文档/规范 | 把纪律写进 AGENTS/references | 成本最低 | 无法机检，回到现状 | 否决 |
| B. 全自动 Agent 插件 | 装 Superpowers 插件/hooks 自动注入 | 体验最好 | 宿主绑定、不可审计、DSH/QoderCN 不支持 | 仅作可选适配 |
| C. 引入 Jira/平台做流程 | 需求/审批/仪表盘都在外部系统 | 企业习惯 | 第二真源、D-AI3 明确不做、迁移成本高 | 仅在 P4 做只读适配 |
| D. 分层 file-based + pinned CLI + 回执门禁 | 本文方案 | 可移植、可复算、离线、与现有 harness/OpenSpec 兼容 | 需要工具链 v0.4.0 + 宿主接线；有学习成本 | **推荐** |

### 6.1 单工具方案对比（为什么不只用一个工具）

| 维度 | 方案1 分层（本设计） | 方案2 只用 OpenSpec | 方案3 只用 Superpowers |
| --- | --- | --- | --- |
| 需求澄清/头脑风暴 | Superpowers brainstorming（按歧义触发 + 回执） | 无专门方法，靠对话/模板 | 最强：brainstorming；但产出是内部 design/plan，不是可校验契约 |
| 行为契约/非目标/场景 | OpenSpec proposal/design/specs + validate | 强：唯一契约源 | 无标准工件，design/plan 属内部产物 |
| 执行计划/任务状态 | tasks.md 唯一；Superpowers 不建 plan | tasks.md 唯一 | writing-plans + progress.md / SDD ledger = 第二状态，与唯一状态冲突 |
| 执行纪律（TDD/调试/验证） | Superpowers 固定版本 + 回执 | 无 | 强 |
| 证据/范围/审查/完成判定 | Harness evidence + scope + review | 无 | 部分（verification skill 只要求跑命令，不产出 Harness 证据） |
| 生命周期/归档 | OpenSpec archive + delivery archive-gate | 有 archive，但可绕过未完成任务（已实测） | 无 |
| 跨宿主可移植 | 工具链 + Git/CI 门禁，不依赖插件 | 中等（CLI 跨宿主，但纪律不强制） | 弱（依赖插件/hook 自动触发；DSH 实测无法自动触发） |
| 自洽来源 | **显式边界契约 + 单一真源 + 回执** | 单工具内部自洽 | 单工具方法自洽 |
| 失败模式 | 边界设计错误 → 双真源或误杀 | 纪律靠自觉、无证据、archive 可误归档 | 第二计划/ledger、契约漂移、宿主绑定 |
| 适用 | 多项目、有证据/审计/流程治理要求 | 人主导、以 spec 为中心的团队 | greenfield / 单 agent、自主长任务 |

**结论**：方案2/3 的“自洽”是**单工具内部自洽**；本方案追求的是**全链自洽**——明确“谁拥有哪个事实、在哪一步交接、用什么回执/门禁验证”，用显式契约消除隐式约定。D-AI11 已排除会导致双真源的计划/SDD ledger 用法；本设计继承该决策，并把边界变成可执行门禁。方案2/3 不再作为目标架构，但保留为 `5.7` 的轻量模式（L0/L1 或单人项目），用于不接全部门禁的场景。

### 6.2 吸收方案3的优点：把需求澄清升级为显式阶段

Superpowers 的 brainstorming 是需求阶段最强能力，不能只当“可选建议”。调整（已并入 4.3 / 5.2 / 5.3）：

- **触发条件**：新行为、跨模块、写不出可验证判据、存在两个以上合理方案、外部依赖不明。
- **产出**：问题清单、候选方案、决策与代价，写入 proposal 的 Why/What 与 design 的 Decisions；不产生第二份 plan。
- **回执与门禁**：clarification receipt（brainstorming 固定版本 + 输出摘要 hash；高风险可用 grilling）作为 G1.5 交接；触发但无 receipt → contract lint ERROR；未触发 → 必须写一行“无需澄清理由”。
- **与 OpenSpec 的关系**：探索用 Superpowers，固化用 OpenSpec；前后接力，不是二选一。

### 6.3 需求澄清方法选型：brainstorming vs grilling vs grill-with-docs

| 维度 | Superpowers brainstorming | grilling | grill-with-docs（= grilling + domain-modeling） |
| --- | --- | --- | --- |
| 目的 | 发现“真正要什么/为什么”，给选项与建议 | 压迫式访谈，把设计树每个决策问清 | grilling + 边问边写 GLOSSARY.md / ADR |
| 交互成本 | 低–中（v7.0.2 已减少无效问题） | 高（多轮，必须等用户逐轮回答） | 高（多轮 + 文档写入） |
| 产出 | 需求问题 / 选项 / 设计草案；映射 proposal/design | 决策树 / 推荐答案；映射 proposal/design/decisions | 同上 + GLOSSARY.md + docs/adr/** |
| 与本仓规则 | 兼容：产出进 OpenSpec，不建第二计划 | 兼容：持久决策进 docs/decisions.md | 冲突：ADR/GLOSSARY 会与“决策唯一表 + 文档预算 + 知识库收敛”竞争 |
| 可门禁性 | 已 pin（v7.0.2 + skill sha256） | 来源已 pin 在 skill lock（mattpocock/skills commit `5863806…`，folderHash），但不在 toolchain manifest | 同上；且输出落点未定 |
| 适用 | 默认 G1.5；模糊需求 | 高风险/不可逆/≥2 未决 tradeoff；用户明确要求 grill | 新领域模型且需要长期术语/决策记录；暂缓 |

**建议（两层）**：

1. **默认**：G1.5 用 `brainstorming`（触发即强制）。它负责“需求发现”，不是评审；产出写入 proposal/design，不建第二份 plan。
2. **进阶**：高风险 L2（并发 / 持久化 / 发布 / 安全 / 跨仓 / 新领域 / 不可逆）或 brainstorming 后仍有 ≥2 个未决 tradeoff → 追加 `grilling`；产出写 design 的 Decisions，持久决策写 `docs/decisions.md`。**已确认（2026-11-18）**：grilling 先在 P3 做 advisory，跑 2–3 个高风险 Change 后再决定是否升为强制。
3. **暂不启用 grill-with-docs 作为门禁（已确认 2026-11-18）**：它的默认输出（`GLOSSARY.md` + `docs/adr/**`）会与本仓“决策唯一表 + 文档预算 + 知识库收敛”冲突；现在不引入 GLOSSARY.md / docs/adr，留到 P3 由 D-AI14 决策术语/ADR 落点后再评估。
4. **门禁**：L11 接受 clarification receipt（brainstorming 或 grilling）；grilling 在 Phase 2 与 P3 初期只作 advisory（WARN）；P3 跑完 2–3 个高风险 Change 后，再决定是否扩展多来源 manifest 并升为高风险 L2 必修。

## 7. 分期路线图

| 阶段 | 交付 | 门禁/验收 | 回滚 |
| --- | --- | --- | --- |
| **P2A1 工具链 v0.3.1**（外部仓 L1/L2） | 版本卫生（pyproject/CLI/__version__ 一致）+ discipline pin + 确定性 release manifest | 全量测试 PASS；annotated tag `v0.3.1`；manifest 双跑一致 | 保留 v0.3.0 tag；只修元数据，不加新门禁 |
| **P2A2 工具链 v0.4.0**（外部仓独立 L2） | provenance gate + contract lint + skill receipts + skills manifest + offline 边界 | 全量测试 PASS；annotated tag `v0.4.0`；发布清单哈希一致 | 保留 v0.3.1 tag；新门禁默认关闭 profile |
| **P2B1 宿主最小接入**（本仓 L2，见 [phase2 计划](../plans/2026-11-18-ai-delivery-phase2.md)） | 修红基线、PIN v0.3.1/v0.4.0、profile、回执工具、全量 L1–L11 lint、traceability 语法、**一个真实 L2 试点** | fixtures 全绿、delivery-check 正负样例、试点全链 PASS、`verify-static`/`release-check` | 回退 PIN/adapter/schema/证据四件套 |
| **P2B2 宿主增量**（后续） | Record v2、pre-commit、doctor、portfolio、lint WARN→ERROR 与 severity 对齐、CI job、模式落地 | 逐项 fixture/验收 | 保留 P2B1 能力 |
| **P2C 首个原生 Change 试点** | 一个真实 L2：scaffold + instructions + lint + skill/TDD 回执 + evidence + review + archive gate | 全链 PASS + 度量记录；archive 前单独确认 | Change Record 改 blocked；保留 tasks 与补丁 |
| **P3 工具链产品化** | `ai-delivery` CLI（init/adopt/pin/doctor/report/portfolio/mode）、lock/cache、host adapters、**交付强度模式（full / light-spec / light-agent）**、多来源 skill manifest、grilling 试运行 | 第二真实项目接入 PASS；light 模式默认门禁正确降级且 L2 不可静默绕过；跑 2–3 个高风险 Change 后决定 grilling 是否强制；D-AI14 术语/ADR 落点决策；本仓切换薄 CLI 后门禁等价 | 保留 vendored 模式 |
| **P4 多仓与集成** | Change Set（D-AI5）、MCP 只读适配、Organization Overlay、可选签名 | 真实 OC/RN 或第二业务仓多仓变更 PASS | 各仓独立回滚 |
| **P5 发布/推广** | 发行说明、迁移文档、示例、度量报告 | 第二团队试用反馈 | 版本回退 |

> 本表是设计分期视图；**排期与验收的唯一源仍是 `docs/04-roadmap.md`**。Phase 2 执行时先把 P2A–P5、验收与度量口径登记到 roadmap，其他文档只引用。

## 8. 验收与度量

- **机制验收**（每阶段）：门禁正负 fixture 全绿；缺回执/错版本/错顺序/哈希不符全部非零；正常路径不被误杀；离线可复算。
- **流程度量**（P2C 起）：首次门禁通过率、返工次数、回执覆盖率、未验证项数、spec 漂移（validate 后改工件次数）、任务 cycle time、人工干预次数、单 Change 成本；写入 Change Record/report，不承诺提效百分比（D-AI10）。
- **可移植验收**（P3）：第二个真实项目按 `init → intake → change → execute → gate` 全流程跑通，且不依赖 Duiyi 专有路径/规则。
- **模式度量**（P3 起）：各模式占比、L2-in-light 尝试与 waiver 数、从 light 升级 full 的次数；作为门禁有效性审计项。

## 9. 风险与缓解

| 风险 | 表现 | 缓解 |
| --- | --- | --- |
| 回执造假 | 手工编 JSON、复用旧回执 | hash + commit 祖先 + evidence 交叉绑定 + review 抽查 + 度量异常告警 |
| 门禁疲劳 | L0/L1 也走全链、错误不可操作 | 分级路由；lint 给修复命令；pre-commit 只做快速检查 |
| 版本漂移 | toolchain/OpenSpec/Superpowers 各自升级 | 三件套统一 lock + `doctor` + `upgrade --check` |
| 宿主差异 | DSH/QoderCN 无 hooks | 强制层放 Git/CI/CLI；host hooks 仅可选增强 |
| 规范膨胀 | 新文档、第二计划、复制字段 | 单一设计文档 + decisions 表 + Record 只引用 |
| 供应链 | tag 被移动、文件被改 | annotated tag + peeled commit + tree + 逐文件哈希；离线校验 |
| 试点失败 | 首个 Change 成本过高 | 选择小行为变更；先 dry-run；允许 blocked 回滚 |
| 第二项目不兼容 | 专有路径/工具假设 | P3 必须真实项目验收；Organization Overlay 分离 |
| 轻量模式被滥用 | L2 走 light、绕过证据/纪律 | L2 禁止静默 light；`mode_waiver`（理由/负责人/到期日）+ status/report 可见 + 月审计 |

## 10. 待定问题（需用户决策）

> 需求澄清方法、轻量模式命名/默认值、light-agent 的 stock plan 例外、术语表/ADR 落点已在 2026-11-18 确认，见第 12 节；以下为其余待定项。

1. ~~外部 v0.4.0 范围~~：**已确认（2026-11-19 调整）**：拆为 v0.3.1（版本卫生 + discipline pin）+ v0.4.0（provenance/lint/skills/offline）；见第 12 节 DD-5。
2. **第二个试点项目**：用哪个真实仓库（OC/RN？frontend？另一个 iOS/工具仓？）验收可移植性？
3. **pre-commit 强度**：L2 是否默认强制回执门禁（推荐），还是只在 pre-push/archive 强制？
4. **分发模式**：长期保留 vendored PIN，还是迁移到“全局 CLI + lock + cache”（推荐 P3 迁移，保留 hermetic 选项）？
5. **OpenSpec 版本**：首个原生 Change 固定 2.1.0（推荐），还是先评估 store/多仓能力再定？
6. **是否允许 host hooks**（Claude Code）作为增强层？是否接受 Superpowers 插件自动注入？
7. **review 执行方式**：高风险 L2 是否必须独立 red-team；普通 L2 的 reviewer 由谁承担？
8. **外部集成**：P4 是否需要 Jira/Linear/GitHub Issues 只读镜像？

## 11. 参考来源

- GitHub Spec Kit 文档：https://github.github.io/spec-kit/ ｜ Agentic SDD 命令与质量门禁：https://github.github.io/spec-kit/reference/agentic-sdd.html ｜ Quickstart：https://github.github.io/spec-kit/quickstart.html
- AWS Kiro Requirements-First / EARS：https://kiro.dev/docs/specs/feature-specs/requirements-first/ ｜ Steering：https://kiro.dev/docs/steering/
- OpenSpec：https://github.com/Fission-AI/OpenSpec ｜ 文档（2.1）：https://openspec.dev/docs/
- Superpowers：https://github.com/obra/superpowers （本地固定 v7.0.2，commit `22f0b46`）
- EARS：https://alistairmavin.com/ears/
- ISO/IEC/IEEE 29148:2018：https://www.iso.org/standard/72089.html
- DORA 2025 State of AI-assisted Software Development：https://dora.dev/research/2025/dora-report/ ｜ Balancing AI tensions：https://dora.dev/insights/balancing-ai-tensions/ ｜ AI Capabilities Model：https://dora.dev/ai/capabilities-model/report/
- SLSA Provenance v1.0：https://slsa.dev/spec/v1.0/provenance ｜ in-toto：https://in-toto.io/
- NIST AI RMF：https://www.nist.gov/itl/ai-risk-management-framework
- Agent Skills（捐赠 AAIF）：https://www.anthropic.com/news/donating-agent-skills-to-the-agentic-ai-foundation ｜ https://agentskills.io/
- AGENTS.md：https://agents.md/
- Backstage Software Templates：https://backstage.io/docs/features/software-templates/
- 本仓证据：`docs/decisions.md`、`docs/case-native-openspec-delivery.md`、`harness/plans/_archive/2026-11-18-ai-delivery-phase1.md`、[PIN.json](../../tools/vendor/ai_delivery_toolchain/PIN.json)、[workflow.md](../../references/workflow.md)、[verification.md](../../references/verification.md)。

## 12. 已确认设计决策（2026-11-18）

> 本节记录用户已确认的设计选择；Phase 2 计划获批后，作为 D-AI12 / D-AI13 / D-AI14 写入 `docs/decisions.md`。

| ID | 决策 | 选择 | 影响 |
| --- | --- | --- | --- |
| DD-1 | 需求澄清方法 | 默认 `brainstorming`（触发即强制）；`grilling` 进阶可选；`grill-with-docs` 暂缓 | L11 接受 clarification receipt；grilling 先 advisory，P3 跑 2–3 个高风险 Change 后再决定是否强制 |
| DD-2 | 轻量模式命名与默认 | 名称固定为 `light-spec` / `light-agent`；**单人项目默认 light**；L2 默认 full | 配置与 CLI 用词统一；单人项目按需选子模式（原型默认 light-agent，需 spec 留痕用 light-spec） |
| DD-3 | light-agent 的计划能力 | 允许 stock `writing-plans` / `executing-plans` | 该模式不维护 tasks.md，不存在双状态竞争；light-spec 仍以 OpenSpec tasks.md 为唯一计划 |
| DD-4 | 术语表 / ADR 落点 | 现在不引入 `GLOSSARY.md` / `docs/adr`；P3 由 D-AI14 决策 | grill-with-docs 暂不作门禁；避免与“决策唯一表 + 文档预算 + 知识库收敛”冲突 |
| DD-5 | 外部 toolchain 发版 | **拆两版（2026-11-19）**：v0.3.1 = 版本卫生 + discipline pin + 确定性 release manifest；v0.4.0 = provenance + contract lint + skill receipts + skills manifest + offline | 宿主可先 pin v0.3.1 做纪律回执，再 pin v0.4.0；降低一次发布耦合风险 |
| DD-6 | Phase 2 首增量范围 | **收窄（2026-11-19）**：先做回执 + 4 条硬 lint + 一个真实 L2 试点；其余 lint/pre-commit/Record v2/doctor/portfolio 后置 | 用真实 Change 验证规则，避免规则未验证就铺满 |
| DD-7 | Review 执行器 | **按风险分层（2026-11-19）**：B 默认普通代码/Spec；`tools/**`、`.githooks/**`、`.github/**`、`harness/config.json` 默认 A 或 gate-runner | 防止默认执行器漏跑门禁 |
| DD-8 | 契约 lint 范围 | **选 A（2026-11-19）**：接受 v0.4.0 全量 L1–L11，不再收窄为 4 条；ERROR 级硬失败，L3 措辞/L5 任务数/L6 Covers 缺失/L11 澄清在 v0.4.0 仍为 WARN | WARN→ERROR 与 severity 对齐列为后续增量，不在 Phase 2 声称完成 |

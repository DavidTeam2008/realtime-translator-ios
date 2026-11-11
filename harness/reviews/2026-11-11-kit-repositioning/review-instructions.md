> 冻结副本：来源 `harness/runs/kit-eval/review-instructions.md`（2026-11-11）；原始命令输出仍在 gitignored 的 `harness/runs/kit-eval/`。
> 本文件为提案/评审冻结稿，实施记录见 `harness/plans/2026-11-06-benchmark-opensource.md` 与 `harness-kit/CHANGELOG.md`。

# 红队评审：harness-kit v0.3 重定位与重构提案（REPORT.md）

> 评审者：独立红队（非作者）。对象：`harness/runs/kit-eval/REPORT.md` 当前 501 行（工作树 2026-11-11 快照；评审期间该文件曾被并发更新，本文以当前版为准）。
> 输入：同目录 `positioning-audit.md`、`research-ecosystem.md`、`usability-audit.md`、`dsh-extensibility.md`；kit 源码 `harness-kit/` v0.2.11；根 `references/workflow.md:22-28`（红队只读协议）。
> 方法：只读对照证据与源码，未复跑会改仓库的命令；唯一写入本文件。

## 结论：**有条件通过（P0×1，必须先修订；否则不通过）**

- 定位转向、五子系统分层、入口/执行/状态拆分有证据支撑；DSH 插件结论已按 `dsh-extensibility.md:70-74,102-108` 修正（sandbox 外执行、full-access/审批、profile 级、engines 强耦合，降级为隔离 spike），与"可退出"定位不再矛盾（REPORT:15,271,281,473）。
- 但 **M2「完成可被机械否证」按当前 kit 实现不成立**：证据 JSON 的 verdict/计数/git commit/dirty/xcresult 全部自报，`verify_claim.py` 不做 provenance/artifact 校验；手写一条 PASS evidence 即可通过。这是本提案的核心差异化，必须先修口径或补信任链。
- **M3 并行、Any-Agent、Skill 主入口、路线图验收、"全生命周期"** 仍有把"计划/设计"写成现状或不可机检验收的问题（P1/P2）。

## P0/P1/P2 问题表

| 严重度 | 问题 | 证据/位置 | 影响 | 最小修复 |
|---|---|---|---|---|
| **P0-1** | **M2「机械否证」名不副实**：证据可手写、commit/dirty/artifact 均可自报 | REPORT:16,132,159,181,216（"确定性否证/已有可对外主打/skill 无法伪造"）；`harness-kit/core/tools/verify_claim.py:317-331`（信任证据自带 verdict）、`:238-240`（xcresult 仅要求非空，不校验存在/内容/哈希）、`:290-302`（freshness 只比 commit..工作树）；`evidence.py:316-317`（只校验 JSON 里 dirty=false）；`check_plan.py:646-659,677-686`（只校验证据 ID 的 verdict 字段与 commit 前缀）；`scripts/harness-selftest:16-23,242-266`（M1-M8 无"伪造 PASS"注入）；schema 字段全部来自证据自身（`evidence/schema.json:5-15,28-32,47-59`） | 对外承诺的护城河可被 Agent 伪造成本极低地绕过；用户会把它当"验真"而非"一致性检查"；M2 作为核心价值不可信 | ①出威胁模型（攻击者能改仓库/写 JSON/提交/配置 git 身份）；②M2 口径改为"提高伪造成本/发现矛盾，非防伪"或补信任链：CI 生成 evidence（OIDC/签名）+ artifact/JUnit 哈希入 commit + 校验 commit 签名/CI run id；③selftest 加 M9：手写 PASS evidence 必须被门禁拒绝；④删掉"确定性/机械否证/skill 无法伪造"作为未限定卖点 |
| **P1-1** | **M3 并行/跨 Agent 是已承诺的核心，但当前仍是"计划"**；顶层定位/README 用现在时，且与"唯一 active 计划"硬门禁冲突 | REPORT:12,57,113-114（同一仓库"接力与并行"）、:134（"多 Agent 并行…kit 独有（v0.3.2）"）、:160（当前仅唯一 active + 提示词，需 v0.3.2）、:449,474（v0.3.2/后做）；`check_plan.py:16,752-754`（>1 active 直接 FAIL） | 用户按定位买"并行"，接入后发现单 workstream；v0.3.0 的 status/start 若按单 active 设计，v0.3.2 改造要迁移状态与门禁 | 顶层定位与 v0.3.0 README 明确"v0.3.0 单 workstream；跨 Agent 并行=路线图 v0.3.2"；v0.3.0 status JSON 预留 workstream 字段；v0.3.2 给出 check_plan 升级/兼容测试与两 Agent fixture |
| **P1-2** | **Skill 主入口缺少与更简单方案的对照证据**：把"纯 CLI + AGENTS.md"直接定为后端而非候选入口；MCP/CC 原生插件未实测 | REPORT:190,221-230；`dsh-extensibility.md:85-88`（skill 只做指令/路由，D 是最低成本）；`usability-audit.md:83-95`（入口摩擦与 Top10） | 若 AGENTS 一行+CLI 已可达零学习，1 skill+10 references+渲染/同步/drift 是新增复杂度；skill 触发/描述截断是已知失败模式，未 A/B 就锁定架构 | v0.3.0-alpha 做 A/B：同一 10 个任务，变体 A=AGENTS 入口行+CLI、B=router skill+CLI；指标=首次动作步数/触发成功率/上下文 token；达不到显著收益则 B 后置（保留 D+A） |
| **P1-3** | **路线图验收多数不可机检、估算无依据、顺序有待商榷**：v0.3.0-alpha "3 步内"、v0.3.0 "命令数减半/一屏可用"、v0.3.2 "证据可合并/交接只需 status" 无 fixture/脚本；可选插件 spike（v0.3.1，3-5 天）排在 M3 协议（v0.3.2）之前 | REPORT:441-452；`:445-450`（各阶段验收/估算）；`:474`（D5 多 Agent 后做）；`dsh-extensibility.md:130-134`（spike 建议放 v0.4 实验分支） | "完成"靠自述；估算 14 个 CLI 命令+skill+10 references+文档重写在 3-5 天不现实；可选插件先于核心卖点 M3，优先级倒置 | 每阶段写可执行验收脚本/fixture（命令数基线脚本、status JSON schema、v0.3.2 两 Agent 并发 fixture + 冲突/伪造负向注入）；估算拆分并给区间；插件 spike 移到 v0.3.2 之后或 v0.4 |
| **P1-4** | **M1「任意 Agent 可接手」没有跨 Agent 证据**；DSH 适配为空、CC 适配只转发 | REPORT:158（"DSH/Claude/Codex 都能读 AGENTS+跑 CLI"）；`harness-kit/adapters/manifest.json:8`（dsh 为空）；`adapters/dsh/README.md:3-4`；`positioning-audit.md:46`；`usability-audit.md` 全部为同一 AI 会话实测 | "跨 Agent"是核心价值；真实 CC+DSH 交接可能因发现/权限/输出契约失败，当前无证据 | v0.3.0-alpha 验收加真实两 Agent 交接演练（CC 设计→DSH 实现→CC 评审），记录冷启动步数/问题；适配能力矩阵写明支持/未验证 |
| P2-1 | **M5 反臃肿与新增面未量化**：新增 1 skill+10 references+14 CLI 命令+docs why/adapters，旧 21 提示词仍保留 fallback；无总预算/删除指标 | REPORT:162,397,432-437；`usability-audit.md:22`（现有 1356 行文档）；`governance.md` 九原则 | 先加后减，"反臃肿"可能变成新增文档/命令；模型 catalog/维护成本上升 | 设可机检上限：skill ≤120 行（已有）、references 总行/token 预算、CLI help 行数、旧提示词退役条件；release 记录趋势 |
| P2-2 | **M6「自进化」部分为现状表述**：capability probe/A-B 未做，`kitVersion` 目前只是记录不是门禁 | REPORT:163,423-430,117；`positioning-audit.md:82-95`；`REPORT:403`（计划升级为门禁） | 对外"可自进化"易被理解为已验证；实际只有 version/CHANGELOG/selftest/drift | README/卖点标注"v0.3+ 交付"；`kitVersion` 门禁与 capability probe 纳入 v0.3.0 验收 |
| P2-3 | **「全生命周期」措辞残留**：§2.3 已定义"工程交付生命周期"，但 §6.3 仍写"满足全生命周期" | REPORT:95,397；`positioning-audit.md:36-49`（产品/运维段为弱/无） | 读者按字面理解包含产品/运维；边界"不做产品/不做编排"被稀释 | 全仓统一"工程交付生命周期（不含产品定义与线上运维）"；README 同句写边界 |
| P2-4 | **CC/竞品「kit 独有」「竞品无一」过度绝对**：CC hooks/scripts 也可做确定性检查；竞品证据能力仅基于 README 未实测 | REPORT:132-136,150,159；`research-ecosystem.md:27-37,101-110`（F4：竞品 evidence 能力未验证） | 对比表失真；发布后易被指出"某工具也能做"; "独有"应指开箱/跨厂商打包，不是能力空白 | 改为"开箱提供/跨厂商可复用"；竞品列标注"README 未实测"；补充 CC 原生 hooks+脚本自建对照 |
| P2-5 | **intake 验收判据"可执行或可复核"未定义机检** | REPORT:418-421,243（`harness intake` 校验"可验收"、拒绝无判据） | AI 可写模糊验收，"拒绝"规则不可复核；与 M2 同类问题 | 给 intake 判据 schema（命令+期望/可复核链接+复核者）；加 fixture 负向测试 |
| P2-6 | **v0.2.11→v0.3 迁移未列**：strict 现有 3 个 skill 与新 1 skill 的关系；unique active→workstream 的状态迁移；kitVersion 门禁升级 | REPORT:382-403,445-449；kit strict profile 3 skills（`profiles/strict.json`/`core/templates/skills/`） | 老用户升级可能冲突/丢状态或技能并存；发布说明不完整 | 写兼容矩阵与迁移命令/测试；v0.2.12 先决定 3 skills 去留与 config 迁移 |

## 被挑战的假设

1. **"M2 可机械否证"**：假设证据 JSON 是可信输入——实际是 Agent 可写文件；无 provenance、无 artifact 校验、commit 无签名、selftest 无伪造用例 → 只能"发现自述矛盾/提高成本"，不能"否证伪造"。
2. **"并行/跨 Agent 是已交付差异化"**：当前唯一 active 门禁即串行；定位与 README 用现在时，v0.3.2 才建。
3. **"任意 Agent 冷启动即可接手"**：无跨厂商实测；DSH 适配为空、CC 只转发；同一 AI 会话的 fake 测试不能替代。
4. **"1 router skill 是零学习成本最优"**：未与 AGENTS 入口行+CLI 做 A/B；skill 路由依赖 description，DSH 只截断 500 字符且 references 需模型主动读。
5. **"全生命周期"**：产品段外挂不等于覆盖；发布后/运维/运营未在边界中显式排除，仍需定义。
6. **"竞品无一主打机械否证"**：仅 README 级证据（research-ecosystem F4 自认未验证），不能下绝对结论。
7. **"3-5 天可完成 v0.3.0 主体"**：14 个 CLI 命令 + skill 渲染/安装/升级 + 10 references + 文档重写 + 兼容层，无风险评估/缓冲。
8. **"DSH 插件只做薄壳就不破坏可退出"**：thin 仍是 profile 级可执行代码；当前报告已承认冲突并降级 spike（这点通过），但 spike 优先级应让位于 M3。

## 缺失信息

- 证据可信性威胁模型与攻击测试（伪造 PASS、旧证据、替换 xcresult、脏树、伪造 commit）。
- 真实跨 Agent 交接数据（CC/DSH/Codex；发现、权限、输出契约）。
- DSH 插件安装/卸载/permission 实际测试（报告自认未实测；dsh-extensibility 未验证清单 1-3）。
- 用户/陌生 Agent 对标：谁需要"并行/审计"，愿意付出 skill/CLI 学习成本；付费/采用意愿。
- v0.3.0 各阶段可执行验收的基线数据（当前命令数、token、步骤数）与 v0.4 A/B 阈值。
- v0.2.11→v0.3 迁移与兼容矩阵、现有 strict 3 skills 的处理。
- 竞品证据能力的实测（而非 README 自述）。
- 插件/供应链安全评审与回滚方案（full-access 安装的风险接受人）。

## 最小验证清单

1. **伪造证据测试**：手写一条 PASS evidence（虚构 counts、commit=HEAD、dirty=false、xcresultPath 为空/不存在），跑 `verify_claim`、`check_plan`、`make check/release-check`；记录哪些会 PASS；在修复前不允许把 M2 写成"机械否证"。
2. **跨 Agent 演练**：真实 CC + DSH 两会话在 fixture 仓完成"设计→实现→评审"接力；记录冷启动动作数/错误/人工转述次数；验证 adapters 现状。
3. **Skill vs AGENTS+CLI A/B**：10 个相同任务，两种入口，测触发/首次动作/上下文/失败率；决定是否值得保留 skill 主入口。
4. **DSH 插件隔离 spike**：独立 `DSH_HOME`/非默认 profile + full-access 审批，安装/卸载/版本不兼容/断网降级；确认不污染现有 profile。
5. **v0.3.0 验收脚本**：fixture 仓三 profile，脚本断言"3 步内"、命令数减半的前后数字、status JSON schema、旧命令兼容测试。
6. **v0.3.2 并发 fixture**：两个 Agent/两个 workstream 改不相交 scope；冲突文件、过期 claim、评审者=作者、伪造证据四类负向注入必须变红。
7. **v0.4 A/B 预注册**：指标/阈值/样本、同任务有 kit vs 无 kit；未达阈值不宣称收益。
8. **文档/预算门禁**：新 skill/references/CLI 帮助的 token/行数上限 + 旧提示词退役条件；`kit-check` 加趋势检查。
9. **迁移演练**：v0.2.11 strict 仓升级到 v0.3，检查 3 skills→1 skill、unique active→workstream、kitVersion 门禁；无数据丢失。
10. **竞品对照复核**：至少验证 CC hooks/workflows 自建证据路径，修正"独有/空白区"表述。

## 更简单的替代方案

1. **先不引入 skill**：AGENTS.md 加一行"入口：先跑 `harness status`" + 统一 CLI；用 A/B 证明 skill 增量收益后再加，可省掉 skill 渲染/同步/drift/10 references 维护。
2. **CC 用原生 slash command/plugin、DSH 用 AGENTS+CLI**：不做跨 Agent 自定义 skill 标准；把跨厂商承诺限定为"仓库文件可被任意 Agent 读"。
3. **任务协作先不建任务板**：git worktree + 每 workstream 一个计划文件 + scope 不相交 + merge gate；先量冲突率，再决定是否上 `harness task claim`。
4. **M2 先做可信链最小版**：CI 生成 JUnit/xcresult 摘要并哈希入证据、evidence 只由 CI 写、commit 签名/CI run id 必填；否则把口号降为"提高说谎成本，不抗伪造"。
5. **把 DSH 插件整体推迟到 v0.4 实验分支**；v0.3 只交付仓库模式（CLI + AGENTS + 可选 skill），避免可选代码/distribution 占用核心路线。
6. **定位先收窄**："仓库级状态/证据/门禁工具（当前单 workstream，并行 v0.3.2）"；"多 Agent 治理层/全生命周期"等交付后再升级对外话术。

# 演化与治理 · 让 kit 跟上模型与 Agent，而不是变成累赘

> 回答两个问题：**AI coding Agent 与模型在快速进化，kit 怎么跟着变？规则加多了，会不会反而拖累 Agent？**
> 以及：**多人维护的项目怎么用 harness engineering 管理，kit 支持到什么程度？**
> 相关：[README](../README.md)（能力清单）、[adoption](adoption.md)（skill 优先接入与日常使用）、[playbook](playbook.md)（操作步骤）、[SPEC](../SPEC.md)（内部契约）。

## 0. 问题定义

harness-kit 的治理对象就是 Harness Engineering 五子系统（Instructions / State / Verification / Scope / Session Lifecycle：模板、门禁与证据见 [README](../README.md#它是什么harness-engineering-脚手架)）。下面所有"规则 / 预算 / 删除"讨论都落到这五层上。

环境在变：模型能力在变强，Agent 提供的 harness 能力（hooks / skills / subagents / memory / MCP）越来越多。对 kit 的威胁有两个方向：

1. **跟不上**：规则绑定某个 Agent/模型的私有机制，换代即失效。
2. **变得累赘**：规则越加越多 → 指令膨胀、上下文被规则占满、规则互相冲突、Agent 为了"讨好门禁"而不是"做对事"——类似"skill 越多，模型越失智"。

kit 的应对不是"写得更多"，而是**把约束尽量变成可执行的门禁，把指令压缩到最小，把变化吸收进版本与薄适配层**。

## 1. 反臃肿：九条设计原则

1. **计算型优先**：能用脚本/schema/hash 判定的，不写进指令。规则一旦可机检，就删掉对应的絮叨文字——"指令税"和"运行时门禁"不能同时收。
2. **规则必须付租金**：每条规则至少对应一个真实失败案例（失败 → 规则 → 门禁 → 负向注入用例）。没有失败案例的规则不进入模板。
3. **预算即设计**：指令层有 token 预算（模板默认根 `AGENTS.md` ≈1200、三份 references 各 ≈700、`HARNESS.md` ≈1500、`docs/README.md` ≈1000，嵌套 AGENTS 另限 `nestedMaxTokens` ≈1000；来源案例按项目调高到 1650/975，宿主按项目调）。模板渲染后的根 `AGENTS.md` 约 730 tokens，给项目留约 470；存量项目超预算用 `harness-init --agents-mode move` 迁移，不靠调高预算。新增规则顶预算时，必须删/合并旧规则，而不是调高预算。
4. **渐进披露、分层加载**：根 `AGENTS.md` 只做"目录 + 铁律 + 路由"；目录级规则放嵌套 `AGENTS.md`；细节放 `references/`；命令式流程放 skills/adapters。Agent 冷启动只读目录页，按任务再深入——不把全部规则一次塞进上下文。
5. **单一真源 + 唯一状态**：一份文档索引、一个 active 计划、一份 `harness/config.json`。同一件事写两处就是漂移源。
6. **最小核心 + 薄适配**：`core/` 只承诺与语言/Agent 无关的机制；Agent/IDE 的专属能力放 `adapters/`（可选、可丢弃）。新 Agent 出现时加适配，不动核心规则。
7. **删除优先**：模型/Agent 已能稳定做对的事，从规则降级为适配层或直接删除；维护者每个版本做一次"删除清单"。
8. **流程税分级**：L0 直接做、L1 短方案、L2 完整方案 + 审查；门禁与人工审查按风险匹配，不是所有改动都走全套流程。
9. **可退出**：kit 产物可整目录删除，不 import 进业务运行时，不成为 CI 的隐式依赖。

## 2. 演化机制：怎么跟上模型与 Agent

### 2.1 版本与契约

- `VERSION` + `CHANGELOG.md` + `SPEC.md` 是 kit 的单真源；对外发布打 tag（当前 v0.2.x）。
- **版本升级路径已验证**（v0.2.4 起文档化）：临时渲染新版 → 逐文件 diff → 只回写 kit 管理面 → `make verify-static` + `harness-selftest` 复核。**profile 升级**（minimal→standard→strict）仍未在真实项目验证——不夸大能力。

### 2.2 真实项目驱动，而不是"想当然加规则"

每个 kit 版本必须有真实仓试点，且经过门禁自测：

- 空白 Python/Node/SwiftPM 项目：init → `make check` → 证据三值。
- 真实 Android/Gradle 存量仓（brownfield 七步法）：文档蒸馏 → 宿主传感器 → JUnit 证据链 → 负向注入 → 计划归档。
- 版本升级试验：v0.2.2→v0.2.3 在真实仓完成，其中**宿主 fork 的脚本被上游化并删除**（`check_plan` / `check_hygiene` / `check_layers`）——这是"删除优先"的实例。
- 门禁自测发现的真实退化：历史清洗把门禁里的本机路径模式改成 `/local/`，`harness-selftest` 的 M5/M8 注入当场失效 → 修复。**门禁会腐烂，必须能被自测。**
- v0.3.0 真实失败：分发/入口仍是"提示词复制"与"人读文档" → router skill 单入口（显式安装）+ intake/release/doctor 能力探测；A/B 未完成前不默认启用 skill。
- v0.3.0-alpha.1 真实失败：计划「未提交改动」段与 git 双状态对账靠 Agent 手抄 → 统一入口 `harness.py verify` 自动同步；日常 `make check` 降为宽松（严格校验独立 `check-plan-strict`，由 verify/CI 使用）。
- v0.2.12 真实失败：旧 `verify_claim` 信任证据自报 counts，手写 PASS 证据可通过全部门禁 → 增加 JUnit XML 独立重算 + commit 祖先/dirty 复核 + M9（失败 → 规则 → 门禁 → 负向用例的完整闭环）。

### 2.3 模型 / Agent 能力变化的复核清单（定期或发现新能力时）

| 观察 | 处置 |
| --- | --- |
| 模型已能稳定遵守某条规则 | 从指令降级为文档提示或删除 |
| Agent 原生提供 hooks/skills/subagents/memory | 把集成移到 `adapters/`，核心只保留"文件 + shell"契约 |
| 出现新的失败模式（并行 Agent、长任务、MCP 工具、跨仓协作） | 先写真实失败案例；必要时才加规则/门禁 |
| 某条规则反复导致 Agent 绕行/成本上升 | 删除或简化；用负向用例验证仍能拦住真实失败 |

**原则：只增加"能拦住新失败"的机制，不增加"看起来更严谨"的机制。**

### 2.4 行为级评估（尚未实现，明确列为 v0.3+ 议题）

当前 kit 的测试是**结构级**的：175 个测试 + 宿主 `harness-selftest` 负向注入（M1–M9；M9 伪造 PASS 必须被拒）。它能证明"门禁按预期工作"，但证明不了"接入后 Agent 的整体表现更好"。

计划中的行为级评估（未实现，不在当前承诺内）：

- 准备 2–3 个可复现的 fixture 仓与任务；
- 同一模型/Agent 在"有 kit / 无 kit"两种设置下跑同一批任务；
- 指标：完成声明准确率（有证据 vs 自述）、越界改动率、文档一致性、修复轮数、上下文 token、任务完成时间；
- 小样本先跑，再决定是否扩；每次模型/Agent 大版本升级后复测。

在它落地之前，对外只声称"结构可验证 + 门禁有效"，不声称"Agent 能力提升 X%"。

### 2.5 复杂度预算与审计

- 每个版本记录：kit 文件数、`harness/config.json` 配置键、门禁数量、指令 token 预算占用（趋势比绝对值更重要）。
- 新增门禁/规则必须同时带：真实失败案例、负向注入用例、文档更新。
- monthly / 大改后审计（strict profile 的评分卡 + `harness/reviews/`）：五子系统复评、未验证项清零、重复失败模式转成规则或门禁。
- 删除也要写 CHANGELOG：删掉一条规则和加一条规则同样重要。

### 2.6 淘汰与降级流程

```text
提案（规则/门禁） → 真实仓试点 → 默认启用（发版） → 观察（selftest/证据/实际使用）
   → 保留 / 降级到适配或文档 / 删除（模型已吸收或成本 > 收益）
```

## 3. 多人与多 Agent 协作

### 3.1 kit 提供什么（机制层）

| 机制 | 作用 |
| --- | --- |
| 唯一 active 计划 + front matter（owner/scope/acceptance/verify） | 协调"谁在做什么、允许改什么、怎么算完成" |
| `scope.allow/deny` 与 `git status` 交叉核对 | 越界改动可见（是否"合理越界"仍由评审判断） |
| 证据三值 + `git.commit` 绑定 + done/submitted | 谁在哪个提交上声称了什么，可复核 |
| CI / pre-push 适配 | 全队统一闸门；宿主可加 required checks |
| `plan.py brief` + 交接约定 | 换人/换 Agent/换会话可恢复 |

### 3.2 团队必须自己提供的（治理层）

kit 不是权限系统，也不替代代码评审：

- 分支保护 + required status checks（来源案例：`static gates` 必过、管理员也受限）；
- PR/MR 流程、CODEOWNERS、评审规则、issue/PR 模板；
- 权限/RBAC、密钥管理、发布权限；
- 发布节奏与版本 tag。

### 3.3 推荐协作流程

1. **集成分支只有一个 active 计划**；计划里写 owner、scope、验收与验证命令。
2. 每人/每 Agent 在 feature branch 或 worktree 工作；分支上可各自维护计划，合并前 rebase 并更新"未提交改动/进度"。
3. PR 描述引用 evidence id 或门禁输出；required checks 必须绿；review 关注"语义正确性"，不重复门禁能判的事。
4. 合并后更新计划（done + submitted 或进入下一阶段），归档到 `_archive/`。
5. **并行 Agent**：先约定写作用域（文件/目录不重叠），各自生成绑定 commit 的证据，合并前统一跑 `verify-static` + `harness-selftest`。
6. **多服务/大团队**：拆仓或每仓一套 harness（各自的 `config.json`、门禁与计划），不要把多套流程塞进一个仓库。

### 3.4 诚实的限制

- 唯一 active 计划隐含"串行集成"假设；并行分支要在合并时收敛，不能靠 kit 自动合并语义。
- kit 不能让不诚实的人变诚实：证据可伪造，只是成本变高；独立审查与评分卡仍是必要的。
- kit 不提供工单/沟通/审批系统；这些在 GitHub/GitLab/飞书等外部系统。
- **多人采用、人类陌生人首访、profile 升级仍未验证**（见 README「局限与未验证」）。

## 4. 什么时候该踩刹车

出现以下信号，说明 harness 可能正在变成负担，应做一轮删减/复评：

- 门禁变红没人修，开始加白名单、删检查或跳过 CI；
- 指令层顶预算，新增规则必须靠删旧规则才能进（先问"这条真的需要写进指令吗"）；
- 同一条规则连续两次失败/被绕过；
- Agent 开始"为了过门禁"写最小合规动作，而不是为了做对；
- 接入后交付速度明显下降、但证据质量没有提升；
- `harness-selftest` 变红（门禁空转/失效）——立即修复，禁止发布。

处置顺序：删除/合并规则 → 降级门禁 → 退回 minimal → 重新做真实仓试点。

## 5. 当前状态（2026-11-10）

- **结构层已闭环**：175 个 kit 测试 + 宿主 `harness-selftest`（M1–M9）+ 两个真实仓案例。
- **演化机制已部分硬化**：版本升级路径、负向注入、评分卡、删除优先原则、CHANGELOG/SPEC。
- **未实现**：行为级 A/B 评估；多人并行协作的真实试点；profile 升级验证。
- 这些缺口写在 README 与 `SPEC §10`，不隐藏、不夸大——**知道边界本身就是 harness 的一部分**。

# 案例：原生 OpenSpec 作为唯一执行计划（可行性 + 目标态）

> **类型**：带证据的可行性案例 + 目标态方案；不是 active 计划，不产生第二份任务状态。
> **结论日期**：2026-11-17
> **决策**：D-AI11。P0 仍按 D-AI2 旧契约执行，本方案从 P0 收口后的下一个 L2 Change 生效。
> **固定版本**：OpenSpec `2.1.0`（commit `8bd4b35`）；Superpowers `v7.0.2`（commit `22f0b46`）。

## 1. 结论

原生 OpenSpec 可以作为唯一执行计划，但必须补四层约束：

1. `tasks.md` 是**唯一计划与任务状态**：不另建 Harness 任务清单，不另建 Superpowers `plan.md`，也不让 SDD ledger 成为恢复判据。
2. `tasks.md` 必须携带 **Delivery Contract**（base / scope / acceptance / verify / evidence / review / archive gate），因为 OpenSpec 只校验结构，不校验这些交付语义。
3. 执行由 Superpowers 纪律承担，完成判定由 Harness 承担；**OpenSpec 的 `status.isComplete` 和 `archive` 都不是交付完成判据**。
4. `delivery-check`、tasks/ledger 冲突处理、Change Record 单一真源和回滚路径必须在首个原生 Change 前实现；本案例不是现行规范，P0 收口前不生效。

一句话边界：**OpenSpec 管“行为契约和任务清单”，Superpowers 管“怎么执行”，Harness 管“是否真的完成”，Git/CI 管“是否允许合并和发布”。**

> 2026-11-17 复核结论：**有条件通过**。以下门禁是首个原生 Change 的前置条件，不是当前仓库已有能力；三项硬缺口目前均无自动门禁。

## 2. 可行性证据（2026-11-17）

在临时夹具中复制当前 `fix-transcript-export`，只替换 `tasks.md` 后执行。夹具不是宿主证据，命令与结果可复核。

| 检查 | 命令 | 结果 | 结论 |
| --- | --- | --- | --- |
| 严格校验 | `openspec validate fix-transcript-export --type change --strict --json` | `valid=true`、`failed=0` | Delivery Contract + 任务清单可通过严格校验 |
| 执行视图 | `openspec instructions apply --change fix-transcript-export --json` | `state=ready`、`total=5`、`remaining=5` | OpenSpec 能识别任务清单并给出进度 |
| 状态语义 | `openspec status --change fix-transcript-export --json` | `isPlanningComplete=true`、`isComplete=true`，但任务仍 0/5 | `isComplete` 是**工件完成**，不是任务完成 |
| 归档行为 | `openspec archive fix-transcript-export --yes --json` | 退出 0，`archivedAs=...`、`specsUpdated=true`，任务仍 0/5 | `--yes`/人工确认可绕过未完成任务；JSON 无 `--yes` 会以 `archive_tasks_incomplete` 阻断 |
| 归档后校验 | `openspec validate --archived --json` | 退出 1：`5 incomplete tasks (0/5 completed)` | 事后校验能发现，但归档已经发生，不能作为唯一门禁 |
| 任务视图兼容 | `openspec instructions apply` 读取“每任务一个复选框 + 非复选框步骤” | `total=2`，与两个 Superpowers 任务一致 | 可用“任务级复选框 + 步骤级普通列表”同时满足两边 |
| 嵌套复选框 | `openspec instructions apply` 读取每个步骤都是 `- [ ]` 的清单 | `total=6`，把 3 个步骤当成 3 个任务 | **禁止**在 L2 `tasks.md` 中使用嵌套复选框 |
| Superpowers 抽取 | `executing-plans/scripts/task-start ... 1` | 成功抽取 `### Task 1` 的 brief 并打印 BASE | 只证明输入格式可抽取，**不证明 ledger 完成状态兼容** |

2026-11-17 对当前宿主做只读复核：`validate --strict` 为 `valid=true`，`status.isComplete=true`，但 `instructions apply` 同时返回 `total=0 / complete=0 / remaining=0 / state=blocked`。这证明只检查 `remaining==0` 会把“没有任务”当成完成；归档门禁还必须检查 `total>0` 与 `state=all_done`。

关键兼容性红线：

- **每个执行任务只允许一个 `- [ ]`**；步骤用 `1.`、`2.` 或普通 `-` 列表，不能用 `- [ ]`，否则 OpenSpec 任务总数会被放大。
- `tasks.md` 全文只能含任务级复选框；代码围栏、注释和示例里的复选框也会被 OpenSpec 计数。门禁必须校验 `OpenSpec total == ### Task N: 标题数`。
- Delivery Contract 的 acceptance / verify / evidence 条目也用普通 `-`，不要用复选框。
- 任务标题使用英文 `### Task N:`；这是 Superpowers `task-brief` 的解析锚点，正文可以中文。
- 不使用 `superpowers:writing-plans` 产出第二份计划；它默认写 `docs/superpowers/plans/`，与 `tasks.md` 竞争。
- 不用 `/openspec-apply-change` 驱动实现；OpenSpec 只作为契约、进度读取和归档工具，执行交给 Superpowers。
- 不在 `tasks.md` 里复制 Harness 证据计数；证据 ID、JUnit、manifest 仍在 Harness。
- 原版 `executing-plans` / SDD 的 `progress.md` 是恢复判据，且 `task-done` 不会同步 tasks；完成状态适配与冲突负向测试前，不得用于 L2 执行。

## 3. 术语与状态边界

| 术语 | 定义 | 唯一所有者 |
| --- | --- | --- |
| Change | 一个外部可观察行为变化；OpenSpec 的变更单元 | OpenSpec |
| Delivery Contract | `tasks.md` 顶部的交付元数据：level / owner / scope / acceptance / verify / evidence / review / archive gate | OpenSpec 工件，`delivery-check` 审计 |
| Task | 一个可独立验证、可独立提交的执行单元；对应一个任务级复选框 | `tasks.md` |
| Plan | 执行顺序与步骤；本模式下就是 `tasks.md`，没有第二份 | `tasks.md` |
| Acceptance | 交付结果必须满足的判据；不是测试命令本身 | Delivery Contract + Harness |
| Evidence | 可独立重算的测试或静态证据：claim、JUnit、manifest、commit | Harness |
| Review | 对 spec 合规与代码质量的独立检查；高风险 L2 必须 | Harness / 审查者 |
| Archive | 契约生命周期结束，spec delta 合入主 specs；不是交付完成 | OpenSpec |
| Delivery Complete | 所有任务完成 + 验收满足 + 必需证据 PASS + 审查关闭 | Harness |
| Mergeable / Release | Delivery Complete + 仓库要求的 CI 与保护分支检查通过 | Git/CI |

必须区分三种“完成”，否则会误报：

| 状态轴 | 来源 | 何时为真 | 不能证明什么 |
| --- | --- | --- | --- |
| 工件完成 | `openspec status.isComplete` | proposal / design / specs / tasks 文件齐全 | 任务是否执行、测试是否通过 |
| 任务完成 | `tasks.md` 复选框 / `instructions apply` | 每个任务级复选框已勾选 | 验收、证据、审查、CI |
| 交付完成 | Harness evidence + acceptance + review | 全部本地交付判据满足 | CI、合并或发布是否已通过 |

## 4. 目标态架构

```text
OpenSpec Change
  proposal.md / design.md / specs/**/spec.md / tasks.md
        │  行为契约 + 唯一任务计划
        ▼
Superpowers execution discipline
  TDD / systematic-debugging / verification-before-completion
  executing-plans / SDD 仅在状态适配后启用
  using-git-worktrees / finishing-a-development-branch
        │  按 tasks.md 执行，不创造第二份计划或状态
        ▼
Harness delivery authority
  scope audit / claims / JUnit / manifest / freshness / review
        │  证明“做到哪、改哪些、是否真的完成”
        ▼
Git + CI
  required checks / CODEOWNERS / branch protection / release gate
```

ECC 在右侧作为**可选素材层**：planner / architect / reviewer / security agents、语言规则、hooks、MCP 配置。ECC 不进入真源路径，不拥有 Change、Task、Evidence 或 Archive。

## 5. `tasks.md` 规范

### 5.1 文件结构

```markdown
# Delivery Contract

- Change: fix-transcript-export
- Level: L2
- Owner: david
- Base: <change-base-commit>
- Scope allow: Duiyi/Services/Export/, Duiyi/Features/Shared/, DuiyiTests/
- Scope deny: Duiyi/Services/Speech/, Duiyi.xcodeproj/
- Acceptance: A1=导出快照在连续分享中不被覆盖（unit-tests-pass）；A2=清理只删除过期导出文件（unit-tests-pass + 人工验收记录）
- Verify: make test-one TEST=DuiyiTests/TranscriptExportServiceTests; make verify-static
- Evidence: unit-tests-pass (JUnit + manifest, required)
- Review: required；报告 harness/reviews/<change>.md，覆盖 Base..Head，P0/P1 已关闭
- Archive gate: 所有任务勾选 + Harness PASS + 必需审查关闭
- Links: proposal.md, design.md, specs/transcript-export/spec.md

## Tasks

### Task 1: 写失败回归测试

- [ ] Task 1: 红测试提交，聚焦失败原因已记录。

**Files:** `DuiyiTests/TranscriptExportServiceTests.swift`

1. 增加“准备 A、准备 B、断言 A 字节不变”的测试。
   - Expected: 失败，原因是快照被覆盖。
2. 运行 `make test-one TEST=DuiyiTests/TranscriptExportServiceTests`。
   - Expected: 一个失败用例，失败原因与预期一致。
3. 提交红测试。

### Task 2: 实现不可变快照

- [ ] Task 2: 聚焦与完整单元测试通过，证据已生成。

**Files:** `Duiyi/Services/Export/TranscriptExportService.swift`

1. 增加内容版本化快照命名。
   - Expected: 聚焦测试由红转绿。
2. 运行聚焦测试与完整单元测试。
   - Expected: 两者通过，既有断言不变。
3. 提交修复。

## Evidence

| 任务 | 证据 ID | 结果 | 环境 |
| --- | --- | --- | --- |
| Task 1-2 | `20261117T...-unit-tests-pass` | 待生成 | 模拟器 |
```

规则：

- 顶部 `# Delivery Contract` 和字段是普通列表，不是复选框。
- `Base` 是 Change 创建时记录的不可变 commit；scope 审计范围为 `Base..HEAD` 的已提交增量加当前工作树，rename/merge 也必须覆盖。
- 每个 `### Task N:` 只放一个任务级复选框；步骤用编号列表或普通列表。
- 全文不得出现其他复选框；`total` 必须等于 Task 标题数，且 Task ID 唯一、连续。
- 每个任务必须有 `Files`、验证命令、`Expected` 和提交点；任务大小控制在 1–4 小时、一个可独立审查的交付物。
- 任务复选框只在**该任务的验证命令真实通过**后勾选；不要因为代码写完就勾选。
- 证据 ID 在任务完成后写入 `## Evidence` 表；不要把 JUnit 计数复制到 `tasks.md`。
- 必需 claim 只从 Delivery Contract 的 `Evidence` 字段读取；CLI 不能通过省略参数降低要求。
- `## Tasks` 之前的 Delivery Contract 不会被 OpenSpec 解析，但会被 `delivery-check` 审计。

### 5.2 任务粒度

- 一个任务 = 一个可独立验证的行为或工程交付，不是“写代码”“补测试”这种泛任务。
- 推荐 3–7 个任务；超过 7 个先拆 Change，或确认是否 L3。
- 任务按 TDD 顺序排列：红测试 → 最小实现 → 聚焦验证 → 完整验证 → 提交。
- 任务之间共享接口时，在后一个任务的 `Files` / 步骤中写清消费的签名；不要复制前一个任务的实现。

## 6. 端到端流程与门禁

| 阶段 | 动作 | 产物 | 门禁 |
| --- | --- | --- | --- |
| G0 分类 | 按 L0/L1/L2/L3 判定 | 分级结论 | L0/L1 不走 OpenSpec；L2 进入 G1；L3 先拆 |
| G1 契约 | `openspec` 创建 change；写 proposal / design / spec delta | 行为契约 | 用户或领域 owner 确认外部行为 |
| G2 计划 | 写 `tasks.md` + Delivery Contract | 唯一计划 | `validate --strict` 通过；`apply` 为 `ready` 且 `total>0`；Task 数与复选框数一致 |
| G3 执行 | Superpowers TDD / debugging / verification；首个 Change 不用 stock executing-plans | 代码、测试、提交 | 每个任务的红→绿输出被记录；任务复选框与交付证据同步 |
| G4 证据 | 运行 Harness 证据链；生成 JUnit + manifest + claim | Evidence | 必需 claim 为 PASS；证据来自 clean 的 HEAD/祖先且通过 freshness；缺失/损坏/复用路径被拒绝 |
| G5 审查 | spec 合规 + 代码质量；高风险 L2 独立审查 | Review | 报告覆盖 Base..Head；P0/P1 关闭；P2 有排期 |
| G6 完成 | 所有任务勾选 + 验收满足 + 证据 PASS + 审查关闭 | Delivery Complete | `all_done`、`total>0`、`complete==total`、`remaining==0`；Harness PASS |
| G7 归档 | `openspec archive`；同步主 specs | Archive | 先过 delivery-check archive-gate；归档动作单独确认；归档后 `validate --archived` 通过 |
| G8 交接/发布 | `make handoff`；按发布流程 | 交接摘要 | 未验证项单列；提交/push/发布单独确认 |

### 6.1 归档门禁（必须新增）

OpenSpec 2.1.0 的 `archive` 在任务未完成时仍返回成功。因此归档前必须运行：

```bash
python3 tools/delivery_check.py archive-gate --change <change-id>
```

必需证据从 `tasks.md` 的 Delivery Contract 读取，CLI 不接受可降低要求的省略参数。该脚本至少检查：

1. `openspec validate <change> --strict` 通过，且 `tasks.md` 可解析。
2. `instructions apply` 为 `all_done`，且 `total>0`、`complete==total`、`remaining==0`；不使用 `status.isComplete`。
3. 每个 `### Task N:` 恰好一个复选框，全文无其他复选框；Task 标题数等于 `total`，ID 唯一。
4. 必需 Harness claim 为 PASS；证据来自 clean 的 HEAD 或其祖先、artifact 已跟踪、freshness 为 fresh。
5. `Base..HEAD` 加工作树的改动命中 Scope allow，不命中 Scope deny；读取失败即失败，不降级为 WARN。
6. 每条 acceptance 均有 evidence 映射或带负责人/日期的人工验收记录。
7. 必需 review 报告存在、覆盖 Base..Head 且 P0/P1 已关闭；报告缺失或范围过期即失败。
8. 仓库策略要求 CI 时，校验 run ID、attempt、commit 与必需检查结果；未配置 CI 门禁时明确写“不适用”，不得声称 CI 绿。
9. 任一 OpenSpec/Harness 命令非零、JSON 不可解析或证据缺失都 fail-closed。

归档后仍运行 `openspec validate --archived --json` 作为事后复核；它不能替代归档前门禁。archive 本身是独立写操作，即使门禁通过也必须再次获得用户确认。

**Legacy 例外**：P0 的 `fix-transcript-export` 使用指向 Harness 计划的指针型 `tasks.md`，不满足 native `total>0`。该 Change 只允许在 P0 Harness 计划验收完成、OpenSpec `validate --strict` 通过、最终 `release-check` 通过且用户单独确认后，以人工 legacy 门禁归档；不得套用 native archive-gate，也不得为过门禁伪造任务清单。该例外只适用于 P0 迁移基线。

## 7. Harness 的角色变化

### 7.1 目标态

Harness 不再保存任务清单或交付契约副本，只保存 **Change Record**：

- change ID / tasks source path / 不可变 Base；
- 当前 evidence ID 摘要、未验证项与 review 链接；
- 状态：active / done / blocked / archived；
- 指向 `tasks.md` 的 scope / acceptance / verify / evidence 字段，不复制其内容。

Change Record 不复制任务勾选状态；进度只引用 `tasks.md` 的 `complete/total` 和 Harness evidence。若工具暂时必须复制字段，必须逐字段对账且声明副本无权威性；不能形成可独立修改的第二真源。

### 7.2 过渡态

当前 `check_plan.py` 只拒绝“多于一个 active”，允许零 active；但零 active 时 `check_plan.py brief` 会失败，`make resume` 也无法给出唯一执行计划。P0 收口前：

- 保留 P0 计划作为唯一 active，不改写成新契约；
- 下一个 L2 Change 才创建新记录；
- 首个原生 Change 前必须让宿主校验器支持 `tasksSource: openspec`（读取 Contract 与 tasks），或提供逐字段对账的适配；**不能只靠复制字段的薄记录**；
- 过渡适配也属于 L2 工具改动，必须有自身测试与回滚；未完成时不得创建首个原生 Change。

### 7.3 Harness 不做什么

- 不调度子代理、不创建 worktree、不合并分支；
- 不生成任务顺序，不判断任务是否“实现得漂亮”；
- 不替代 Superpowers 的 TDD / debugging / review 纪律。

## 8. Superpowers 的接入方式

| 场景 | 使用的 skill | 约束 |
| --- | --- | --- |
| 需求不清、方案未定 | `brainstorming` | 产出设计讨论，不写第二份计划 |
| L2 实现计划 | **不调用** `writing-plans` | `tasks.md` 已是唯一计划；再写会竞争 |
| 单会话顺序执行 | 首个 Change 只用 TDD / debugging / verification | `executing-plans` 在完成状态适配前会以 ledger 为恢复判据，禁止直接使用 |
| 多任务并行、需要每任务审查 | `subagent-driven-development` | 仅 Phase 3 以后；共享 ledger 必须由适配器生成且不得成为恢复真源 |
| 隔离工作区 | `using-git-worktrees` | 默认 `.worktrees/`；需要用户同意 |
| 任务内调试 | `systematic-debugging` | 先根因，不补症状 |
| 完成前 | `verification-before-completion` | 必须有真实命令输出，不能推断 |
| 分支收尾 | `finishing-a-development-branch` | 先跑全量测试，再给 merge/PR/keep 选项 |

执行器注意：

- `task-start` 只证明能抽取 brief 和打印 BASE；`executing-plans/SKILL.md` 会要求恢复时信任 `progress.md`，`task-done` 只追加 ledger、不同步 `tasks.md`。
- 首个原生 Change 不使用 stock `executing-plans` / SDD；只采用 TDD、systematic-debugging、verification-before-completion。
- 后续若启用执行器，必须提供适配：tasks 是唯一状态，ledger 仅为派生缓存；tasks 与 ledger 冲突时拒绝继续；kill/restart 后不得仅凭 ledger 跳过任务。
- `writing-plans` 默认写 `docs/superpowers/plans/`，L2 禁用；更细 brief 只能是派生视图，不得持久化第二计划。
- `.superpowers/sdd/` 由工具自身写入局部 `.gitignore`，但仍必须验证未入库；运行产物不能进入提交。

## 9. ECC 的定位

ECC 是**可选、固定版本、经审查的素材层**，不是第四个真源。

- 采用：planner / architect / code-reviewer / security-reviewer 子代理；iOS/RN 规则；危险命令与密钥扫描 hooks；MCP 配置模板。
- 不采用：整仓全量安装、未审查 hooks、自动写全局配置、把 ECC 的 plan/memory 当项目状态。
- 审查：每个 hook 和 MCP server 记录来源、版本、权限、失败模式；供应链风险按 D-AI9。
- 上下文预算：只启用当前 Change 需要的 agent/rule；不把整套 ECC 注入每次会话。

## 10. 大型存量 App 的落地约束

| 约束 | 做法 | 理由 |
| --- | --- | --- |
| 行为契约只写外部可观察行为 | OpenSpec spec 按能力/用户场景写；内部桥接用版本化技术契约 | 避免为每个内部方法写 Scenario，控制维护成本（D-AI6） |
| 小批量 | 一个 Change 一个行为；3–7 个任务；trunk-based 短分支 | 降低审查和回归成本 |
| 长变更 | feature flag 或分阶段 Change，不长期挂分支 | 保持主干可发布 |
| 领域所有权 | CODEOWNERS 管 spec 与核心模块；平台 owner 管 harness/CI | 让契约变更有人负责 |
| 风险分级审查 | 并发/持久化/发布/迁移必须独立审查；其他 L2 自检 + 确认 | 把审查预算放在高风险处 |
| 决策记录 | 只写 `docs/decisions.md`；不在多个文档复制结论 | 避免决策漂移 |
| 多仓 | Change Set 由业务/平台责任仓持有；每仓自己的 `tasks.md` 与证据 | D-AI5；不造跨仓总任务表 |
| 度量 | lead time、返工、门禁失败、证据覆盖率、spec 漂移、单 Change 成本 | 先证明机制，不承诺效率百分比（D-AI10） |
| 推广 | 一个团队/一个仓/一类 Change 试点 → 第二团队 → 组织模板 | 避免“一次全铺” |

企业常见控制可直接复用：trunk-based development、required status checks、CODEOWNERS、ADR/决策日志、evidence-based release、最小权限与密钥扫描。这里不引用某家公司的具体数字，避免把外部案例当成未经验证的承诺。

## 11. 迁移路线

### Phase 0：当前（P0）

- 保持 `harness/plans/2026-11-17-ai-delivery-p0.md` 为唯一 active。
- P0 仍按 D-AI2 旧契约：Harness 是唯一执行计划。
- 完成 P0 必需项：CI 实际运行、双 Agent 实测与最终 fresh/strict 门禁。
- 真机 UI 与 ShareSheet 按用户 2026-11-17 的书面豁免处理；豁免不等于验证。
- P0 验收完成后，当前 `fix-transcript-export` 经单独确认后归档；不得改写成原生 tasks。
- 本方案与 D-AI11 落盘，但不创建第二个 active 计划。

### Phase 1：P0 收口后，准备适配器

- 在 `ai-delivery-toolchain` 增加 `delivery-check`：
  - 解析 Delivery Contract 与 Base；
  - 校验 tasks/标题/复选框一致，要求 `total>0`、`all_done`；
  - 校验 scope 的 Base..HEAD + 工作树；
  - 校验 evidence 的 clean ancestor、artifact、freshness；
  - 校验 acceptance 映射、review 范围、仓库 CI 策略；
  - 提供 archive gate 与全部负向 fixture。
- 增加宿主 Change Record 适配：tasks 是唯一契约与状态，记录只引用；不支持时 fail-closed。
- 增加仓库固定 OpenSpec wrapper（固定 2.1.0 并校验版本），文档不再依赖裸命令。
- 把 `XCODEBUILD_BUILD_ARGS` 等本机构建参数写入 manifest 的可复核字段或明确完整命令口径。
- 在宿主 Makefile 增加薄入口（例如 `make delivery-check CHANGE=...`）。
- 只用隔离夹具和工具仓测试 dry run；不在宿主创建第二个 active。

### Phase 2：首个原生 Change

- 仅在 P0 已收口、旧 Change 已按确认处置、delivery-check 与状态适配通过负向测试后创建。
- 选择一个真实 L2，写 `tasks.md` + Delivery Contract；不改写旧 P0 的 tasks。
- 首个 Change 只采用 Superpowers TDD / debugging / verification；不使用 stock `executing-plans` / SDD。
- Harness 生成证据；`delivery-check archive-gate` 通过；archive 前再次获得用户确认。
- 记录：任务数、实际耗时、返工、门禁失败、Agent 干预次数。

### Phase 3：并行与子代理（后续，非首个 Change）

- 状态适配和冲突负向测试完成后，才考虑 `subagent-driven-development` + `using-git-worktrees`。
- 引入 ECC 的 reviewer/security 子代理（固定版本、审查 hooks）。
- 对并发/持久化/发布变更强制独立审查。

### Phase 4：多仓（后续，需真实 OC + RN 项目）

- 在真实 OC + 自研 RN 项目建立 Change Set 约定。
- 每个仓独立 `tasks.md` / evidence；总验收在责任仓。
- 只把通用适配器放入 `ai-delivery-toolchain`，公司私有规则放 Organization Overlay。

### 回滚路径

- **未归档、执行失败**：Change Record 改 `blocked`，保留 `tasks.md` 与未提交改动补丁；不启动第二个 active。修复后继续，或经用户确认建立新的 Harness 恢复计划；不得复活已归档 P0。
- **门禁失败**：只修根因，不降级检查、不手改 tasks 复选框、不伪造 evidence。
- **已归档、需要撤销**：保留 archive commit，经用户确认后用 revert 撤销该提交并重新 `validate`；禁止 `reset --hard`、手工删主 specs 或静默改历史。
- **跨仓失败**：责任仓保留 Change Set 与总验收，受影响仓各自回滚自己的 tasks/提交；不得用未固定工作树充当证据。

## 12. 风险与缓解

| 风险 | 表现 | 缓解 |
| --- | --- | --- |
| 任务清单变“假进度” | 代码写完就勾选，没有测试输出 | 复选框只在验证通过后勾选；证据与 acceptance 映射；Harness 复核 |
| OpenSpec 校验通过但交付不可用 | `validate --strict` 只查结构 | Delivery Contract + `delivery-check` + evidence |
| 归档过早 | `--yes` 可对未完成任务归档 | 归档前要求 `total>0`、`all_done`、evidence、review；archive 单独确认 |
| 双计划复活 | `writing-plans`、Harness 清单或 SDD ledger | L2 禁用 `writing-plans`；Record 只引用；首个 Change 不用 stock SDD |
| 空计划或嵌套复选框放大 | `remaining==0` 对 0/0 成立；步骤 `- [ ]` 增加 total | 要求 `total>0`、`state=all_done`；Task 标题数与复选框数一致 |
| 多 Agent 冲突 | worktree/branch/提交互相覆盖 | worktree 隔离；scope Base 审计；每任务提交；冲突拒绝继续 |
| ECC 上下文与供应链风险 | 全量规则注入、未审查 hooks | 固定版本、按需启用、逐项审查、最小权限 |
| 证据与代码不匹配 | 旧 JUnit 复用、commit 不一致 | 现有 Harness freshness / manifest / commit 绑定 |
| 团队把 L2 流程套到 L0/L1 | 小改动也写完整 Change | 分级路由；L0/L1 走 Harness 轻量流程 |

## 13. 验收标准（目标态）

- [ ] 一个真实 L2 Change 的 `tasks.md` 通过 `validate --strict`，`instructions apply` 为 `ready` 且 `total>0`。
- [ ] 每个任务只有一个复选框；全文无其他复选框；Task 标题数等于 `total`。
- [ ] Superpowers TDD / debugging / verification 被实际遵循；stock SDD ledger 未被当作完成或恢复真源。
- [ ] 完成时为 `all_done`、`total>0`、`complete==total`、`remaining==0`；Harness 必需 claim PASS；审查关闭。
- [ ] `delivery-check archive-gate` 通过且再次确认后才执行 `openspec archive`；归档后 `validate --archived` 通过。
- [ ] 没有第二份 Harness 任务清单、Superpowers `plan.md` 或可独立决定状态的 ledger。
- [ ] `status.isComplete` 从未被当作交付完成判据，0/0 指针或空 tasks 被拒绝。
- [ ] 失败路径被测试：0/0、未完成任务、缺失/陈旧证据、Base scope 越界、嵌套复选框、review 范围过期。

## 14. 交接

### 当前状态

- 唯一 active 计划：`harness/plans/2026-11-17-ai-delivery-p0.md`。
- P0 旧契约不追溯改写；本方案是下一阶段目标态。
- D-AI11 已记录；`docs/README.md` 已登记本案例。
- 用户 2026-11-17 已批准真机 UI/ShareSheet 书面豁免，并同意 P0 验收后归档当前 Change（archive 仍需单独确认）。
- 未创建第二 active 计划；未修改 `tasks.md` 当前指针（P0 仍按旧模式）。
- 未提交、未 push、未发布。

### 下一任执行者

1. 先读本文件、`docs/decisions.md` D-AI11、P0 active 计划。
2. 完成 P0 必需项；不要为了试新流程提前新建 active 计划。
3. P0 验收后经确认归档当前 `fix-transcript-export`；不得替换其指针型 tasks。
4. 在 `ai-delivery-toolchain` 实现并负向测试 `delivery-check` 与状态适配，固定版本后再创建新的首个原生 L2 Change。
5. 首个原生 Change 只采用 TDD / debugging / verification；不要使用 `writing-plans` 或 stock `executing-plans` / SDD。
6. 归档前跑 `delivery-check archive-gate` 并再次确认；归档后跑 `validate --archived`。
7. 记录流程成本与失败路径；未实测项写“未验证”。

### 不要做

- 不要同时保留 P0 计划和新的原生 Change 作为两个 active。
- 不要把 `openspec status.isComplete`、`remaining==0`（未带 `total>0`）或 SDD ledger 当成完成。
- 不要在 `tasks.md` 里使用步骤级或额外复选框。
- 不要用 `archive` 代替完成门禁。
- 不要改写旧 P0 Change 的 tasks，也不要在归档后手工删除主 specs。
- 不要把 ECC 全量安装进项目或把 `.superpowers/sdd/` 入库。

## 15. 相关文件

- [`decisions.md`](decisions.md)：D-AI11 决策。
- [`../harness/plans/_archive/2026-11-17-ai-delivery-p0.md`](../harness/plans/_archive/2026-11-17-ai-delivery-p0.md)：已完成的 P0 快照。
- [`../references/workflow.md`](../references/workflow.md)：L0/L1/L2 与红队协议。
- [`../references/verification.md`](../references/verification.md)：验证矩阵与测试计数。
- [`../openspec/changes/fix-transcript-export/tasks.md`](../openspec/changes/fix-transcript-export/tasks.md)：当前 P0 的指针型 tasks.md；P0 验收后归档，绝不改写成目标态任务清单。

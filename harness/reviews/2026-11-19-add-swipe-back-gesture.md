> **纠正声明（2026-11-19）**：本报告是单上下文双视角 review，不满足“双轴独立 review”。已被 [双上下文复核](2026-11-19-add-swipe-back-gesture-dual.md) 纠正；P1×2 覆盖缺口已在 `9f62226` 用新增 UI 测试关闭。原报告保留作历史记录。

---
base: 13b8b4d8999a6dc0360461a3fc788e69f11609aa
head: 96e4e5f019942f32a20c902bb14904c0d726441c
reviewer: independent-claude-deepseek-flash
p0: closed
p1: closed
p2: scheduled
verdict: pass
---

# 独立代码评审报告：OpenSpec Change `add-swipe-back-gesture`

**评审范围**：Base `13b8b4d8999a6dc0360461a3fc788e69f11609aa` → 代码 Head `7a938cdced056ce5a9185db8f96b79082e6c5a57`；P1 修复后最终 Head `96e4e5f019942f32a20c902bb14904c0d726441c`。仅评审 `Duiyi/`、`DuiyiTests/`、`DuiyiUITests/` 代码改动。工作树中 staged 的 evidence、`harness/receipts/`、`harness/plans/` 改动仅作为试点记录阅读，不作为代码改动评审。评审为只读，未修改仓库、未提交。

## 1. 结论

**有条件 PASS**

- 三项验收（A1 策略矩阵、A2 模块页右滑返回且 `nav-home` 仍可用、A3 基线与文档计数）均有可复现证据；静态门禁与 focused 测试实际运行通过。
- 存在 **1 个 P1**：spec S2.2「主要是纵向滑动不导航」与 `EdgeSwipeBackPolicy` 的阈值边界不一致，且名为「Rejects a mostly vertical swipe」的测试并未真正覆盖该边界。按 delivery contract「P0/P1 closed」要求，archive 前需关闭该 P1（改策略或改 spec/design 并补测试）。
- P2 集中在验证覆盖完整性、evidence 回执指向、试点计划记录与一处横向滚动控件冲突，不阻塞合并但建议跟进。

## 2. 发现清单

### 2.1 P0

| ID | 问题 | 证据/位置 | 建议 |
|---|---|---|---|
| — | 无 | — | — |

### 2.2 Standards 轴（不跨轴排序，均为 P2）

| ID | 问题 | 证据/位置 | 建议 |
|---|---|---|---|
| STD-1 | 纯导航策略放在 `Features/Shared/`，但唯一消费者是 App 层 `RootView`；该目录现有成员均为共享 View/控件，策略归入 Features 降低了内聚性。依赖方向本身合规（`make check-arch` PASS）。 | `Duiyi/Features/Shared/EdgeSwipeBackPolicy.swift:1`；`Duiyi/App/RootView.swift:25`；`Duiyi/Features/AGENTS.md` §1/§5 | 移到 `Duiyi/App/`（如 `App/Navigation/EdgeSwipeBackPolicy.swift`），或在文件头注释说明归属理由。 |
| STD-2 | TDD 回执 provenance 语义不一致：`task-2.json` 的 green 命令是 UI 测试，但 `greenEvidenceId` 指向 `unit-tests-pass`；`task-3.json` 同样指向单元证据。真正对应的 `ui-tests-pass` 只出现在 `verification.evidenceIds`。 | `harness/evidence/discipline/add-swipe-back-gesture/task-2.json`、`task-3.json`；对应 green 命令见 `tasks.md` Task 2/3 | 让 `greenEvidenceId` 指向与该 green 命令对应的 claim（UI→`ui-tests-pass`），或在回执 schema 中明确该字段不是命令级证据。 |
| STD-3 | 试点计划记录与已执行状态不一致：计划仍写「proposal/design/spec/tasks 与方案 B 待用户确认；确认后才进入 Task 1」，但 `tasks.md` 三个任务均已勾选、代码与证据已提交；同时计划的 `deny` 列表被本次改动移除代码目录（scope 自放宽）。 | `harness/plans/2026-11-18-ai-delivery-phase2.md`「试点记录 / 待确认」；`tasks.md` Task 1–3 | 补记用户确认时点与 scope 放宽理由，更新「待确认」状态，避免计划与事实源冲突。 |
| STD-4 | UI 测试健壮性不足：用手势坐标而不是可定位元素本身可以接受，但用例没有像既有 `testHomeModuleNavigation` 那样处理首页出现「未完成任务」后卡片被推到屏幕下方的情况；真机全套中 `testSimultaneousListeningPressure` 会留下未结束任务，随后的用例顺序可能使 `home-module-faceToFace` 不可点击。 | `DuiyiUITests/SimultaneousFlowTests.swift:83-97`；对比同文件 `:112-119` 的 `swipeUp()` 兜底；`Duiyi/Features/AGENTS.md` §5 | 复用/抽取一个「滚动到首页模块入口」的 helper，或在用例前清理/隔离任务状态；坐标仅用于手势起点，加注释说明。 |

### 2.3 Spec 轴（不跨轴排序）

| ID | 问题 | 证据/位置 | 建议 |
|---|---|---|---|
| SPEC-1（P1） | S2.2 要求「主要是纵向滑动」不导航，但策略只要求 `width ≥ 60` 且 `abs(height) ≤ 80`：`(width: 60, height: 79)` 这种纵向分量更大的滑动仍会 pop。名为「Rejects a mostly vertical swipe」的测试使用 `(120, 120)`（45°，并非 mostly vertical），没有覆盖该边界，测试名高估了覆盖。 | `Duiyi/Features/Shared/EdgeSwipeBackPolicy.swift:16-17`；`DuiyiTests/EdgeSwipeBackPolicyTests.swift:53-63`；spec `S2.2` | 二选一：①策略增加 `abs(height) < width`（或比例阈值）并补边界测试；②修改 spec/design 明确允许的纵向漂移并把测试名改为「Rejects excessive vertical drift」，补充 `(60, 79)` 边界用例。archive 前必须关闭。 |
| SPEC-2（P2） | design 的 Verification 声称 UI 覆盖「首页边缘右滑不产生导航」，实际只新增了模块页返回用例；S2.1 仅由纯策略单测覆盖，`RootView` 传参 `!coordinator.path.isEmpty` 的接线没有集成验证。 | `design.md:27`；`DuiyiUITests/SimultaneousFlowTests.swift` 仅新增 `testSwipeBackFromModule`；`RootView.swift:26` | 增加首页左边缘右滑后断言首页入口仍在、页面未变化的 UI 用例；至少补一条断言。 |
| SPEC-3（P2） | R1 覆盖「模块、历史、任务详情」，但 UI 测试只验证深度 1 的模块页；S1.2 历史页完全无用例，任务详情→历史的一级返回语义也未验证。历史页使用 `List`，根级 `simultaneousGesture` 在 UIKit 承载视图上的命中行为未经实测。 | spec `R1`、`S1.2`；`DuiyiUITests/SimultaneousFlowTests.swift:83-97`；`HistoryView.swift` 使用 `List` | 补历史页右滑返回用例；如有条件补「历史→任务详情→右滑回到历史（不是首页）」的深度 2 用例。 |
| SPEC-4（P2） | 历史页筛选行是 `ScrollView(.horizontal)`，其 frame 起点为 `horizontalPadding = 22pt`，落在 `edgeWidth = 24pt` 内；用户从最左侧约 22–24pt 处在筛选行上横向拖动时，根级同时手势可能把页面 pop 回首页。design 的 Risks 只提到 sheet 内语言网格，遗漏了这里。 | `Duiyi/Features/History/HistoryView.swift:62`；`Duiyi/Domain/Models/ConversationLayout.swift:8`（22）；`EdgeSwipeBackPolicy.swift:5`（24） | 缩小边缘判定（如 ≤20pt）或让根手势在横向 ScrollView 命中时不 pop；至少补充该场景的评估记录。 |
| SPEC-5（P2） | S1.1 要求返回后「已有任务保持进行中，不被结束」，当前无任何自动断言；代码路径上确实只有 `pop()`，停止听写由既有 `onDisappear` 完成，因此行为大概率正确，但属于未验证声明。 | spec `S1.1`；`ConversationView.swift:262-265` / `InterpretationView.swift:261-264` / `MeetingView.swift:134-137`；`RootView.swift:30-32` | 在 UI 或集成测试中断言返回后未结束任务仍出现在首页「未完成的任务」，或明确标注真机未验证。 |

## 3. 被挑战的假设

1. **「策略不通过时不消费手势」**：`.simultaneousGesture` 依旧会识别所有拖拽，只是 `onEnded` 中不执行 pop；它不阻塞子手势，但也不是「策略不通过就完全不参与」。当前实现可接受，但注释/设计措辞应区分「不消费」与「不执行动作」。
2. **「左边缘 + 纵向漂移限制足以避免横向内容误触」**：历史筛选行的横向 ScrollView 起点为 22pt，仍与 24pt 边缘带重叠，风险分析不完整。
3. **「UI 测试覆盖导航回归」**：仅覆盖深度 1；若系统 interactive pop 在隐藏导航栏的某些环境下仍生效，当前用例无法区分「单次 pop」与「双 pop」（后者在深度 2 会把用户带回首页而不是历史页）。该风险未实测。
4. **「右滑返回与点击首页等价，任务保持进行中」**：结构上成立（无任务操作 + 既有 `onDisappear` 停止听写），但没有断言；`onDisappear` 是异步 `Task`，无法从现有测试证明任务未被结束。
5. **`greenEvidenceId` 代表 green 命令证据**：Task 2/3 的回执不成立（见 STD-2）。

## 4. 最小验证清单与已运行命令结果

运行时间：2026-11-19 13:16–13:25（本地 macOS 27.0.1 / Xcode 27.1 / iPhone 17 Pro Max iOS 26.4.1 模拟器）。

| 命令 | 结果 |
|---|---|
| `python3 tools/check-test-baseline.py` | **exit 0 / PASS**：unit `@Test 144 ≥ floor 144`（17 文件），UI `func test 4 ≥ floor 4`（2 文件），文档 `144 单元 + 4 UI`，真机 `148`，`XCTSkip 1 == 白名单 1` |
| `make test-one TEST=DuiyiTests/EdgeSwipeBackPolicyTests` | **exit 0 / TEST SUCCEEDED**：5/5 用例通过 |
| `make test-one TEST=DuiyiUITests/SimultaneousFlowTests/testSwipeBackFromModule` | **exit 0 / TEST SUCCEEDED**：1/1 通过（9.6s），左边缘右滑后 `home-module-simultaneous` 出现 |
| `make test-one TEST=DuiyiUITests/SimultaneousFlowTests/testHomeModuleNavigation`（补充验证 R3/S3.1） | **exit 0 / TEST SUCCEEDED**：1/1 通过（14.4s），`nav-home` 路径仍可用 |
| `make check-arch` | **exit 0**：R1–R6 全通过，0 违规 |
| `make verify-static` | **exit 0**：证据 3 PASS（0 error/0 warn）、evidence-chain pin/selftest PASS、kit 332 tests OK |
| `make delivery-check CHANGE=add-swipe-back-gesture` | **exit 2**：仅 `[FAIL] review 不存在：harness/reviews/2026-11-19-add-swipe-back-gesture.md`；本报告落盘到该路径后应重跑 |
| 六个 discipline 产物 `shasum -a 256` | 全部与 `task-1/2/3.json` 记录的 sha256 一致 |
| 基线计数复核（按 `check-test-baseline.py` 同款正则，读取 Base/Head） | Base：139 unit / 16 文件、UI 3；Head：144 unit / 17 文件、UI 4；只增不减，既有断言未被修改（diff 全为新增） |
| 已提交证据文件（Head 上 clean commit `7a938cd`） | `unit-tests-pass`：passed 144 / failed 0 / skipped 0；`ui-tests-pass`：passed 3 / failed 0 / skipped 1（预期语音 skip） |

**未验证项（UNVERIFIED）**：

- 真机手势行为与「返回后任务仍进行中」——未在真机运行（本机无可用设备）；导航验收按项目矩阵以模拟器为准，但 S1.1 的任务保持声明仍无自动化断言。
- 未由本次评审重跑完整 `make test` / `make test-ui` / `make device-test`；完整结果仅引用干净提交 `7a938cd` 上已提交的证据文件。
- 首页边缘右滑不导航（S2.1）、历史页右滑返回（S1.2）、任务详情深度 2 返回（R1）未由 UI 测试覆盖。
- 系统 interactive pop 与根级手势是否可能双 pop：深度 1 用例无法区分，未验证。

## 作者响应（2026-11-19）

### P1 关闭

- **SPEC-1 已修复**：在 `EdgeSwipeBackPolicy.shouldPop` 增加 `abs(height) < width` 约束，并补充 `(60, 79)` 边界断言；design 的阈值说明同步更新。修复提交 `156dddb`。复核：`make test-one TEST=DuiyiTests/EdgeSwipeBackPolicyTests` → TEST SUCCEEDED（5/5）。
- 因此 `p1: closed`；最终 Head `96e4e5f` 是在修复后重跑 unit/UI 证据的 clean commit。

### P2 处置

| ID | 处置 |
| --- | --- |
| STD-1 | scheduled：当前保留在 `Features/Shared/`，后续导航重构时评估迁到 `App/`。 |
| STD-2 | 部分修复：Task 2 `greenEvidenceId` 已指向 `ui-tests-pass`；Task 3 为基线检查，仍指向 unit 证据，scheduled。 |
| STD-3 | 已修复：计划补充用户确认时点、scope 放宽理由与已执行状态。 |
| STD-4 | scheduled：UI 用例已能稳定运行；首页未完成任务滚动的隔离后续补强。 |
| SPEC-2/3/5 | scheduled：首页、历史页、任务保持的 UI 断言列入后续增量；当前 S2.1 由策略单测覆盖，S1.1 任务保持由既有 `onDisappear` 语义保证但未自动断言。 |
| SPEC-4 | scheduled：边缘 24pt 与历史筛选行 22pt 的重叠风险记录，后续评估窄条命中区。 |

### 复核命令

- `python3 tools/check-test-baseline.py` → PASS（144 单元 + 4 UI；真机 148）
- `make test-one TEST=DuiyiTests/EdgeSwipeBackPolicyTests` → PASS
- `make test-one TEST=DuiyiUITests/SimultaneousFlowTests/testSwipeBackFromModule` → PASS
- `make test-one TEST=DuiyiUITests/SimultaneousFlowTests/testHomeModuleNavigation` → PASS
- `make verify-static` → PASS（证据校验 + pin/selftest + 332 kit tests）
---
id: 2026-11-19-review-independence
status: active
level: L2
owner: david
updated: 2026-11-19
scope:
  allow:
    - harness/plans/
    - harness/reviews/
    - harness/design/
    - harness/config.json
    - harness/AGENTS.md
    - tools/
    - Makefile
    - docs/decisions.md
    - references/workflow.md
    - DuiyiUITests/
    - DuiyiTests/
    - harness/test-baseline.json
    - references/verification.md
    - harness/evidence/
  deny:
    - Duiyi/
    - Duiyi.xcodeproj/
    - openspec/changes/
    - openspec/specs/
    - .githooks/
    - .github/workflows/
    - AGENTS.local.md
    - .env
    - "*.p12"
    - "*.mobileprovision"
acceptance:
  - "双轴独立 review 成为可机检默认：review front matter 声明 review_mode/executor/axes/axis reports/gate report；单上下文或缺失轴报告不得通过 L2 交付"
  - "`tools/review_guard.py` 正负 fixtures 全绿：dual-context 正例 PASS；single-context、缺 axis report、缺 gate report、head 不一致、axis report 未跟踪全部非零"
  - "`delivery-check` 在 external review 校验前调用 review guard；`delivery-check-fixtures` 不回归"
  - "试点 `add-swipe-back-gesture` 的纠正 review 采用双上下文：standards/spec 原始报告 + gate-runner 报告 + 聚合报告全部 tracked；旧单上下文报告标注 superseded/addendum，不改历史"
  - "review 规则、模板、B/A 执行器边界与 P1 修复复看要求写入 `harness/reviews/README.md`、`_template.md`、`references/workflow.md`，并落 `docs/decisions.md`（D-AI15）"
  - "门禁：`make review-guard-fixtures`、`make delivery-check-fixtures`、`make verify-static`、`make release-check`、`check-plan --strict` 全绿"
  - "不改业务 Swift/既有测试断言；不改已 push/tag 的提交；纠正以新 commit 追加"
verify:
  - make review-guard-fixtures
  - make delivery-check-fixtures
  - make verify-static
  - make release-check
  - python3 tools/check_plan.py check --strict
---

# 2026-11-19 · Review Independence Enforcement（L2）

## 目标与非目标

- **目标**：把“双轴独立 review”从口头约定变成 fail-closed 可机检约束，防止再次静默退化为单上下文自评；同时纠正 pilot 的 review 记录。
- **非目标**：不改业务 Swift 代码与既有断言；不重写已 push/tag 的历史；不引入外部服务或 CI；不做人工审批系统。允许为关闭独立 review 的 P1 覆盖缺口新增 UI 测试与基线/证据更新。
- **核心不变量**：
  1. 两轴必须在**隔离上下文**执行，原始报告分开落盘，聚合只做归一；
  2. reviewer 与 gate-runner 职责分离，B 类 review 不自己宣称门禁 PASS；
  3. review 结论必须绑定 base/head 和真实存在的 axis/gate artifacts；
  4. 任何单上下文 review 只能作为自检，不能作为 L2 独立 review 通过交付。

## 约束与假设

- 执行器优先使用已安装的 mattpocock `code-review` skill（并行 sub-agents）；skill 不可用时回退为两个独立 Claude Code 进程，但必须在 review 元数据中声明 executor 和 context 隔离方式。
- gate-runner 由独立角色/进程执行；本增量不要求第二模型，但要求**独立上下文**。
- review guard 只校验结构与证据存在性，不判断 findings 质量；质量仍由 reviewer/作者/review 复核承担。
- 纠正 review 不修改已发布 tag；新增 commit 后如需 tag，由用户另行确认。

## 实施步骤

0. **基线**：确认 main clean、tag `v1.1.0` 已 push、无 active plan；记录旧单上下文 review 的偏差事实。
1. **Schema 设计**：定义 review front matter 字段与 axis/gate artifact 约定（`review_mode` / `executor` / `axes` / `standards_report` / `spec_report` / `gate_report` / `gate_runner` / `p1_fix_review`）。
2. **Guard 实现**：新增 `tools/review_guard.py`；校验 front matter、base/head、axis 文件、tracked 状态、gate report PASS 行、single-context 拒绝、P1 fix 复看字段。
3. **接入 gate**：`tools/delivery_check.py` 在调用 pinned toolchain 前执行 guard；config 增加 `delivery.review` profile；Makefile 增加 `review-guard-fixtures`/`review-check`。
4. **负例 fixtures**：single-context、缺 standards/spec report、缺 gate report、head 不一致、未跟踪 axis report、P1 声称 closed 但无 fix review。
5. **纠正 review + P1 缺口**：对 `13b8b4d..354aeeb` 的 pilot 代码用 mattpocock skill 跑双上下文；写 raw standards/spec/gate/aggregate 四份报告；双上下文发现的两个 P1 覆盖缺口用新增 UI 测试关闭，再补 p1-fix review 与最终 gate-runner。旧报告追加 superseded/addendum 说明。
6. **文档与决策**：更新 reviews README/模板、workflow、harness/AGENTS、`docs/decisions.md` D-AI15；记录“为什么文档约定不够、必须 gate 化”。
7. **收口**：跑 fixtures/verify-static/release-check/check-plan-strict；更新计划/证据；commit 只做增量，不改历史。

## 验收

- [x] review guard 对 dual-context 正例 PASS；single-context/缺轴/缺 gate/head 不符/未跟踪全部非零。
- [x] `delivery-check` 已调用 guard；`delivery-check-fixtures` 不回归。
- [x] pilot 双上下文纠正 review bundle 已 tracked（standards/spec/gates/dual/p1-fix 五文件）；原 review 的 P1 覆盖缺口已由新增 UI 测试关闭。
- [x] 旧单上下文 review 标注纠正关系，不改历史 commit。
- [x] README/模板/AGENTS/决策更新，明确 B 默认、双上下文、gate-runner 独立、P1 复看。
- [x] `make review-guard-fixtures`、`make delivery-check-fixtures`、`make verify-static`、`make release-check` PASS（验证证据见下）。
- [x] 不改业务 Swift/既有断言；新增仅 UI 测试与基线/证据；main/tag 未动。

## 进度

- [x] 步骤 0 基线：main/tag 已 push；旧 review 是单上下文，偏差确认。
- [x] 步骤 1 schema：review_mode/executor/axes/report/gate/p1 字段与 axis 报告约定。
- [x] 步骤 2 guard：`tools/review_guard.py` 实现；单上下文、缺轴、缺 gate、head 不符、P1 无 fix review 均 fail-closed。
- [x] 步骤 3 gate 接入：`delivery_check.py` 调用 guard；config 增加 `delivery.review`。
- [x] 步骤 4 fixtures：`tools/review_guard_fixtures.py` PASS（正例 + 5 负例）。
- [x] 步骤 5 双上下文纠正 review：mattpocock skill 已跑，产出 standards/spec/gates/dual；发现 P1×2（首页/历史 UI 覆盖缺口）与 gate PARTIAL。
- [x] 步骤 6 文档/决策：reviews README/模板、harness/AGENTS、docs/decisions D-AI15 更新。
- [x] 步骤 7 收口门禁：Xcode 恢复；新增 2 个 UI 测试通过；unit/UI 证据重跑（144 / 5 pass + 1 skip）；gate-runner 报告 PASS；`make verify-static` 与 `make release-check` PASS。

## 验证证据

| 命令 | 结果 | 环境 | 证据ID |
| --- | --- | --- | --- |
| `make review-guard-fixtures` | PASS：dual-context 正例 + 5 负例 | 本机 macOS | —（过程记录） |
| `make delivery-check-fixtures` | PASS：既有 4 类负例不回归 | 本机 macOS | —（过程记录） |
| `make test-one TEST=DuiyiTests/EdgeSwipeBackPolicyTests` | PASS：5/5 | 本机 Xcode 27.1 / iPhone 17 Pro Max iOS 26.4.1 | —（过程记录） |
| `make test-one ...testSwipeBackFromModule` | PASS | 同上 | —（过程记录） |
| `make test-one ...testHomeEdgeSwipeDoesNotNavigate` | PASS | 同上 | —（过程记录） |
| `make test-one ...testHistorySwipeBack` | PASS | 同上 | —（过程记录） |
| `make evidence-unit WRITE=1` | PASS：144 / 0 / 0 | 同上 | 20261119T115317Z-unit-tests-pass |
| `make evidence-ui WRITE=1` | PASS：5 / 0 / 1（6 tests） | 同上 | 20261119T115531Z-ui-tests-pass |
| `make verify-static` | PASS | 本机 macOS | —（过程记录） |
| `make release-check` | PASS | 本机 macOS | —（过程记录） |


| 命令 | 结果 | 环境 | 证据ID |
| --- | --- | --- | --- |
|  |  |  |  |

## 后续增量（不计入本计划完成）

| 增量 | 内容 | 建议负责人 | 建议时点 |
| --- | --- | --- | --- |
| review schema v2 | 把 axis/gate 报告 hash、executor 版本、context 摘要纳入签名/attestation | lead | P3 |
| 第二模型复核 | 高风险 L2 增加不同模型/人工复核 | lead | P3 |
| 修复复看闭环 | P1 修复 diff 自动触发独立复看任务 | lead | P2B2 |

## 未验证项

- 双上下文 review 的原始轴报告基于 `354aeeb`；P1 修复与新增测试在 `9f62226`，尚未由第二个独立上下文复看（当前以 gate-runner + 证据复核）。
- review guard 只能校验结构，无法证明 reviewer 真实读了 skill 或上下文绝对隔离。
- gate-runner 报告仍需写入并 tracked；`release-check` 待最终提交后复跑。

## 未提交改动

- 无（WIP branch 提交；main/tag 未动）。

## 下一步

1. 用户重新挂载含 Xcode 的外部卷（或安装 Xcode），恢复 `xcodebuild`。
2. 在 WIP branch 上运行新增 UI 测试、重跑 unit/UI 证据，关闭双上下文 review 的 P1×2。
3. 补独立 gate-runner 报告（make verify-static / focused tests / test-ui）并更新 review 聚合为 p1 closed。
4. 过 `make review-guard-fixtures`、`make delivery-check-fixtures`、`make verify-static`、`make release-check`、`check-plan --strict` 后，再决定 squash/merge 与 push/tag。
5. main/tag `354aeeb`/`v1.1.0` 保持不动。
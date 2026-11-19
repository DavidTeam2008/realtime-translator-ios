---
id: 2026-11-19-review-execution-provenance
status: done
level: L2
owner: david
updated: 2026-11-19
submitted: ac244e4 fa3a47a
scope:
  allow:
    - harness/plans/
    - harness/reviews/
    - harness/receipts/reviews/
    - harness/evidence/
    - harness/AGENTS.md
    - harness/superpowers-overlay.md
    - harness/config.json
    - tools/
    - Makefile
    - docs/decisions.md
    - references/workflow.md
  deny:
    - Duiyi/
    - Duiyi.xcodeproj/
    - DuiyiTests/
    - DuiyiUITests/
    - openspec/changes/
    - openspec/specs/
    - .githooks/
    - .github/workflows/
    - AGENTS.local.md
    - .env
    - "*.p12"
    - "*.mobileprovision"
acceptance:
  - "review_guard 拒绝未固定 executor：任意非空字符串不再通过；只接受 config 固定的 claude-code-code-review-skill"
  - "review bundle 必须引用 tracked execution_receipt；receipt 绑定 change/base/head/executor，记录 /code-review prompt、Claude Code session、Skill+Task 权限、≥2 个 Task 子代理与只读工具集"
  - "gate-runner 必须引用 tracked gate_receipt；required gate commands 由 wrapper 实际执行且 exit 0，不再只靠手写 PASS 行"
  - "review guard fixtures 覆盖正例与至少 8 类负例：executor 不符、缺 execution receipt、缺 Skill/Task 权限、Task 子代理 <2、receipt head 不符、transcript 哈希被改、缺 gate receipt、gate 命令非 0"
  - "tools/run_dual_review.py 与 tools/run_gate_runner.py 可 headless 调起 Claude Code /code-review 并落 receipt；headless 不可调时明确 UNVERIFIED，不伪造回执"
  - "README/模板/AGENTS/workflow/decisions 同步；delivery-check 继续 fail-closed；make review-guard-fixtures、make delivery-check-fixtures、make verify-static、make release-check PASS"
verify:
  - make review-guard-fixtures
  - make delivery-check-fixtures
  - make verify-static
  - make release-check
  - python3 tools/check_plan.py check --strict
---

# 2026-11-19 · Review Execution Provenance（L2）

## 目标与非目标

- **目标**：把“L2 必须显式调用 `/code-review`（Claude Code + Skill/Task 权限，按 skill 并行 sub-agent 流程）并由独立 gate-runner 复跑门禁”从文档约定变成 fail-closed 可机检约束；单上下文手写报告或手写 gate PASS 不再能通过 `delivery-check`。
- **非目标**：不改业务 Swift 代码与既有测试；不重写已发布历史；不引入外部 CI/服务；不做密码学签名或人工审批系统；不要求第二模型。
- **核心不变量**：
  1. `executor` 固定为 `claude-code-code-review-skill`，报告不能自选执行器；
  2. 每份 L2 review 必须绑定一份 tracked `execution_receipt`，回执由 wrapper 实际执行 `/code-review` 生成，记录 session、权限、Task 子代理与只读工具；
  3. gate-runner 必须绑定 tracked `gate_receipt`，required 命令由 wrapper 实际执行并记录退出码；
  4. 回执与 base/head/change 绑定，聚合报告、axis 报告、gate 报告、回执之间任一不一致即 FAIL；
  5. 本地回执只能证明“执行声明与产物一致”，不能密码学证明不可伪造；该残余风险继续显式记录。

## 约束与假设

- Claude Code v2.1.310 已安装，headless `claude -p` 可用；用户级 `code-review` skill 存在（`~/.agents/skills/code-review`）。
- skill 的并行 sub-agent 由 Claude Code 内置 Task 工具执行；回执以 `subagent_stats.spawned` 与 Task tool_use 计数交叉验证。
- wrapper 只读执行 review：允许 Read/Grep/Glob 与只读 git 命令，禁止 Write/Edit 与写 git 命令。
- gate-runner 仍是同一开发机上的独立进程；cross-machine/CI 复算不在本增量，继续保留豁免。
- 本增量产生的 review/gate 回执由新 wrapper 首次真实运行生成；若 headless 调用失败，明确记录 UNVERIFIED 并停止，不用手写回执冒充。

## 实施步骤

0. **基线**：确认 main clean、无 active 计划；记录当前只做结构校验的偏差证据（任意 executor 字符串可通过）。
1. **契约与配置**：`harness/config.json` 增加 `delivery.review.executor`（固定值、Skill/Task 权限、禁止写工具、minSubagents）与 `delivery.review.gate` 回执要求；README/模板同步字段。
2. **review wrapper**：新增 `tools/run_dual_review.py`：解析 Delivery Contract base/head，校验 HEAD==head，调 `claude -p --output-format stream-json --verbose "/code-review <base>"`，解析 session/Task/子代理/工具事件，落 `execution_receipt` + trimmed events，staged 供 guard 检查。
3. **gate wrapper**：新增 `tools/run_gate_runner.py`：实际执行 required gate commands（可追加既有 focused 命令），记录 exit/耗时/输出摘要，生成 gate receipt 与 gate report markdown。
4. **guard 扩展**：`tools/review_guard.py` 增加 executor 固定、execution_receipt、gate_receipt、权限、Task 子代理数、事件/哈希、change/base/head 绑定校验；保留既有 axis/gate/P1 校验。
5. **fixtures**：`tools/review_guard_fixtures.py` 重做正例（含 receipt/events/gate receipt）与 ≥8 负例；确保不调用真实 Claude。
6. **文档/决策**：reviews README、`_template.md`、`harness/AGENTS.md`、`references/workflow.md`、`docs/decisions.md`（D-AI16）；Makefile 增加 `review-execute` / `review-gates`。
7. **真实 smoke**：在临时 worktree/临时 change 上用 wrapper 跑一次真实 `/code-review`，验证 headless 可用、Task 子代理≥2、receipt 可被 guard 接受；失败则记录 UNVERIFIED 并停止。
8. **收口**：fixtures、delivery-check-fixtures、verify-static、release-check、check-plan --strict；提交前询问用户，main/tag 不改写。

## 验收

- [x] guard 对固定 executor + execution_receipt + gate_receipt 的正例 PASS；13 类负例全部非零。
- [x] 任意自造 executor 在真实 smoke bundle 上也被拒绝；无 receipt、单上下文两份报告、手写 gate PASS 均无法通过。
- [x] wrapper 真实跑通一次 `/code-review`：headless Claude Code、2 个并行子代理、execution receipt + gate receipt 被 guard 接受。
- [x] `make verify-static`、`check_plan --strict` PASS。
- [x] `make release-check` PASS：3 PASS / 0 FAIL / 0 UNVERIFIED；新 unit/UI 证据 `20261119T145759Z-unit-tests-pass`、`20261119T145927Z-ui-tests-pass` 已 tracked，旧证据归档并声明 supersedes。
- [x] 文档/决策/模板同步；未回写已发布历史。

## 改动范围

- 允许：`tools/`、`Makefile`、`harness/config.json`、`harness/reviews/`、`harness/receipts/reviews/`、`harness/plans/`、`harness/AGENTS.md`、`docs/decisions.md`、`references/workflow.md`。
- 禁止：业务 Swift、既有测试断言、OpenSpec 产品 spec、已 push/tag 历史、机器本地签名文件。

## 进度

- [x] 偏差确认：guard 只检查 executor 非空；fixture 探针显示任意字符串可通过。
- [x] 契约/配置与 wrapper 实现：`run_dual_review.py` / `run_gate_runner.py`；config 固定 executor 与回执要求。
- [x] guard 扩展与 fixtures：executor/execution receipt/gate receipt/权限/子代理/哈希校验；正例 + 13 负例。
- [x] 文档/决策/Makefile：README/template/AGENTS/overlay/D-AI16；review-execute/review-gates 目标。
- [x] 真实 `/code-review` smoke：headless 成功，2 个并行子代理，execution receipt、gate receipt 均被 guard 接受；临时 change 已清理。
- [x] 门禁收口与计划归档：`make verify-static`、`make release-check`、`check_plan --strict` 全 PASS；计划归档。

## 验证证据

| 命令 | 结果 | 环境 | 证据ID |
| --- | --- | --- | --- |
| `make review-guard-fixtures` | PASS：dual-context 正例 + 13 负例 | 本机 macOS / Python 3.14 | —（过程记录） |
| `make delivery-check-fixtures` | PASS：4 类 fixture 不回归 | 本机 macOS | —（过程记录） |
| `python3 tools/run_dual_review.py --change _wrapper-smoke` | PASS：exit 0、spawned=2、Standards/Spec 各 1、session `908a5725-3569-4579-9fab-ddd85b7963e9` | Claude Code 2.1.310 / deepseek-flash[1m] | —（过程记录：临时 smoke，已清理，不入库） |
| `python3 tools/run_gate_runner.py --change _wrapper-smoke --runner gate-runner-smoke` | PASS：required command exit 0，生成 gate receipt/report | 本机 macOS | —（过程记录：临时 smoke，已清理） |
| `python3 tools/review_guard.py check --change _wrapper-smoke` | PASS：真实 execution/gate receipt 被 guard 接受 | 本机 macOS | —（过程记录：临时 smoke，已清理） |
| 同 bundle 改 `executor: custom-single-context` | FAIL：`review.executor 必须是 claude-code-code-review-skill` | 本机 macOS | 负例探针 |
| `make verify-static` | PASS | 本机 macOS | —（过程记录） |
| `make release-check` | PASS：3 PASS / 0 FAIL / 0 UNVERIFIED；新证据 tracked 且 supersedes 旧证据 | 本机 macOS | 20261119T145759Z-unit-tests-pass / 20261119T145927Z-ui-tests-pass |
| `python3 tools/check_plan.py check --strict` | PASS（0 error / 51 warn） | 本机 macOS | —（过程记录） |
| `make evidence-unit WRITE=1` | PASS：144 passed / 0 failed / 0 skipped | Xcode 27.1 / iPhone 17 Pro Max iOS 26.4.1 | 20261119T145759Z-unit-tests-pass |
| `make evidence-ui WRITE=1` | PASS：5 passed / 0 failed / 1 skipped（6 tests） | Xcode 27.1 / iPhone 17 Pro Max iOS 26.4.1 | 20261119T145927Z-ui-tests-pass |

## 未验证项

- 本地 receipt 可被蓄意伪造；只能提高偏差成本，不能密码学证明。
- gate-runner 与 reviewer 仍同机；真正的跨机器/CI 隔离未覆盖。
- wrapper 只在 docs-only smoke change 上真实跑过；尚未在真实产品 L2 change 上首次使用。
- gate-runner 的 required commands 固定为 `make verify-static` + baseline；focused tests/真实测试证据仍需另行附加到 gate report，guard 只强制 required 子集。

## 未验证豁免

| 项目 | 理由 | 负责人 | 到期日 |
| --- | --- | --- | --- |
| 本地 receipt 不可密码学验证 | 无外部签名/CI；信任锚仍是 Git + review + 人工复核 | david | 2026-12-31 |
| gate-runner 同机 | 独立进程但同一开发机；跨机器复算列入后续增量 | david | 2026-12-31 |

## 未提交改动

- 无（本计划收口提交包含 evidence 刷新与计划归档）。

## 下一步

1. 本增量已本地提交（`ac244e4`、`fa3a47a`）；push/tag 仍待用户单独确认。
2. 下一处真实产品 L2 change 首次使用 `make review-execute` + `make review-gates`，作为真实交付证据。
3. 后续可评估：跨机器/CI gate-runner、P1 修复第二上下文复核、plan-based L2 的 review receipt。

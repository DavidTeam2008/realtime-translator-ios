# 双 Agent L2 接管复核（QoderCN / Claude Code）

## 结论

- 同一任务卡、同一 clean HEAD 下，QoderCN 与 Claude Code 均完成只读 L2 接管复核，退出码均为 0，运行前后仓库均 clean。
- 两者独立确认：唯一 active 计划、指针型 OpenSpec tasks、3 条当前证据 fresh/strict 可重算、OpenSpec strict 校验、scope 与 CI static 结果均成立。
- 两者均指出：P0 当时缺双 Agent 记录，且动态 CI 只有 static 实跑；本次已补齐双 Agent 记录，并按用户 2026-11-18 决策对动态 CI 书面豁免。
- 目标态 `delivery-check` 仍未实现；旧指针型 Change 的归档必须走单独确认的 legacy 人工门禁，不得直接套用未来 `total>0` 的 native archive-gate。

## 运行条件

| 项 | QoderCN | Claude Code |
| --- | --- | --- |
| 宿主 | QoderCN CLI 1.1.91 | Claude Code 2.1.310 |
| 模型口径 | CLI 默认 Auto | 网关默认；本次出现 `deepseek-flash[1m]` unrecognized_model 警告，不据此声称具体模型 |
| 开始（UTC） | 2026-11-18T01:55:35Z | 2026-11-18T02:09:37Z |
| 结束（UTC） | 2026-11-18T02:09:16Z | 2026-11-18T02:23:13Z |
| 实际耗时 | 821.35s（user 140.22s / sys 55.56s） | 815.75s（user 246.11s / sys 102.72s） |
| 退出码 | 0 | 0 |
| 人工干预 | 登录授权 1 次；首次设备流程超时后重试 | 0 |
| 返工 | 0 | 0 |
| 仓库改动 | 0 | 0 |

共同输入：`AGENTS.md`、`AGENTS.local.md`、P0 active 计划、`docs/case-native-openspec-delivery.md`、D-AI1–D-AI11、workflow/verification、当前 OpenSpec Change、Harness 规则。
共同只读命令：`git status --short`、`make resume`、`make check`、`make verify-static`、`check_plan --strict`、`verify_claim_chain --all --fresh --strict`、OpenSpec 2.1.0 `validate --strict`、`instructions apply`、`status`、HEAD CI run 检查。未运行 archive、handoff、end、start、plan 或动态 iOS 测试。

## 共同通过项

- HEAD `a80a8e6`，运行前后工作树 clean；唯一 active 计划为 P0。
- 3 条当前证据 fresh/strict：docs、unit 131/131、UI 2 passed + 1 expected skip；旧证据归档。
- `make verify-static` 与 `make release-check` PASS；330 kit tests；证据链 8/5 负向自检 PASS。
- OpenSpec `validate --strict` 为 `valid=true`、`failed=0`；`instructions apply` 为 `total=0 / state=blocked`，证明旧指针 tasks 不能当任务状态。
- GitHub Actions run `44198282108` @ `a80a8e6`：static success；macOS unit/UI skipped。
- P0 全区间 `4c8d006..HEAD` 未命中 scope deny；产品改动仅两个 allow 文件。

## 发现与处置

| 级别 | 发现 | 双方一致性 | 处置 |
| --- | --- | --- | --- |
| P0 | 双 Agent 同流程记录缺失 | 一致 | 本次补齐；记录见本文件 |
| P0/P1 | 动态 CI 是否收口必需存在口径矛盾 | Claude 明确、Qoder 记录 skipped | 用户 2026-11-18 书面豁免动态 CI；static 实跑保留，动态链保持未验证 |
| P1 | P1-2 已修复但 roadmap 仍列待办 | 一致 | 收口提交更新 roadmap 状态与测试计数引用 |
| P1 | 无仓库固定 OpenSpec wrapper，文档裸命令不可直接复现 | Claude | 作为下一阶段前置：增加固定 wrapper 后再创建原生 Change |
| P1 | B1–B8 独立审查只有计划摘要 | Claude | 本报告补双 Agent 独立复核；原 B1–B8 详细报告仍标历史过程，不伪造 |
| P1 | 旧指针 tasks 0/0 与未来 `total>0` 门禁冲突 | Claude | 明确 legacy Change 使用人工归档门禁，不套用 native delivery-check |
| P1 | `delivery-check` 未实现 | 一致 | P0 不实现；P0 收口后先在外部工具仓实现并通过负向测试 |
| P1 | manifest argv 未包含本机构建参数 | Claude | 记录为后续证据链加固项；本次 evidence.command 含完整参数，计数与用例集合仍强绑定 |
| P2 | CI 记录、Superpowers pin、归档 supersede 链、空 artifact 目录等记录卫生 | 部分一致 | 收口时更新可定位记录；不修改历史证据 |

## 被挑战的假设

1. `status.isComplete` 或 `remaining==0` 单独可代表完成：证伪；0/0 时两者都可成立，必须叠加 `total>0` 与 `all_done`。
2. CI `success` 代表动态测试通过：证伪；macOS job 实际 skipped。
3. 证据 `fresh` 等于在 HEAD 重跑动态测试：不等于；它证明证据提交后无相关源码/配置变更。
4. P0 没有第二 active 即没有第二状态源：P0 旧契约内仍有验收与进度两套复选框；D-AI11 目标态才改为 tasks 单一状态。
5. 双 Agent 的标题/任务解析兼容等于执行状态兼容：证伪；stock SDD ledger 仍不能作为唯一状态。

## 最小验证

| 命令 | 期望 |
| --- | --- |
| `make resume` | 唯一 active；3 条证据 PASS / 0 UNVERIFIED |
| `make verify-static` | exit 0；330 tests；证据链自检 PASS |
| `python3 tools/verify_claim_chain.py --all --fresh --strict` | exit 0；3 PASS / 0 UNVERIFIED |
| OpenSpec 2.1.0 `validate --strict` | `valid=true`、`failed=0` |
| `gh run view 44198282108 --json headSha,conclusion,jobs` | HEAD；static success；macOS skipped |
| `git status --short` | 空 |

## 收口判定

双 Agent 实测已满足“同一 L2 接管复核”口径；动态 CI 由用户书面豁免，不能声称已验证。P0 可在完成 roadmap/review 记录与最终 fresh/strict 门禁后收口。目标态 `delivery-check`、固定 OpenSpec wrapper、manifest build settings 加固仍是后续 L2 的前置，不影响 P0 旧契约收口。

## 未验证

- macOS unit/UI CI 未实际运行；仅本地 strict JUnit/manifest 证据。
- Claude Code 本次具体上游模型无法从网关警告中确认。
- 真实 ShareSheet 与真机 UI 按既有书面豁免保持未验证。

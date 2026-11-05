# AGENTS.md · .apm

> 触发：读写计划、验证证据、问题单、独立审查或基准数据前先读本页。
> 本页只写 `.apm/` 的增量协议；分级与红队细则见 [`references/workflow.md`](../references/workflow.md)，项目入口见根 [`AGENTS.md`](../AGENTS.md)。

## 1. 目录职责

- `plans/`：跨会话计划的唯一进度真源；`_template.md` 是起稿模板。
- `reviews/`：独立只读审查报告；结论与作者回应写入对应计划。
- `issues/`：问题单（根因、证据、状态）。
- `baseline/`、`report.md`：性能口径与历史复盘；先读结论再用数据。
- `tools/`：真机/测量脚本（`device-test.sh`、`measure-launch.sh`）。
- `runs/`：原始测量产物，已 gitignore；入库的只有证据摘要与结论。

## 2. 计划状态机

- 用 `make plan TOPIC=<topic>` 新建；同一时间只允许 1 个 active 计划（唯一认领）。
- front matter 必填：`id`、`status`、`level`、`owner`、`updated`、`scope`（允许/禁止改动的文件或目录）、`acceptance`、`verify`。
- `status` 取值：`active` / `done` / `blocked` / `archived`；完成后改 `done` 并移入 `plans/_archive/`。
- 正文必填：目标、验收（可执行判据）、改动范围、DoD、验证证据、未验证项、下一步。
- 越界改动先停并更新 `scope`；计划不是规范文档，事实引用 `docs/` 与 `HANDOFF.md`。

## 3. 验证证据

- 表固定四列：`命令 | 结果 | 环境 | 证据 ID`。
- 结果写退出码/通过数/skip 数；环境写 Xcode/模拟器 runtime 或真机型号 + iOS。
- 证据 ID：Phase 0 记命令 + commit 短 hash；Phase 1 引入 `.apm/evidence/` 后填 evidence id。无证据的“已验证”按未验证处理。
- 未运行/未验证单列；不得把“环境跑不了”写成“代码通过”。

## 4. 红队 / 独立审查协议

- 范围：L2 中的并发、持久化、发布工程（见根 AGENTS 第 7 节）；其他 L2 用自检 + 用户确认。
- 只读：不改文件、不读 `.env`、不跑破坏性命令；输入只有任务 + 方案 + 仓库路径，不传起草对话、自评或既往结论。
- 输出：结论；P0/P1/P2 表（问题 | 证据/位置 | 影响 | 建议）；被挑战假设；缺失信息；最小验证清单。
- 作者逐条回应（接受/拒绝/待定 + 理由），最多两轮；P0/P1 执行前解决，P2 记录排期。
- 报告写入 `reviews/`；没有子 Agent 时用新会话兜底。

## 5. 写入卫生

- 计划/证据/审查不写本机绝对路径、设备 UDID、密钥/Token；只写仓库相对路径。
- 机器本地事实（Team、设备 ID、本机路径）写 `AGENTS.local.md`（如存在；gitignore，不入库）。
- 不把大产物、日志、截图入库；`.apm/runs/` 保持忽略。

## 6. 交接与收尾

- 中断/交接前更新：进度、已排除、验证证据、未提交改动、下一步（1 条具体动作）。
- `make resume` 接手；`make check-plan` 校验状态与必填字段；`make end` 收尾；`make handoff` 取最新 active 计划摘要。
- 同一失败修 2 次 / 同一子任务 3 轮无进展 → 按 [`references/workflow.md`](../references/workflow.md) 阻塞报告上报，并记入计划的尝试记录。

# Change Records

`harness/records/<change-id>.md` 是原生 OpenSpec L2 Change 的 Harness 记录：
只保存 Change ID、不可变 Base、`tasksSource: openspec` 指针、scope 与证据/审查指针。

- **任务状态唯一来源**：`openspec/changes/<change-id>/tasks.md`；记录中不得有任务复选框或独立进度。
- `check_plan.py` 与 `harness status/brief/resume` 会把记录与 `harness/plans/*.md` 一起读取，因此 0 active plan + 1 active Record 仍可恢复。
- 记录通过 `tools/openspec` 固定 wrapper 和 `make delivery-check CHANGE=<change-id>` 校验；不要用 `openspec/status.isComplete` 代替交付完成。
- `_template.md` 不是活动记录；复制后填写 front matter 与指针。

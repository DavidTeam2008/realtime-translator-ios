---
name: handoff
description: 中断/收工/交接时固化状态：更新计划、跑门禁、记录未验证与下一步，保证下一棒只靠仓库恢复。
---

# handoff

> 触发：任务中断、收工、换人或提交前。
> 参考：[根指令](../../../{{ROOT_AGENTS}})、[工作流](../../../{{REFERENCES_DIR}}/workflow.md)、[状态目录规则](../../../{{HARNESS_DIR}}/AGENTS.md)。

## 步骤

1. 更新 active 计划：[`_template.md`](../../../{{HARNESS_DIR}}/plans/_template.md) 的结构下写清
   status / 进度 / 关键决策 / 验证证据（命令 | 结果 | 环境 | 证据ID）/ 未验证项 / 未提交改动 / 下一步（1 条具体动作）。
2. 跑 `make check-plan`（standard / strict profile）：期望 exit 0；失败先修计划而不是绕过。
3. 跑 `{{VERIFY_COMMAND}}` 并记录结果；失败时标 FAIL 并写复现步骤。
4. 启用证据目录时跑 `make verify-claim`；无证据的结论一律标“未验证”。
5. 完成的计划改 `status: done` 并归档；交接摘要只写“下一步 1 条 + 建议阅读”。
6. 提交前询问用户；不清理、不覆盖未声明的未提交改动。

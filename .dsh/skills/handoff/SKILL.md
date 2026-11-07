---
name: handoff
description: 对译 Duiyi 中断/收工/交接时的状态固化：更新 active 计划（status、进度、证据、未验证、未提交、下一步）→ make check-plan → make end → make handoff，done 计划归档。保证下一棒只靠仓库就能恢复，不依赖对话记忆。
whenToUse: 长任务中断、收工、提交前、换 agent 或换会话、用户说"先到这/交接/收尾"。
---

# handoff · 交接与收尾

目标：下一棒只用仓库就能恢复。对话里说过的等于没说过。

## 动作（按序）

1. 更新 active 计划（`harness/plans/<topic>.md`，front matter + 正文）：
   - `status`：active | done | blocked | archived；同一时刻只允许 1 个 active。
   - 进度：已完成项勾选；"已排除（勿重试）"写方案 / 失败原因 / 证据。
   - 验证证据表：命令 | 结果 | 环境 | 证据 id（每条"已完成"都要有）。
   - 未验证项：单列未运行 / 跑不了的项，不写成已完成。
   - 未提交改动：与 `git status --short` 逐项对齐。
   - 下一步：只写 1 条具体动作（含命令）。
2. `make check-plan`：计划机检（front matter / 必填节 / 证据 / 未提交交叉比对）；红了先修计划，不改门禁。
3. `make end`：verify-static + 计划检查 + git 状态 + 未验证项 + 提交前提醒。
4. `make handoff`：输出交接摘要，粘贴给用户或下一棒；可 `PLAN=<path>` 指定。
5. 完成（done）计划：front matter 改 `status: done` 并填 `submitted: <hash,...>`，移入 `harness/plans/_archive/`（不存在则创建）。

## 提交（仅当用户确认；未确认不提交）

- 先问用户再 commit；提交信息用英文、跟随近 5 条非 merge commit 风格、不加 AI 署名。
- 不提交 build/、`harness/runs/`、trace、他人签名信息、本机 `AGENTS.local.md`。
- 提交后把 short hash 回填计划 `submitted`。

## 硬约束

- 不写本机绝对路径、设备 UDID、密钥 / Token。
- 不在未更新计划的情况下结束会话；blocked 要在计划写卡点、已尝试证据、需要谁决定。
- 交接摘要以计划文件为准，不另起一份手写总结当第二真源。

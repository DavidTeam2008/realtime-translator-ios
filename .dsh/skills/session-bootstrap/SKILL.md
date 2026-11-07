---
name: session-bootstrap
description: 对译 Duiyi 冷启动接手：先 make doctor 查环境、make resume 取 active 计划与 git 状态，最终只输出"一个下一步 + 建议阅读清单"。只读定位，不改代码；环境不可用时把动态验证标为未验证。
whenToUse: 新会话第一轮；用户说接手/继续/做到哪了/下一步做什么；恢复中断任务或换 agent 接手前。
---

# session-bootstrap · 冷启动接手

只读。目标：≤3 次读取回答"我是谁、做到哪、下一步、怎么算完成"。

## 动作（按序，勿省略）

1. `make doctor`
   - 退出码 2 = 动态验证不可用（缺 xcodebuild 或基线模拟器 runtime）。这是环境结论，不是代码结论；后续测试只能写"未验证"。
   - 退出码 0 也不代表代码已验证：doctor 只查环境，不跑测试。
2. `make resume`
   - 取 active 计划、三问速答、验证证据、未验证项、未提交改动、建议阅读。
3. 打开 active 计划（`harness/plans/` 中 `status: active`）核对目标/验收/DoD/下一步；上一轮没有 evidence id 的"已完成"按未验证处理。
4. 只读核对 `git status --short` 与 `git log -5 --oneline`；计划"未提交改动"节与实际不一致时先报告，不擅自 stash/reset/清理。

## 输出（固定 5 行）

- 阶段 / active 计划：
- 已证据化：
- 未验证：
- 一个下一步（只写 1 条可执行动作，含命令）：
- 建议阅读（≤2 条，按 `AGENTS.md` §3 路由）：

## 硬约束

- 不改文件、不写计划、不跑 xcodebuild/make test、不 commit。
- 无 active 计划且任务跨会话：建议 `make plan TOPIC=<topic>`；不要跳过计划直接改。
- 计划与 git/最新证据冲突时以 git 与可复核证据为准，先说明冲突再继续。
- `make doctor` 的 WARN（如 mobilebuildmcp 不在 PATH）不等于代码失败，不得据此改代码。

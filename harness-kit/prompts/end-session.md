---
id: end-session
title: 结束会话（保存状态）
short: 结束会话
number: 17
group: 协作与收尾
stage: adopted
kind: task
when: 本次会话要结束，需要把状态固化到仓库
returns: 计划更新、brief 摘要、5 行交接
fail_signal: 只在聊天里说“做完了”
placeholders: 
---

结束本次会话并保存状态：
1) 更新 active 计划：进度、验证证据表（命令 / 结果 / 环境 / 证据 ID）、未验证项、未提交改动（与 git status 对齐）、下一步 1 条。
2) 跑 make check / make verify-static；跑 python3 tools/check_plan.py brief（standard 及以上）。
3) 提交计划与证据；不提交与任务无关的改动。
4) 返回 5 行交接摘要：做了什么 / 证据 / 未验证 / 下一步 / 需要我决策的事。

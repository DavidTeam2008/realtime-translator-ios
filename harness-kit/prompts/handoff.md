---
id: handoff
title: 项目交接（换人 / 换 Agent）
short: 项目交接
number: 18
group: 协作与收尾
stage: adopted
kind: task
when: 要把项目交给另一个 Agent 或人继续
returns: 5 问交接摘要、可 clone 复现
fail_signal: 依赖对话历史才能接手
placeholders: 
---

把项目交接给另一个 Agent 或人：
1) 确认计划状态、证据、未验证项、未提交改动可被 clean clone 复现；依赖对话历史才能接手的地方补进计划。
2) 生成交接摘要，回答 5 问：是什么 / 做到哪 / 怎么验证 / 有哪些坑 / 下一步。
3) 跑 make verify-static 与 make verify-claim（standard+；未配置就跳过并说明）。
4) 把交接写进计划的「下一步」并提交，确保新会话只读仓库即可接手。

返回：交接摘要、验证命令与结果、仍需我决策的事。

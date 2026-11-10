---
id: cold-start
title: 接手陌生项目（冷启动）
short: 接手陌生项目
number: 3
group: 接入与接手
stage: adopted
kind: task
when: 新会话 / 新 Agent 接手，需要先只读了解现状
returns: 5 问回答 + 未验证项
fail_signal: 读不到仓库状态、靠猜测
placeholders: 
---

你刚接手本仓库（只有仓库内容，没有对话历史）。先不要改代码，只读回答 5 问：
1) 这个项目是什么；
2) 现在做到哪（唯一 active 计划 + 最近提交）；
3) 怎么验证（命令、基线测试数、证据在哪）；
4) 踩过哪些坑（CONTRIBUTING / references / 历史评审里记录的）；
5) 下一步是什么（计划里的下一步 + 未验证项）。

入口：AGENTS.md → HARNESS.md（如有）→ 它的阅读路由（docs/ 索引、references/）→ 唯一 active 计划 → harness/evidence/（standard+）。
不确定的项明确写“未验证”；不要为了回答完整而猜测。

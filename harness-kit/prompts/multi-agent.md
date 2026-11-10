---
id: multi-agent
title: 多人 / 多 Agent 分工
short: 多人分工
number: 16
group: 协作与收尾
stage: adopted
kind: task
when: 一个目标需要多个 Agent / 多人并行推进
returns: 写作用域清单、分支/合并顺序、统一门禁结果
fail_signal: 多 Agent 同改一文件
placeholders: GOAL, AGENT_COUNT
---

目标：{{GOAL}}；计划用 {{AGENT_COUNT}} 个 Agent 并行推进（数量不确定就按实际任务拆）。

1) 先写一个 active 计划（owner=我，总 scope.allow），列出子任务与互不重叠的写作用域（文件 / 目录）。
2) 每个 Agent 用独立 branch / worktree；写作用域不重叠；各自完成前跑 make verify-static 并写 evidence。
3) 合并前统一跑 make verify-static 与相关测试；按依赖顺序合并；冲突或跨 scope 改动先停下问我。
4) 返回：子任务 → 分支 → 证据 → 合并结果 对照表。

禁止：多个 Agent 同时改同一文件或同一 active 计划；未经我确认不合并、不改 CI / 门禁。

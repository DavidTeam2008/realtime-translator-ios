---
id: completion-claim
title: 完成声明（附加到任意任务末尾）
short: 完成声明
number: 20
group: 附加片段
stage: any
kind: addon
when: 任意任务收尾时附加，要求 Agent 用证据说话
returns: 
fail_signal: 
placeholders: 
---

声明前：跑 make verify-static 与 make verify-claim（standard+；minimal 没有 verify-claim 就跳过并说明），贴出 claim 输出；
测试类附 evidence id；无法验证写“未验证 + 手动步骤”。
不要用“应该 / 可能 / 看起来”代替证据。

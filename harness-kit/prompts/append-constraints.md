---
id: append-constraints
title: 可选附加约束（按需粘贴）
short: 附加约束
number: 22
group: 附加片段
stage: any
kind: addon
when: 需要额外限制（只读 / 先计划 / 小步提交 / 不联网 / 每步汇报）
returns: 
fail_signal: 
placeholders: 
---

- 只读模式：本次只允许读文件与跑只读命令，不写任何文件。
- 先计划后动手：先给方案与验收命令，我确认后才写代码。
- 小步提交：每个可验证点一个提交，提交信息跟仓库语言。
- 不联网 / 不安装依赖：环境不可用就写“未验证”。
- 每步汇报：命令、exit code、证据 id、下一步。

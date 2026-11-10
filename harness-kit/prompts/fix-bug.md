---
id: fix-bug
title: 修 Bug / 调试
short: 修 Bug
number: 7
group: 需求、计划与开发
stage: adopted
kind: task
when: 有可复现的缺陷或异常，需要定位根因并修
returns: 复现证据、根因、最小修复、回归测试
fail_signal: 直接改代码、无复现
placeholders: SYMPTOM, REPRO
---

症状：{{SYMPTOM}}
复现步骤：{{REPRO}}

1) 先复现并留下失败证据（命令 / 日志 / 退出码）；不要先改代码。
2) 定位根因，给出 file:line 或命令证据；不确定就说明排查计划。
3) 最小修复；不顺手重构无关代码。
4) 补回归测试（测试只增不减、既有断言不改弱），用修复后的测试证明。
5) 跑 make verify-static 与相关测试；返回：根因、修复 diff、回归证据（命令 + exit code + evidence id）、未验证项。

不要用“看起来对”“应该修好了”代替证据。

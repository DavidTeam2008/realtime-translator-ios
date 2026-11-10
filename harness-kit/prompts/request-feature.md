---
id: request-feature
title: 提项目需求（小改动 / 功能）
short: 提需求
number: 4
group: 需求、计划与开发
stage: adopted
kind: task
when: 有一个明确的小需求或功能要改，先判断是否需要新计划
returns: 目标/非目标、影响文件、验收命令、scope 变更
fail_signal: 未确认就改 / 改范围外文件
placeholders: FEATURE
---

需求：{{FEATURE}}

先读根 AGENTS.md 与当前 active 计划，然后：
1) 判断是否需要新计划（小改沿用现有计划；大改先用「提新计划」模板）。
2) 给出：目标 / 非目标、影响文件、验收命令、是否需要改 scope。
3) 我确认后再实现；实现中一次一个可验证点，越界先停下问我。
4) 完成后跑 make verify-static；测试类声明附 evidence id；返回改动、验证命令与未验证项。

不要只说“完成了”；不要把顺手的重构混进本次改动。

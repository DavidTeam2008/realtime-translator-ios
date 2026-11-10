---
id: update-docs
title: 文档 / ADR 更新
short: 文档更新
number: 12
group: 需求、计划与开发
stage: adopted
kind: task
when: 代码或决策变化后，需要同步当前文档与索引
returns: 当前真源改动、历史归档
fail_signal: 直接改历史文档
placeholders: TOPIC
---

同步 {{TOPIC}} 的文档：
1) 找出当前真源（docs/README.md 索引指向的现状文档、决策表 / ADR 如存在、README 当前状态）。
2) 只改当前文档；历史文档只归档不改写；一个事实只出现一次。
3) 跑 make check（含文档链接 / 索引 / 指令预算门禁）。
4) 返回：改动清单、代码与文档仍不一致的地方、未验证项。

---
id: close-stage
title: 结束项目 / 阶段（done + 归档）
short: 结束项目
number: 19
group: 协作与收尾
stage: adopted
kind: task
when: 一个阶段或项目收口，要归档计划并更新现状文档
returns: done/submitted、证据 id、归档、最终报告
fail_signal: 无证据宣布完成
placeholders: 
---

结束本阶段 / 项目：
1) 确认 active 计划 done：submitted 填提交短 hash（若模板没有该字段，按 check_plan 报错补上）；证据表引用真实 evidence id（standard+）。
2) 归档到仓库约定的计划归档目录（kit 模板默认 harness/plans/_archive/；仓库另有约定就按仓库）；更新现状文档（docs/ 索引指向的 roadmap / 当前状态）与 README 的当前状态。
3) 跑 make verify-static 与 make verify-claim。
4) 返回最终报告：完成项 / 未验证项 / 遗留风险 / 下一步（1 条）。

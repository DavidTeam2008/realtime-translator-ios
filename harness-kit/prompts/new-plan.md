---
id: new-plan
title: 提新计划（跨会话任务）
short: 提计划
number: 6
group: 需求、计划与开发
stage: adopted
kind: task
when: 任务跨会话 / 改动较大，需要一个持久计划与 scope
returns: front matter 完整、check_plan PASS
fail_signal: 无计划或两个 active 计划
placeholders: TOPIC
---

为 {{TOPIC}} 建一个跨会话计划：
1) 用 make plan TOPIC={{TOPIC}} 生成计划文件（命名由工具决定；minimal 档没有 plan 目标时先问我要不要升级 profile）。
2) 填 front matter：id / status=active / level / owner / updated / scope.allow / acceptance / verify；scope.allow 至少覆盖计划文件自身（可直接写 harness/plans/）与本次要改的路径。
3) 正文写：目标与非目标 / 验收 / 改动范围 / 进度 / 验证证据 / 未验证项 / 未提交改动 / 下一步。
4) 跑 make check（含 check_plan）通过后提交计划；若报「计划文件在 scope.allow 之外」，把 harness/plans/ 加进 scope.allow 再跑。
5) 之后每个改动同时更新计划与证据。

约束：同一时间只允许一个 active 计划；已有 active 时先问我是继续还是结束它。

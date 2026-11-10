---
id: pr-self-check
title: 代码审查 / PR 前自检
short: 自检 / PR 前
number: 9
group: 评审与发布
stage: adopted
kind: task
when: 改动准备提交 / 开 PR 前，自查范围、证据与门禁
returns: P0/P1/P2 清单 + 门禁输出
fail_signal: 只自评“没问题”
placeholders: 
---

审查我即将提交的改动（先只读，不要改代码）：
1) 看 git status / git diff（含未跟踪文件），确认改动都在本次任务与计划 scope.allow 内。
2) 检查：测试与证据是否齐全、文档影响、敏感信息 / 本机绝对路径、是否删除或弱化了门禁、是否有无关改动。
3) 跑 make verify-static 并记录命令与 exit code。
4) 输出 P0/P1/P2 风险清单（每条附 file:line 或命令证据）与最小修复建议；我确认后再改。

红线：门禁被弱化、证据与提交不绑定、scope 外改动、完成声明无证据 → 直接 P0。

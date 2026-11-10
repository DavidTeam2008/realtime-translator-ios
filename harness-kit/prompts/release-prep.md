---
id: release-prep
title: 发布前操作
short: 发布前
number: 15
group: 评审与发布
stage: adopted
kind: task
when: 准备发版本或对外发布，需要最后一道门禁与证据确认
returns: 门禁/claim 输出、版本与 CHANGELOG、未验证项
fail_signal: 用旧证据、跳过 release-check
placeholders: VERSION
---

目标：准备发布 {{VERSION}}。

1) 确认工作树干净（git status）；active 计划 done 且 submitted 填提交短 hash；证据绑定当前提交。
2) 跑 make verify-static；strict 档再跑 make release-check（fresh + strict 证据）。
3) 跑 make verify-claim（standard+）并贴出 CLAIM 输出。
4) 按仓库约定更新版本号 / CHANGELOG / 当前状态文档；未验证项单列。
5) 只在我确认后执行 tag / push / 发布动作。

约束：不得用旧证据冒充本次发布；真机 / 性能 / 环境不可复核的项写 UNVERIFIED。

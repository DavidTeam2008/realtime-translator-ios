---
id: upgrade-deps
title: 依赖 / 工具升级
short: 依赖升级
number: 11
group: 需求、计划与开发
stage: adopted
kind: task
when: 需要升级依赖、构建工具或运行时版本
returns: 版本差异、兼容风险、回滚方式
fail_signal: 顺手升级无关依赖
placeholders: DEPENDENCY, OLD_VERSION, NEW_VERSION
---

升级 {{DEPENDENCY}}：{{OLD_VERSION}} → {{NEW_VERSION}}（版本号不确定就先查当前锁定版本，再问我确认目标版本）。

1) 先读锁文件 / 清单与兼容说明，列出会影响的范围；不顺手升级无关依赖。
2) 最小改动升级，记录回滚方式。
3) 跑 make verify-static + 相关测试；能复核的写结果，环境不可复核写“未验证”。
4) 更新 CHANGELOG / 依赖文档；返回：变更清单、验证证据、风险与回滚步骤。

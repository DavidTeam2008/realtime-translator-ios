---
id: refactor
title: 重构（行为不变）
short: 重构
number: 8
group: 需求、计划与开发
stage: adopted
kind: task
when: 结构需要整理但行为不能变，需要等价性证据
returns: 基线测试、等价性证据、测试计数不降
fail_signal: 顺手改行为、删测试
placeholders: SCOPE
---

范围：{{SCOPE}}；目标：行为不变、结构更清晰。

1) 先跑基线测试并记录（命令 / 通过数 / exit code）。
2) 只改 scope 内文件；每个可验证点一个提交。
3) 测试计数不得下降，既有断言不得改弱；不要顺手改行为或依赖版本。
4) 完成后跑 make verify-static + 相关测试；返回：行为等价性证据（测试 / 调用点检查）、风险、未验证项。

---
name: verify-change
description: 完成声明前的验证闸门：按变更类型选命令、记录命令/退出码/环境/证据，给出 PASS/FAIL/UNVERIFIED。
---

# verify-change

> 触发：任何“完成 / 已验证 / 已修复”声明之前。
> 参考：[根指令](../../../{{ROOT_AGENTS}})、[验证矩阵](../../../{{REFERENCES_DIR}}/verification.md)、[工作流](../../../{{REFERENCES_DIR}}/workflow.md)。

## 步骤

1. 按变更类型选最低验证：
   - 文档 / 规则 / 工具：`{{CHECK_COMMAND}}`
   - 单模块逻辑：`{{TEST_COMMAND}}` 的相关用例
   - 接口 / 配置 / CI：`{{VERIFY_COMMAND}}` + 干净环境复跑
2. 记录：命令、退出码、环境（OS / 运行时 / 版本）、时间与提交号。
3. 判定三值：
   - 全部通过 → PASS
   - 有失败 → FAIL（先定位，不扩大改动）
   - 未运行或环境不可用 → UNVERIFIED（写原因 + 手动步骤）
4. 启用证据目录时，用 `python3 tools/evidence.py write --claim <name>` 写入，再 `make verify-claim`；计划「验证证据」表引用证据 ID。
5. 输出结论：PASS / FAIL / UNVERIFIED 三选一 + 证据行；禁止把 UNVERIFIED 写成“通过”。

## 禁止

- 删除断言、放宽计数、扩大 skip 白名单来变绿。
- 用“应该能过 / 之前跑过”代替本次运行。

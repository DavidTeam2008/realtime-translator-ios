---
id: <date>-<topic>
status: <status>
level: L1
owner: <owner>
updated: <date>
scope:
  allow:
    - <允许改动的文件或目录>
  deny: []
acceptance:
  - <可执行、可复核的验收判据>
verify:
  - {{VERIFY_COMMAND}}
# 完成（status: done）时填写：证据 commit 的短 hash（逗号/空格分隔，如 `abc1234`）
# submitted: <hash1,hash2>
---

# <date>-<topic> · 执行计划

> 计划是跨会话任务的进度真源：中断 / 交接前更新，完成后归档。
> 根指令见 [`../../{{ROOT_AGENTS}}`](../../{{ROOT_AGENTS}})，流程见 [`../../{{REFERENCES_DIR}}/workflow.md`](../../{{REFERENCES_DIR}}/workflow.md)，证据格式见 [`../evidence/README.md`](../evidence/README.md)。
> **完成流程**：验证证据 + `submitted` 填好 → 移入 `_archive/` → `make check-plan` 通过后再收尾。

## 目标与非目标

- 目标：
- 非目标：

## 验收

- [ ] <可执行判据（命令 / 结果 / 阈值）>

## 改动范围

- 允许：
- 禁止：

## 进度

- [ ]

## 验证证据

| 命令 | 结果 | 环境 | 证据ID |
| --- | --- | --- | --- |
|  |  |  |  |

## 未验证项

- 

## 未提交改动

- 文件 / 意图 / 是否可丢弃：

## 下一步

1. 

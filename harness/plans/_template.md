---
id: <date>-<topic>
status: <active|done|blocked|archived>
level: <L0|L1|L2>
owner: <owner>
updated: <YYYY-MM-DD>
# submitted 只在 status: done 时填：逗号分隔的提交短 hash，如 c412aff,306a9f3
submitted:
scope:              # 允许/禁止改动的文件或目录；越界先停并更新计划
  allow:            # 允许
    - <path or dir>
  deny:             # 禁止
    - <path or dir>
acceptance:         # 可执行判据（与正文“验收”一致，机检非空）
  - <命令 + 期望结果>
verify:             # 完成前必须跑的命令
  - <make 目标或脚本命令>
---

# <主题> · 执行计划

> 跨会话任务的唯一进度真源；用 `make plan TOPIC=<topic>` 生成 `YYYY-MM-DD-<topic>.md`。
> front matter 是机检字段（`tools/plan.py check`）；正文是给下一棒读的事实。
> `status` 只取 active | done | blocked | archived；同一时刻只允许 1 个 active 计划。
> 计划入库：不写本机绝对路径、密钥、设备 UDID；中断、交接、提交前必须更新。

## 目标与非目标

- 目标：
- 非目标：

## 改动范围

- 允许：见 front matter `scope.allow`。
- 禁止：见 front matter `scope.deny`。
- 越界处理：先停下，更新计划与 scope，再继续。

## 验收

- 待填（可执行判据，如命令 + 期望结果）

## Definition of Done

- [ ] 验收判据全部满足（可执行、可复核）
- [ ] `make check` / `make verify-static` PASS
- [ ] 验证证据已记录（命令 + 结果 + 环境）
- [ ] 未验证项已单列
- [ ] 未提交改动与 `git status` 一致
- [ ] 计划已更新；提交前已询问用户

## 进度

- [ ]
- [x]

## 关键决策与理由

- 

## 已排除（勿重试）

- 方案 / 失败原因 / 证据：

## 验证证据

| 命令 | 结果 | 环境 | 证据ID |
| --- | --- | --- | --- |
|  |  |  |  |

## 未验证项

- （未运行 / 未取得证据的项；没有则写“无”）

## 尝试记录

| 尝试# | 动作 | 结果 | 时间 |
| --- | --- | --- | --- |
| 1 |  |  |  |

## 未提交改动

- 文件 / 意图 / 是否可丢弃：（必须与 `git status --short` 一致；没有则写“无”）

## 下一步

1. 

## 待确认

- 

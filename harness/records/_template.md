---
id: <date>-<change-id>
status: <status>
level: L2
owner: <owner>
updated: <date>
tasksSource: openspec
change: <change-id>
base: <immutable-base-commit>
tasks: openspec/changes/<change-id>/tasks.md
scope:
  allow:
    - <允许改动的文件或目录>
  deny: []
acceptance:
  - <从 tasks.md Delivery Contract 读取，不在此复制任务状态>
verify:
  - tools/openspec validate <change-id> --type change --strict --json
  - make delivery-check CHANGE=<change-id>
---

# <change-id> · Change Record

> 本文件只保存 Change ID、不可变 Base、tasks 指针、scope/验收/证据/审查指针；不保存任务复选框或第二份进度。
> 任务状态唯一来源：`openspec/changes/<change-id>/tasks.md`。

## 目标与非目标

- 目标：<一句话>
- 非目标：<边界>

## 验收

- [ ] 以 tasks.md 的 Delivery Contract 与 `delivery-check` 结果为准，不在本记录复制任务状态。

## 改动范围

- 允许：见 front matter `scope.allow`，由 delivery-check 审计 `Base..HEAD` 与工作树。
- 禁止：见 front matter `scope.deny` 与 Delivery Contract。

## 进度

- 指针：任务勾选与 `complete/total` 只从 `tasks` 读取；本记录不维护独立进度。

## 验证证据

| 命令 | 结果 | 环境 | 证据ID |
| --- | --- | --- | --- |
| `make delivery-check CHANGE=<change-id>` | 未运行 | 本机 | —（过程记录） |

## 未验证项

- 首个原生 Change 尚未创建；本模板不产生 active Change。

## 未验证豁免

| 项目 | 理由 | 负责人 | 到期日 |
| --- | --- | --- | --- |

## 未提交改动

- 无未提交改动。

## 下一步

1. 由 delivery-check 校验 tasks/Delivery Contract 后再开始执行。

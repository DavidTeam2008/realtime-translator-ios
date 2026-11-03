# 跨会话任务与交接（人读版）

> 适用：一个任务做不完，或要换 AI Agent / 换会话接着做。
> Agent 侧精简规则见 [`references/workflow.md`](../references/workflow.md)，计划模板在
> [`.apm/plans/_template.md`](../.apm/plans/_template.md)。

## 1. 谁维护

- 计划由**执行任务的 Agent** 维护，不要求人改内容。
- 人只负责两个口令：开工建计划、收工更新并交接。
- 计划是任务进度的唯一真源；[`HANDOFF.md`](../HANDOFF.md) 只管项目阶段与优先级。
- 优先级：代码、`docs/01`–`04`、`HANDOFF.md` 是事实，`references/` 是规则视图；冲突时以前者为准。

## 2. 四个动作

| 时机 | 你做什么 | Agent 做什么 |
| --- | --- | --- |
| 开工 | 说：`跨会话任务，先 make plan TOPIC=speech-gate 再开工` | 生成 `.apm/plans/YYYY-MM-DD-speech-gate.md`，填目标与验收 |
| 过程中 | 不用管 | 每完成一个可验证步骤勾进度；跑完测试贴证据；换方案记“已排除” |
| 收工 / 换 Agent | 说：`更新计划并跑 make handoff` | 补齐 5 项，输出交接摘要 |
| 接手 | 对新 Agent 说：`按 AGENTS.md 接手` | 读最新计划 + `git status`，按“下一步”继续 |

收工必须补齐的 5 项：**进度、已排除方案、验证证据、未提交改动、下一步**。

## 3. 命令

| 命令 | 作用 |
| --- | --- |
| `make plan TOPIC=<topic>` | 新建计划；日期自动加，同日同名拒绝覆盖 |
| `make handoff` | 按最后修改时间取最新计划；`PLAN=<path>` 可指定；输出进度、已排除、验证证据、未提交改动、下一步、待确认 + `git status`，缺“目标/下一步”会告警 |
| `make check` | 文档链接 / 围栏 / 索引 / token 预算；**不检查计划内容** |
| `make check-all` | `make check` + 团队基线；无模板仓时 `check-agents` 显示 SKIP，不阻断 |

`TOPIC` 是 2–5 个短词的任务短名（英文小写优先，允许汉字），如 `speech-gate`、`swiftdata-migration`；只影响文件名。

## 4. 交接示例

把 `make handoff` 的输出整段发给下一个 Agent：

```text
按 AGENTS.md 接手；先读 .apm/plans/2026-10-30-speech-gate.md，再继续。

## 进度
- [x] 已完成项
- [ ] 未完成项

## 已排除（勿重试）
- 方案 / 失败原因 / 证据

## 验证证据
- 命令 / 结果 / 时间

## 未提交改动
- 文件 / 意图 / 是否可丢弃

## 下一步
1. 第一条具体动作
```

## 5. 什么时候不需要

一次会话内能完成、不跨会话、不留未提交改动的小任务（L0/L1）不需要建计划；
判断标准是“换一个 Agent 后，它能否只靠仓库恢复”。

## 6. 常见问题

- **Agent 忘了更新**：跑 `make handoff`，缺“目标与验收”或“下一步”会告警；把告警原样发回给 Agent。
- **同一天多个任务**：`TOPIC` 不同即可；同日同名会拒绝覆盖；`handoff` 按最后修改时间取最新，也可用 `PLAN=` 指定。
- **计划会不会入库**：会，`.apm/plans/` 随仓库提交；计划里不写本机绝对路径、密钥、设备 UDID。完成的计划保留，不自动删除。
- **没有模板仓**：`make check` 照常可用；`make check-all` 的团队基线会显示 SKIP，有模板仓时再复跑。
- **换机器 / 换人**：计划 + `git status` + `git log` 足够恢复任务；设备、签名和测试结果需重新验证。
- **计划写多长**：只写下一棒需要的事实，不写过程流水账；验证证据用命令 + 结果。

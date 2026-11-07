# 跨会话任务与交接（人读版）

> 适用：一个任务做不完，或要换 AI Agent / 换会话接着做。
> Agent 侧精简规则见 [`references/workflow.md`](../references/workflow.md)，计划模板在
> [`.apm/plans/_template.md`](../.apm/plans/_template.md)。

## 1. 谁维护

- 计划由**执行任务的 Agent** 维护，不要求人改内容。
- 人只负责两个口令：开工恢复计划、收工更新并交接。
- 计划是任务进度的唯一真源；[`CONTRIBUTING.md`](../CONTRIBUTING.md) 负责环境与项目阶段入口。
- 每份计划有 front matter：`status: active | done | blocked | archived`；**同一时间只允许一个 active**，完成后标 `done` 并移入 `.apm/plans/_archive/`。
- 真源优先级只在 [`README.md`](README.md) 维护；本页不重复声明。

## 2. 四个动作

| 时机 | 你做什么 | Agent 做什么 |
| --- | --- | --- |
| 开工 | 新任务说：`make plan TOPIC=speech-gate`；已有任务说：`make resume` | 新任务用新模板建计划（填目标/验收/改动范围）；恢复时读 active 计划 + `git status`，输出目标/验收与下一步 |
| 过程中 | 不用管 | 每完成一个可验证步骤勾进度；跑完测试贴证据；换方案记“已排除”；一次只推进一个 active 任务 |
| 收工 / 换 Agent | 说：`make end`，再 `make handoff` | 补齐 5 项 → 跑门禁与计划检查 → 输出交接摘要；完成的任务标 `status: done` 并归档 |
| 接手 | 对新 Agent 说：`按 AGENTS.md 接手` | `make doctor` 查环境 → `make resume` → active 计划 + `git status`，按“下一步”继续 |

收工必须补齐的 5 项：**进度、已排除方案、验证证据、未提交改动、下一步**。

## 3. 命令

| 命令 | 作用 |
| --- | --- |
| `make plan TOPIC=<topic>` | 新建计划（模板含 front matter：status/level/scope/acceptance/verify）；日期自动加，同日同名拒绝覆盖 |
| `make resume` | 开工/接手：active 计划的目标/验收/关键决策 + `git status` + `git log -5` + 下一步 1 条 + 建议阅读清单 |
| `make check-plan` | 计划状态机与必填字段；与 `git status` 交叉比对未提交改动 |
| `make end` | 收尾：`verify-static` 门禁 + 计划检查 + 未验证项清单 + 提交前询问提醒 |
| `make handoff` | 交接摘要：默认最新 active 计划；`PLAN=<path>` 可指定；缺“目标/下一步”会告警 |
| `make doctor` | 环境检查：Xcode / 模拟器 runtime / 真机工具 / 模板仓；环境不满足时输出“动态验证不可执行 → 未验证” |
| `make check` / `make verify-static` | 静态门禁（docs + 架构 + 测试计数 + harness + 计划；后者加脚本语法）；**不判断测试是否真跑过** |
| `make check-all` | `verify-static` + 团队基线；无模板仓时 `check-agents` 显示 SKIP，不阻断 |

`TOPIC` 是 2–5 个短词的任务短名（英文小写优先，允许汉字），如 `speech-gate`、`swiftdata-migration`；只影响文件名。

## 4. 交接示例

把 `make handoff` 的输出整段发给下一个 Agent：

```text
按 AGENTS.md 接手；先跑 `make resume`，读 active 计划后继续。

## 进度
- [x] 已完成项
- [ ] 未完成项

## 已排除（勿重试）
- 方案 / 失败原因 / 证据

## 验证证据
- 命令 | 结果（exit/通过数） | 环境 | 证据 ID

## 未提交改动
- 文件 / 意图 / 是否可丢弃

## 下一步
1. 第一条具体动作
```

## 5. 什么时候不需要

一次会话内能完成、不跨会话、不留未提交改动的小任务（L0/L1）不需要建计划；
判断标准是“换一个 Agent 后，它能否只靠仓库恢复”。

## 6. 常见问题

- **Agent 忘了更新**：跑 `make end`（门禁 + 计划检查）或 `make handoff`；缺“目标/验收/下一步/证据”会告警，把告警原样发回给 Agent。
- **同一时间多份计划**：只有一份 `status: active`；`make resume` 只取 active，无 active 时会报错——先决定继续旧任务还是归档。
- **同一天多个任务**：`TOPIC` 不同即可；同日同名会拒绝覆盖；`handoff` 默认取最新 active，也可用 `PLAN=` 指定。
- **计划会不会入库**：会，`.apm/plans/` 随仓库提交；计划里不写本机绝对路径、密钥、设备 UDID。完成的计划标 `status: done` 后移入 `.apm/plans/_archive/`，保留不删除。
- **没有模板仓**：`make check` 照常可用；`make check-all` 的团队基线会显示 SKIP，有模板仓时再复跑。
- **换机器 / 换人**：计划 + `git status` + `git log` 足够恢复任务；设备、签名和测试结果需重新验证。
- **计划写多长**：只写下一棒需要的事实，不写过程流水账；验证证据用“命令 | 结果 | 环境”。

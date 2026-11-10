# AI coding Agent 提示词模板（接入 / 需求 / 计划 / 分工 / 交接 / 收尾）

> harness-kit 的主要使用者是 **AI coding Agent**。本文给出可直接复制的提示词模板，覆盖从接入到收尾的常见场景；模板与具体 Agent 无关（DeepSeek Harness / Claude Code / Codex / Cursor / 自研），前提是它能读文件、跑 shell。
> 用法：先贴「公共前置」，再把对应场景模板整段发给 Agent，替换 `<...>`。相关：[README](../README.md)、[接入指南](adoption.md)、[playbook](playbook.md)、[演化与治理](governance.md)。

## 0. 公共前置（每个任务前贴一次）

```text
你是本仓库的 AI coding Agent，按 Harness Engineering 流程工作：
1) 先读 AGENTS.md；按任务读嵌套 AGENTS.md / references/；跑 make check 确认基线。
2) 计划是唯一状态源：先看 harness/plans/ 的 active 计划；跨会话/大任务先建计划。
3) 完成前必须 make verify-static；测试类声明附 evidence id；没有证据就写“未验证 + 手动步骤”。
4) 不得删除、弱化或绕过门禁；不得改 scope.allow/deny 之外的文件；越界先停下问我。
```

## 1. 接入新项目（Agent-first）

```text
目标：用 harness-kit 接入本仓库（新项目，standard profile）。
kit 位置：<kit checkout 路径>。
步骤：
1) 读 <kit>/README.md 与 docs/adoption.md；不要凭记忆。
2) 给出 init 计划并把 --dry-run 输出给我确认：
   harness-init --profile standard --target . --name <项目名> --language <语言> \
     --test-command "<真实测试命令>" --dry-run
3) 我确认后执行 init（会自动跑首次 make check）；若 FAIL，按提示修内容，不要删检查。
4) 提交 init 产物；创建第一份 active 计划（目标/非目标、scope、验收、下一步）。
5) 返回：改动列表、make check 输出、下一步 1 条。
约束：不引入 kit 运行时依赖；不改动业务代码；测试命令必须真实存在。
```

## 2. 接入存量项目（Agent-first，先只读）

```text
目标：用 harness-kit 改造本存量仓库（brownfield），先只读、后改造。
步骤：
1) 只读盘点，不要先改代码：
   harness-adopt --target . --report /tmp/adoption-report.md --json
2) 给我盘点摘要：文档缺口/断链/过期、卫生问题（构建产物/绝对符号链接/本机路径/大文件）、
   现有测试命令、建议 profile；列出改造顺序，等我确认。
3) 确认后：harness-init --profile standard --dry-run → 执行 → 首次 make check。
4) 按 docs/playbook.md 的 brownfield 七步法逐步执行：
   文档蒸馏 → 清洁 → config 的 hygiene/layers → CI/hooks → JUnit 证据 → harness-selftest。
   每步先更新计划再改代码，一个可验证点一个提交。
5) 每步返回：命令、exit code、证据 id（如有）、未验证项。
约束：不 --force 覆盖既有文档；历史文档只归档不改写；越界改动停下并更新 scope。
```

## 3. 提项目需求（小改动 / 功能）

```text
需求：<一句话描述功能/修复>。
先读 AGENTS.md 与当前 active 计划；判断是否需要新计划（小改沿用现有计划，大改走「提新计划」模板）。
给出：目标/非目标、影响文件、验收命令、是否需要改 scope。
我确认后再实现；完成后跑 make verify-static，测试类附 evidence id，不要只说“完成了”。
```

## 4. 提新计划（跨会话任务）

```text
为 <主题> 建一个跨会话计划：
1) 读 harness/plans/_template.md，生成 harness/plans/<日期>-<topic>.md；
2) 填 front matter：id / status=active / level / owner / updated / scope.allow / acceptance / verify；
3) 写「目标与非目标 / 验收 / 改动范围 / 进度 / 验证证据 / 未验证项 / 未提交改动 / 下一步」；
4) 跑 python3 tools/check_plan.py 通过后提交计划；
5) 之后每个改动更新计划与证据。
约束：同一时间只允许一个 active 计划；已有 active 时先问我是继续还是结束它。
```

## 5. 多人 / 多 Agent 分工

```text
目标：<目标>，用 <N> 个 Agent 并行推进。
1) 先写一个 active 计划（owner=我，总 scope.allow），列出子任务与互不重叠的写作用域（文件/目录）；
2) 每个 Agent 独立 branch/worktree 工作；各自完成前跑 make verify-static 并写 evidence；
3) 合并前统一跑 make verify-static 与 harness-selftest；按 <顺序> 合并；
4) 冲突或跨 scope 改动先停下问我。
禁止：多个 Agent 同时改同一文件或同一 active 计划；未经我确认不合并、不改 CI/门禁。
```

## 6. 结束会话（保存状态）

```text
结束本次会话并保存状态：
1) 更新 active 计划：进度、验证证据表（命令/结果/环境/证据 ID）、未验证项、未提交改动（与 git status 对齐）、下一步 1 条；
2) 跑 make check / make verify-static；跑 python3 tools/check_plan.py brief；
3) 提交计划与证据；
4) 返回 5 行交接摘要：做了什么 / 证据 / 未验证 / 下一步 / 需要我决策的事。
不要提交与任务无关的改动。
```

## 7. 项目交接（换人 / 换 Agent）

```text
把项目交接给另一个 Agent 或人：
1) 确认计划状态、证据、未验证项、未提交改动可被 clean clone 复现；
2) 生成交接摘要，回答 5 问：是什么 / 做到哪 / 怎么验证 / 有哪些坑 / 下一步；
3) 跑 make verify-static 与 make verify-claim（如已配置）；
4) 把交接写进计划的「下一步」并提交，确保新会话只读仓库即可接手。
```

## 8. 结束项目 / 阶段（done + 归档）

```text
结束本阶段/项目：
1) 确认 active 计划 done：submitted 填提交短 hash；证据表引用真实 evidence id；
2) 归档到 harness/plans/_archive/；更新 docs/06-roadmap（或对应现状文档）与 README 当前状态；
3) 跑 make verify-static 与 make verify-claim；
4) 返回最终报告：完成项 / 未验证项 / 遗留风险 / 下一步。
```

## 9. 完成声明（附加到任意任务末尾）

```text
声明前：跑 make verify-static 与 make verify-claim，贴出 claim 输出；
测试类附 evidence id；无法验证写“未验证 + 手动步骤”。
不要用“应该 / 可能 / 看起来”代替证据。
```

## 10. 场景 → Agent 应返回什么

| 场景 | Agent 必须返回 | 失败信号 |
| --- | --- | --- |
| 接入新项目 | init dry-run 计划、首次 `make check` 输出、第一份计划 | 直接改业务代码 / 跳过 dry-run |
| 接入存量项目 | 只读盘点摘要、改造顺序、逐步提交与证据 | 先重构再盘点 / `--force` 覆盖文档 |
| 提需求 | 目标/非目标、影响文件、验收命令、scope 变更 | 未确认就改 / 改范围外文件 |
| 提计划 | front matter 完整、`check_plan` PASS | 无计划或两个 active 计划 |
| 多人分工 | 写作用域清单、分支/合并顺序、统一门禁结果 | 多 Agent 同改一文件 |
| 结束会话 | 计划更新、`brief` 摘要、5 行交接 | 只在聊天里说“做完了” |
| 项目交接 | 5 问交接摘要、可 clone 复现 | 依赖对话历史才能接手 |
| 结束项目 | done/submitted、证据 id、归档、最终报告 | 无证据宣布完成 |

## 11. 可选附加约束（按需粘贴）

```text
- 只读模式：本次只允许读文件与跑只读命令，不写任何文件。
- 先计划后动手：先给方案与验收命令，我确认后才写代码。
- 小步提交：每个可验证点一个提交，提交信息跟仓库语言。
- 不联网 / 不安装依赖：环境不可用就写“未验证”。
- 每步汇报：命令、exit code、证据 id、下一步。
```

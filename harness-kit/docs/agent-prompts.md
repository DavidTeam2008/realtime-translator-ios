# AI coding Agent 提示词模板（接入 / 开发 / 评审 / 发布 / 交接 / 收尾）

> harness-kit 的主要使用者是 **AI coding Agent**。本文给出可直接复制的提示词模板，覆盖接入、开发、评审、发布、协作与收尾；模板与具体 Agent 无关（DeepSeek Harness / Claude Code / Codex / Cursor / 自研），前提是它能读文件、跑 shell。
> 用法：先贴「公共前置」，再贴对应场景模板，替换 `<...>`。任务复杂时可组合多个模板（例如：自检 → 对抗性评审 → 发布前 → 完成声明）。相关：[README](../README.md)、[接入指南](adoption.md)、[playbook](playbook.md)、[演化与治理](governance.md)。

## 0. 公共前置（每个任务前贴一次）

```text
你是本仓库的 AI coding Agent，按 Harness Engineering 流程工作：
1) 先读 AGENTS.md；按任务读嵌套 AGENTS.md / references/。
2) 若仓库已接入（存在 Makefile 与 harness/）：跑 make check 确认基线，并查看 harness/plans/ 的 active 计划。
   若是尚未接入的新仓库：跳过 make check，先按「接入新项目 / 接入存量项目」模板执行。
3) 完成前必须 make verify-static；测试类声明附 evidence id；没有证据就写“未验证 + 手动步骤”。
4) 不得删除、弱化或绕过门禁；不得改 scope.allow/deny 之外的文件；越界先停下问我。
```

## 1. 接入新项目（Agent-first）

```text
目标：用 harness-kit 接入本仓库（新项目，standard profile）。
kit 位置：<kit checkout 路径>。
步骤：
1) 读 <kit>/README.md 与 <kit>/docs/adoption.md；不要凭记忆。
2) 给出 init 计划并把 --dry-run 输出给我确认：
   python3 <kit>/scripts/harness-init --profile standard --target . --name <项目名> \
     --language <语言> --test-command "<真实测试命令>" --dry-run
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
   python3 <kit>/scripts/harness-adopt --target . --report /tmp/adoption-report.md --json
2) 给我盘点摘要：文档缺口/断链/过期、卫生问题（构建产物/绝对符号链接/本机路径/大文件）、
   现有测试命令、建议 profile；列出改造顺序，等我确认。
3) 确认后：python3 <kit>/scripts/harness-init --profile standard --target . --dry-run → 执行 → 首次 make check。
4) 按 <kit>/docs/playbook.md 的 brownfield 七步法逐步执行：
   文档蒸馏 → 清洁 → config 的 hygiene/layers → CI/hooks → JUnit 证据 → harness-selftest。
   每步先更新计划再改代码，一个可验证点一个提交。
5) 每步返回：命令、exit code、证据 id（如有）、未验证项。
约束：不 --force 覆盖既有文档；历史文档只归档不改写；越界改动停下并更新 scope。
```

## 3. 接手陌生项目（冷启动）

```text
你刚接手本仓库（只有仓库内容，没有对话历史）。只读回答 5 问：
1) 这个项目是什么；2) 现在做到哪；3) 怎么验证；4) 踩过哪些坑；5) 下一步是什么。
入口：AGENTS.md → HARNESS.md（如有）→ docs/README.md → active 计划 → harness/evidence/。
不要改代码；不确定的项明确写“未验证”。
```

## 4. 提项目需求（小改动 / 功能）

```text
需求：<一句话描述功能/修复>。
先读 AGENTS.md 与当前 active 计划；判断是否需要新计划（小改沿用现有计划，大改走「提新计划」模板）。
给出：目标/非目标、影响文件、验收命令、是否需要改 scope。
我确认后再实现；完成后跑 make verify-static，测试类附 evidence id，不要只说“完成了”。
```

## 5. 方案评估 / 技术选型

```text
针对 <问题> 给 2–3 个方案：约束、成本、风险、验证方式；先不写代码。
推荐其中一个并说明放弃其他方案的理由；我确认后再进入「提新计划」。
不要把未验证的性能/兼容性假设写成结论。
```

## 6. 提新计划（跨会话任务）

```text
为 <主题> 建一个跨会话计划：
1) 读 harness/plans/_template.md，生成 harness/plans/<日期>-<topic>.md；
2) 填 front matter：id / status=active / level / owner / updated / scope.allow / acceptance / verify；
3) 写「目标与非目标 / 验收 / 改动范围 / 进度 / 验证证据 / 未验证项 / 未提交改动 / 下一步」；
4) 跑 python3 tools/check_plan.py 通过后提交计划；
5) 之后每个改动更新计划与证据。
约束：同一时间只允许一个 active 计划；已有 active 时先问我是继续还是结束它。
```

## 7. 修 Bug / 调试

```text
症状：<描述>；复现步骤：<...>。
1) 先复现并留下失败证据（命令/日志）；2) 定位根因（给 file:line 或命令证据）；
3) 最小修复；4) 补回归测试（测试只增不减）；
5) 跑 make verify-static 与相关测试；返回根因、修复、回归证据、未验证项。
不要用“看起来对”代替证据；不要顺手重构无关代码。
```

## 8. 重构（行为不变）

```text
范围：<目录/模块>；目标：行为不变、结构更清晰。
1) 先跑基线测试并记录；2) 只改 scope 内文件；3) 每个可验证点一个提交；
4) 测试计数不得下降、既有断言不得改弱；
5) 完成后跑 make verify-static + 测试；返回行为等价性证据（测试/调用点检查）与风险。
```

## 9. 代码审查 / PR 前自检

```text
审查我即将提交的改动（先不要改代码）：
1) 看 git status / git diff；2) 检查 scope 是否越界、测试与证据是否齐全、
   文档影响、敏感信息/本机路径、是否删除或弱化了门禁；
3) 跑 make verify-static；
4) 输出 P0/P1/P2 风险清单（每条附 file:line 或命令证据）与最小修复建议，我确认后再改。
```

## 10. 新开会话对抗性评审

```text
新开一个干净会话（不要带起草历史），对 <计划/PR/改动范围> 做对抗性评审。
输入：仓库路径、目标声明、改动清单（可选 diff）；不要提供自评或起草过程。
步骤：只读仓库；核对门禁与证据；主动找低成本蒙混路径；挑战隐含假设。
输出：结论（可合并 / 需修改 / 不可合并）、P0/P1/P2 问题表（每条附 file:line 或命令）、
被挑战的假设、缺失信息、最小验证清单。
红线：门禁被弱化、证据与提交不绑定、scope 外改动、完成声明无证据 → 直接 P0。
禁止：复述作者结论、给无证据的好评。
```

## 11. 依赖 / 工具升级

```text
升级 <依赖/工具> 从 <旧版本> 到 <新版本>；先读锁文件与兼容说明，最小改动；
不顺手升级无关依赖；升级后跑 make verify-static + 相关测试；
记录 CHANGELOG/风险/回滚方式；环境不可复核的项写“未验证”。
```

## 12. 文档 / ADR 更新

```text
同步 <主题> 的文档：docs 当前真源、决策表（如适用）、README 当前状态；
历史文档只归档不改写；跑文档门禁（make check）；
返回改动清单、与代码不一致的地方、未验证项。
```

## 13. 性能 / 延迟验证（先测量）

```text
先测量再优化：定义指标/口径/环境；跑基线（n≥<样本数>）并记录命令与数据；
改动后同口径复测；没有数据不声称“更快”；把测量方法与结果写进证据/文档。
```

## 14. 安全 / 敏感信息自查

```text
检查本次改动是否引入：密钥/Token/凭证、本机绝对路径、个人数据、未校验的外部内容执行。
跑仓库敏感信息门禁（如有）；发现问题先报告、不要写入 git 历史；
返回问题清单、修复建议、剩余风险。
```

## 15. 发布前操作

```text
目标：准备发布 <版本/阶段>。
1) 确认 clean tree；active 计划 done + submitted；证据绑定当前提交；
2) 跑 make verify-static；strict profile 再跑 make release-check（fresh + strict 证据）；
3) 跑 make verify-claim 并贴出 CLAIM 行；
4) 按仓库约定更新版本号/CHANGELOG/当前状态文档；未验证项单列；
5) 只在我确认后执行 tag / push / 发布动作。
约束：不得用旧证据冒充本次发布；真机/性能/环境不可复核的项写 UNVERIFIED。
```

## 16. 多人 / 多 Agent 分工

```text
目标：<目标>，用 <N> 个 Agent 并行推进。
1) 先写一个 active 计划（owner=我，总 scope.allow），列出子任务与互不重叠的写作用域（文件/目录）；
2) 每个 Agent 独立 branch/worktree 工作；各自完成前跑 make verify-static 并写 evidence；
3) 合并前统一跑 make verify-static 与 harness-selftest；按 <顺序> 合并；
4) 冲突或跨 scope 改动先停下问我。
禁止：多个 Agent 同时改同一文件或同一 active 计划；未经我确认不合并、不改 CI/门禁。
```

## 17. 结束会话（保存状态）

```text
结束本次会话并保存状态：
1) 更新 active 计划：进度、验证证据表（命令/结果/环境/证据 ID）、未验证项、未提交改动（与 git status 对齐）、下一步 1 条；
2) 跑 make check / make verify-static；跑 python3 tools/check_plan.py brief；
3) 提交计划与证据；
4) 返回 5 行交接摘要：做了什么 / 证据 / 未验证 / 下一步 / 需要我决策的事。
不要提交与任务无关的改动。
```

## 18. 项目交接（换人 / 换 Agent）

```text
把项目交接给另一个 Agent 或人：
1) 确认计划状态、证据、未验证项、未提交改动可被 clean clone 复现；
2) 生成交接摘要，回答 5 问：是什么 / 做到哪 / 怎么验证 / 有哪些坑 / 下一步；
3) 跑 make verify-static 与 make verify-claim（如已配置）；
4) 把交接写进计划的「下一步」并提交，确保新会话只读仓库即可接手。
```

## 19. 结束项目 / 阶段（done + 归档）

```text
结束本阶段/项目：
1) 确认 active 计划 done：submitted 填提交短 hash；证据表引用真实 evidence id；
2) 归档到 harness/plans/_archive/；更新 docs/06-roadmap（或对应现状文档）与 README 当前状态；
3) 跑 make verify-static 与 make verify-claim；
4) 返回最终报告：完成项 / 未验证项 / 遗留风险 / 下一步。
```

## 20. 完成声明（附加到任意任务末尾）

```text
声明前：跑 make verify-static 与 make verify-claim，贴出 claim 输出；
测试类附 evidence id；无法验证写“未验证 + 手动步骤”。
不要用“应该 / 可能 / 看起来”代替证据。
```

## 21. 场景 → Agent 应返回什么

| 场景 | Agent 必须返回 | 失败信号 |
| --- | --- | --- |
| 接入新项目 | init dry-run 计划、首次 `make check` 输出、第一份计划 | 直接改业务代码 / 跳过 dry-run |
| 接入存量项目 | 只读盘点摘要、改造顺序、逐步提交与证据 | 先重构再盘点 / `--force` 覆盖文档 |
| 接手陌生项目 | 5 问回答 + 未验证项 | 读不到仓库状态、靠猜测 |
| 提需求 | 目标/非目标、影响文件、验收命令、scope 变更 | 未确认就改 / 改范围外文件 |
| 方案评估 | 2–3 个方案 + 推荐理由 + 验证方式 | 只给一个方案、把假设当结论 |
| 提计划 | front matter 完整、`check_plan` PASS | 无计划或两个 active 计划 |
| 修 Bug | 复现证据、根因、最小修复、回归测试 | 直接改代码、无复现 |
| 重构 | 基线测试、等价性证据、测试计数不降 | 顺手改行为、删测试 |
| 自检 / PR 前 | P0/P1/P2 清单 + 门禁输出 | 只自评“没问题” |
| 对抗性评审 | 结论 + P0/P1/P2 + 被挑战假设 + 最小验证 | 复述作者结论、无证据好评 |
| 依赖升级 | 版本差异、兼容风险、回滚方式 | 顺手升级无关依赖 |
| 文档更新 | 当前真源改动、历史归档 | 直接改历史文档 |
| 性能验证 | 指标/基线数据/复测数据 | 无数据宣称更快 |
| 安全自查 | 敏感项清单 + 修复建议 | 把密钥/路径写进历史 |
| 发布前 | 门禁/claim 输出、版本与 CHANGELOG、未验证项 | 用旧证据、跳过 release-check |
| 多人分工 | 写作用域清单、分支/合并顺序、统一门禁结果 | 多 Agent 同改一文件 |
| 结束会话 | 计划更新、`brief` 摘要、5 行交接 | 只在聊天里说“做完了” |
| 项目交接 | 5 问交接摘要、可 clone 复现 | 依赖对话历史才能接手 |
| 结束项目 | done/submitted、证据 id、归档、最终报告 | 无证据宣布完成 |

## 22. 可选附加约束（按需粘贴）

```text
- 只读模式：本次只允许读文件与跑只读命令，不写任何文件。
- 先计划后动手：先给方案与验收命令，我确认后才写代码。
- 小步提交：每个可验证点一个提交，提交信息跟仓库语言。
- 不联网 / 不安装依赖：环境不可用就写“未验证”。
- 每步汇报：命令、exit code、证据 id、下一步。
```

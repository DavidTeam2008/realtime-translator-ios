# AI coding Agent 提示词模板（兜底入口：接入 / 开发 / 评审 / 发布 / 交接 / 收尾）

> harness-kit 的**默认入口是入口 skill**：装一次（`<kit>/scripts/harness-skill install --scope user`），任意仓库的 Agent 会话都能通过 skill 路由到接入/计划/验证/发布流程，不需要复制提示词。
>
> 本文是**兜底**提示词库：只在宿主不支持 skills，或你临时想用命令行拿一段文本时使用。模板与具体 Agent 无关（DeepSeek Harness / Claude Code / Codex / Cursor / 自研），前提是它能读文件、跑 shell。
>
> **本文件由 `scripts/harness-prompt render` 从 `prompts/*.md` 生成，不要手改**；改模板请改 `prompts/` 后重新渲染。

## 怎么用：先装 skill（推荐），再用提示词兜底

**推荐（一次）**：在目标仓库根目录执行一次用户级安装，之后直接对 Agent 说「接入这个项目」：

```bash
<kit>/scripts/harness-skill install --scope user   # 装到 ~/.agents/skills；所有仓库可见
```

**兜底（宿主没有 skills 支持时）**：一条命令拿提示词，粘贴给 Agent；下文 `<kit>` 指 kit 克隆路径：

```bash
cd /path/to/your-project
<kit>/scripts/harness-prompt list                     # 看场景清单（会显示目标仓库是否已接入）
<kit>/scripts/harness-prompt copy adopt-brownfield    # 复制到剪贴板，直接粘给 Agent
<kit>/scripts/harness-prompt show fix-bug             # 或打印出来手动复制
```

- `copy` / `show` 会按**所选场景**拼接前置：接入场景用 0B（未接入，含 kit 路径与只读约束），日常场景用 0A（已接入）；并填好 kit 与目标仓库的绝对路径。
- 如果目标仓库看起来与场景阶段不符（例如在未接入仓库里选日常场景），命令会先给 WARN，不会静默贴错前置。
- 需要你补充的信息（如 `<SYMPTOM>`）会列出来；也可以 `--set SYMPTOM="..." --set REPRO="..."` 一次填好。
- 剪贴板：`copy` 依次尝试 `pbcopy` / `clip` / `wl-copy` / `xclip` / `xsel`；都没有时会把提示词打印到 stdout 并给 WARN，可手动复制。
- 可加别名：`alias hp='<kit>/scripts/harness-prompt'`，之后 `hp copy fix-bug`。
- 没有命令行时手工复制：先贴 §0A（已接入）或 §0B（未接入），把 `<kit>` / `<目标仓库路径>` 换成本机路径，再贴场景模板；§1 / §2 是未接入场景，手工复制时也要先贴 0B。

## 0. 公共前置（按项目阶段选一段）

**先判断阶段**：仓库根有 `Makefile`（或 `Makefile.harness`）且存在 `harness/config.json` → 已接入（用 0A）；否则未接入（用 0B）。
由 `harness-prompt show/copy` 自动拼接；手工复制时按上面的规则先贴对应前置。接入完成后的日常任务统一用 0A。

### 0A. 已接入项目（日常任务贴这一段）

```text
【前置｜已接入项目】工作目录（仓库根）：<目标仓库路径>
你是本仓库的 AI coding Agent，按 Harness Engineering 流程工作：
1) 先读根 AGENTS.md，并按它的路由读嵌套 AGENTS.md / references/；不要凭记忆。
2) 确认仓库已接入：根目录有 Makefile 且存在 harness/ 目录。
3) 跑 make check 确认基线；查看唯一 active 计划（harness/plans/，standard 及以上）。
4) 严格作用域：只改本次任务与计划 scope.allow 覆盖的文件；越界先停下问我，不顺手重构。
5) 完成前跑 make verify-static；测试类声明附 evidence id（harness/evidence/），没有证据写“未验证 + 手动步骤”。
6) 命令不存在（如 minimal 档没有 verify-claim 或计划目录）就跳过并说明，不得伪造输出；不得删除、弱化或绕过任何门禁。
```

### 0B. 未接入项目（接入阶段贴这一段；§1 / §2 的 show/copy 输出会自动带上）

```text
【前置｜未接入项目（接入阶段）】工作目录（仓库根）：<目标仓库路径>；harness-kit 位置：<kit>
下文所有 kit 路径都指 <kit>；本仓库可能还没有 Makefile / harness/ / tools/，这是正常的。
接入阶段规则：
1) 先读 <kit>/README.md 与 <kit>/docs/adoption.md 的相关章节，再执行；不要凭记忆。
2) 先只读盘点，后改造：harness-adopt 只读；harness-init 先 --dry-run 给我确认。
3) 命令不存在 = 尚未接入：直接说明，不要伪造输出，也不要假设 make check 可用。
4) 不删除或弱化既有检查；不用 --force 覆盖既有文档；历史文档只归档不改写；越界先停。
5) 每阶段返回：命令 + exit code + 产物路径 + 未验证项；接入完成后改用已接入流程（0A）。
```

## 1. 接入新项目（Agent-first）

> 阶段：未接入 · 前置：CLI 自动拼 0B（含 kit 路径与只读约束）；手工复制请先贴 §0B · 需替换：无占位符（命令示例参数按第 2 步结论替换） · 复制：`<kit>/scripts/harness-prompt copy adopt-new`

```text
目标：用 harness-kit 接入本仓库（新项目 / 空仓，standard profile），接入后能跑通首次 make check。

步骤：
1) 读 <kit>/README.md 与 <kit>/docs/adoption.md 的接入章节，不要凭记忆。
2) 盘点本仓库：语言、构建系统、真实测试命令（实际跑一下确认可用）；给出 profile、项目名、语言与测试命令的选择理由。拿不准先问我。
3) 先出计划并执行 dry-run（不写文件），把计划给我确认；把第 2 步确定的参数加到命令上：
   python3 <kit>/scripts/harness-init --profile standard --target . --dry-run
   参数示例（仅示形，用第 2 步的结论替换）：--name MyApp --language python --test-command "python3 -m unittest discover -s tests -q"
4) 我确认后去掉 --dry-run 执行；init 会自动跑首次 make check。若 FAIL，按提示修内容，不要删检查。
5) 检查产物（git status / 文件列表）后提交；再用 make plan TOPIC=first-milestone 建第一份 active 计划（目标/非目标、scope、验收、下一步；TOPIC 用你定的里程碑名）。
6) 返回：改动列表、make check 输出（命令 + exit code）、下一步 1 条。

约束：不改业务代码；不引入 kit 运行时依赖；测试命令必须真实存在。
```

## 2. 接入存量项目（Agent-first，先只读）

> 阶段：未接入 · 前置：CLI 自动拼 0B（含 kit 路径与只读约束）；手工复制请先贴 §0B · 需替换：无占位符（命令示例参数按第 2 步结论替换） · 复制：`<kit>/scripts/harness-prompt copy adopt-brownfield`

```text
目标：用 harness-kit 改造本存量仓库（brownfield），严格先只读、后改造。

步骤：
1) 先只读盘点，不要改任何代码；报告写到系统临时目录（如 /tmp/adoption-report.md），不要写进被盘点仓库：
   python3 <kit>/scripts/harness-adopt --target . --report /tmp/adoption-report.md --json
2) 给我盘点摘要，等我确认：
   - 文档：断链 / 未登记 / 疑似过期 / 索引缺失；
   - 卫生：被跟踪构建产物 / 绝对符号链接 / 本机路径 / 大文件；
   - 现有门禁与 CI、推荐 profile（默认 standard）与理由、建议测试命令的
     可执行性探测结果（报告已给出「建议命令 / 可执行性」；不要跑全量测试）；
   - 改造顺序：文档蒸馏 → 清洁 → config hygiene/layers → CI/hooks → JUnit 证据 → harness-selftest。
3) 确认后先 dry-run 再 init。profile 口径：**默认 standard**；只有用户明确要求
   strict（需要 adapters / red-team / release-check）并写清理由时才升级（显式选择）。
   把第 2 步确定的参数带上（--language / --test-command 用盘点的结论；
   报告建议命令不可执行时先在宿主修正，或用 --test-command 覆盖）：
   python3 <kit>/scripts/harness-init --profile standard --target . --dry-run
   复核动作标签 RENDER / COPY / APPEND / CONFLICT（已有文件冲突时才出现 CONFLICT），再执行；首次 make check FAIL 就修内容，不删检查。
4) 按 <kit>/docs/playbook.md 的 brownfield 七步法逐步做；每步先更新计划再改代码，一个可验证点一个提交。
5) 接入完成后（顺序固定）：
   - 归档盘点报告：python3 <kit>/scripts/harness-adopt --target . --archive-report 第 1 步报告的文件路径；
   - 生成评分卡草稿：make scorecard（自评 / 独立复评两列填证据，不把自评当认证）；
   - 跑负向注入自检：make selftest（证明门禁会红）；
   - 未验证项清零，或写入计划的「未验证豁免」表（理由 / 负责人 / 到期日）。
6) 每步返回：命令、exit code、证据 id（接入后）、未验证项。

约束：不用 --force 覆盖既有文档；历史文档只归档不改写；越界改动先停下并更新 scope。盘点完成前不改代码。
```

## 3. 接手陌生项目（冷启动）

> 阶段：已接入 · 前置：CLI 自动拼 0A；手工复制请先贴 §0A · 需替换：无 · 复制：`<kit>/scripts/harness-prompt copy cold-start`

```text
你刚接手本仓库（只有仓库内容，没有对话历史）。先不要改代码，只读回答 5 问：
1) 这个项目是什么；
2) 现在做到哪（唯一 active 计划 + 最近提交）；
3) 怎么验证（命令、基线测试数、证据在哪）；
4) 踩过哪些坑（CONTRIBUTING / references / 历史评审里记录的）；
5) 下一步是什么（计划里的下一步 + 未验证项）。

入口：AGENTS.md → HARNESS.md（如有）→ 它的阅读路由（docs/ 索引、references/）→ 唯一 active 计划 → harness/evidence/（standard+）。
不确定的项明确写“未验证”；不要为了回答完整而猜测。
```

## 4. 提项目需求（小改动 / 功能）

> 阶段：已接入 · 前置：CLI 自动拼 0A；手工复制请先贴 §0A · 需替换：`<FEATURE>` · 复制：`<kit>/scripts/harness-prompt copy request-feature`

```text
需求：<FEATURE>

先读根 AGENTS.md 与当前 active 计划，然后：
1) 判断是否需要新计划（小改沿用现有计划；大改先用「提新计划」模板）。
2) 给出：目标 / 非目标、影响文件、验收命令、是否需要改 scope。
3) 我确认后再实现；实现中一次一个可验证点，越界先停下问我。
4) 完成后跑 make verify-static；测试类声明附 evidence id；返回改动、验证命令与未验证项。

不要只说“完成了”；不要把顺手的重构混进本次改动。
```

## 5. 方案评估 / 技术选型

> 阶段：已接入 · 前置：CLI 自动拼 0A；手工复制请先贴 §0A · 需替换：`<PROBLEM>` · 复制：`<kit>/scripts/harness-prompt copy evaluate-options`

```text
针对 <PROBLEM> 给 2–3 个可选方案，先不写代码：
- 每个方案：约束、成本、风险、验证方式、放弃理由；
- 推荐其中一个，说明为什么；
- 标出你无法验证的假设（性能 / 兼容性 / 环境），不要写成结论。

我确认后再进入「提新计划」。
```

## 6. 提新计划（跨会话任务）

> 阶段：已接入 · 前置：CLI 自动拼 0A；手工复制请先贴 §0A · 需替换：`<TOPIC>` · 复制：`<kit>/scripts/harness-prompt copy new-plan`

```text
为 <TOPIC> 建一个跨会话计划：
1) 用 make plan TOPIC=<TOPIC> 生成计划文件（命名由工具决定；minimal 档没有 plan 目标时先问我要不要升级 profile）。
2) 填 front matter：id / status=active / level / owner / updated / scope.allow / acceptance / verify；scope.allow 至少覆盖计划文件自身（可直接写 harness/plans/）与本次要改的路径。
3) 正文写：目标与非目标 / 验收 / 改动范围 / 进度 / 验证证据 / 未验证项 / 未提交改动 / 下一步。
4) 跑 make check（含 check_plan）通过后提交计划；若报「计划文件在 scope.allow 之外」，把 harness/plans/ 加进 scope.allow 再跑。
5) 之后每个改动同时更新计划与证据。

约束：同一时间只允许一个 active 计划；已有 active 时先问我是继续还是结束它。
```

## 7. 修 Bug / 调试

> 阶段：已接入 · 前置：CLI 自动拼 0A；手工复制请先贴 §0A · 需替换：`<SYMPTOM>`、`<REPRO>` · 复制：`<kit>/scripts/harness-prompt copy fix-bug`

```text
症状：<SYMPTOM>
复现步骤：<REPRO>

1) 先复现并留下失败证据（命令 / 日志 / 退出码）；不要先改代码。
2) 定位根因，给出 file:line 或命令证据；不确定就说明排查计划。
3) 最小修复；不顺手重构无关代码。
4) 补回归测试（测试只增不减、既有断言不改弱），用修复后的测试证明。
5) 跑 make verify-static 与相关测试；返回：根因、修复 diff、回归证据（命令 + exit code + evidence id）、未验证项。

不要用“看起来对”“应该修好了”代替证据。
```

## 8. 重构（行为不变）

> 阶段：已接入 · 前置：CLI 自动拼 0A；手工复制请先贴 §0A · 需替换：`<SCOPE>` · 复制：`<kit>/scripts/harness-prompt copy refactor`

```text
范围：<SCOPE>；目标：行为不变、结构更清晰。

1) 先跑基线测试并记录（命令 / 通过数 / exit code）。
2) 只改 scope 内文件；每个可验证点一个提交。
3) 测试计数不得下降，既有断言不得改弱；不要顺手改行为或依赖版本。
4) 完成后跑 make verify-static + 相关测试；返回：行为等价性证据（测试 / 调用点检查）、风险、未验证项。
```

## 9. 代码审查 / PR 前自检

> 阶段：已接入 · 前置：CLI 自动拼 0A；手工复制请先贴 §0A · 需替换：无 · 复制：`<kit>/scripts/harness-prompt copy pr-self-check`

```text
审查我即将提交的改动（先只读，不要改代码）：
1) 看 git status / git diff（含未跟踪文件），确认改动都在本次任务与计划 scope.allow 内。
2) 检查：测试与证据是否齐全、文档影响、敏感信息 / 本机绝对路径、是否删除或弱化了门禁、是否有无关改动。
3) 跑 make verify-static 并记录命令与 exit code。
4) 输出 P0/P1/P2 风险清单（每条附 file:line 或命令证据）与最小修复建议；我确认后再改。

红线：门禁被弱化、证据与提交不绑定、scope 外改动、完成声明无证据 → 直接 P0。
```

## 10. 新开会话对抗性评审

> 阶段：已接入 · 前置：CLI 自动拼 0A；手工复制请先贴 §0A · 需替换：`<REVIEW_SCOPE>` · 复制：`<kit>/scripts/harness-prompt copy adversarial-review`

```text
任务：对 <REVIEW_SCOPE> 做对抗性评审。如果你所在的会话带有起草历史或自评，先停下并让我新开会话再继续。

输入（只给这些，不提供起草过程或自评）：当前仓库路径、目标声明、改动清单（可选 git diff）。
规则：
- 只读仓库；不修改文件；可以跑只读命令与 make verify-static 复核。
- 核对门禁与证据是否真的成立；主动找低成本蒙混路径；挑战隐含假设。
- 禁止复述作者结论、禁止无证据好评。

输出：
1) 结论：可合并 / 需修改 / 不可合并；
2) P0/P1/P2 问题表（每条附 file:line 或命令证据）；
3) 被挑战的假设；
4) 缺失信息；
5) 最小验证清单（作者可用哪些命令自证）。
红线：门禁被弱化、证据与提交不绑定、scope 外改动、完成声明无证据 → 直接 P0。
```

## 11. 依赖 / 工具升级

> 阶段：已接入 · 前置：CLI 自动拼 0A；手工复制请先贴 §0A · 需替换：`<DEPENDENCY>`、`<OLD_VERSION>`、`<NEW_VERSION>` · 复制：`<kit>/scripts/harness-prompt copy upgrade-deps`

```text
升级 <DEPENDENCY>：<OLD_VERSION> → <NEW_VERSION>（版本号不确定就先查当前锁定版本，再问我确认目标版本）。

1) 先读锁文件 / 清单与兼容说明，列出会影响的范围；不顺手升级无关依赖。
2) 最小改动升级，记录回滚方式。
3) 跑 make verify-static + 相关测试；能复核的写结果，环境不可复核写“未验证”。
4) 更新 CHANGELOG / 依赖文档；返回：变更清单、验证证据、风险与回滚步骤。
```

## 12. 文档 / ADR 更新

> 阶段：已接入 · 前置：CLI 自动拼 0A；手工复制请先贴 §0A · 需替换：`<TOPIC>` · 复制：`<kit>/scripts/harness-prompt copy update-docs`

```text
同步 <TOPIC> 的文档：
1) 找出当前真源（docs/README.md 索引指向的现状文档、决策表 / ADR 如存在、README 当前状态）。
2) 只改当前文档；历史文档只归档不改写；一个事实只出现一次。
3) 跑 make check（含文档链接 / 索引 / 指令预算门禁）。
4) 返回：改动清单、代码与文档仍不一致的地方、未验证项。
```

## 13. 性能 / 延迟验证（先测量）

> 阶段：已接入 · 前置：CLI 自动拼 0A；手工复制请先贴 §0A · 需替换：`<METRIC>`、`<SAMPLE_SIZE>` · 复制：`<kit>/scripts/harness-prompt copy verify-performance`

```text
先测量再优化：
1) 定义指标（<METRIC>）、口径、环境（设备 / 版本 / 数据规模），写清楚再跑。
2) 跑基线 n≥<SAMPLE_SIZE> 次，记录命令与原始数据。
3) 改动后用同一口径复测；没有数据不声称“更快”。
4) 把方法与结果写进 evidence / 性能文档；返回前后对比、波动范围、未验证项。
```

## 14. 安全 / 敏感信息自查

> 阶段：已接入 · 前置：CLI 自动拼 0A；手工复制请先贴 §0A · 需替换：无 · 复制：`<kit>/scripts/harness-prompt copy security-self-check`

```text
检查本次改动是否引入：密钥 / Token / 凭证、本机绝对路径、设备标识 / 个人数据、未校验的外部内容执行。
1) 跑 make verify-static（含敏感串与本机路径检查）。
2) 如仓库有专用敏感信息门禁也跑，并记录命令与 exit code。
3) 发现问题先报告、不要写入 git 历史；给出修复建议。
4) 返回：问题清单（file:line）、修复建议、剩余风险、未验证项。
```

## 15. 发布前操作

> 阶段：已接入 · 前置：CLI 自动拼 0A；手工复制请先贴 §0A · 需替换：`<VERSION>` · 复制：`<kit>/scripts/harness-prompt copy release-prep`

```text
目标：准备发布 <VERSION>。

1) 确认工作树干净（git status）；active 计划 done 且 submitted 填提交短 hash；证据绑定当前提交。
2) 跑 make verify-static；strict 档再跑 make release-check（fresh + strict 证据）。
3) 跑 make verify-claim（standard+）并贴出 CLAIM 输出。
4) 按仓库约定更新版本号 / CHANGELOG / 当前状态文档；未验证项单列。
5) 只在我确认后执行 tag / push / 发布动作。

约束：不得用旧证据冒充本次发布；真机 / 性能 / 环境不可复核的项写 UNVERIFIED。
```

## 16. 多人 / 多 Agent 分工

> 阶段：已接入 · 前置：CLI 自动拼 0A；手工复制请先贴 §0A · 需替换：`<GOAL>`、`<AGENT_COUNT>` · 复制：`<kit>/scripts/harness-prompt copy multi-agent`

```text
目标：<GOAL>；计划用 <AGENT_COUNT> 个 Agent 并行推进（数量不确定就按实际任务拆）。

1) 先写一个 active 计划（owner=我，总 scope.allow），列出子任务与互不重叠的写作用域（文件 / 目录）。
2) 每个 Agent 用独立 branch / worktree；写作用域不重叠；各自完成前跑 make verify-static 并写 evidence。
3) 合并前统一跑 make verify-static 与相关测试；按依赖顺序合并；冲突或跨 scope 改动先停下问我。
4) 返回：子任务 → 分支 → 证据 → 合并结果 对照表。

禁止：多个 Agent 同时改同一文件或同一 active 计划；未经我确认不合并、不改 CI / 门禁。
```

## 17. 结束会话（保存状态）

> 阶段：已接入 · 前置：CLI 自动拼 0A；手工复制请先贴 §0A · 需替换：无 · 复制：`<kit>/scripts/harness-prompt copy end-session`

```text
结束本次会话并保存状态：
1) 更新 active 计划：进度、验证证据表（命令 / 结果 / 环境 / 证据 ID）、未验证项、未提交改动（与 git status 对齐）、下一步 1 条。
2) 跑 make check / make verify-static；跑 python3 tools/check_plan.py brief（standard 及以上）。
3) 提交计划与证据；不提交与任务无关的改动。
4) 返回 5 行交接摘要：做了什么 / 证据 / 未验证 / 下一步 / 需要我决策的事。
```

## 18. 项目交接（换人 / 换 Agent）

> 阶段：已接入 · 前置：CLI 自动拼 0A；手工复制请先贴 §0A · 需替换：无 · 复制：`<kit>/scripts/harness-prompt copy handoff`

```text
把项目交接给另一个 Agent 或人：
1) 确认计划状态、证据、未验证项、未提交改动可被 clean clone 复现；依赖对话历史才能接手的地方补进计划。
2) 生成交接摘要，回答 5 问：是什么 / 做到哪 / 怎么验证 / 有哪些坑 / 下一步。
3) 跑 make verify-static 与 make verify-claim（standard+；未配置就跳过并说明）。
4) 把交接写进计划的「下一步」并提交，确保新会话只读仓库即可接手。

返回：交接摘要、验证命令与结果、仍需我决策的事。
```

## 19. 结束项目 / 阶段（done + 归档）

> 阶段：已接入 · 前置：CLI 自动拼 0A；手工复制请先贴 §0A · 需替换：无 · 复制：`<kit>/scripts/harness-prompt copy close-stage`

```text
结束本阶段 / 项目：
1) 确认 active 计划 done：submitted 填提交短 hash（若模板没有该字段，按 check_plan 报错补上）；证据表引用真实 evidence id（standard+）。
2) 归档到仓库约定的计划归档目录（kit 模板默认 harness/plans/_archive/；仓库另有约定就按仓库）；更新现状文档（docs/ 索引指向的 roadmap / 当前状态）与 README 的当前状态。
3) 跑 make verify-static 与 make verify-claim。
4) 返回最终报告：完成项 / 未验证项 / 遗留风险 / 下一步（1 条）。
```

## 20. 完成声明（附加到任意任务末尾）

> 用法：附加片段，贴到任务末尾（不单独使用）· 复制：`<kit>/scripts/harness-prompt copy completion-claim`

```text
声明前：跑 make verify-static 与 make verify-claim（standard+；minimal 没有 verify-claim 就跳过并说明），贴出 claim 输出；
测试类附 evidence id；无法验证写“未验证 + 手动步骤”。
不要用“应该 / 可能 / 看起来”代替证据。
```

## 21. 场景 → Agent 应返回什么

> 下表与上面的模板一一对应；完成声明至少要覆盖「Agent 必须返回」这一列。

| 场景 | Agent 必须返回 | 失败信号 |
| --- | --- | --- |
| 接入新项目 | init dry-run 计划、首次 make check 输出、第一份计划 | 直接改业务代码 / 跳过 dry-run |
| 接入存量项目 | 只读盘点摘要、改造顺序、逐步提交与证据 | 先重构再盘点 / --force 覆盖文档 |
| 接手陌生项目 | 5 问回答 + 未验证项 | 读不到仓库状态、靠猜测 |
| 提需求 | 目标/非目标、影响文件、验收命令、scope 变更 | 未确认就改 / 改范围外文件 |
| 方案评估 | 2–3 个方案 + 推荐理由 + 验证方式 | 只给一个方案、把假设当结论 |
| 提计划 | front matter 完整、check_plan PASS | 无计划或两个 active 计划 |
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
| 结束会话 | 计划更新、brief 摘要、5 行交接 | 只在聊天里说“做完了” |
| 项目交接 | 5 问交接摘要、可 clone 复现 | 依赖对话历史才能接手 |
| 结束项目 | done/submitted、证据 id、归档、最终报告 | 无证据宣布完成 |
| 反馈 kit 问题 | 可粘贴的 issue 草稿（版本/环境/命令/期望/最小复现）与是否已提交 | 改宿主仓的 kit 门禁绕过，或未确认就对外发 issue |

## 22. 可选附加约束（按需粘贴）

> 用法：附加片段，贴到任务末尾（不单独使用）· 复制：`<kit>/scripts/harness-prompt copy append-constraints`

```text
- 只读模式：本次只允许读文件与跑只读命令，不写任何文件。
- 先计划后动手：先给方案与验收命令，我确认后才写代码。
- 小步提交：每个可验证点一个提交，提交信息跟仓库语言。
- 不联网 / 不安装依赖：环境不可用就写“未验证”。
- 每步汇报：命令、exit code、证据 id、下一步。
```

## 23. 反馈 kit 问题（缺陷 / 文档不一致 / 需求）

> 阶段：接入或已接入 · 前置：无（模板自包含，接入/日常均可用） · 需替换：`<KIND>` · 复制：`<kit>/scripts/harness-prompt copy feedback`

```text
处理 kit 自身问题的反馈（类型：<KIND>）。先分诊，再产出 issue 草稿，不要替用户直接发布：
1) 分诊：kit 缺陷 / 文档不一致 / 宿主侧问题 / 需求建议。宿主侧问题（文档未登记、测试命令不真实、环境差异）先在宿主内修，不占 kit issue；kit 未承诺能力（不跑测试、不解析测试输出）先读 kit README 的「局限与未验证」。
2) 收集最小信息：kit 版本（`<kit>/VERSION` 或 `.harness-manifest.json` 的 kitVersion）、profile、宿主技术栈、复现命令原文 + 退出码 + 关键输出（脱敏）、期望 vs 实际、最小复现（空白临时仓 init 或一个最小 commit）。
3) 输出一份可直接粘贴的 issue 草稿：标题 `[缺陷|文档|需求] 一句话现象`，正文按上面的信息分段；提交地址 <https://github.com/DavidTeam2008/harness-engineering-kit/issues>（公开镜像仓受理，镜像只读）。
4) 对外动作先问：建议用户确认后再提交；修复发布后按升级流程回流——`<kit>/scripts/harness-upgrade --check/--plan` → 只回写 kit 管理面 → 重装入口 skill → `make verify-static` 复核。
禁止：改宿主 `tools/` / kit 模板绕过缺陷（升级会覆盖）；删除或弱化门禁。
```

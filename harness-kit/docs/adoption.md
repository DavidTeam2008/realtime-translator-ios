# 接入指南 · AI coding Agent 优先（新项目 / 存量项目 / 命令行手动接入）

> harness-kit 的主要使用者是 **AI coding Agent**：接入、日常任务、计划、分工、交接、收尾都以 Agent 为主路径。**默认入口是入口 skill**：装一次（`<kit>/scripts/harness-skill install --scope user`），之后任意仓库对 Agent 说「接入这个项目」或当前任务即可，不需要复制提示词；宿主不支持 skills 时再用 `<kit>/scripts/harness-prompt copy <场景>` 兜底（按场景拼前置、填路径；阶段不符会 WARN），完整模板见[提示词库](agent-prompts.md)。
> 相关：[README](../README.md)（能力与价值）、[提示词库](agent-prompts.md)（兜底模板）、[playbook](playbook.md)（命令行五步/七步细节）、[governance](governance.md)（演化、反臃肿、多人协作）、[SPEC](../SPEC.md)（内部契约）。

## 1. 先看症状：你需不需要 harness-kit

| 你可能正在经历 | harness-kit 对应机制 |
| --- | --- |
| Agent 说"完成了/已验证"，但仓库里没有可复核的记录 | 证据三值（PASS / FAIL / UNVERIFIED）+ clean tree + commit 绑定；**没有 evidence id 一律按未验证处理** |
| 文档、计划、进度散落在聊天记录和 README 里，每次新会话都要重建上下文 | AGENTS 树 + 唯一 active 计划 + 交接摘要；冷启动只读仓库 |
| Agent 越改越宽：顺手重构、改配置、动无关文件 | `scope.allow/deny` 与 `git status` 交叉核对；越界 FAIL |
| 文档链接断、索引缺、过期结论被当现状、本机路径/构建产物入库 | `check_docs` / `check_agents` / `check_hygiene` 静态门禁 |
| 门禁写了但"永远绿"，没人知道它是否还有效 | `harness-selftest` 负向注入：往临时副本里制造违规，断言对应门禁必须变红 |
| 换模型/换 Agent/换人就重写一遍规则 | 规则与门禁是仓库里的文件与命令，不绑定任何 Agent；适配层可选、薄 |

**不适合**：只需要一次性脚本、没有测试与协作、也不打算长期维护的仓库——接入成本会大于收益。

## 2. AI coding Agent 接入（推荐）

harness-kit 的脚手架能力覆盖 Harness Engineering 五子系统（Instructions / State / Verification / Scope / Session Lifecycle），Agent 接入、存量改造、版本升级用的是同一套五子系统资产；每步落到哪一层，见 [README「它是什么」](../README.md#它是什么harness-engineering-脚手架)。

**默认入口：装一次入口 skill（推荐，零粘贴）**。`<kit>` = kit 克隆路径；在目标仓库根目录执行：

```bash
cd /path/to/your-project
<kit>/scripts/harness-skill install --scope user      # 装到 ~/.agents/skills（DSH）与 ~/.claude/skills（Claude Code）
# 然后直接对 Agent 说：「用 harness-kit 接入这个项目」
```

- 用户级安装写 `~/.agents/skills/harness/`（DSH rank 500）与 `~/.claude/skills/harness/`（Claude Code，v0.5.1 起默认两个 agent；项目级同名 skill 优先），不写入仓库；`--scope project` 则装到仓库 `.dsh/skills/`、`.claude/skills/` 并随仓库提交（适合团队 pin 版本）。
- 装完 `harness-skill check --scope user` 应报 in sync；升级 kit 后重装 `install --scope user --force`（`references/upgrade.md` 有步骤）。
- 宿主支持斜杠调用时（DSH / Qoder CN / Claude Code 输入框有「技能」补全）优先输入 `/harness`：显式加载、确定性强；自然语言点名（「用 harness skill 接入这个项目」）是兜底。
- skill 会先定位 kit（用户级 `install.json` → 仓内/父目录 `harness-kit/` → 问一次），再按「未接入走 adopt、已接入先 `status`」路由。

**兜底：宿主不支持 skills 时用提示词**（一条命令拿到，粘贴给 Agent）：

```bash
cd /path/to/your-project                             # 在目标仓库根目录执行（或加 --target）
<kit>/scripts/harness-prompt copy adopt-brownfield   # 接入存量项目：拼 0B 前置 + 填 kit/目标路径
<kit>/scripts/harness-prompt copy fix-bug            # 接入后的日常任务：拼 0A 前置
<kit>/scripts/harness-prompt list                    # 看全部场景；目标仓库阶段与场景不符时给 WARN
```

手工复制时见 [prompts §0 公共前置](agent-prompts.md#0-公共前置按项目阶段选一段)：先贴 0A（已接入）或 0B（未接入），再把 `<kit>` / `<目标仓库路径>` 换成本机路径；§1 / §2 是未接入场景，手工复制时同样先贴 0B。**不要给未接入项目贴 0A**（它假设 `make check` 与 `harness/plans/` 已存在）。

### 2.1 新项目（Agent-first）

让 Agent 自己执行接入，但按顺序、可复查。装了入口 skill 时直接说「接入这个项目」；没装时用兜底模板 `<kit>/scripts/harness-prompt copy adopt-new`（完整模板见 [prompts §1](agent-prompts.md#1-接入新项目agent-first)）。核心步骤：

```text
读 <kit>/README.md 与 <kit>/docs/adoption.md → python3 <kit>/scripts/harness-init --dry-run 给人确认 →
执行 init（自动 make check）→ 提交 → 第一份 active 计划（scope/验收/下一步）
```

- 失败按提示修内容，不删检查；测试命令必须真实存在。
- 接入后从每次任务都走：计划 → 实现 → `make verify-static` → 证据 → `verify-claim` → 交接。
- **v0.3.0+ 统一入口**：接入后第一条命令 `python3 tools/harness.py status`（或 `make status`）；建计划 `harness.py start`（有需求卡用 `intake`），完成前 `harness.py verify` / 发布 `release --check`，交接 `harness.py handoff`（详见 playbook「日常循环」）。
- **入口 skill（默认）**：用户级 `harness-skill install --scope user` 装一次，所有仓库可见；需要团队 pin 版本时用 `--scope project` 装到仓库 `.dsh/skills/`、`.claude/skills/` 并提交。A/B 未执行前，skill 只做入口路由，所有事实与门禁仍以仓库文件为准。
- test-count 类完成声明需要可重算的 **JUnit XML artifact**（`tools/evidence_from_junit.py`）；xcresult 等不可重算产物会判 UNVERIFIED。

### 2.2 存量项目（Agent-first，先只读）

**强制顺序**：`harness-adopt` 只读盘点 → 人确认改造计划 → init → 按 playbook 七步法。装了入口 skill 时直接说「接入这个项目」，skill 会按 `references/adopt.md` 执行；没装时用兜底模板 `<kit>/scripts/harness-prompt copy adopt-brownfield`（完整模板见 [prompts §2](agent-prompts.md#2-接入存量项目agent-first先只读)）。

```bash
<kit>/scripts/harness-adopt --target . --report /tmp/adoption-report.md --json   # 只读，0 写入
```

- 禁止 Agent 在看懂现状之前重构代码；盘点报告作为"改造前基线"存档。
- 核心纪律：**门禁红就修内容，不删检查**；项目自有文档留在项目内，kit 只提供骨架与门禁。

### 2.3 按 Agent 能力分层接入（不绑定具体产品）

| 层 | 做什么 | 备注 |
| --- | --- | --- |
| 指令层 | 项目根 `AGENTS.md`（kit 渲染）作为唯一入口 | 支持 AGENTS.md 的 Agent 直接生效；只认 `CLAUDE.md` 的用 kit 的 `claude-code` 适配器；其他在系统提示里写"先读 AGENTS.md" |
| 执行层 | Makefile 统一接口：`make check` / `verify-static` / `verify-claim` / `check-host` / `plan` | Agent 不需要知道脚本细节 |
| 状态层 | 唯一 active 计划 + 证据摘要 + 交接摘要 | 跨会话/跨 Agent 的共享状态，不依赖对话历史 |
| 证据层 | 完成声明引用 evidence id；静态 claim 由 `verify-claim` 复跑命令判定 | 无 id 或 UNVERIFIED 不算完成 |
| 保护层 | `harness-selftest` 负向注入；`scope.allow` 越界拦截 | 防止门禁腐烂与范围失控 |

各 Agent 的最小差异：

- **DeepSeek Harness / Codex / Claude Code（v2.1.277+）**：原生读取 AGENTS.md，直接可用；kit 的 `dsh` 适配器目前为预留。
- **只认 CLAUDE.md 的 Claude Code 旧版本**：用 `claude-code` 适配器生成 `CLAUDE.md` 与 hooks 示例。
- **Cursor / 自研 Agent / 其他**：只要"读文件 + 跑命令"即可；hooks 用 git `pre-push`（与 Agent 无关）。
- **多 Agent 并行**：先写计划与写作用域，再并行；证据绑定 commit，合并前统一跑门禁（见 [governance 多人协作](governance.md#3-多人与多-agent-协作)与 [分工模板](agent-prompts.md#16-多人--多-agent-分工)）。

### 2.4 Agent 反模式（会被仓库抓住）

1. **改门禁让它变绿**：用 `harness-selftest` 证明门禁仍会红，提交记录可审计。
2. **先改代码后补计划/证据**：`check_plan` 会把"未提交改动与计划声明不一致"报 FAIL。
3. **把构建产物/本机路径提交**：`check_hygiene` 直接失败。
4. **在对话里宣布完成**：没有证据 = 未验证，`verify-claim` 不会给 PASS。
5. **多个 Agent 同时改一个仓库**：唯一 active 计划会被打破（`check_plan` FAIL），先协调再写。

## 3. 命令行手动接入（不依赖 Agent）

适合想先手动理解流程、或环境里没有 Agent 的场景。命令与 Agent 执行的是同一套。

### 3.1 新项目（10 分钟最小接入）

```bash
git clone --depth 1 --branch <kit-ver> https://github.com/DavidTeam2008/harness-engineering-kit.git /path/to/harness-kit

python3 /path/to/harness-kit/scripts/harness-init \
  --profile standard --target . --name MyApp \
  --language python \
  --test-command "python3 -m unittest discover -s tests -q" \
  --dry-run          # 先看 RENDER/COPY/APPEND/CONFLICT；确认后去掉 --dry-run

git add -A && git commit -m "chore: adopt harness-kit standard profile"
```

- init 会自动跑首次 `make check` 并透传退出码；exit 0 即最小接入完成。
- 已有 `Makefile` 时不会被覆盖：生成 `Makefile.harness`，宿主 `Makefile` 里加 `include Makefile.harness`。
- 详细步骤（含测试/证据/CI 接线）见 [playbook 第 1–5 步](playbook.md)。

### 3.2 存量项目（brownfield，先只读再改造）

```bash
# ① 只读盘点（0 写入；报告写到目标仓之外）
python3 /path/to/harness-kit/scripts/harness-adopt --target ../legacy-app --report /tmp/adoption.md
python3 /path/to/harness-kit/scripts/harness-adopt --target ../legacy-app --json

# ② 定 profile / 基线 / 真实测试命令（存量默认 standard；strict 需显式选择并写理由）
# ③ scaffold：先 --dry-run 再 init（已有文件默认 CONFLICT；--force 会备份后覆盖）
python3 /path/to/harness-kit/scripts/harness-init --profile standard --target ../legacy-app \
  --language android --test-command "./gradlew testDebugUnitTest"

# ④ 文档蒸馏 → ⑤ 清洁 → ⑥ config hygiene/layers + CI/hooks + JUnit 证据
# ⑦ 负向注入验收：
python3 /path/to/harness-kit/scripts/harness-selftest --target ../legacy-app

# ⑧ 接入后收口：归档盘点报告 → 评分卡 → 自检 → 未验证项清零/豁免
python3 /path/to/harness-kit/scripts/harness-adopt --target . --archive-report /tmp/adoption.md
# 之后在目标仓内：make scorecard && make selftest
```

- 七步法每一步的退出信号/回滚见 [playbook「存量项目（brownfield）改造」](playbook.md#存量项目brownfield改造七步法)。
- 接入前建议记录**基线评分**（见 §5），接入后再复评，才能回答"到底改善了没有"。盘点报告在只读阶段放目标仓之外是刻意的；接入完成后用 `--archive-report` 归档到`harness/reports/adoption-<YYYY-MM-DD>.md`，仓库内才有可追溯的接入前基线。

## 4. 接入后：skill 路由（默认）与场景模板（兜底）

接入完成后，装了 skill 的 Agent 直接按意图触发（`status` / `plan` / `verify` / `review` / `release` / `handoff` / `upgrade`），不需要取模板。宿主不支持 skills 时，用 `<kit>/scripts/harness-prompt copy <场景>` 取兜底模板（自动拼 0A 前置并填路径），下表是场景索引：

**接入与接手**

| 场景 | 模板 |
| --- | --- |
| 接入新项目 | [§1 接入新项目](agent-prompts.md#1-接入新项目agent-first) |
| 接入存量项目 | [§2 接入存量项目](agent-prompts.md#2-接入存量项目agent-first先只读) |
| 接手陌生项目 | [§3 冷启动](agent-prompts.md#3-接手陌生项目冷启动) |

**需求、计划与开发**

| 场景 | 模板 |
| --- | --- |
| 提项目需求 | [§4 提项目需求](agent-prompts.md#4-提项目需求小改动--功能) |
| 方案评估 / 技术选型 | [§5 方案评估](agent-prompts.md#5-方案评估--技术选型) |
| 提新计划 | [§6 提新计划](agent-prompts.md#6-提新计划跨会话任务) |
| 修 Bug / 调试 | [§7 修 Bug](agent-prompts.md#7-修-bug--调试) |
| 重构（行为不变） | [§8 重构](agent-prompts.md#8-重构行为不变) |
| 依赖 / 工具升级 | [§11 依赖升级](agent-prompts.md#11-依赖--工具升级) |
| 文档 / ADR 更新 | [§12 文档更新](agent-prompts.md#12-文档--adr-更新) |
| 性能 / 延迟验证 | [§13 性能验证](agent-prompts.md#13-性能--延迟验证先测量) |
| 安全 / 敏感信息自查 | [§14 安全自查](agent-prompts.md#14-安全--敏感信息自查) |

**评审与发布**

| 场景 | 模板 |
| --- | --- |
| 代码审查 / PR 前自检 | [§9 自检](agent-prompts.md#9-代码审查--pr-前自检) |
| 新开会话对抗性评审 | [§10 对抗性评审](agent-prompts.md#10-新开会话对抗性评审) |
| 发布前操作 | [§15 发布前](agent-prompts.md#15-发布前操作) |

**协作与收尾**

| 场景 | 模板 |
| --- | --- |
| 多人 / 多 Agent 分工 | [§16 分工](agent-prompts.md#16-多人--多-agent-分工) |
| 结束会话 | [§17 结束会话](agent-prompts.md#17-结束会话保存状态) |
| 项目交接 | [§18 交接](agent-prompts.md#18-项目交接换人--换-agent) |
| 结束项目 / 阶段 | [§19 结束项目](agent-prompts.md#19-结束项目--阶段done--归档) |
| 完成声明（任意任务） | [§20 完成声明](agent-prompts.md#20-完成声明附加到任意任务末尾) |

## 5. 真实案例：接入前后五子系统评分

### 5.1 评分口径（先对齐，避免"自嗨分"）

- 五子系统各 1–5 分，口径见 standard profile 自带的 `docs/harness-scorecard.md`（模板：[评分卡模板](../core/templates/docs/harness-scorecard.md.template)）：
  **1 = 缺失；3 = 有规则但不可机检；5 = 有门禁 + 有证据 + 定期复核**。
- 每一分必须附证据（文件/命令/证据 ID）；没有证据的评分按未验证处理。
- 自评与独立复评**分列**；独立复评的输入只有仓库，不参考起草过程。
- 这个分数是工程判断，不是认证；它会随仓库变化，大改后需重评。

### 5.2 案例 A：存量 Android/Gradle 仓（brownfield，自评）

同一评分卡、同一口径，接入前基于只读盘点证据打分，接入后基于当前门禁/证据打分：

| 子系统 | 接入前 | 接入后 | 关键证据（前 → 后） |
| --- | --- | --- | --- |
| Instructions | 1 | 4 | 前：无 AGENTS/HARNESS，docs 无索引、1 条跨仓断链、61 处过期内容；后：3 个指令文件预算/敏感串机检，11 篇当前文档 + 10 篇归档，`docs/README` 索引 100% |
| State | 1 | 4 | 前：进度只在 README/commit 里，无计划/证据；后：唯一 active 计划 + done/submitted 绑定，2 条证据（tests-pass 65/65、static-gates） |
| Verification | 2 | 4 | 前：65 个单测只能手跑，无 CI、无门禁、完成不可否证；后：`check` / `verify-static` / `verify-claim` 三值 + `harness-selftest` 8/8 + 分支保护的 `static gates` CI |
| Scope | 1 | 4 | 前：无作用域机制；后：`scope.allow/deny` 与 `git status` 交叉核验，改动走 PR + required check |
| Session Lifecycle | 1 | 4 | 前：无冷启动/交接/审计；后：接手步骤 + 计划状态机 + 归档约定 + 版本升级路径（v0.2.2→v0.2.3 已验证） |
| **合计** | **6/25（24%）** | **20/25（80%）** | 同口径复评；未做独立复评 |

> 口径声明：这是**自评**，证据可复核（见该仓 `HARNESS.md`、`harness/plans/_archive/`、`harness/evidence/`）；接入前的 1–2 分来自该仓接入评估报告里的实测问题（无 AGENTS/HARNESS/CI、无计划/证据、文档断链与过期、环境事实入库）。

### 5.3 案例 B：来源案例 iOS 仓（独立复评）

同一个评分卡，由**非作者**独立复评（只读仓库、独立复跑门禁）：

| 时间/口径 | Instructions | State | Verification | Scope | Lifecycle | 综合 |
| --- | --- | --- | --- | --- | --- | --- |
| 改造前独立审计（2026-11-04） | — | — | — | — | — | **2.5/5**（文档型 harness：有规则、无结构化证据，验证层不可否证） |
| Phase 2.3 独立复评（2026-11-07） | 4.0 | 3.5 | 4.0 | 3.0 | 3.5 | **3.6/5（72%）** |
| Phase 2.5 独立复评（2026-11-07） | 4.0 | 4.0 | 4.3 | 3.5 | 4.0 | **≈4.0/5（79%）** |

补充口径：同一仓库的"对外标杆成熟度"由独立审计给出 **17/35 → 25.5/35（3.6/5）**；当前自评/独立复评均约 4.0。分数与局限见该仓的评分卡与复评记录（仓库内 `docs/harness-scorecard.md`）。

### 5.4 怎么复现这套评分

```text
接入前：harness-adopt --report（只读盘点）→ 人工按评分卡打分 → 存入改造计划作为基线
接入后：make scorecard 生成草稿（自动跑门禁、记录 exit/证据 ID/测试与文档计数）
        → 人工填「自评」→ 独立复评填「独立复评」列 → 过期由 make check WARN
        → 需要时 make selftest 证明门禁仍会红
```

**注意**：接入 ≠ 问题消失。kit 只覆盖结构性、可机检的部分；文档语义正确性、代码质量、真机/性能验证仍需要人或宿主传感器（detekt/lint/真机测试等）。分数提升反映的是"可验证性与可维护性"，不是产品质量自动提升。

## 6. 接入验收清单

**Agent 接入（推荐）**
- [ ] 入口 skill 已装一次（`harness-skill install --scope user`；`check --scope user` in sync），或宿主不支持 skills 时有可用的兜底提示词流程
- [ ] Agent 冷启动只读仓库可回答"现在做到哪、下一步、哪些未验证"
- [ ] Agent 的完成声明带 evidence id 或显式"未验证"
- [ ] 计划 `scope.allow` 与实际改动一致
- [ ] 换一个 Agent/新会话不丢状态（唯一 active 计划 + 证据摘要）

**命令行手动接入（10 分钟最小）**
- [ ] `harness-init --dry-run` 计划已复核，无意外覆盖
- [ ] 首次 `make check` exit 0
- [ ] `git status` 干净后提交
- [ ] 选定了真实测试命令并写入 `harness/config.json.commands.test`

**完整接入（1 天，真实仓库）**
- [ ] 文档蒸馏完成（当前/历史分层、索引 100%、链接可用）
- [ ] 一条真实测试证据 PASS，`make verify-claim` exit 0
- [ ] CI（或 pre-push）跑 `make verify-static`
- [ ] `make selftest` exit 0（门禁证明会红）
- [ ] `make scorecard` 生成评分卡草稿；过期由 `make check` WARN；自评 / 独立复评分列
- [ ] 盘点报告已归档到 `harness/reports/adoption-<YYYY-MM-DD>.md`
- [ ] 接入前后五子系统评分各一份（自评 + 可选独立复评）

## 7. FAQ

**Q：kit 会不会变成负担？**
A：三档 profile、配置化门禁、可整目录删除；安装的只是文件与 Makefile 命令，不是依赖。已接入后想退出：删除 kit 生成的文件即可，业务代码零改动。

**Q：会不会拖慢 CI/本地？**
A：静态链路只依赖 Python 标准库 + make + git，秒级（来源案例 CI 约 4 秒）；不跑宿主测试、不装依赖。

**Q：模型/Agent 换代要重写规则吗？**
A：核心规则与门禁是仓库文件与命令，与模型无关；Agent 特有集成放在 `adapters/`（薄、可选）。换 Agent 主要是改适配层或系统提示，不是重写 harness。

**Q：能防住 Agent 说谎吗？**
A：不能提供密码学保证；它把"随口宣布完成"的成本显著抬高，并让低成本蒙混路径在门禁上可见。

**Q：怎么让 Agent 最快进入流程？**
A：装一次入口 skill：`<kit>/scripts/harness-skill install --scope user`（写 `~/.agents/skills/harness/` 与 `~/.claude/skills/harness/`），之后任意仓库的 Agent 会话直接说「接入这个项目」或当前任务即可，不需要每次取提示词。宿主不支持 skills 时才用兜底：在目标仓库根目录跑 `<kit>/scripts/harness-prompt list` 看场景，`copy <场景>` 复制到剪贴板（按场景拼 0A/0B 前置、填好路径、列出待补占位符；无剪贴板时打印到 stdout）。

**Q：多人怎么用？**
A：见 [governance 多人协作](governance.md#3-多人与多-agent-协作)：唯一 active 计划、`scope.allow`、PR + required checks、证据绑定 commit；分工提示词见 [prompts §16](agent-prompts.md#16-多人--多-agent-分工)。

**Q：存量接入要多久？**
A：Agent 接入通常 10 分钟到 1–2 天（文档蒸馏与清洁占大头）；来源案例的 Android/Gradle 存量仓由 AI 代理在约 1 天内完成接入 + 验收。

**Q：和"多写几个 skill / 多加几条规则"的区别？**
A：kit 的原则是**能机检的不写进指令**、规则必须对应真实失败、指令有 token 预算。规则越多不等于越安全——详见 [governance](governance.md)。

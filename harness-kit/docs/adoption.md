# 接入与日常使用 · skill 优先（新项目 / 存量项目 / 手动接入）

> **默认路径是入口 skill**：装一次（`<kit>/scripts/harness-skill install --scope user`），之后每个场景一句话——
> 接入、接手、计划、实现、验证、评审、发布、交接、升级都由 skill 按意图路由，不需要复制提示词。
> 只有**不支持 skills 的宿主**才用提示词兜底（§6）；**没有 Agent** 时才走命令行手动接入（§5）。
>
> 相关：[README](../README.md)（能力、五子系统、边界）、[playbook](playbook.md)（命令级操作步骤）、[governance](governance.md)（演化、反臃肿、多人协作）、[SPEC](../SPEC.md)（内部契约）、[提示词库（兜底）](agent-prompts.md)。

## 0. 先看症状，再选路径

| 你可能正在经历 | harness-kit 对应机制 |
| --- | --- |
| Agent 说"完成了/已验证"，但仓库里没有可复核的记录 | 证据三值（PASS / FAIL / UNVERIFIED）+ clean tree + commit 绑定；**没有 evidence id 一律按未验证处理** |
| 文档、计划、进度散落在聊天记录和 README 里，每次新会话都要重建上下文 | AGENTS 树 + 唯一 active 计划 + 交接摘要；冷启动只读仓库 |
| Agent 越改越宽：顺手重构、改配置、动无关文件 | `scope.allow/deny` 与 `git status` 交叉核对；越界 FAIL |
| 文档链接断、索引缺、过期结论被当现状、本机路径/构建产物入库 | `check_docs` / `check_agents` / `check_hygiene` 静态门禁 |
| 门禁写了但"永远绿"，没人知道它是否还有效 | `harness-selftest` 负向注入：往临时副本里制造违规，断言对应门禁必须变红 |
| 换模型/换 Agent/换人就重写一遍规则 | 规则与门禁是仓库里的文件与命令，不绑定任何 Agent；适配层可选、薄 |

**不适合**：只需要一次性脚本、没有测试与协作、也不打算长期维护的仓库——接入成本会大于收益。

### 0.1 三条路径（按顺序选一条）

| 路径 | 适用场景 | 入口 |
| --- | --- | --- |
| **① 入口 skill（推荐，默认）** | 有 AI coding Agent 的日常开发；接入/接手/计划/验证/发布/交接都走它 | §1 装一次 → §2 接入 → §3 按场景使用 |
| ② 命令行手动接入 | 环境里没有 Agent，或想先手动理解流程 | §5 |
| ③ 提示词兜底 | 宿主不支持 skills（只能粘贴文本） | §6 |

> 三条路径执行的是**同一套**仓库文件、门禁与证据；skill 只是入口路由，不是额外能力。装了 skill 就不需要 §6 的提示词模板。

## 1. 装一次入口 skill（默认）

`<kit>` = kit 克隆路径；在目标仓库根目录执行：

```bash
cd /path/to/your-project
<kit>/scripts/harness-skill install --scope user   # 写 ~/.agents/skills/harness/（DSH）与 ~/.claude/skills/harness/（Claude Code）
<kit>/scripts/harness-skill check --scope user     # 期望 in sync
```

- **用户级安装**（`--scope user`，默认 `agents,claude-code`）：机器上所有仓库的 Agent 会话可见，不写入仓库；升级 kit 后重装 `install --scope user --force`。
- **项目级安装**（`--scope project`）：装到仓库 `.dsh/skills/`、`.claude/skills/` 并随仓库提交，适合团队 pin 版本；项目级同名 skill 优先于用户级。
- **怎么调用**：宿主支持斜杠时（DSH / Qoder CN / Claude Code 输入框有「技能」补全）优先 `/harness`（显式、确定性强）；输入自然语言也能按 description 触发（如「用 harness-kit 接入这个项目」「接手这个项目」「发布前检查」）。
- **skill 怎么定位 kit**：用户级安装记录 `~/.agents/skills/.harness-kit-skill.json` 的 `kitRoot` → 仓库内/父目录 `harness-kit/` → 都没有时问用户一次。
- **版本不符**：skill 的 `min_version` 高于本机 kit 时，skill 会提示升级 kit 并重装，不会自行改仓库。
- 装完确认：Agent 的 skill 列表里出现 `harness`，或输入 `/har` 出现补全。

## 2. 接入项目（skill 主路径）

目标仓库还没有 `tools/harness.py` 时，skill 按 `../skills/harness/references/adopt.md` 路由：**定位 kit → 只读盘点 → 给方案确认 → dry-run → init → 首次门禁 → 第一份 active 计划**，不伪造 `make` / 门禁输出。

### 2.1 新项目

对 Agent 说：**「用 harness-kit 接入这个项目」**（或先 `/harness` 再说明）。

Agent 会：

1. 读 kit 的 README / 本指南，确认 profile（默认 `standard`）与真实测试命令；
2. `harness-init --dry-run` 给你看将写入的文件，确认后执行（自动跑首次 `make check`）；
3. 提交后建第一份 active 计划（目标 / scope / 验收 / 下一步）；
4. 从下一次任务起按 §3 的循环工作。

> 没有 Agent 时，等价命令见 §5.1。

### 2.2 存量项目（先只读，再改造）

**强制顺序**：`harness-adopt` 只读盘点 → 人确认改造计划 → `harness-init` → 按 playbook 七步法改造。对 Agent 说：**「用 harness-kit 改造这个存量项目」**。

```bash
# Agent 会先跑这条（你也可以手动复核；只读、0 写入）
<kit>/scripts/harness-adopt --target . --report /tmp/adoption-report.md --json
```

- 禁止在看懂现状之前重构代码；盘点报告作为"改造前基线"存档。
- 核心纪律：**门禁红就修内容，不删检查**；项目自有文档留在项目内，kit 只提供骨架与门禁。
- 七步法每一步的退出信号/回滚见 [playbook「存量项目（brownfield）改造」](playbook.md#存量项目brownfield改造七步法)。
- 接入前建议记录**基线评分**（见 §7），接入后复评，才能回答"到底改善了没有"。盘点报告在只读阶段放目标仓之外是刻意的；接入完成后用 `--archive-report` 归档到 `harness/reports/adoption-<YYYY-MM-DD>.md`。

### 2.3 接入验收清单

**Agent 接入（推荐）**

- [ ] 入口 skill 已装一次（`harness-skill install --scope user`；`check --scope user` in sync），或宿主不支持 skills 时有可用的兜底提示词流程
- [ ] Agent 冷启动只读仓库可回答"现在做到哪、下一步、哪些未验证"
- [ ] Agent 的完成声明带 evidence id 或显式"未验证"
- [ ] 计划 `scope.allow` 与实际改动一致
- [ ] 换一个 Agent/新会话不丢状态（唯一 active 计划 + 证据摘要）

**完整接入（1 天，真实仓库）**

- [ ] 文档蒸馏完成（当前/历史分层、索引 100%、链接可用）
- [ ] 一条真实测试证据 PASS，`make verify-claim` exit 0
- [ ] CI（或 pre-push）跑 `make verify-static`
- [ ] `make selftest` exit 0（门禁证明会红）
- [ ] `make scorecard` 生成评分卡草稿；过期由 `make check` WARN；自评 / 独立复评分列
- [ ] 盘点报告已归档到 `harness/reports/adoption-<YYYY-MM-DD>.md`
- [ ] 接入前后五子系统评分各一份（自评 + 可选独立复评）

## 3. 接入后：按场景用 skill（核心）

接入完成后，不需要记命令：**说场景，skill 按 §1 的路由表加载对应流程**，再按仓库里的计划/证据/门禁执行。

### 3.1 场景路由表

| 你要做的事 | 对 Agent 说（或 `/harness` 后说） | skill 执行的流程 | 手工等价命令（无 Agent 时） |
| --- | --- | --- | --- |
| 接手 / 继续 / 做到哪了 | 「接手这个项目」「现在做到哪了」 | `references/status.md` | `python3 tools/harness.py status`（或 `make status`） |
| 接入新项目 / 改造存量 | 「用 harness-kit 接入这个项目」 | `references/adopt.md` | §5 的 `harness-adopt` / `harness-init` |
| 提需求 / 建计划 | 「给这个需求建计划」 | `references/plan.md`（`start` / `intake`） | `python3 tools/harness.py start`（或 `make start TOPIC=…`） |
| 实现 / 修 bug / 重构 / 依赖升级 | 「按计划实现…」 | `references/build.md` | 计划 scope 内改代码 + 对应测试 |
| 完成前验证 / 写证据 / 三值判定 | 「验证这个改动并写证据」 | `references/verify.md`（`verify`） | `make verify-static` → 写证据 → `make verify-claim` |
| Code Review / PR 前自检 / 对抗评审 | 「做一次对抗评审」 | `references/review.md`（strict 含 red-team） | 按评审清单 + `make check` / `make verify-static` |
| 发布 / 安全检查 / 性能 | 「做发布前检查」 | `references/release.md`（`release --check`） | `python3 tools/harness.py release --check` |
| 交接 / 换 Agent / 多 Agent 分工 | 「交接给下一个 Agent」 | `references/collaborate.md`（`handoff`） | `python3 tools/harness.py handoff` |
| 升级 harness-kit | 「升级 harness-kit」 | `references/upgrade.md` | `harness-upgrade --check/--plan`（只读）+ 重装 skill |

> 斜杠 `/harness` 是显式入口；自然语言按 skill description 自动触发。两者冲突时，以 skill + 仓库文件为准。

### 3.2 一次典型任务的完整循环

```text
① 冷启动     skill: status  → 读唯一 active 计划（没有就先建）
② 开工       计划写清目标 / scope.allow / 验收 / 下一步；确认无越界
③ 实现       小步改；每步跑对应检查（make check / 测试）
④ 完成前验证 make verify-static → 写证据（命令/退出码/环境/计数）
             → make verify-claim（UNVERIFIED 不算完成）
⑤ 收尾       更新计划：证据 ID / 未验证项 / 未提交改动 / 下一步
             → handoff（下一棒只靠仓库就能恢复）
⑥ 提交/发布  提交前问人；push、发布、删除、--force 覆盖前每次单独确认
```

### 3.3 skill 会强制的硬约束（不可协商）

| 约束 | 含义 |
| --- | --- |
| **作用域** | 只改计划 `scope.allow` 覆盖的文件；越界先停下更新计划并说明 |
| **证据** | 没有证据不写"已完成/已验证"；未运行写"未验证 + 手动步骤"；test-count 的 PASS 需要可重算 artifact（JUnit XML），证据 JSON 与 artifact 都必须 git 入库 |
| **归档** | `_archive` 计划/证据是历史快照；没有 active 计划时先读 status/handoff 的归档回读，再决定新建计划 |
| **门禁** | `make check` / `harness.py verify` 红了先修根因；不删除、不弱化、不绕过门禁 |
| **问人** | push、发布、删除、改规则/门禁、`--force` 覆盖前先问 |
| **单一状态源** | 计划与证据是仓库文件；不把进度只留在对话里 |
| **可退出** | 不装 skill 也能工作；skill 只是入口，所有事实与流程都在仓库文件和 kit 文档里 |

### 3.4 Agent 反模式（会被仓库抓住）

1. **改门禁让它变绿**：用 `harness-selftest` 证明门禁仍会红，提交记录可审计。
2. **先改代码后补计划/证据**：`check_plan` 会把"未提交改动与计划声明不一致"报 FAIL。
3. **把构建产物/本机路径提交**：`check_hygiene` 直接失败。
4. **在对话里宣布完成**：没有证据 = 未验证，`verify-claim` 不会给 PASS。
5. **多个 Agent 同时改一个仓库**：唯一 active 计划会被打破（`check_plan` FAIL），先协调再写。

### 3.5 打包 / 发布时排除 harness 文件（可选）

harness 过程文件（计划、证据、门禁脚本）是开发期资产，通常不需要进发布产物。**不要为了打包调整接入布局**：用各生态现成的排除机制即可，kit 提供一个 opt-in 适配器生成推荐规则。

```bash
# 新项目：init 时加 --adapters gitattributes（需要保留默认适配器时写 githooks,ci,gitattributes）
python3 <kit>/scripts/harness-init --profile standard --target . --adapters gitattributes ...
# 已接入仓库：把 <kit>/adapters/gitattributes/export-ignore.append 的内容追加到 .gitattributes
```

生成块内容（按项目增删；`harness-kit` 标记用于升级识别与幂等）：

```gitattributes
# harness-kit · export-ignore（发布源码包时排除 harness 过程文件；git archive / GitHub Source zip 生效）
/harness/ export-ignore
/tools/ export-ignore
/HARNESS.md export-ignore
/.harness-manifest.json export-ignore
```

各生态做法：

| 发布形态 | 机制 | 建议 |
| --- | --- | --- |
| git 源码包 / GitHub Source zip | `.gitattributes` 的 `export-ignore` | 用上面的适配器；解包验证见下 |
| npm / pnpm 发布 | `package.json` 的 `files` 白名单 | 显式列 `dist/` 等；未列目录（含 harness/tools）默认不进包 |
| Docker / Podman 镜像 | `.dockerignore` | 逐行排除 `harness/`、`tools/`、`docs/` 等，或用默认拒绝 + allowlist |
| Python 包 | `packages`（setuptools）/ `MANIFEST.in` | 只打源码包，避免全量 `graft .` |
| Xcode / iOS | target 成员决定打包内容 | harness 目录不进 target 即不进 ipa，无需额外排除 |

发布前可解包验证：

```bash
git archive HEAD | tar t | grep -E '^(harness/|tools/|HARNESS\.md)' \
  && echo "仍有 harness 文件" || echo "已排除"
```

> 若希望源码包仍能跑 `make check`，从块里删掉 `/tools/ export-ignore`（门禁脚本需要）。该块只影响发布归档，不影响仓库内容与日常开发。

## 4. 按 Agent 能力分层（不绑定具体产品）

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

## 5. 没有 Agent：命令行手动接入

适合想先手动理解流程、或环境里没有 Agent 的场景。命令与 Agent 执行的是同一套。

### 5.1 新项目（10 分钟最小接入）

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

### 5.2 存量项目（brownfield，先只读再改造）

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

### 5.3 手动接入验收清单（10 分钟最小）

- [ ] `harness-init --dry-run` 计划已复核，无意外覆盖
- [ ] 首次 `make check` exit 0
- [ ] `git status` 干净后提交
- [ ] 选定了真实测试命令并写入 `harness/config.json.commands.test`

## 6. 不支持 skills：提示词兜底

只在宿主只能粘贴文本时使用；装了 skill 就不需要本节内容。

```bash
cd /path/to/your-project                             # 在目标仓库根目录执行（或加 --target）
<kit>/scripts/harness-prompt copy adopt-brownfield   # 接入存量项目：拼 0B 前置 + 填 kit/目标路径
<kit>/scripts/harness-prompt copy fix-bug            # 接入后的日常任务：拼 0A 前置
<kit>/scripts/harness-prompt list                    # 看全部场景；目标仓库阶段与场景不符时给 WARN
```

手工复制时见 [prompts §0 公共前置](agent-prompts.md#0-公共前置按项目阶段选一段)：先贴 0A（已接入）或 0B（未接入），再把 `<kit>` / `<目标仓库路径>` 换成本机路径；§1 / §2 是未接入场景，手工复制时同样先贴 0B。**不要给未接入项目贴 0A**（它假设 `make check` 与 `harness/plans/` 已存在）。

**场景索引**

接入与接手：

| 场景 | 模板 |
| --- | --- |
| 接入新项目 | [§1 接入新项目](agent-prompts.md#1-接入新项目agent-first) |
| 接入存量项目 | [§2 接入存量项目](agent-prompts.md#2-接入存量项目agent-first先只读) |
| 接手陌生项目 | [§3 冷启动](agent-prompts.md#3-接手陌生项目冷启动) |

需求、计划与开发：

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

评审与发布：

| 场景 | 模板 |
| --- | --- |
| 代码审查 / PR 前自检 | [§9 自检](agent-prompts.md#9-代码审查--pr-前自检) |
| 新开会话对抗性评审 | [§10 对抗性评审](agent-prompts.md#10-新开会话对抗性评审) |
| 发布前操作 | [§15 发布前](agent-prompts.md#15-发布前操作) |

协作与收尾：

| 场景 | 模板 |
| --- | --- |
| 多人 / 多 Agent 分工 | [§16 分工](agent-prompts.md#16-多人--多-agent-分工) |
| 结束会话 | [§17 结束会话](agent-prompts.md#17-结束会话保存状态) |
| 项目交接 | [§18 交接](agent-prompts.md#18-项目交接换人--换-agent) |
| 结束项目 / 阶段 | [§19 结束项目](agent-prompts.md#19-结束项目--阶段done--归档) |
| 完成声明（任意任务） | [§20 完成声明](agent-prompts.md#20-完成声明附加到任意任务末尾) |

## 7. 真实案例：接入前后五子系统评分

### 7.1 评分口径（先对齐，避免"自嗨分"）

- 五子系统各 1–5 分，口径见 standard profile 自带的 `docs/harness-scorecard.md`（模板：[评分卡模板](../core/templates/docs/harness-scorecard.md.template)）：
  **1 = 缺失；3 = 有规则但不可机检；5 = 有门禁 + 有证据 + 定期复核**。
- 每一分必须附证据（文件/命令/证据 ID）；没有证据的评分按未验证处理。
- 自评与独立复评**分列**；独立复评的输入只有仓库，不参考起草过程。
- 这个分数是工程判断，不是认证；它会随仓库变化，大改后需重评。

### 7.2 案例 A：存量 Android/Gradle 仓（brownfield，自评）

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

### 7.3 案例 B：来源案例 iOS 仓（独立复评）

同一个评分卡，由**非作者**独立复评（只读仓库、独立复跑门禁）：

| 时间/口径 | Instructions | State | Verification | Scope | Lifecycle | 综合 |
| --- | --- | --- | --- | --- | --- | --- |
| 改造前独立审计（2026-11-04） | — | — | — | — | — | **2.5/5**（文档型 harness：有规则、无结构化证据，验证层不可否证） |
| Phase 2.3 独立复评（2026-11-07） | 4.0 | 3.5 | 4.0 | 3.0 | 3.5 | **3.6/5（72%）** |
| Phase 2.5 独立复评（2026-11-07） | 4.0 | 4.0 | 4.3 | 3.5 | 4.0 | **≈4.0/5（79%）** |

补充口径：同一仓库的"对外标杆成熟度"由独立审计给出 **17/35 → 25.5/35（3.6/5）**；当前自评/独立复评均约 4.0。分数与局限见该仓的评分卡与复评记录（仓库内 `docs/harness-scorecard.md`）。

### 7.4 怎么复现这套评分

```text
接入前：harness-adopt --report（只读盘点）→ 人工按评分卡打分 → 存入改造计划作为基线
接入后：make scorecard 生成草稿（自动跑门禁、记录 exit/证据 ID/测试与文档计数）
        → 人工填「自评」→ 独立复评填「独立复评」列 → 过期由 make check WARN
        → 需要时 make selftest 证明门禁仍会红
```

**注意**：接入 ≠ 问题消失。kit 只覆盖结构性、可机检的部分；文档语义正确性、代码质量、真机/性能验证仍需要人或宿主传感器（detekt/lint/真机测试等）。分数提升反映的是"可验证性与可维护性"，不是产品质量自动提升。

## 8. FAQ

**Q：skill 和提示词模板是什么关系？**
A：skill 是默认入口（装一次，按场景路由到仓库里的流程与命令）；提示词模板只在宿主不支持 skills 时兜底（§6）。两者冲突时以 skill + 仓库文件为准。

**Q：kit 会不会变成负担？**
A：三档 profile、配置化门禁、可整目录删除；安装的只是文件与 Makefile 命令，不是依赖。已接入后想退出：删除 kit 生成的文件即可，业务代码零改动。

**Q：会不会拖慢 CI/本地？**
A：静态链路只依赖 Python 标准库 + make + git，秒级（来源案例 CI 约 4 秒）；不跑宿主测试、不装依赖。

**Q：模型/Agent 换代要重写规则吗？**
A：核心规则与门禁是仓库文件与命令，与模型无关；Agent 特有集成放在 `adapters/`（薄、可选）。换 Agent 主要是改适配层或系统提示，不是重写 harness。

**Q：能防住 Agent 说谎吗？**
A：不能提供密码学保证；它把"随口宣布完成"的成本显著抬高，并让低成本蒙混路径在门禁上可见。

**Q：多人怎么用？**
A：见 [governance 多人协作](governance.md#3-多人与多-agent-协作)：唯一 active 计划、`scope.allow`、PR + required checks、证据绑定 commit；分工提示词见 [prompts §16](agent-prompts.md#16-多人--多-agent-分工)。

**Q：存量接入要多久？**
A：Agent 接入通常 10 分钟到 1–2 天（文档蒸馏与清洁占大头）；来源案例的 Android/Gradle 存量仓由 AI 代理在约 1 天内完成接入 + 验收。

**Q：和"多写几个 skill / 多加几条规则"的区别？**
A：kit 的原则是**能机检的不写进指令**、规则必须对应真实失败、指令有 token 预算。规则越多不等于越安全——详见 [governance](governance.md)。

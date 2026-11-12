# harness-engineering-kit

> **给 AI Coding Agent 用的 Harness Engineering 项目管理工具**：按 **Instructions / State / Verification / Scope / Session Lifecycle** 五子系统，把规则、状态与证据落成仓库里的文件、门禁与命令，让多个 Agent / 模型在同一仓库上接力开发、让“完成”可复核。

**把“agent 说完成了”变成“证据说了算”。** test-count 证据必须由可重算的 JUnit XML 支撑（伪造/矛盾/未入库会被门禁拒绝）；计划 scope、归档计划与证据链都有可回读的闭环；不是框架，也不是依赖；生成物可整目录删除。

> 当前范围：**单工作流接力与分工**；跨 Agent 交接演练与多 Agent 并行门禁在路线图（v0.4.x）；行为级 A/B 后置（v0.5.x），不在当前承诺内。

- 仓库名 `harness-engineering-kit`（原名 `harness-kit`；目录、命令与 tag 前缀沿用短名）
- 版本：`0.5.1`（见 [`VERSION`](VERSION)）
- **[AI coding Agent 接入指南（新项目 / 存量项目）](docs/adoption.md)** ← 先看这个
- **入口 skill（默认，装一次全局可用）**：`<kit>/scripts/harness-skill install --scope user`，之后任意仓库对 Agent 说「接入这个项目」；不支持 skills 的宿主用 [提示词库（兜底）](docs/agent-prompts.md)
- 命令行手动接入：[采用 playbook](docs/playbook.md)（新项目五步 / 存量七步）
- 深入：[为什么是项目管理工具](docs/why.md) · [演化与治理](docs/governance.md) · [内部契约 SPEC](SPEC.md)

## 它是什么：Harness Engineering 项目管理工具（治理层）

Harness Engineering 的工作定义：**Agent = Model + Harness**。模型能力在变，但"指令、状态、验证、作用域、会话生命周期"这些模型之外的工程设施决定能力兑现率。harness-kit 把这五层做成仓库里的规则、状态与门禁，并提供 Agent 可自助执行的统一入口；脚手架是它的接入方式，不是身份。为什么需要它、与 Claude Code 自管的关系见 **[docs/why.md](docs/why.md)**。

| 子系统 | 它回答的问题 | kit 交付物（生成 / 改造 / 门禁） |
| --- | --- | --- |
| **Instructions** | 该做什么、去哪读 | 根 / 嵌套 `AGENTS.md` 模板 + `references/`；`check_docs` / `check_agents`（目录、链接、预算、`§` 引用、敏感串） |
| **State** | 做到哪、证据在哪、下一步 | 计划模板（front matter + 唯一 active）+ 证据 schema / `evidence.py` / `verify_claim` 三值 + `check_plan.py brief` 交接 |
| **Verification** | 怎么算完成、能否否证 | 静态门禁 + 证据 clean-tree/commit 绑定 + `check-host` 宿主传感器 + `harness-selftest` 负向注入 + JUnit XML 适配 + CI / pre-push 适配 |
| **Scope** | 一次只做什么、边界在哪 | 计划 `scope.allow/deny` 与 `git status` 交叉核对；L0/L1/L2 与红队评审约定（strict） |
| **Session Lifecycle** | 开工 / 交接 / 收尾 | 计划状态机（new → brief → done / archive）+ handoff / verify-change / red-team skills（strict）+ `doctor`（strict）+ 版本升级与月度审计流程 |

**脚手架能力矩阵**：

| 场景 | kit 做什么 | 边界（不承诺） |
| --- | --- | --- |
| 新项目初始化 | `harness-init` 三档 profile：生成五子系统骨架 + 首次 `make check` | 测试命令由项目提供；kit 不跑 / 不解析宿主测试 |
| 存量项目改造 | `harness-adopt` 只读盘点（文档/卫生/测试/建议）+ `--write-plan`；playbook 七步法 | 不自动重写业务代码或文档内容；语义蒸馏由人/Agent 完成，门禁负责验收 |
| 版本升级 | 临时渲染新版 → 逐文件 diff → 只回写 kit 管理面 → `selftest` 复核 | 无 in-place 命令；profile 升级仍未验证（版本升级已验证） |
| 五子系统是否真的落地 | 每层都有可执行门禁 + 证据；`harness-selftest` 证明门禁会红 | 结构可验证 ≠ 行为正确；不提供权限 / 工单 / 审批系统 |

## 30 秒：它在解决什么问题

| 你正在经历 | harness-kit 的机制 |
| --- | --- |
| Agent 说"完成/已验证"，仓库里没有可复核的记录 | 证据三值（PASS / FAIL / UNVERIFIED）+ clean tree + commit 绑定；**无 evidence id 即未验证** |
| 新会话失忆：不知道做到哪、哪些没验证 | AGENTS 路由 + 唯一 active 计划 + 交接摘要，只读仓库即可恢复上下文 |
| Agent 越改越宽：顺手重构、动无关文件 | 计划 `scope.allow/deny` 与 `git status` 交叉核对，越界 FAIL |
| 文档断链、索引缺失、过期结论被当现状 | `check_docs` / `check_agents` / `check_hygiene` 静态门禁 |
| 门禁"永远绿"，没人知道是否还有效 | `harness-selftest` 负向注入：M1–M9 逐项制造违规，断言门禁必须变红 |
| 证据移动/删除文件就变绿，归档计划失忆 | 证据递归扫描 + `_archive` 标 `SUPERSEDED`、in F/UNVERIFIED 需 `supersedes` 接管、必需 claim 完整性；无 active 计划时 `status`/`handoff` 回读上一归档计划 |
| 测试环境不同（本机/CI/服务器）导致假 FAIL | claim `environment` + `floorByEnvironment` + `expectedSkipped` 区间/按环境；环境不满足判 UNVERIFIED 而不是 PASS |
| 换模型/换 Agent/换人就要重写规则 | 规则与门禁是仓库文件与命令，不绑定任何 Agent；适配层薄、可选 |

## 适合谁 / 不适合谁

**适合**
- 想按 **Harness Engineering 五子系统**搭建或改造项目、并用 AI Coding Agent（DeepSeek Harness、Claude Code、Codex、Cursor、自研 Agent）长期维护的项目；
- 存量项目：已有文档/测试/构建，但文档和过程记录开始失控；
- 需要跨会话、跨人、跨 Agent 交接，又不想把状态留在聊天记录里的团队；
- 想给"完成声明"加一道可复核闸门，而不是靠自觉。

**不适合**
- 一次性脚本、没有测试也不打算长期维护的仓库；
- 只想要"自动写代码"而不想要任何过程约束的项目；
- 把 kit 当运行时依赖或业务框架——kit 生成的文件可整目录删除，不应进入业务代码。

## 接入路径：AI coding Agent 优先

| 路径 | 入口 | 说明 |
| --- | --- | --- |
| **AI coding Agent（推荐）** | 装一次入口 skill（`harness-skill install --scope user`）→ 对 Agent 说「接入这个项目」 | Agent 自行盘点/init/建计划/验证；skill 按阶段路由（adopt / status / plan / verify / release / handoff / upgrade） |
| 不支持 skills 的宿主 | `<kit>/scripts/harness-prompt copy <场景>` 一条命令拿兜底提示词 | 模板覆盖接入、需求、开发、评审、发布、分工、交接、收尾 |
| 命令行手动接入 · 新项目 | `harness-init --profile standard` → 首次 `make check` → commit | 10 分钟最小接入；命令见本节下方 |
| 命令行手动接入 · 存量项目 | `harness-adopt` 只读盘点 → `harness-init` → 七步法 | 先盘后改；文档蒸馏与清洁占大头 |

### AI coding Agent（推荐）

**第一步（一次）**：装入口 skill 到用户级，任意仓库的 Agent 会话可见（`<kit>` = kit 克隆路径）：

```bash
<kit>/scripts/harness-skill install --scope user   # 写 ~/.agents/skills/harness/（DSH）与 ~/.claude/skills/harness/（Claude Code）
<kit>/scripts/harness-skill check --scope user     # 期望 in sync
```

之后在目标仓库对 Agent 说一句「用 harness-kit 接入这个项目」即可；skill 会先定位 kit、只读盘点、dry-run 后等你确认，再 init。日常任务同理（「建计划」「完成前验证」「发布前检查」「交接」「升级 kit」）。

- 用户级安装写 `~/.agents/skills/harness/`（DSH rank 500）与 `~/.claude/skills/harness/`（Claude Code，v0.5.1 起；项目级同名 skill 优先），**不写入仓库、不提交**；`--scope project` 可装到仓库 `.dsh/skills/`、`.claude/skills/` 随仓库提交（团队 pin 版本）。
- **支持斜杠调用的宿主优先用 `/harness`**（DSH / Qoder CN / Claude Code 输入框里会出现「技能」补全）：显式加载、触发确定、不依赖模型判断描述是否匹配；自然语言「用 harness-kit 接入这个项目」是兜底（模型按描述自行判断是否加载）。
- 升级 kit 后重装：`install --scope user --force`；`check --scope user` 报漂移。
- 宿主不支持 skills 时再用兜底提示词（一条命令拿到可直接粘贴的完整提示词）：

```bash
cd /path/to/your-project                                   # 在目标仓库根目录执行（或加 --target）
<kit>/scripts/harness-prompt list                     # 看场景清单（会显示目标仓库是否已接入）
<kit>/scripts/harness-prompt copy adopt-brownfield    # 复制到剪贴板：自动拼 0B 前置、填 kit 与目标仓库路径
<kit>/scripts/harness-prompt copy fix-bug             # 接入后的日常任务同理（自动拼 0A 前置）
```

- 前置按**所选场景**拼：接入场景用 0B（未接入，含 kit 路径与「先只读」约束），日常场景用 0A（已接入）；目标仓库阶段与场景不符时命令会给 WARN，不会静默贴错。
- `copy` 复制成功会显示目标仓库；没有剪贴板工具时自动打印到 stdout 并给 WARN。
- 需要你补充的信息（如 `<SYMPTOM>`）会列出来；也可以 `--set SYMPTOM="..."` 直接填。
- 不用命令行时：[提示词库](docs/agent-prompts.md) 里手工复制，每个模板都标注了「阶段 / 前置 / 需替换 / 复制命令」。
- 接入顺序与验收路径不变：接入 → 计划 → 开发 → 自检 → 发布 → 交接。

### 命令行手动接入 · 新项目（10 分钟）

前置：Python 3（标准库）、`make`、`git`；`--target` 指向**已存在**的目录（init 不执行 `git init`；建议先 `git status` 确认干净）。把 `<kit>` 替换成 kit 克隆路径（在本仓内开发时 `<kit>` 即 `harness-kit/`）。

```bash
git clone --depth 1 --branch <kit-ver> \
  https://github.com/DavidTeam2008/harness-engineering-kit.git <kit>

# 0) 先看计划（按动作打印 RENDER / COPY / APPEND / CONFLICT；不写文件、不跑检查）
python3 <kit>/scripts/harness-init --profile standard --target ../myapp --name MyApp --dry-run

# 1) 标准档（+ 计划/证据/CI 与 pre-push；真实仓库推荐）
python3 <kit>/scripts/harness-init --profile standard --target ../myapp --name MyApp

# 2) 严格档（+ 适配器门禁/评分卡/红队/发布前 strict 证据校验）
python3 <kit>/scripts/harness-init --profile strict --target ../myapp --name MyApp

git add -A && git commit -m "chore: adopt harness-kit standard profile"
```

- 非 `--dry-run` 时，init 写完后会在目标目录执行首次 `make check` 并**透传退出码**；加 `--no-check` 可先跳过。
- 目标已有 `Makefile` 时**不覆盖**：写入 `Makefile.harness`，并提示在原 `Makefile` 末尾加 `include Makefile.harness`。
- 冲突默认 `fail` 并列出文件；`--force` 前先 `--dry-run` 复核是推荐姿势。
- **宿主门禁（standard+）**：`make check-host` 运行 `check_hygiene.py` + `check_layers.py`，只在 `harness/config.json` 配置了 `hygiene` / `layers` 段时生效，未配置 `[SKIP]`；`verify-static` 已包含。

### 命令行手动接入 · 存量项目（brownfield）

```bash
# ① 只读盘点（0 写入；报告写到目标仓之外）
python3 <kit>/scripts/harness-adopt --target ../legacy-app --report /tmp/adoption.md
python3 <kit>/scripts/harness-adopt --target ../legacy-app --json

# ② 定 profile / 基线 / 真实测试命令（存量优先 standard）
# ③ scaffold：先 --dry-run 再 init（已有文件默认 CONFLICT；--force 会备份后覆盖）
python3 <kit>/scripts/harness-init --profile standard --target ../legacy-app \
  --language android --test-command "./gradlew testDebugUnitTest"

# ④ 文档蒸馏 → ⑤ 清洁 → ⑥ config hygiene/layers + CI/hooks + JUnit 证据
# ⑦ 负向注入验收：
python3 <kit>/scripts/harness-selftest --target ../legacy-app
```

- 七步法每一步的退出信号/回滚见 [playbook「存量项目（brownfield）改造」](docs/playbook.md#存量项目brownfield改造七步法)。
- **验证门禁真的会红**：`harness-selftest --target .`（exit 0 = 全部按预期拦截并恢复）。
- 存量项目不要直接 `--force` init：先只读盘点，把"接入前基线"存档，再定改造顺序。

## 能力清单

| 能力 | 提供方 | 说明 |
| --- | --- | --- |
| 指令层 / 静态门禁 | `AGENTS.md` 模板 + `tools/check_docs.py` / `check_agents.py` | 目录页规则、链接/围栏/索引/预算、预算与敏感串、`§` 引用 |
| 计划状态 | `tools/check_plan.py` + `harness/plans/` | front matter、唯一 active、证据表、done/submitted 绑定；**submitted 增量按提交时点 scope 审计**；归档计划不再免检；done 未验证项需 waiver |
| 证据三值 + 独立重算 | `tools/evidence.py` + `verify_claim.py` | PASS / FAIL / UNVERIFIED；无 evidence id 即未验证；test-count 的 PASS 要求 JUnit XML artifact 重算 counts 一致 + commit 祖先 + clean tree；**证据 JSON 与 artifact 都必须 git 跟踪**；递归扫描 + `_archive` 证据 SUPERSEDED；必需 claim 缺失/归档未接管 → UNVERIFIED |
| **JUnit XML 适配器** | `tools/evidence_from_junit.py`（standard+） | 聚合 JUnit XML（pytest/unittest、Gradle、JUnit 等）为 evidence JSON；**默认脱敏并复制到 `<evidence>/artifacts/`**（hostname/system-out/本机路径去除，5 MiB 上限、symlink 拒绝、原子写）；`--keep-raw` 为显式逃生口 |
| **宿主卫生 / 分层门禁** | `tools/check_hygiene.py` / `check_layers.py`（standard+，可选配置） | 构建产物、根文件白名单、绝对符号链接、跟踪文件本机路径、超大文件；import 方向与 symbol guard；缺配置自动 SKIP |
| **门禁自测** | `scripts/harness-selftest`（kit 侧）/ `make selftest`（standard+） | 目标仓临时副本里做基线检查、逐项注入（M1–M9；M6 无 active 时用归档计划造 fixture）、断言门禁非 0、恢复后复核全绿；默认不写目标仓；SKIP ≠ PASS |
| **存量项目盘点** | `scripts/harness-adopt`（kit 侧） | 只读盘点 + `--report` / `--json` / `--write-plan`；profile 推荐统一为 standard（strict 需显式理由）；Python 测试命令逐候选探测 `.venv/uv/poetry`；`--archive-report` 脱敏归档 |
| **提示词兜底（不支持 skills 的宿主）** | `scripts/harness-prompt`（kit 侧） | `list` / `show` / `copy` / `render --check`：按所选场景拼前置（目标阶段不符给 WARN）、填 kit 与目标路径、剪贴板；文档由 `prompts/` 单源生成并受测试保护；输出会提示优先用 skill |
| **统一入口 / 一屏状态** | `tools/harness.py`（init 复制到宿主） | `status`（Agent 冷启动第一命令，`--json`）/ `start`（幂等建计划，建完即绿）/ `verify`（自动同步未提交段 + `verify-static` + 计划严格校验 + 证据摘要；`--claims-strict` 可阻断）/ `handoff`（交接摘要）/ `plan check` / `upgrade`（指引 kit 侧只读升级） |
| **入口 skill（默认）** | `skills/harness/` + `scripts/harness-skill`（kit 侧） | `install` / `check` / `list` / `uninstall`：单入口 SKILL.md + 9 个按阶段 references；`--scope user` 一次装到 `~/.agents/skills/harness/`（DSH）与 `~/.claude/skills/harness/`（Claude Code；v0.5.1 起默认两个 agent），`--scope project` 装到 `.dsh/skills/`、`.agents/skills/`、`.claude/skills/`；用户级元数据 `~/.agents/skills/.harness-kit-skill.json`（不入库） |
| **需求卡 intake** | `tools/harness.py intake` | 机检 `## 目标` + `## 验收判据`（命令+期望，或可复核链接+复核者），模糊判据拒绝并给原因 |
| **发布分级检查** | `tools/harness.py release [--check] [--strict]` | 静态门禁 + `verify_claim --fresh`；standard 也有发布门（strict 的 `release-check` 保留） |
| **评分卡（standard+）** | `tools/scorecard.py` + `make scorecard` | 生成 `harness/reviews/<date>-scorecard.md` 草稿（门禁快照/证据 ID/计数，不自动打分）；`--check-stale` 对过期/缺失 WARN，`--strict` 阻断；自评≠认证，独立复评列 TBD 不算完成 |
| **工程化升级（只读）** | `scripts/harness-upgrade`（kit 侧）+ `.harness-manifest.json` | `--check`：manifest / 目标文件 / kit 版本三方校验（in sync 0 / 本地漂移 1 / 版本不符 3）；`--plan`：同 profile/options 重渲染的新版三方 diff（SAME/LOCAL_ONLY/UPGRADE/ALREADY/CONFLICT/ADD/OBSOLETE/NOT_MANAGED/APPEND），**不写目标仓**；`--apply` 仍未实现（v0.4；按 plan 人工应用） |
| 语言探测 | `scripts/harness-init` | `python` / `swift` / `node` / `go` / `android` / `other` |
| 适配器 | `adapters/` | `githooks` / `ci` / `claude-code` / `dsh`（预留） |

## 真实案例：接入前后五子系统评分

评分口径：五子系统各 1–5 分（1 = 缺失；3 = 有规则但不可机检；5 = 有门禁 + 有证据 + 定期复核），每分必须附证据；自评与独立复评分列。完整口径与两张评分表见 [adoption.md 案例章节](docs/adoption.md#5-真实案例接入前后五子系统评分)。

| 案例 | 接入前 | 接入后 | 说明 |
| --- | --- | --- | --- |
| 存量 Android/Gradle 仓（brownfield，**自评**） | **6/25（24%）** | **20/25（80%）** | 接入前：无 AGENTS/HARNESS/计划/证据/CI，文档断链与过期、本机路径入库；接入后：门禁/证据/唯一 active 计划/宿主传感器/CI 分支保护全落地 |
| 来源案例 iOS 仓（**独立复评**） | **2.5/5**（改造前独立审计，2026-11-04） | **≈4.0/5（79%）** | Phase 2.3 独立复评 3.6/5 → Phase 2.5 独立复评 ≈4.0/5；对外标杆 17/35 → 25.5/35 |

> 这是"可验证性与可维护性"的提升，不是产品质量自动提升：文档语义、代码质量、真机/性能仍归宿主与人。分数是工程判断，不是认证；接入前后要用同一评分卡、同一证据口径，详见 [adoption.md](docs/adoption.md)。

## 为什么不会变成累赘

kit 的目标不是"规则越多越安全"，而是**能机检的就不写进指令；写进指令的必须有预算**：

- **计算型优先**：能用脚本/schema 判定的，不靠模型自觉；
- **规则付租金**：每条规则对应一个真实失败案例（失败 → 规则 → 门禁 → 负向注入），没有失败案例不进入模板；
- **预算即设计**：根 `AGENTS.md` ≈1650 token 预算，三份 references 各 ≈950–1000 token；新增规则顶预算必须删/合并旧规则；
- **渐进披露**：根指令只指路，目录级规则在嵌套 `AGENTS.md`，细节在 `references/`，流程在 skills/adapters；不一次塞满上下文；
- **删除优先 + 薄适配**：模型/Agent 已能稳定做对的事降级或删除；Agent 私有能力只进 `adapters/`，不污染核心规则；
- **门禁会腐烂，所以能自测**：`harness-selftest` 负向注入（含 M9 伪造证据）+ 275 个 kit 测试；门禁空转（例：模式被改坏）会当场变红。

完整机制（版本演化、行为级评估计划、删除/降级流程、踩刹车信号）见 **[governance.md](docs/governance.md)**。

## 多人 / 多 Agent 协作

kit 提供机制层，团队自管治理层：

- **机制层**：唯一 active 计划（front matter 写 owner/scope/验收）、`scope.allow/deny` 与 `git status` 交叉核对、证据绑定 commit、`brief` 交接摘要、CI/pre-push 适配；
- **治理层（宿主自管）**：分支保护 + required status checks（来源案例：`static gates` 必过、管理员也受限）、PR 流程、CODEOWNERS、评审规则、权限；
- **并行策略**：先约定写作用域，再并行；合并前统一跑 `verify-static` + `harness-selftest`；多服务拆仓而不是塞一套流程；
- **诚实的限制**：唯一 active 计划隐含"串行集成"假设；kit 不能让不诚实的人变诚实（证据可伪造，只是成本变高）；多人采用的真实试点仍未验证。

推荐流程、并行分支/多 Agent 细节、适用边界见 [governance.md §3](docs/governance.md#3-多人与多-agent-协作)。

## profiles 对比

| profile | 新增内容（相对上一档） | 主要 Makefile target | 适用场景 |
| --- | --- | --- | --- |
| `minimal` | `AGENTS.md`、`docs/README.md`、`docs/AGENTS.md`、`references/{contracts,verification,workflow}.md`、`harness/{README,AGENTS,config}`、`tools/{token_estimate,check_docs,check_agents}.py` | `check`（docs+agents）、`verify-static`（=check） | 先立规则与文档门禁；不需要测试框架 |
| `standard` | `HARNESS.md`、`CONTRIBUTING.md`、`harness/plans/_template.md`、`harness/evidence/{README,schema,TEMPLATE}`、`harness/test-baseline.json`、`tools/{check_plan,evidence,verify_claim,evidence_from_junit,check_hygiene,check_layers}.py`、可选 `githooks`/`ci` | `check`（+plan）、`verify-static`（含 `check-host` + 证据校验）、`check-host`、`verify-claim`、`plan TOPIC=` | 真实仓库：需要跨会话状态与「完成可证伪」 |
| `strict` | `docs/harness-scorecard.md`、`harness/reviews/`、`.dsh/skills/{verify-change,handoff,red-team}`、`tools/{doctor,adapters}.py`、可选 `claude-code`/`dsh` 适配 | 以上 + `release-check`（fresh/strict 证据）、`doctor`、`adapters-sync`/`adapters-check` | 长期维护项目：发布前强门禁、红队、适配器一致性 |

> `dsh` 适配器当前为预留（manifest 为空列表），`claude-code` 提供 `CLAUDE.md` 与 hooks 示例。

## 语言与测试框架（实测矩阵）

| 语言/生态 | 语言探测依据 | init 建议的测试命令 | kit 实测 |
| --- | --- | --- | --- |
| Python | `pyproject.toml` / `setup.py` / `requirements.txt` / `*.py` | `python3 -m unittest discover -s tests -q` | ✅ 空白项目 + 外部代理试点 |
| Node | `package.json` | 有 `scripts.test` → `npm test`；无 → `node --test` | ✅ Node 24 / `node --test` + `npm test` |
| Swift | `Package.swift` / `*.xcodeproj` | SwiftPM → `swift test`；Xcode 工程必须显式 `--test-command` | ✅ SwiftPM；**Xcode iOS 工程未实测** |
| Go | `go.mod` | `go test ./...` | ❌ 本机未安装 Go，未实测 |
| Android / Gradle | `settings.gradle(.kts)` / `build.gradle(.kts)` | `./gradlew testDebugUnitTest` | ✅ 真实 Android/Gradle 仓完整试点（init → 文档蒸馏 → 宿主传感器 → JUnit 证据链 → 负向注入 → 计划归档）；JDK 17–21 / wrapper 由项目自管，kit 不代跑、不解析测试输出 |
| 其他 | 手动 `--language other` | `make test` | — |

## 目录结构

```text
harness-kit/
├── README.md            # 本文件（对外接入说明）
├── SPEC.md              # 内部构建契约（脚本/模板/测试必须遵守）
├── VERSION              # kit 版本单一来源
├── profiles/            # minimal / standard / strict manifest（extends 链）
├── core/                # config schema + 通用门禁脚本 + 模板（含评分卡模板）
├── adapters/            # githooks / ci / claude-code / dsh 薄适配
├── scripts/harness-init     # 统一入口（探测、渲染、冲突处理、首次 check）
├── scripts/harness-adopt    # 存量项目只读盘点 + 改造计划草稿
├── scripts/harness-selftest # 门禁自测：注入 → 断言门禁会红 → 恢复复核
├── scripts/harness-prompt   # 提示词库 CLI：list / show / copy / render（自动拼前置、填路径）
├── scripts/harness-upgrade  # 升级检查 / 三方 diff（只读；v0.2.13）
├── scripts/harness-skill    # 入口 skill 安装/校验/卸载（用户级 / 项目级；v0.5.0）
├── skills/harness/          # 单入口 SKILL.md + 按阶段 references（v0.3.0）
├── prompts/             # 提示词单源（2 前置 + 19 场景 + 2 附加片段；文档由此生成）
├── docs/adoption.md     # 接入指南（AI coding Agent 优先 + 命令行手动接入 + 前后评分）
├── docs/agent-prompts.md # 由 prompts/ 生成的提示词库（勿手改；见 harness-prompt render）
├── docs/playbook.md     # 新项目五步法 + 存量项目七步法 + 常见坑 + 升级路径
├── docs/governance.md   # 演化与治理（反臃肿、版本策略、多人协作）
├── docs/why.md          # 定位：为什么是项目管理工具（与 Claude Code 自管的关系、卖点成熟度）
├── CHANGELOG.md         # 版本变更记录
└── tests/               # kit 自身 unittest（标准库，275 个测试）
```

宿主目标（init 之后，按 profile 增减；以 SPEC §2 为准）：

```text
<target>/
├── AGENTS.md                     # 根指令（引用 references/、按目录读嵌套 AGENTS）
├── HARNESS.md / CONTRIBUTING.md   # standard+：系统地图 / 环境与验证
├── Makefile（或 Makefile.harness）# 门禁入口，按 profile 生成
├── .harness-manifest.json        # v0.2.13+：kit 管理面清单（升级/漂移基线）
├── docs/README.md, docs/AGENTS.md
├── references/{contracts,verification,workflow}.md
├── harness/
│   ├── config.json               # 唯一配置源（路径/命令/预算/claims/freshness/传感器）
│   ├── README.md, AGENTS.md
│   ├── plans/                    # standard+：front matter + 唯一 active
│   ├── evidence/                 # standard+：schema/TEMPLATE/摘要 JSON
│   └── reviews/                  # strict：独立审查记录
├── tools/*.py                    # 按 profile 复制（standard+ 含 check_hygiene / check_layers）
├── tools/harness.py              # v0.3.0+：统一入口（status/start/intake/verify/release/handoff）
├── tools/scorecard.py            # v0.4.0+：评分卡草稿 / 过期检查（standard+）
├── tools/harness_selftest        # v0.4.0+：门禁负向注入自检（standard+）
├── harness/requirements/         # standard+：需求卡模板（intake 读取）
├── .dsh/skills/harness/         # 可选：入口 skill 项目级安装；用户级装在 ~/.agents/skills/harness
├── .githooks/pre-push            # standard+（可选）
├── .github/workflows/verify.yml  # standard+（可选）
└── .dsh/skills/ / .claude/       # strict + 对应适配器（可选）
```

## 采用后的日常工作流

> Agent 场景用 `<kit>/scripts/harness-prompt copy <场景>` 一条命令取提示词（见 [提示词库](docs/agent-prompts.md)）；下面是人/Agent 共用的命令循环。

1. **冷启动/接手**：`make status`（或 `python3 tools/harness.py status`）——一屏状态 + 建议下一步。
2. **做任务前**：`make start TOPIC=<topic> GOAL="<目标>" SCOPE="src/ ..."`（或 `harness.py start`）——幂等建 active 计划，建完 `make check` 即绿。
3. **每次改动后**：`make check`（日常静态门禁；计划「未提交改动」差异只告警）。
4. **完成声明前**：`python3 tools/harness.py verify`——自动同步未提交段 + `make verify-static` + 计划严格校验 + 证据三值摘要（`--claims-strict` 可阻断）。
5. **发布前（strict）**：`make release-check`——证据必须 fresh 且 strict。
6. **交接/中断**：`python3 tools/harness.py handoff`（或 `make handoff`），输出计划/证据/未验证/下一步摘要。

> 核心约定：**没有 evidence id 的"已验证"按未验证处理**；UNVERIFIED（exit 2）不是通过。

## 自定义

kit 的定制入口只有**目标项目的 `harness/config.json`**（所有门禁脚本只读这一份，不接受硬编码路径）：

| 字段 | 用途 |
| --- | --- |
| `project.name` / `project.language` | 渲染占位符与展示 |
| `paths.*` | docs/references/harness/plans/evidence/reviews/tools 相对路径 |
| `instructions.budgets` / `nestedMaxBytes` / `sensitivePatterns` | 指令层 token 预算、嵌套 AGENTS 上限、敏感串扫描 |
| `docs.publicWhitelist` / `publicBudget` / `rootMarkdownAllowed` | 公开文档白名单与数量上限（防"删了又长回来"） |
| `commands.test` / `check` / `verify` | 宿主的真实命令（测试命令必须存在，不能写假命令） |
| `claims` / `freshness` | 可证伪声明与证据时效范围（`verify-claim --fresh` 用） |
| `layers` / `hygiene` | 宿主分层守卫与卫生检查（可选；缺段自动 SKIP） |
| `adapters` | 可选适配器配置（如 skills 同步目录） |

可用模板占位符：`{{PROJECT_NAME}}` `{{PROJECT_LANGUAGE}}` `{{TEST_COMMAND}}` `{{CHECK_COMMAND}}` `{{VERIFY_COMMAND}}` `{{KIT_VERSION}}` `{{YEAR}}` `{{DOCS_DIR}}` `{{REFERENCES_DIR}}` `{{HARNESS_DIR}}` `{{ROOT_AGENTS}}` `{{DEFAULT_BRANCH}}`。

> 缺失必填字段时脚本必须给可读错误并 exit 1（不静默用默认值）；路径一律相对目标根，不接受绝对路径。

## 维护与镜像（维护者）

本仓内 `harness-kit/` 是**唯一源**；独立模板仓 <https://github.com/DavidTeam2008/harness-engineering-kit> 由 `git subtree split` 生成的**只读镜像**。

- **改**：只改来源仓库的 `harness-kit/`，跑 `make kit-check` / `make verify-static`。
- **发布**：`make kit-publish`（subtree split → 推送镜像 `main`；非快进会被拒绝，说明镜像被直接改过）。
- **校验**：`make kit-drift` 比较本地 split 提交与镜像 `main`，不一致 exit 1。
- **禁止**直接在镜像仓提交后推送；Issue/PR 先回上游修，再发布并关闭。
- **版本**：`VERSION`（单一来源）+ `CHANGELOG.md`；发布同步在镜像仓打 tag。
- **改提示词**：只改 `prompts/*.md`，然后 `python3 scripts/harness-prompt render`（本仓可用 `make kit-prompts`）重新生成 `docs/agent-prompts.md`；`render --check` 与 `make kit-check` 会拦住"改了模板没重新生成"。

## 来源案例

harness-kit 从 Duiyi 仓库的 harness 改造中提炼（案例与证据：<https://github.com/DavidTeam2008/realtime-translator-ios>）。该仓库是第一个案例；第二个真实案例是 Android/Gradle 存量仓 <https://github.com/DavidTeam2008/realtime-translator-android>（brownfield 接入 + v0.2.2→v0.2.3 版本升级验证 + 接入前后评分）。第三个真实案例是 Python/MySQL 存量仓（standard 档接入 + v0.4.0 反馈收口）。kit 本身不包含其业务代码或专有规则。

## 局限与未验证（别当成能力）

- **结构可验证 ≠ 行为正确**：静态门禁与证据判定证明"仓库内部自洽 + 声明的 artifact 能按当前文件重算"，不证明测试真实执行、执行环境真实、独立评审发生、waiver 合法、scope allow 未被历史放宽，也不证明产品行为/性能/真机结果正确。
- **v0.4 明确「能证明 / 不能证明」**：能证明——证据文件与 artifact 已入库、commit 祖先/clean tree、JUnit counts 可重算、必需 claim 有当前证据、归档失败证据被合法接管、submitted scope 与归档状态可见；不能证明——测试由谁/在哪跑、environment 自报是否真实、waiver 是否经独立审批、ledger 级"证据从未消失"（v0.4 未做 tracked ledger）、绝对防伪造。
- **升级会变红/变绿**：v0.4 的 scope/证据/归档/strict 规则会让旧仓出现新的红或 WARN；升级前按 [playbook「v0.3.0 → v0.4.0 升级自检」](docs/playbook.md) 逐项核对，不要直接 `--force` 覆盖。
- **行为级 A/B 后置**：v0.5.0 把默认入口切到入口 skill（依据是真实接入反馈：提示词「生成→粘贴」繁琐，而 skill 可一次安装、跨仓生效）；但 skill vs 提示词的**行为级 A/B 尚未执行**（v0.5.x），在此之前不声称 skill 能提升 Agent 表现。
- **入口 skill 的验证面**：`install` / `check` / `uninstall`、用户级/项目级 scope、漂移检测有单测；用户级安装是机器级副作用（写 `~/.agents/skills/` 与 `~/.claude/skills/`，可 `uninstall` 清理）；skill 是否被具体模型选中、跨 Agent 交接、多 Agent 并发仍未实测；skill 与仓库 kit 版本漂移由 `check` 报，不会自动修复。
- **多人协作未验证**：唯一 active 计划、scope、证据绑定、CI required checks 能提供机制层支持；人类多人并行采用、人类陌生人首访仍未验证。
- **版本升级已验证，profile 升级未验证**：v0.2.2→v0.2.3 已在真实 Android/Gradle 仓验证；minimal→standard→strict 的 profile 升级路径仍未在真实项目验证。
- **语言/测试框架需要你提供**：`{{TEST_COMMAND}}` 与 `commands.test` 必须填真实命令；kit 不代跑、不解析测试输出（只提供 JUnit XML → evidence 转换）。
- **宿主已有文档/规则时首次 `make check` 可能不绿**：按预算与白名单修内容，不要删检查绕过。
- **外部试点有限**：空白 Python/Node/SwiftPM 项目、真实 Android/Gradle 存量仓已完成；其他语言生态、超大仓性能未验证。
- **kit 自身测试**：275 个测试（三档 init、`make check`/`verify-static`/`check-host`、证据三值/伪造证据负向/artifact 重算、strict `release-check`、存量盘点、JUnit 聚合、宿主传感器、门禁 selftest M1–M9、manifest/upgrade `--check`/`--plan`、统一入口 `harness.py`（status/start/intake/verify/release/handoff）、skill 安装/漂移、doctor `--agent`、Android 推断、dry-run/冲突/备份、无专有引用、版本引用一致、提示词单源与生成文档同步/CLI 前置选择）；随来源仓库 `verify` workflow 运行。
- **升级是"检查 + 人工应用"**：v0.2.13 的 `harness-upgrade` 只读（`--apply` 未实现）；无 manifest 的旧仓（v0.2.13 之前接入）走 playbook 手工升级路径。
- **test-count 证据要求 artifact**：只有 JUnit XML 能被独立重算；xcresult 目前判 UNVERIFIED（先用 `evidence_from_junit.py` 转换）；显式 `requireArtifact=false` 的 legacy claim 仍接受自报值，但原因会标注"未重算"（不推荐）。
- **适配器成熟度不一**：`githooks`/`ci` 有模板；`claude-code` 为薄适配；`dsh` 当前为预留。
- **未做外部安全审计**：kit 只承诺不联网、不写目标之外文件（SPEC §8.7），但未在第三方 CI/受限沙箱验证。
- **提示词 CLI 平台面**：macOS/Linux 已验证（`pbcopy` / 无剪贴板回退）；Windows 的 `clip` 分支未实测；报告路径示例使用 POSIX 临时目录。

## License

与 [LICENSE](LICENSE) 一致：**MIT**。kit 版本 `0.5.1`；向后兼容策略见 [SPEC §10](SPEC.md)。

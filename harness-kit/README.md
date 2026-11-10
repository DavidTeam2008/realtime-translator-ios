# harness-kit

> **Harness Engineering 项目脚手架**：把「AI coding agent 可验收的研发约束」按 **Instructions / State / Verification / Scope / Session Lifecycle** 五子系统固化为**项目无关**的模板、门禁与证据链。
> 面向用 AI Coding Agent / Vibe Coding 交付、但代码、文档、验证开始失控的项目：**把"agent 说完成了"变成"证据说了算"，让仓库重新可维护、可交接、可迭代。**
> 不是框架、不是依赖：只生成 Markdown、Python 标准库脚本和一个 Makefile 入口；接入失败可整目录删除，不留运行时包袱。

- 版本：`0.2.5`（见 [`VERSION`](VERSION)）
- **[接入指南：新项目 / 存量项目 / AI coding Agent](docs/adoption.md)** ← 先看这个
- 采用方法：[`docs/playbook.md`](docs/playbook.md)（新项目五步法 + 存量项目七步法 + 常见坑）
- 演化与治理：[`docs/governance.md`](docs/governance.md)（反臃肿、版本演化、多人协作）
- 内部构建契约：[`SPEC.md`](SPEC.md)

## 它是什么：Harness Engineering 脚手架

Harness Engineering 的工作定义：**Agent = Model + Harness**。模型能力在变，但"指令、状态、验证、作用域、会话生命周期"这些模型之外的工程设施决定能力兑现率。harness-kit 把这五层做成**可生成、可改造、可验证**的脚手架：

| 子系统 | 它回答的问题 | kit 交付物（生成 / 改造 / 门禁） |
| --- | --- | --- |
| **Instructions** | 该做什么、去哪读 | 根 / 嵌套 `AGENTS.md` 模板 + `references/`；`check_docs` / `check_agents`（目录、链接、预算、`§` 引用、敏感串） |
| **State** | 做到哪、证据在哪、下一步 | 计划模板（front matter + 唯一 active）+ 证据 schema / `evidence.py` / `verify_claim` 三值 + `check_plan.py brief` 交接 |
| **Verification** | 怎么算完成、能否否证 | 静态门禁 + 证据 clean-tree/commit 绑定 + `check-host` 宿主传感器 + `harness-selftest` 负向注入 + JUnit XML 适配 + CI / pre-push 适配 |
| **Scope** | 一次只做什么、边界在哪 | 计划 `scope.allow/deny` 与 `git status` 交叉核对；L0/L1/L2 与红队评审约定（strict） |
| **Session Lifecycle** | 开工 / 交接 / 收尾 | 计划状态机（new → brief → done / archive）+ handoff / verify-change / red-team skills（strict）+ `doctor`（strict）+ 版本升级与月度审计流程 |

**脚手架能力矩阵**（接入场景 × 支持程度）：

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
| 门禁"永远绿"，没人知道是否还有效 | `harness-selftest` 负向注入：M1–M8 逐项制造违规，断言门禁必须变红 |
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

## 能力清单

| 能力 | 提供方 | 说明 |
| --- | --- | --- |
| 指令层 / 静态门禁 | `AGENTS.md` 模板 + `tools/check_docs.py` / `check_agents.py` | 目录页规则、链接/围栏/索引/预算、预算与敏感串、`§` 引用 |
| 计划状态 | `tools/check_plan.py` + `harness/plans/` | front matter、唯一 active、证据表、done/submitted 绑定 |
| 证据三值 | `tools/evidence.py` + `verify_claim.py` | PASS / FAIL / UNVERIFIED；无 evidence id 即未验证 |
| **JUnit XML 适配器** | `tools/evidence_from_junit.py`（standard+） | 聚合 JUnit XML（pytest/unittest、Gradle、JUnit 等）为 evidence JSON；缺文件/解析失败 exit 2 |
| **宿主卫生 / 分层门禁** | `tools/check_hygiene.py` / `check_layers.py`（standard+，可选配置） | 构建产物、根文件白名单、绝对符号链接、跟踪文件本机路径、超大文件；import 方向与 symbol guard；缺配置自动 SKIP |
| **门禁自测** | `scripts/harness-selftest`（kit 侧） | 目标仓临时副本里做基线检查、逐项注入、断言门禁非 0、恢复后复核全绿；默认不写目标仓 |
| **存量项目盘点** | `scripts/harness-adopt`（kit 侧） | 只读盘点 + `--report` / `--json` / `--write-plan`（改造计划草稿） |
| **版本升级路径** | playbook「升级路径」 | 无 in-place 命令：临时渲染 + 逐文件 diff + `harness-selftest` 复核；已在 Android/Gradle 存量仓验证 v0.2.2→v0.2.3（2026-11-10）；profile 升级仍未验证 |
| 语言探测 | `scripts/harness-init` | `python` / `swift` / `node` / `go` / `android` / `other` |
| 适配器 | `adapters/` | `githooks` / `ci` / `claude-code` / `dsh`（预留） |

## 10 分钟接入

前置：Python 3（标准库）、`make`、`git`；`--target` 指向**已存在**的目录（init 不执行 `git init`；建议先 `git status` 确认干净）。

```bash
# 0) 先看计划（只打印 CREATE / COPY / SKIP / CONFLICT / RENDER；不写文件、不跑检查）
python3 harness-kit/scripts/harness-init --profile standard --target ../myapp --name MyApp --dry-run

# 1) 标准档（+ 计划/证据/CI 与 pre-push；真实仓库推荐）
python3 harness-kit/scripts/harness-init --profile standard --target ../myapp --name MyApp

# 2) 严格档（+ 适配器门禁/评分卡/红队/发布前 strict 证据校验）
python3 harness-kit/scripts/harness-init --profile strict --target ../myapp --name MyApp
```

- 非 `--dry-run` 时，init 写完后会在目标目录执行首次 `make check` 并**透传退出码**；加 `--no-check` 可先跳过。
- 目标已有 `Makefile` 时**不覆盖**：写入 `Makefile.harness`，并提示在原 `Makefile` 末尾加 `include Makefile.harness`。
- 冲突默认 `fail` 并列出文件；`--force` 前先 `--dry-run` 复核是推荐姿势。
- **宿主门禁（standard+）**：`make check-host` 运行 `check_hygiene.py` + `check_layers.py`，只在 `harness/config.json` 配置了 `hygiene` / `layers` 段时生效，未配置 `[SKIP]`；`verify-static` 已包含。
- **验证门禁真的会红**：接入后跑 `python3 harness-kit/scripts/harness-selftest --target .`（exit 0 = 全部按预期拦截并恢复）。

## 两种接入路径（人类团队 / AI Agent）

| 路径 | 入口 | 说明 |
| --- | --- | --- |
| 新项目（人类/AI 均可） | `harness-init --profile standard` → 首次 `make check` → commit | 10 分钟最小接入；按 playbook 第 4–5 步接测试/证据/CI |
| 存量项目（brownfield） | `harness-adopt` 只读盘点 → 定 profile/基线 → `harness-init` → 七步法 | 先盘后改；文档蒸馏与清洁占大头，见 playbook 七步法 |
| **AI coding Agent** | 让 Agent 读 `AGENTS.md`，用 Makefile 做统一闸门；完成声明必须带 evidence id | 分 Agent 能力分层接入、bootstrap 提示、多 Agent 协作与反模式，见 **[adoption.md](docs/adoption.md#3-ai-coding-agent-路径)** |

存量项目不要直接 `--force` init：先跑只读盘点（`harness-adopt --report`），把"接入前基线"存档，再定改造顺序。

## 真实案例：接入前后五子系统评分

评分口径：五子系统各 1–5 分（1 = 缺失；3 = 有规则但不可机检；5 = 有门禁 + 有证据 + 定期复核），每分必须附证据；自评与独立复评分列。完整口径与两张评分表见 [adoption.md §4](docs/adoption.md#4-真实案例接入前后五子系统评分)。

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
- **门禁会腐烂，所以能自测**：`harness-selftest` 负向注入 + 121 个 kit 端到端用例；门禁空转（例：模式被改坏）会当场变红。

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
├── docs/adoption.md     # 接入指南（新项目 / 存量项目 / AI coding Agent + 前后评分案例）
├── docs/playbook.md     # 新项目五步法 + 存量项目七步法 + 常见坑 + 升级路径
├── docs/governance.md   # 演化与治理（反臃肿、版本策略、多人协作）
├── CHANGELOG.md         # 版本变更记录
└── tests/               # kit 自身 unittest（标准库，121 个端到端用例）
```

宿主目标（init 之后，按 profile 增减；以 SPEC §2 为准）：

```text
<target>/
├── AGENTS.md                     # 根指令（引用 references/、按目录读嵌套 AGENTS）
├── HARNESS.md / CONTRIBUTING.md   # standard+：系统地图 / 环境与验证
├── Makefile（或 Makefile.harness）# 门禁入口，按 profile 生成
├── docs/README.md, docs/AGENTS.md
├── references/{contracts,verification,workflow}.md
├── harness/
│   ├── config.json               # 唯一配置源（路径/命令/预算/claims/freshness/传感器）
│   ├── README.md, AGENTS.md
│   ├── plans/                    # standard+：front matter + 唯一 active
│   ├── evidence/                 # standard+：schema/TEMPLATE/摘要 JSON
│   └── reviews/                  # strict：独立审查记录
├── tools/*.py                    # 按 profile 复制（standard+ 含 check_hygiene / check_layers）
├── .githooks/pre-push            # standard+（可选）
├── .github/workflows/verify.yml  # standard+（可选）
└── .dsh/skills/ / .claude/       # strict + 对应适配器（可选）
```

## 采用后的日常工作流

1. **做任务前**：`make plan TOPIC=<topic>` 建计划，填 front matter（owner/scope/验收/verify）；同一时间只允许一个 active。
2. **每次改动后**：`make check`（静态门禁，必须 0）。
3. **完成声明前**：`make verify-static`；测试类声明先写 evidence（`tools/evidence.py write`），再 `make verify-claim` 取 PASS / FAIL / UNVERIFIED。
4. **发布前（strict）**：`make release-check`——证据必须 fresh 且 strict。
5. **交接/中断**：更新计划（进度、证据、未验证、未提交、下一步），用 `python3 tools/check_plan.py brief` 生成摘要。

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

本仓内 `harness-kit/` 是**唯一源**；独立模板仓 <https://github.com/DavidTeam2008/harness-kit> 由 `git subtree split` 生成的**只读镜像**。

- **改**：只改来源仓库的 `harness-kit/`，跑 `make kit-check` / `make verify-static`。
- **发布**：`make kit-publish`（subtree split → 推送镜像 `main`；非快进会被拒绝，说明镜像被直接改过）。
- **校验**：`make kit-drift` 比较本地 split 提交与镜像 `main`，不一致 exit 1。
- **禁止**直接在镜像仓提交后推送；Issue/PR 先回上游修，再发布并关闭。
- **版本**：`VERSION`（单一来源）+ `CHANGELOG.md`；发布同步在镜像仓打 tag。

## 来源案例

harness-kit 从 Duiyi 仓库的 harness 改造中提炼（案例与证据：<https://github.com/DavidTeam2008/realtime-translator-ios>）。该仓库是第一个案例；第二个真实案例是 Android/Gradle 存量仓 <https://github.com/DavidTeam2008/realtime-translator-android>（brownfield 接入 + v0.2.2→v0.2.3 版本升级验证 + 接入前后评分）。kit 本身不包含其业务代码或专有规则。

## 局限与未验证（别当成能力）

- **结构可验证 ≠ 行为正确**：静态门禁与证据判定证明"流程可复核"，不证明产品行为/性能/真机结果正确——这些仍靠宿主动态测试、真机与人工评审。
- **行为级评估尚未实现**：当前只有结构门禁 + 121 个 kit 测试 + 宿主 `harness-selftest`；"接入后 Agent 表现提升多少"的 A/B 评估是 v0.3+ 议题（见 governance §2.4），未做前不对外声称。
- **多人协作未验证**：唯一 active 计划、scope、证据绑定、CI required checks 能提供机制层支持；人类多人并行采用、人类陌生人首访仍未验证。
- **版本升级已验证，profile 升级未验证**：v0.2.2→v0.2.3 已在真实 Android/Gradle 仓验证；minimal→standard→strict 的 profile 升级路径仍未在真实项目验证。
- **语言/测试框架需要你提供**：`{{TEST_COMMAND}}` 与 `commands.test` 必须填真实命令；kit 不代跑、不解析测试输出（只提供 JUnit XML → evidence 转换）。
- **宿主已有文档/规则时首次 `make check` 可能不绿**：按预算与白名单修内容，不要删检查绕过。
- **外部试点有限**：空白 Python/Node/SwiftPM 项目、真实 Android/Gradle 存量仓已完成；其他语言生态、超大仓性能未验证。
- **kit 自身测试**：121 个端到端用例（三档 init、`make check`/`verify-static`/`check-host`、证据三值、strict `release-check`、存量盘点、JUnit 聚合、宿主传感器、门禁 selftest、Android 推断、dry-run/冲突/备份、无专有引用）；随来源仓库 `verify` workflow 运行。
- **适配器成熟度不一**：`githooks`/`ci` 有模板；`claude-code` 为薄适配；`dsh` 当前为预留。
- **未做外部安全审计**：kit 只承诺不联网、不写目标之外文件（SPEC §8.7），但未在第三方 CI/受限沙箱验证。

## License

与 [LICENSE](LICENSE) 一致：**MIT**。kit 版本 `0.2.5`；向后兼容策略见 [SPEC §10](SPEC.md)。

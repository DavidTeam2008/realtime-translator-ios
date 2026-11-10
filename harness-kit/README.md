# harness-kit

> 把「AI coding agent 可验收的研发约束」做成**项目无关**模板：**guides**（指令/规则）+ **sensors**（门禁/证据）+ **state**（计划/交接）。
> 不是框架、不是依赖：只生成 Markdown、Python 标准库脚本和一个 Makefile 入口；接入失败可整目录删除，不留运行时包袱。

- 版本：`0.2.3`（见 [`VERSION`](VERSION)）
- 内部构建契约：[`SPEC.md`](SPEC.md)
- 采用方法：[`docs/playbook.md`](docs/playbook.md)（新项目五步法 + 存量项目七步法 + 常见坑）

## 这是什么

- **指令层**：根 `AGENTS.md`（定位/路由/铁律）+ 嵌套 `AGENTS.md`（目录级增量规则），Agent 冷启动只读目录页。
- **静态门禁**：`make check` 秒级可跑（文档链接/围栏/索引/token 预算、指令层预算与敏感串、计划状态、适配器漂移）。
- **证据链**：claim + evidence JSON + `verify-claim` 三值判定（PASS / FAIL / UNVERIFIED）；**无 evidence id 一律按未验证处理**。
- **状态层**：`harness/plans/` 计划模板（front matter + 唯一 active）、`make plan`（standard+）、`python3 tools/check_plan.py brief` 交接摘要。
- **适配薄层**：`.githooks/pre-push`、CI workflow、Claude Code 兼容文件、skills 同步；工具差异不进入核心规则。

## 不是什么

- 不是 CI 平台 / Agent 框架 / 测试框架：不引入第三方依赖，只要求 **Python 3 + make + git**。
- 不替你写测试命令：`commands.test` 与 `{{TEST_COMMAND}}` 由宿主项目提供（SPEC §3/§6）。
- 不保证「接入即通过」：首次接入通常要按项目实际调整预算、规则与命令，再跑门禁。
- 不是产品代码：生成到宿主的文件只承担研发流程约束，不应进入业务运行时。

## 能力清单

| 能力 | 提供方 | 说明 |
| --- | --- | --- |
| 指令层 / 静态门禁 | `AGENTS.md` 模板 + `tools/check_docs.py` / `check_agents.py` | 目录页规则、链接/围栏/索引/预算、预算与敏感串、`§` 引用 |
| 计划状态 | `tools/check_plan.py` + `harness/plans/` | front matter、唯一 active、证据表、done/submitted 绑定 |
| 证据三值 | `tools/evidence.py` + `verify_claim.py` | PASS / FAIL / UNVERIFIED；无 evidence id 即未验证 |
| **JUnit XML 适配器** | `tools/evidence_from_junit.py`（standard+） | 聚合 JUnit XML（pytest/unittest、Gradle、JUnit 等）的 `tests/failures/errors/skipped/duration` 为 evidence JSON，供 `evidence.py write --from-json`；缺文件/解析失败 exit 2 |
| **宿主卫生 / 分层门禁** | `tools/check_hygiene.py` / `tools/check_layers.py`（standard+，可选配置） | 卫生：构建产物、根文件白名单、绝对符号链接、跟踪文件中的本机路径、超大文件；分层：import 方向与 symbol guard。`harness/config.json` 缺 `hygiene`/`layers` 段时自动 SKIP（不阻断） |
| **门禁自测** | `scripts/harness-selftest`（kit 侧） | 对目标仓的临时副本做基线检查、逐项注入并断言对应门禁非 0、恢复后复核全绿；默认不写目标仓 |
| **存量项目盘点** | `scripts/harness-adopt`（kit 侧） | 只读盘点 + `--report` / `--json` / `--write-plan`（改造计划草稿） |
| 语言探测 | `scripts/harness-init` | `python` / `swift` / `node` / `go` / `android` / `other` |
| 适配器 | `adapters/` | `githooks` / `ci` / `claude-code` / `dsh`（预留） |

## 10 分钟接入

前置：Python 3（标准库）、`make`、`git`；`--target` 指向**已存在**的目录（init 不执行 `git init`；建议先 `git status` 确认干净）。

```bash
# 0) 看计划（只打印 CREATE / COPY / SKIP / CONFLICT / RENDER，覆盖时另打印 BACKUP；不写文件、不跑检查）
python3 harness-kit/scripts/harness-init --profile standard --target ../myapp --name MyApp --dry-run

# 1) 最小档（只有指令 + 文档/指令门禁；不需要测试框架）
python3 harness-kit/scripts/harness-init --profile minimal --target ../myapp --name MyApp

# 2) 标准档（+ 计划/证据/CI 与 pre-push；真实仓库推荐）
python3 harness-kit/scripts/harness-init --profile standard --target ../myapp --name MyApp

# 3) 严格档（+ 适配器门禁/评分卡/红队/发布前 strict 证据校验）
python3 harness-kit/scripts/harness-init --profile strict --target ../myapp --name MyApp
```

- 非 `--dry-run` 时，init 写完后会在目标目录执行首次 `make check` 并**透传退出码**；加 `--no-check` 可先跳过。
- 常用参数（完整契约见 [SPEC §8](SPEC.md)）：

| 参数 | 作用 |
| --- | --- |
| `--profile {minimal,standard,strict}` | 选择交付层面 |
| `--target PATH` | 目标项目目录（相对当前工作目录） |
| `--name NAME` | 渲染进模板的项目名（缺省取目标目录名） |
| `--language auto\|python\|swift\|node\|go\|android\|other` | 语言探测/显式指定（决定建议命令与适配默认值；Gradle 仓探测为 `android`） |
| `--test-command "make test"` | 宿主项目真实测试命令；不传时 init 按语言给建议并打印 |
| `--adapters dsh,claude-code,ci,githooks` | 显式选择适配器（覆盖 profile 默认；`none` 表示不装；`dsh` 当前为预留） |
| `--dry-run` | 只输出计划，不写文件、不跑检查 |
| `--force` | 冲突文件先备份到 `<target>/.harness-init-backup/<UTC>/` 再覆盖 |
| `--no-check` | 跳过写完后自动执行的首次 `make check` |
| `--backup-dir PATH` | 覆盖备份目录位置 |

- 目标已有 `Makefile` 时**不覆盖**：写入 `Makefile.harness`，并提示你在原 `Makefile` 末尾加 `include Makefile.harness`。
- 冲突默认 `fail` 并列出文件；重复 init 不会重复追加 `.gitignore`（去重）；`--force` 前先 `--dry-run` 复核是推荐姿势。
- init 会**自动执行首次 `make check` 并透传退出码**；exit 0 即最小接入完成（标准/严格档再按 playbook 第 4–5 步接入测试与证据）。
- 推荐顺序：`init` → 首次 `make check`(自动) → `git commit`（证据写入要求 clean tree）→ 真实测试 → `evidence.py write` → `verify-claim`；`make plan` 生成的草稿在填完必填节并提交前会让 `make check` 变红（预期）。
- **宿主门禁（standard+）**：`make check-host` 运行 `tools/check_hygiene.py` + `tools/check_layers.py`；两者只在 `harness/config.json` 配置了 `hygiene` / `layers` 段时生效，未配置会 `[SKIP]`（不阻断）。`verify-static` 已包含 `check-host`。
- **验证门禁真的会红**：接入后可跑 `python3 harness-kit/scripts/harness-selftest --target .`——它在目标仓的临时副本里做基线检查并逐项注入（未登记文档/断链/超预算/本机路径/重复 active 计划/缺证据等），断言对应门禁非 0，再恢复并复核全绿；默认不写目标仓。exit 0=全部按预期拦截并恢复，1=有门禁未按预期变红，2=目标仓脏或 baseline 本身红。
- kit 目录**自包含**：`cp -r harness-kit /path/to/kit` 到仓库外后，`scripts/harness-init` 仍可直接使用（不依赖来源仓库的路径/历史）；拆分独立仓库时复制该目录即可。

### 存量项目（brownfield）先只读盘点

已有文档/测试/构建的仓库不要直接 init：先跑**只读盘点**（默认不写任何文件），再定 profile、迁移与清洁顺序。

```bash
# 只读盘点（默认 0 写入；report 写到目标之外，避免弄脏待改造仓库）
python3 harness-kit/scripts/harness-adopt --target ../legacy-app
python3 harness-kit/scripts/harness-adopt --target ../legacy-app --report ../harness-adoption-report.md
python3 harness-kit/scripts/harness-adopt --target ../legacy-app --json

# 生成改造计划草稿（要求目标已有 harness/plans/，否则 exit 1）
python3 harness-kit/scripts/harness-adopt --target ../legacy-app --write-plan
```

盘点输出：概览（git 状态/语言/构建/既有门禁）、文档（索引缺口/断链/疑似过期）、卫生（被跟踪构建产物/绝对符号链接/本机路径/大文件）、建议 profile 与 test 命令、下一步清单。exit 0=盘点完成；1=用法错误、目标不存在或 `--write-plan` 前置不满足。存量仓库的完整改造步骤见 playbook 的「存量项目（brownfield）改造」七步法。

## profiles 对比

| profile | 新增内容（相对上一档） | 主要 Makefile target | 适用场景 |
| --- | --- | --- | --- |
| `minimal` | `AGENTS.md`、`docs/README.md`、`docs/AGENTS.md`、`references/{contracts,verification,workflow}.md`、`harness/{README,AGENTS,config}`、`tools/{token_estimate,check_docs,check_agents}.py` | `check`（docs+agents）、`verify-static`（=check） | 先立规则与文档门禁；不需要测试框架 |
| `standard` | `HARNESS.md`、`CONTRIBUTING.md`、`harness/plans/_template.md`、`harness/evidence/{README,schema,TEMPLATE}`、`harness/test-baseline.json`、`tools/{check_plan,evidence,verify_claim,evidence_from_junit,check_hygiene,check_layers}.py`、可选 `githooks`/`ci` | `check`（+plan）、`verify-static`（含 `check-host` + 证据校验）、`check-host`（可选配置）、`verify-claim`、`plan TOPIC=` | 真实仓库：需要跨会话状态与「完成可证伪」 |
| `strict` | `docs/harness-scorecard.md`、`harness/reviews/`、`.dsh/skills/{verify-change,handoff,red-team}`、`tools/{doctor,adapters}.py`、可选 `claude-code`/`dsh` 适配 | 以上（`verify-static` 含 `check-host`）+ `release-check`（fresh/strict 证据）、`doctor`、`adapters-sync`/`adapters-check` | 长期维护项目：发布前强门禁、红队、适配器一致性 |

> 表格按 `profiles/*.json` 与 SPEC §5 整理；`dsh` 适配器当前为预留（manifest 为空列表），`claude-code` 提供 `CLAUDE.md` 与 hooks 示例。

## 语言与测试框架（实测矩阵）

| 语言/生态 | 语言探测依据 | init 建议的测试命令 | kit 实测 |
| --- | --- | --- | --- |
| Python | `pyproject.toml` / `setup.py` / `requirements.txt` / `*.py` | `python3 -m unittest discover -s tests -q` | ✅ 空白 Python 项目（unittest）+ 外部代理试点 |
| Node | `package.json` | 有 `scripts.test` → `npm test`；无 → `node --test`（Node 18+） | ✅ Node 24 / `node --test` + `npm test` |
| Swift | `Package.swift` → SwiftPM；`*.xcodeproj` → Xcode 工程 | `swift test`；Xcode 工程提示必须用 `--test-command` 显式给 `xcodebuild test -scheme …` | ✅ SwiftPM（Apple Swift 6.4）；**Xcode iOS 工程未实测** |
| Go | `go.mod` | `go test ./...` | ❌ 本机未安装 Go，未实测 |
| Android / Gradle | `settings.gradle(.kts)` / `build.gradle(.kts)` → `android`（优先于 python 的混合仓判定） | `./gradlew testDebugUnitTest` | ✅ 真实 Android/Gradle 仓完整试点（init → 文档蒸馏 → 宿主传感器 → JUnit 证据链 → 负向注入 → 计划归档）；JDK 17–21 与 wrapper 版本由项目固定；wrapper 路径/NDK/多模块边界由项目自管；kit 不代跑、不解析测试输出（JUnit XML + `evidence_from_junit.py` 取计数） |
| 其他 | 手动 `--language other` | `make test` | — |

> 语言支持的边界：kit 只负责**指令/门禁/计划/证据流程**，不解析业务测试输出。测试计数（`passed/failed/skipped`）由宿主用 `tools/evidence.py write --from-json` 提供（例如把 `swift test` 的 `Executed N test` 或 `node --test` 的 `# pass N` 填入）；需要更紧的集成时可在宿主加一层薄 wrapper。`gitignore` 模板已包含 `node_modules/`、`.build/`、`.swiftpm/`、`__pycache__/`，避免构建产物让证据写入被 dirty tree 拦住。

## 目录结构

kit 源（本模板，不进入宿主运行时）：

```text
harness-kit/
├── README.md            # 本文件（对外接入说明）
├── SPEC.md              # 内部构建契约（脚本/模板/测试必须遵守）
├── VERSION              # kit 版本单一来源
├── profiles/            # minimal / standard / strict manifest（extends 链）
├── core/                # config schema + 通用门禁脚本（docs/agents/plan/evidence/hygiene/layers…）+ 模板
├── adapters/            # githooks / ci / claude-code / dsh 薄适配
├── scripts/harness-init # 统一入口（探测、渲染、冲突处理、首次 check）
├── scripts/harness-adopt# 存量项目只读盘点 + 改造计划草稿（kit 侧）
├── scripts/harness-selftest # 门禁自测：临时副本注入、断言门禁会红、恢复后复核（kit 侧，默认不写目标仓）
├── docs/playbook.md     # 新项目五步法 + 存量项目七步法 + 常见坑
├── CHANGELOG.md         # 版本变更记录
└── tests/               # kit 自身 unittest（标准库）
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
│   ├── config.json               # 唯一配置源（路径/命令/预算/claims/adapters）
│   ├── README.md, AGENTS.md
│   ├── plans/                    # standard+：front matter + 唯一 active（adopt 可生成 _adoption.md 草稿）
│   ├── evidence/                 # standard+：schema/TEMPLATE/摘要 JSON
│   └── reviews/                  # strict：独立审查记录
├── tools/*.py                    # 按 profile 复制（standard+ 含 check_hygiene / check_layers）
├── .githooks/pre-push            # standard+（可选）
├── .github/workflows/verify.yml  # standard+（可选）
└── .dsh/skills/ / .claude/       # strict + 对应适配器（可选）
```

## 采用后的日常工作流

1. **每次改动后**：`make check`（静态门禁，必须 0）。
2. **做任务前**：`make plan TOPIC=<topic>` 建计划；完成后更新计划并写证据，而不是在聊天里记状态。
   > 新建的计划草稿在填完「目标/验收/下一步/scope.allow」前会让 `make check` 失败——这是设计：未填完的计划不算通过。
3. **完成声明前**：`make verify-static`（standard+ 含证据校验）；测试类声明先 `python3 tools/evidence.py write` 写证据（参数以 `--help` 为准，claim 定义在 `harness/config.json`），再 `make verify-claim` 取 PASS / FAIL / UNVERIFIED。
4. **发布前（strict）**：`make release-check`——要求证据 fresh 且 strict，STALE/缺证据一律不能绿。
5. **交接/中断**：更新计划（进度、证据、未验证、未提交、下一步），用 `python3 tools/check_plan.py brief` 生成交接摘要。

> 核心约定：**没有 evidence id 的“已验证”按未验证处理**；UNVERIFIED（exit 2）不是通过。

## 自定义

kit 的定制入口只有**目标项目的 `harness/config.json`**（所有门禁脚本只读这一份，不接受硬编码路径）；kit 源通过模板渲染生成它（SPEC §3）：

| 字段 | 用途 |
| --- | --- |
| `project.name` / `project.language` | 渲染占位符与展示 |
| `paths.*` | docs/references/harness/plans/evidence/reviews/tools 相对路径 |
| `instructions.budgets` / `nestedMaxBytes` / `sensitivePatterns` | 指令层 token 预算、嵌套 AGENTS 上限、敏感串扫描 |
| `docs.publicWhitelist` / `publicBudget` / `rootMarkdownAllowed` | 公开文档白名单与数量上限（防“删了又长回来”） |
| `commands.test` / `check` / `verify` | 宿主的真实命令（测试命令必须存在，不能写假命令） |
| `claims` / `freshness` | 可证伪声明与证据时效范围（`verify-claim --fresh` 用） |
| `adapters` | 可选适配器配置（如 skills 同步目录） |

可用模板占位符（渲染时替换；渲染后不得残留 `{{`）：`{{PROJECT_NAME}}` `{{PROJECT_LANGUAGE}}` `{{TEST_COMMAND}}` `{{CHECK_COMMAND}}` `{{VERIFY_COMMAND}}` `{{KIT_VERSION}}` `{{YEAR}}` `{{DOCS_DIR}}` `{{REFERENCES_DIR}}` `{{HARNESS_DIR}}` `{{ROOT_AGENTS}}` `{{DEFAULT_BRANCH}}`。

> 缺失必填字段时脚本必须给可读错误并 exit 1（不静默用默认值）；路径一律相对目标根，不接受绝对路径。

## 维护与镜像（维护者）

本仓内 `harness-kit/` 是**唯一源**；独立模板仓 <https://github.com/DavidTeam2008/harness-kit> 由 `git subtree split` 生成的**只读镜像**。

- **改**：只改来源仓库的 `harness-kit/`，跑 `make kit-check` / `make verify-static`。
- **发布**：`make kit-publish`（subtree split → 推送镜像 `main`；非快进会被拒绝，说明镜像被直接改过）。
- **校验**：`make kit-drift` 比较本地 split 提交与镜像 `main`，不一致 exit 1，提示先在上游改。
- **禁止**直接在镜像仓网页/本地提交后推送；收到 Issue/PR 时先在来源仓库修，再发布并关闭。
- **版本**：`VERSION`（单一来源）+ `CHANGELOG.md`；发布会同步在镜像仓打 tag（如 `v0.2.0`）。

## 来源案例

harness-kit 从 Duiyi 仓库的 harness 改造中提炼（案例与证据：<https://github.com/DavidTeam2008/realtime-translator-ios>）。该仓库是第一个案例；kit 本身不包含其业务代码或专有规则。

## 局限与未验证（别当成能力）

- **外部试点**：空白 Python 项目由 AI 代理完成 standard 接入（首次 `make check` 一次通过）；另一真实 Android/Gradle 仓完成完整 brownfield 试点（init → 文档蒸馏 → 宿主传感器 → JUnit 证据链 → 负向注入 → 计划归档）。**人类采用者、其他语言生态、超大仓性能仍未验证。**
- **语言/测试框架需要你提供**：不同语言只有建议命令；`{{TEST_COMMAND}}` 与 `harness/config.json.commands.test` 必须由你填真实命令，kit 不验证测试语义。
- **宿主已有文档/规则时首次 `make check` 可能不绿**：kit 生成的空白脚手架本身可通过；若目标已有 `AGENTS.md`/`docs/`/`Makefile`，需按预算与白名单调整（看 `FAIL` 提示，不要删检查绕过）。
- **存量项目（brownfield）流程已在真实 Android/Gradle 仓完整走通**（七步法 + `harness-adopt`）；其他语言/生态的存量仓、超大仓性能与 profile 升级路径仍未验证。
- **kit 自身测试**：`harness-kit/tests/` 含 121 个端到端用例（三档 init、`make check`/`verify-static`/`check-host`、证据三值、strict `release-check`、存量项目盘点、JUnit XML 聚合、宿主卫生/分层门禁、门禁 selftest、Android 推断、dry-run/冲突/备份、无专有引用）；已接入来源仓库的 `make verify-static`，本地执行 PASS，CI 随来源仓库 `verify` workflow 运行。
- **适配器成熟度不一**：`githooks`/`ci` 有模板；`claude-code` 为薄适配；`dsh` 当前 manifest 为空（预留）。
- **未做外部安全审计**：kit 只承诺不联网、不写目标之外文件（SPEC §8.7），但未在第三方 CI/受限沙箱验证。

## License

与 [LICENSE](LICENSE) 一致：**MIT**。kit 版本 `0.2.3`；向后兼容策略见 [SPEC §10](SPEC.md)。

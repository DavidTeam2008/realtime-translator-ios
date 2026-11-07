# harness-kit

> 把「AI coding agent 可验收的研发约束」做成**项目无关**模板：**guides**（指令/规则）+ **sensors**（门禁/证据）+ **state**（计划/交接）。
> 不是框架、不是依赖：只生成 Markdown、Python 标准库脚本和一个 Makefile 入口；接入失败可整目录删除，不留运行时包袱。

- 版本：`0.1.0`（见 [`VERSION`](VERSION)）
- 内部构建契约：[`SPEC.md`](SPEC.md)
- 采用方法：[`docs/playbook.md`](docs/playbook.md)（五步改造法 + 常见坑）

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
| `--language auto\|python\|swift\|node\|go\|other` | 语言探测/显式指定（决定建议命令与适配默认值） |
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
- kit 目录**自包含**：`cp -r harness-kit /path/to/kit` 到仓库外后，`scripts/harness-init` 仍可直接使用（不依赖来源仓库的路径/历史）；拆分独立仓库时复制该目录即可。

## profiles 对比

| profile | 新增内容（相对上一档） | 主要 Makefile target | 适用场景 |
| --- | --- | --- | --- |
| `minimal` | `AGENTS.md`、`docs/README.md`、`docs/AGENTS.md`、`references/{contracts,verification,workflow}.md`、`harness/{README,AGENTS,config}`、`tools/{token_estimate,check_docs,check_agents}.py` | `check`（docs+agents）、`verify-static`（=check） | 先立规则与文档门禁；不需要测试框架 |
| `standard` | `HARNESS.md`、`CONTRIBUTING.md`、`harness/plans/_template.md`、`harness/evidence/{README,schema,TEMPLATE}`、`harness/test-baseline.json`、`tools/{check_plan,evidence,verify_claim}.py`、可选 `githooks`/`ci` | `check`（+plan）、`verify-static`（+证据校验）、`verify-claim`、`plan TOPIC=` | 真实仓库：需要跨会话状态与「完成可证伪」 |
| `strict` | `docs/harness-scorecard.md`、`harness/reviews/`、`.dsh/skills/{verify-change,handoff,red-team}`、`tools/{doctor,adapters}.py`、可选 `claude-code`/`dsh` 适配 | 以上 + `release-check`（fresh/strict 证据）、`doctor`、`adapters-sync`/`adapters-check` | 长期维护项目：发布前强门禁、红队、适配器一致性 |

> 表格按 `profiles/*.json` 与 SPEC §5 整理；`dsh` 适配器当前为预留（manifest 为空列表），`claude-code` 提供 `CLAUDE.md` 与 hooks 示例。

## 目录结构

kit 源（本模板，不进入宿主运行时）：

```text
harness-kit/
├── README.md            # 本文件（对外接入说明）
├── SPEC.md              # 内部构建契约（脚本/模板/测试必须遵守）
├── VERSION              # kit 版本单一来源
├── profiles/            # minimal / standard / strict manifest（extends 链）
├── core/                # config schema + 通用门禁脚本 + 模板（复制/渲染到宿主）
├── adapters/            # githooks / ci / claude-code / dsh 薄适配
├── scripts/harness-init # 统一入口（探测、渲染、冲突处理、首次 check）
├── docs/playbook.md     # 五步改造法
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
│   ├── plans/                    # standard+：front matter + 唯一 active
│   ├── evidence/                 # standard+：schema/TEMPLATE/摘要 JSON
│   └── reviews/                  # strict：独立审查记录
├── tools/*.py                    # 按 profile 复制的标准库脚本
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

## 来源案例

harness-kit 从 Duiyi 仓库的 harness 改造中提炼（案例与证据：<https://github.com/DavidTeam2008/realtimeTranslatorOptimize>）。该仓库是第一个案例；kit 本身不包含其业务代码或专有规则。

## 局限与未验证（别当成能力）

- **外部试点仅有代理结果**：首个外部试点由 AI 代理在空白 Python 项目完成（standard 档接入成功，执行耗时 ≈80s，首次 `make check` 一次通过；报告见 [`../harness/reviews/2026-11-07-kit-pilot.md`](../harness/reviews/2026-11-07-kit-pilot.md)）。**作者另一个真实项目、人类采用者、历史文档冲突整合仍未验证**。
- **语言/测试框架需要你提供**：不同语言只有建议命令；`{{TEST_COMMAND}}` 与 `harness/config.json.commands.test` 必须由你填真实命令，kit 不验证测试语义。
- **宿主已有文档/规则时首次 `make check` 可能不绿**：kit 生成的空白脚手架本身可通过；若目标已有 `AGENTS.md`/`docs/`/`Makefile`，需按预算与白名单调整（看 `FAIL` 提示，不要删检查绕过）。
- **kit 自身测试**：`harness-kit/tests/` 含 67 个端到端用例（三档 init、`make check`/`verify-static`、证据三值、strict `release-check`、dry-run/冲突/备份、无专有引用）；已接入来源仓库的 `make verify-static`，本地执行 PASS，CI 随来源仓库 `verify` workflow 运行。
- **适配器成熟度不一**：`githooks`/`ci` 有模板；`claude-code` 为薄适配；`dsh` 当前 manifest 为空（预留）。
- **未做外部安全审计**：kit 只承诺不联网、不写目标之外文件（SPEC §8.7），但未在第三方 CI/受限沙箱验证。

## License

与仓库根 [LICENSE](../LICENSE) 一致：**MIT**。kit 版本 `0.1.0`；向后兼容策略见 [SPEC §10](SPEC.md)。

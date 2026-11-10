# harness-kit · SPEC（构建契约）

> 本文件是 `harness-kit` 的**内部构建契约**：所有 core 脚本、模板、profiles、脚手架与测试必须按本文件实现。
> 对外使用说明见 [`README.md`](README.md)；接入路径见 [`docs/adoption.md`](docs/adoption.md)；提示词模板见 [`docs/agent-prompts.md`](docs/agent-prompts.md)；逐步操作见 [`docs/playbook.md`](docs/playbook.md)；演化与治理见 [`docs/governance.md`](docs/governance.md)。
> 目标：把 Duiyi 验证过的 harness 机制抽成**与 Duiyi 无关**、可在任意项目 10 分钟接入的 **Harness Engineering 项目脚手架**（Instructions / State / Verification / Scope / Session Lifecycle 五子系统）。

## 0. 非目标

- 不是通用 CI 平台/Agent 框架；不引入第三方依赖（仅 Python 3 标准库 + make + git）。
- 不做语言运行时/测试框架封装：测试命令由项目配置提供（`{{TEST_COMMAND}}`）。
- 不在模板里写任何 Duiyi 专有名词（仅 `README.md` 的「来源案例」一节可提一次）。
- 不是代码迁移器：存量改造只做只读盘点、骨架与门禁，不自动重写业务代码或文档语义（由人/Agent 完成，门禁验收）。

## 1. 目录结构（kit 源）

```
harness-kit/
├── README.md                 # 对外：10 分钟接入、profiles、与 Duiyi 案例的关系
├── SPEC.md                   # 本文件（内部契约）
├── core/
│   ├── config.schema.json    # 目标项目 harness/config.json 的 JSON Schema（手写子集）
│   ├── tools/                # 复制到目标项目 tools/ 的通用脚本（标准库）
│   │   ├── token_estimate.py
│   │   ├── check_docs.py
│   │   ├── check_agents.py
│   │   ├── check_plan.py
│   │   ├── evidence.py
│   │   ├── verify_claim.py
│   │   ├── doctor.py
│   │   ├── adapters.py
│   │   ├── evidence_from_junit.py   # standard+：JUnit XML → evidence JSON
│   │   ├── check_hygiene.py         # standard+：宿主卫生门禁（可选 hygiene 段）
│   │   └── check_layers.py          # standard+：分层/依赖方向门禁（可选 layers 段）
│   └── templates/            # 渲染到目标项目的模板（{{PLACEHOLDER}}）
│       ├── AGENTS.md.template
│       ├── CONTRIBUTING.md.template
│       ├── HARNESS.md.template
│       ├── docs/README.md.template
│       ├── docs/AGENTS.md.template
│       ├── docs/harness-scorecard.md.template
│       ├── references/{contracts,verification,workflow}.md.template
│       ├── harness/{README,AGENTS}.md.template
│       ├── harness/plans/_template.md
│       ├── harness/plans/_adoption.md.template   # 仅供 harness-adopt --write-plan 渲染，不复制到宿主
│       ├── harness/evidence/{README.md.template,schema.json,TEMPLATE.json}
│       ├── harness/reviews/{README.md.template,_template.md}
│       ├── harness/test-baseline.json.template
│       ├── harness/config.json.template
│       ├── makefiles/Makefile.{minimal,standard,strict}.template
│       └── gitignore.append
├── adapters/
│   ├── dsh/README.md
│   ├── claude-code/{CLAUDE.md.template,settings.hooks.example.json,agents/red-team.md}
│   ├── ci/verify.yml.template
│   └── githooks/pre-push
├── profiles/
│   ├── minimal.json
│   ├── standard.json
│   └── strict.json
├── scripts/harness-init      # 可执行 Python3 脚手架（无扩展名）
├── scripts/harness-adopt     # kit 侧只读盘点 + 改造计划草稿（无扩展名）
├── scripts/harness-selftest  # kit 侧门禁自测：临时副本注入 → 断言门禁非 0 → 恢复复核（无扩展名）
├── docs/adoption.md          # 接入指南（AI coding Agent 优先 + 命令行手动接入 + 前后评分案例）
├── docs/agent-prompts.md     # AI coding Agent 提示词模板（接入/需求/计划/分工/交接/收尾）
├── docs/playbook.md          # 五步改造法 + 存量项目七步法 + 常见坑 + 升级路径
├── docs/governance.md        # 演化与治理（反臃肿、版本策略、多人协作）
└── tests/                    # kit 自身的 unittest（仅标准库）
```

## 2. 目标项目产物（init 后）

```
<target>/
├── AGENTS.md                         # 根指令（rendered）
├── HARNESS.md                        # standard/strict：系统地图（rendered）
├── CONTRIBUTING.md                   # standard/strict：环境/验证/PR（rendered）
├── Makefile 或 Makefile.harness      # 见 §5
├── docs/README.md, docs/AGENTS.md    # rendered
├── references/{contracts,verification,workflow}.md
├── harness/
│   ├── config.json                   # 目标项目配置（工具唯一读取源）
│   ├── README.md, AGENTS.md
│   ├── plans/_template.md
│   ├── plans/_adoption.md            # 可选：harness-adopt --write-plan 生成的改造计划草稿
│   ├── evidence/{schema.json,TEMPLATE.json,README.md}
│   ├── test-baseline.json            # standard/strict
│   └── reviews/…                     # strict
├── tools/*.py                        # 按 profile 复制；standard+ 另含 check_hygiene.py / check_layers.py
├── .gitignore                        # append 块
├── .githooks/pre-push                # standard/strict（可选初始化）
├── .github/workflows/verify.yml      # standard/strict（可选初始化）
├── .dsh/skills/*/SKILL.md            # strict（可选初始化）
└── .claude/…                         # strict + claude-code adapter（可选初始化）
```

## 3. `harness/config.json`（目标项目配置）

由 `core/templates/harness/config.json.template` 渲染生成，**所有 core 脚本只读这一份配置**（不接受硬编码路径）。字段：

```json
{
  "kitVersion": "0.2.10",
  "project": { "name": "{{PROJECT_NAME}}", "language": "{{PROJECT_LANGUAGE}}" },
  "paths": {
    "docs": "docs",
    "references": "references",
    "harness": "harness",
    "plans": "harness/plans",
    "evidence": "harness/evidence",
    "reviews": "harness/reviews",
    "tools": "tools",
    "rootDocs": ["AGENTS.md"]
  },
  "instructions": {
    "root": "AGENTS.md",
    "nested": ["docs/AGENTS.md", "harness/AGENTS.md"],
    "nestedMaxBytes": 8192,
    "budgets": { "AGENTS.md": 1200, "references/contracts.md": 700, "references/verification.md": 700, "references/workflow.md": 700 },
    "sensitivePatterns": ["/Users/", "sk-"]
  },
  "docs": {
    "publicWhitelist": ["README.md", "AGENTS.md", "HARNESS.md", "CONTRIBUTING.md", "docs/README.md", "docs/AGENTS.md", "docs/harness-scorecard.md"],
    "publicBudget": 12,
    "rootMarkdownAllowed": ["README.md", "AGENTS.md", "HARNESS.md", "CONTRIBUTING.md"]
  },
  "commands": {
    "check": "make check",
    "verify": "make verify-static",
    "test": "{{TEST_COMMAND}}"
  },
  "claims": [
    { "name": "tests-pass", "type": "test-count", "baseline": "harness/test-baseline.json",
      "floor": "unit.floor", "expectedSkipped": "unit.expectedSkipped",
      "requireArtifact": false, "command": "{{TEST_COMMAND}}" },
    { "name": "docs-pass", "type": "static", "command": "python3 tools/check_docs.py" }
  ],
  "freshness": {
    "tests-pass": ["**/*.py", "**/*.swift", "**/*.ts", "tests/**"],
    "docs-pass": ["docs/**", "references/**", "AGENTS.md", "harness/**"]
  },
  "adapters": { "claudeCode": { "skillsSource": ".dsh/skills", "skillsTarget": ".claude/skills" } }
}
```

- 缺失字段时脚本必须给出**可读错误**并 exit 1，不得静默使用默认值（`examples` 里的默认值仅用于模板生成）。
- 可选段：`hygiene` / `layers`（宿主按需添加，模板默认不生成；字段契约见 §4，`core/config.schema.json` 中 `additionalProperties: true`）。
- 路径一律相对目标项目根；不接受绝对路径。

## 4. 脚本 CLI 契约（宿主 `tools/`；kit 侧 `scripts/*` 例外，见本节末）

| 脚本 | 用法 | 输出/语义 |
| --- | --- | --- |
| `token_estimate.py` | import 用：`estimate_tokens(text) -> int` | v2 估算：CJK/全角=1，ASCII=1/4 |
| `check_docs.py` | `python3 tools/check_docs.py [--root PATH]` | a) `paths.rootDocs` 必须存在；b) `docs.rootMarkdownAllowed` 中**实际存在**的根 md 也检查（不强制存在）；c) 链接/围栏/docs 索引/公开白名单/上限/token 预算；`[OK]/[FAIL]`，exit 1。空 docs 索引只有 README 视为通过 |
| `check_agents.py` | 同上 | 根/嵌套 AGENTS 存在与字节上限、token 预算、敏感串扫描、`§N`/`第 N 节` 引用解析（目标标题存在）；exit 1 |
| `check_plan.py` | `python3 tools/check_plan.py [check\|new TOPIC\|brief] [--root PATH]` | 计划 front matter（status/level/owner/updated/scope.allow/acceptance/verify）、唯一 active、必填节、验证证据表（命令/结果/环境/证据ID）、evidence id 必须存在且 PASS、done 必须有 `submitted` 且证据 commit 绑定、未提交改动与 `git status` 一致；exit 1 |
| `evidence.py` | `python3 tools/evidence.py {ls\|validate\|write} [--claim NAME …] [--root PATH]` | 读写 `harness/evidence/<UTC>-<claim>.json`（schema 见 `harness/evidence/schema.json`）；自动填 `git.commit/dirty`；`write` 要求 clean tree |
| `verify_claim.py` | `python3 tools/verify_claim.py --all [--fresh] [--strict] [--root PATH]` | 三值：`CLAIM <id>: PASS|FAIL|UNVERIFIED — reason`；聚合 exit：任一 FAIL→1，否则任一 UNVERIFIED→2，全 PASS→0；`--fresh` 按 config.freshness 比较证据 commit 与工作树（evidence/plans/reviews 过程目录不计入）；`--strict` 时 STALE→UNVERIFIED；test-count 的产物要求由 `claim.requireArtifact`（默认 false）控制 |
| `doctor.py` | `python3 tools/doctor.py [--root PATH]` | OK/WARN/FAIL/SKIP：python3、git 仓库、config.commands.test 可执行性、可选适配器；缺必需项 exit 2，否则 0 |
| `adapters.py` | `python3 tools/adapters.py {sync\|check} [--root PATH]` | `.dsh/skills` 单源 → `.claude/skills` 生成/哈希比对；exit 1 |
| `evidence_from_junit.py` | `python3 tools/evidence_from_junit.py --xml GLOB [--xml GLOB …] --claim NAME --command CMD [--environment KEY=VALUE …] [--notes TEXT] [--output PATH] [--root PATH]` | standard+：聚合 JUnit XML（`testsuites`/`testsuite`/`testcase`，统计 `failures`/`errors`/`skipped`/`time`）为 `evidence.py write --from-json` 可接受的 JSON（schemaVersion/claim/command/environment/result{status,passed,failed,skipped,durationSec}/verdict/verifier/notes）；`passed = tests − failures − errors − skipped`；`--xml` 缺失或解析失败 exit 2，缺 `--command` exit 2；`--output` 缺省 stdout |
| `check_hygiene.py` | `python3 tools/check_hygiene.py [--root PATH]` | standard+：读 `harness/config.json` 的**可选** `hygiene` 段（缺失 → `[SKIP]` exit 0）。字段：`trackedArtifactGlobs`（被跟踪构建产物 glob）、`rootAllowlist`（根目录文件白名单）、`localPathPatterns`（本机路径；以 `/` 开头且以 `/` 结尾的目录型条目按字面前缀 + 标识符边界匹配，避免 `features/home/` 误报；其他条目按正则解析）、`skipLocalPathScan`（前缀跳过）、`maxTrackedFileBytes`、`forbidAbsoluteSymlinks`（默认 true）。检查 `git ls-files` 的构建产物 / 根文件白名单（仅配置了 `rootAllowlist` 时生效）/ 绝对符号链接（mode `120000` 且 `cat-file` 目标以 `/` 开头）/ 跟踪文本文件中的本机路径 / 超大跟踪文件；`[OK]/[FAIL]`，违规 exit 1；非 git 仓库 → SKIP exit 0 |
| `check_layers.py` | `python3 tools/check_layers.py [--root PATH]` | standard+：读可选 `layers` 段（缺失 → `[SKIP]` exit 0）。字段：`sourceRoot`、`extensions`（默认 `.kt`/`.java`/`.py`）、`rules`（`name`/`pathPrefix`/`forbiddenImports`/`allowedImports`）、`symbolGuards`（`classes`/`allowedPaths`）。解析 Kotlin/Java `import` 与 Python `import`/`from … import`；前缀匹配支持带点前缀，`allowedImports` 可覆盖；`symbolGuards` 扫描非注释代码行并校验路径 glob；违规输出 `file:rule`，exit 1 |

通用约定：脚本自行 `Path(__file__).resolve().parent.parent` 定位根，或 `--root` 覆盖；不要读取 kit 源目录；不写目标项目之外的文件（tempfile 除外）；不联网。

kit 侧脚本（**不复制到宿主**）：`python3 harness-kit/scripts/harness-adopt --target PATH [--report PATH] [--json] [--write-plan] [--root KIT_ROOT]`。默认**只读盘点**（0 写入 target）；`--report` 写 Markdown 报告、`--json` 输出机器可读 JSON、`--write-plan` 渲染 `core/templates/harness/plans/_adoption.md.template` 到 `<target>/harness/plans/<DATE>-adopt-harness.md`（要求该目录已存在，否则 exit 1；模板缺失/未知占位符给可读错误；目标文件已存在则拒绝覆盖）。盘点内容：概览（git/语言/构建/既有门禁）、文档（索引缺口/断链/疑似过期）、卫生（被跟踪产物/绝对符号链接/本机路径/大文件）、建议 profile 与 test 命令、下一步清单。exit 0=盘点完成；1=用法错误、目标不存在或 `--write-plan` 前置不满足。

kit 侧门禁自测（**不复制到宿主**）：`python3 harness-kit/scripts/harness-selftest --target PATH [--keep] [--json]`。`--target` 必须是 git 仓库且工作树干净；脚本 `git clone -q` 到临时目录，先跑 baseline `make check`（baseline 红 → 报告后 exit 2，清理退出），再逐项注入并断言对应门禁**非 0**：M1 新增未登记 `docs/__selftest__.md`（`check_docs.py`）、M2 `docs/README.md` 追加断链（`check_docs.py`）、M3 根目录新增未白名单 md（`check_docs.py`）、M4 `AGENTS.md` 追加超预算文本（`check_agents.py`）、M5 `AGENTS.md` 追加本机路径（`check_agents.py`）、M6 若存在 active 计划则复制出第二个 active（`check_plan.py check`）、M7 若存在证据 JSON 则临时移走后 `verify_claim.py --all` 期望非 0、M8 若配置了 `hygiene` 段则在跟踪文件追加本机路径（`check_hygiene.py`）。每项注入后 `git checkout -- .` 并删除新增文件恢复；最后再跑一次 `make check` 复核为 0。输出 `mutation | gate | 注入 exit | 期望 | PASS/FAIL` 表：全部符合 exit 0，任一不符 exit 1，target 脏或 baseline 红 exit 2；默认清理临时目录，`--keep` 保留并打印路径，`--json` 输出机器可读结果；**默认不写 `--target` 仓库**。

空状态语义（新接入项目必须能一次通过）：`harness/plans/` 无计划、`harness/evidence/` 无证据、`docs/` 只有 README、`.dsh/skills/` 不存在，均视为 **OK（带提示）**，不得因此 FAIL。

## 5. Makefile 与 profile 分层

`init` 的 Makefile 规则：

- 目标没有 `Makefile` → 写入 `Makefile`（对应 profile 模板）。
- 目标已有 `Makefile` → 写 `Makefile.harness`（同名模板），并打印「在 Makefile 末尾加 `include Makefile.harness`」；**不覆盖**已有 Makefile。

各 profile 的 target：

| profile | files / tools | Makefile targets |
| --- | --- | --- |
| minimal | AGENTS + docs IA + 3 references + harness/{README,AGENTS,config} + `token_estimate` `check_docs` `check_agents` | `check`（docs+agents）、`verify-static`（=check） |
| standard | minimal + plans/evidence/test-baseline + `check_plan` `evidence` `verify_claim` `evidence_from_junit` `check_hygiene` `check_layers` + HARNESS/CONTRIBUTING + githooks/CI（可选） | `check`（docs+agents+plan）、`verify-static`（check + check-host + check-evidence）、`check-host`（`check_hygiene` + `check_layers`，缺配置 SKIP）、`verify-claim`、`plan TOPIC=` |
| strict | standard + doctor/adapters + scorecard/reviews/red-team skill + adapters（可选） | 以上（`verify-static` 含 `check-host`）+ `release-check`（verify-static + `--fresh --strict`）、`doctor`、`adapters-sync/check` |

`check-host` 在 standard/strict 的 Makefile 中定义为 `python3 tools/check_hygiene.py` + `python3 tools/check_layers.py`，`verify-static` 依赖它；两个脚本读 `harness/config.json` 的**可选** `hygiene` / `layers` 段，未配置时 SKIP，空白项目 init 后 `make check` 仍应通过。

注意：`docs/README.md.template` 是 minimal/standard 共用的索引（只能列 minimal 存在的文件）；strict 用 `core/templates/docs/README.strict.md.template` 覆盖 `docs/README.md`，额外登记 `harness-scorecard.md`（profile 合并按 `dst` 覆盖）。

## 6. 模板占位符（渲染时替换；未知占位符必须报错而不是留空）

`{{PROJECT_NAME}}` `{{PROJECT_LANGUAGE}}` `{{TEST_COMMAND}}` `{{CHECK_COMMAND}}` `{{VERIFY_COMMAND}}` `{{KIT_VERSION}}` `{{YEAR}}` `{{DOCS_DIR}}` `{{REFERENCES_DIR}}` `{{HARNESS_DIR}}` `{{ROOT_AGENTS}}` `{{DEFAULT_BRANCH}}` `{{DATE}}`

`{{DATE}}` 仅用于 `scripts/harness-adopt --write-plan` 渲染 `harness/plans/_adoption.md.template`（生成改造计划草稿）；其他模板不使用。

渲染后不得残留 `{{`。

## 7. profile manifest schema（`profiles/*.json`）

```json
{
  "name": "standard",
  "description": "一句话说明",
  "extends": "minimal",
  "files": [
    { "src": "core/templates/AGENTS.md.template", "dst": "AGENTS.md", "render": true, "onConflict": "fail" },
    { "src": "core/tools/check_docs.py", "dst": "tools/check_docs.py", "render": false, "executable": false, "onConflict": "fail" }
  ],
  "makefile": "core/templates/makefiles/Makefile.standard.template",
  "makeTargets": ["check", "verify-static", "verify-claim"],
  "optionalAdapters": ["githooks", "ci"]
}
```

- `extends`：合并父 profile 的 `files`（同 `dst` 子覆盖父），最多一层继承。
- `onConflict`：`fail`（默认；非交互场景报错，`--force` 时备份后覆盖）| `skip`（保留现有，WARN）。
- `src` 相对 kit 根；`dst` 相对目标根；禁止 `..`。

## 8. `harness-init` 契约

```
python3 harness-kit/scripts/harness-init --profile standard --target ../myapp \
  [--name MyApp] [--language auto|python|swift|node|go|android|other] \
  [--test-command "make test"] [--adapters dsh,claude-code,ci,githooks] \
  [--dry-run] [--force] [--no-check] [--backup-dir PATH] [--root KIT_ROOT]
```

行为：

1. 校验 `--profile` 存在、manifest schema 合法、所有 `src` 存在、目标目录存在（否则报错）。
2. 探测/推断：语言（`settings.gradle|settings.gradle.kts|build.gradle|build.gradle.kts`→android（**优先判定**，避免混合仓被误判为 python）；`Package.swift` / `*.xcodeproj`→swift；`package.json`→node；`pyproject.toml|setup.py|requirements.txt|*.py`→python；`go.mod`→go；否则 other）；`--test-command` 缺省按语言/工具链推断并打印来源提示：android（`./gradlew testDebugUnitTest`；JDK 17–21 与 wrapper 版本由项目固定，wrapper 路径/NDK/多模块边界由项目自管，kit 不代跑、不解析输出）、node（有 `scripts.test`→`npm test`，否则 `node --test`）、swift（`Package.swift`→`swift test`；`*.xcodeproj`→提示必须用 `--test-command` 显式给 `xcodebuild test -scheme …`）、其他→`make test`。kit 不解析测试输出，计数由宿主写入 evidence（结构化 JUnit XML 可用 `tools/evidence_from_junit.py` 聚合后交给 `evidence.py`）。
3. 冲突：目标已有同名文件 → 默认 `fail` 并列出；`--force` 时把被覆盖文件备份到 `<target>/.harness-init-backup/<UTC>/` 后写入。
4. `--dry-run`：只打印 `CREATE / SKIP / CONFLICT / RENDER` 计划，不写文件、不跑 check。
   `.gitignore` 追加块包含通用构建产物（`node_modules/`、`.build/`、`.swiftpm/`、`__pycache__/`），保证测试后的 clean tree 可用于写证据。
5. 写完后打印「下一步」；非 `--no-check` 时在目标目录执行 `make check`（或 `python3 tools/check_docs.py` 等按 profile 的命令链），透传退出码。
6. 幂等：重复 init（无 `--force`）应报冲突而不是重复追加；`gitignore.append` 需去重。
7. 安全：不打印/写入密钥；不访问网络；不修改 git 历史。

## 9. 测试契约（`harness-kit/tests/`）

- 全部 `unittest` + 标准库；命令行方式跑：`python3 -m unittest discover -s harness-kit/tests -q`（从仓库根）或 `cd harness-kit && python3 -m unittest discover -s tests -q`。
- 必须覆盖：
  - `test_kit_profiles.py`（Lead）：每个 profile 在 tmp 空白 git 仓 init 后：`make check` exit 0；standard/strict 的 `make verify-static` exit 0；dry-run 不写文件；冲突报错；`--force` 产生备份；无残留 `{{`；Android 推断：tmp 放 `settings.gradle.kts` 时 `--dry-run` 推断 `language=android`、建议 `./gradlew testDebugUnitTest` 并打印 Gradle 边界提示。
  - `test_kit_hygiene.py`（Lead）：`core/` `adapters/` `profiles/` `scripts/` 中不得出现 `Duiyi|duiyi|对译|TranslationSession|SwiftData|DuiyiTests`（仅 `harness-kit/README.md` 的来源一节允许一次）；kit 顶层文档相对链接可解析；`VERSION`/profiles 结构一致；README/SPEC 中的版本引用与 `VERSION` 一致。
  - `test_harness_adopt.py`（gates）：tmp git fixture（断链/未登记文档/根 `NOTES.md`/被跟踪构建产物/绝对符号链接/本机路径）上 `scripts/harness-adopt` 的报告命中、默认 0 写入、`--json` 键、`--write-plan` 在存在 `harness/plans/` 时渲染计划、非法 target exit 1；不依赖网络/Xcode。
  - `test_evidence_junit.py`（gates）：JUnit XML 单/多 suite、`failures`/`errors`/`skipped` 计数、duration 聚合、malformed/missing exit 2、`--output` 必需键（`passed = tests − failures − errors − skipped`）。
  - `test_kit_host_tools.py`（gates）：tmp git fixture + `harness/config.json`；`check_hygiene.py` 覆盖被跟踪构建产物 / 根文件白名单 / 绝对符号链接 / 本机路径四类违规与正常情况、缺 `hygiene` 段 SKIP；`check_layers.py` 覆盖违规 import / `allowedImports` 覆盖 / `symbolGuards`、缺 `layers` 段 SKIP；≥8 用例。
  - `test_harness_selftest.py`（gates）：`harness-init --profile standard` 生成临时宿主 + git commit；正常 target → `scripts/harness-selftest` exit 0 且输出含 mutation 行；target 脏 → exit 2；baseline 红（预先提交未登记 docs）→ exit 2；总时长约 10s。
  - `test_core_plan_evidence_claim.py`（state）：check_plan/evidence/verify_claim 的通过、失败、三值、freshness、done/submitted 负向；check_plan 对无扩展名根文件（`Makefile`/`GNUmakefile`/`Dockerfile`/`LICENSE`/`NOTICE`）的未提交改动声明：声明 → PASS，不声明 → FAIL。
  - `test_core_docs_agents_doctor.py`（gates）：check_docs/check_agents/doctor 的链接/围栏/预算/§ 引用/敏感串/exit code。
- 测试禁止依赖本机 Xcode/真机/网络；临时目录用 `tempfile.TemporaryDirectory`。

## 10. 版本与迁移

- `KIT_VERSION` 单一来源 `harness-kit/VERSION`（kit 自身）与目标项目 `harness/config.json.kitVersion`。
- 向后兼容：新增 config 字段必须可选；破坏性变更需在 README 的 changelog 记录。
- 仓库改名：`harness-kit` → `harness-engineering-kit`（2026-11-10，GitHub 301 重定向；目录、命令、tag 前缀沿用短名 `harness-kit`）。
- 升级：kit 不提供 in-place 迁移命令（设计决定，避免覆盖宿主文档）。版本升级按 playbook「升级路径」执行（临时渲染 → 逐文件 diff → 只回写 kit 管理面 → `verify-static` + `harness-selftest`）；该路径已由真实 Android/Gradle 存量仓 v0.2.2→v0.2.3 验证（2026-11-10），profile 升级仍未验证。

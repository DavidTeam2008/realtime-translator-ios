# harness-kit · SPEC（构建契约）

> 本文件是 `harness-kit` 的**内部构建契约**：所有 core 脚本、模板、profiles、脚手架与测试必须按本文件实现。
> 对外使用说明见 [`README.md`](README.md)；采用方法见 [`docs/playbook.md`](docs/playbook.md)。
> 目标：把 Duiyi 验证过的 harness 机制抽成**与 Duiyi 无关**、可在任意项目 10 分钟接入的模板。

## 0. 非目标

- 不是通用 CI 平台/Agent 框架；不引入第三方依赖（仅 Python 3 标准库 + make + git）。
- 不做语言运行时/测试框架封装：测试命令由项目配置提供（`{{TEST_COMMAND}}`）。
- 不在模板里写任何 Duiyi 专有名词（仅 `README.md` 的「来源案例」一节可提一次）。

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
│   │   └── adapters.py
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
├── docs/playbook.md          # 五步改造法 + 常见坑
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
│   ├── evidence/{schema.json,TEMPLATE.json,README.md}
│   ├── test-baseline.json            # standard/strict
│   └── reviews/…                     # strict
├── tools/*.py                        # 按 profile 复制
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
  "kitVersion": "0.1.0",
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
- 路径一律相对目标项目根；不接受绝对路径。

## 4. 脚本 CLI 契约（全部位于目标项目 `tools/`，`--root` 默认「脚本上级目录」）

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

通用约定：脚本自行 `Path(__file__).resolve().parent.parent` 定位根，或 `--root` 覆盖；不要读取 kit 源目录；不写目标项目之外的文件（tempfile 除外）；不联网。

空状态语义（新接入项目必须能一次通过）：`harness/plans/` 无计划、`harness/evidence/` 无证据、`docs/` 只有 README、`.dsh/skills/` 不存在，均视为 **OK（带提示）**，不得因此 FAIL。

## 5. Makefile 与 profile 分层

`init` 的 Makefile 规则：

- 目标没有 `Makefile` → 写入 `Makefile`（对应 profile 模板）。
- 目标已有 `Makefile` → 写 `Makefile.harness`（同名模板），并打印「在 Makefile 末尾加 `include Makefile.harness`」；**不覆盖**已有 Makefile。

各 profile 的 target：

| profile | files / tools | Makefile targets |
| --- | --- | --- |
| minimal | AGENTS + docs IA + 3 references + harness/{README,AGENTS,config} + `token_estimate` `check_docs` `check_agents` | `check`（docs+agents）、`verify-static`（=check） |
| standard | minimal + plans/evidence/test-baseline + `check_agents` `check_plan` `evidence` `verify_claim` + HARNESS/CONTRIBUTING + githooks/CI（可选） | `check`（docs+agents+plan）、`verify-static`（check+check-evidence）、`verify-claim`、`plan TOPIC=` |
| strict | standard + doctor/adapters + scorecard/reviews/red-team skill + adapters（可选） | `check`（含 adapters-check）、`verify-static`、`verify-claim`、`release-check`（verify-static + `--fresh --strict`）、`doctor`、`adapters-sync/check` |

注意：`docs/README.md.template` 是 minimal/standard 共用的索引（只能列 minimal 存在的文件）；strict 用 `core/templates/docs/README.strict.md.template` 覆盖 `docs/README.md`，额外登记 `harness-scorecard.md`（profile 合并按 `dst` 覆盖）。

## 6. 模板占位符（渲染时替换；未知占位符必须报错而不是留空）

`{{PROJECT_NAME}}` `{{PROJECT_LANGUAGE}}` `{{TEST_COMMAND}}` `{{CHECK_COMMAND}}` `{{VERIFY_COMMAND}}` `{{KIT_VERSION}}` `{{YEAR}}` `{{DOCS_DIR}}` `{{REFERENCES_DIR}}` `{{HARNESS_DIR}}` `{{ROOT_AGENTS}}` `{{DEFAULT_BRANCH}}`

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
  [--name MyApp] [--language auto|python|swift|node|go|other] \
  [--test-command "make test"] [--adapters dsh,claude-code,ci,githooks] \
  [--dry-run] [--force] [--no-check] [--backup-dir PATH] [--root KIT_ROOT]
```

行为：

1. 校验 `--profile` 存在、manifest schema 合法、所有 `src` 存在、目标目录存在（否则报错）。
2. 探测/推断：语言（`Package.swift`→swift、`package.json`→node、`pyproject.toml|setup.py|requirements.txt`→python、`go.mod`→go，否则 other）；`--test-command` 缺省按语言给建议并打印（不写死假命令）。
3. 冲突：目标已有同名文件 → 默认 `fail` 并列出；`--force` 时把被覆盖文件备份到 `<target>/.harness-init-backup/<UTC>/` 后写入。
4. `--dry-run`：只打印 `CREATE / SKIP / CONFLICT / RENDER` 计划，不写文件、不跑 check。
5. 写完后打印「下一步」；非 `--no-check` 时在目标目录执行 `make check`（或 `python3 tools/check_docs.py` 等按 profile 的命令链），透传退出码。
6. 幂等：重复 init（无 `--force`）应报冲突而不是重复追加；`gitignore.append` 需去重。
7. 安全：不打印/写入密钥；不访问网络；不修改 git 历史。

## 9. 测试契约（`harness-kit/tests/`）

- 全部 `unittest` + 标准库；命令行方式跑：`python3 -m unittest discover -s harness-kit/tests -q`（从仓库根）或 `cd harness-kit && python3 -m unittest discover -s tests -q`。
- 必须覆盖：
  - `test_kit_profiles.py`（Lead）：每个 profile 在 tmp 空白 git 仓 init 后：`make check` exit 0；standard/strict 的 `make verify-static` exit 0；dry-run 不写文件；冲突报错；`--force` 产生备份；无残留 `{{`。
  - `test_no_duiyi_refs.py`（Lead）：`core/` `adapters/` `profiles/` `scripts/` 中不得出现 `Duiyi|duiyi|对译|TranslationSession|SwiftData|DuiyiTests`（仅 `harness-kit/README.md` 的来源一节允许一次）。
  - `test_core_plan_evidence_claim.py`（state）：check_plan/evidence/verify_claim 的通过、失败、三值、freshness、done/submitted 负向。
  - `test_core_docs_agents_doctor.py`（gates）：check_docs/check_agents/doctor 的链接/围栏/预算/§ 引用/敏感串/exit code。
- 测试禁止依赖本机 Xcode/真机/网络；临时目录用 `tempfile.TemporaryDirectory`。

## 10. 版本与迁移

- `KIT_VERSION` 单一来源 `harness-kit/VERSION`（kit 自身）与目标项目 `harness/config.json.kitVersion`。
- 向后兼容：新增 config 字段必须可选；破坏性变更需在 README 的 changelog 记录。

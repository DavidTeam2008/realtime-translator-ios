# harness-kit · SPEC（构建契约）

> 本文件是 `harness-kit` 的**内部构建契约**：所有 core 脚本、模板、profiles、脚手架与测试必须按本文件实现。
> 对外使用说明见 [`README.md`](README.md)；接入与日常使用见 [`docs/adoption.md`](docs/adoption.md)；提示词库见 [`docs/agent-prompts.md`](docs/agent-prompts.md)（由 `prompts/` 生成）；逐步操作见 [`docs/playbook.md`](docs/playbook.md)；演化与治理见 [`docs/governance.md`](docs/governance.md)。
> 目标：把 Duiyi 验证过的 harness 机制抽成**与 Duiyi 无关**、可在任意项目 10 分钟接入的 **Harness Engineering 项目脚手架**（Instructions / State / Verification / Scope / Session Lifecycle 五子系统）。

## 0. 非目标

- 不是通用 CI 平台/Agent 框架；不引入第三方依赖（仅 Python 3 标准库 + make + git）。
- 不做语言运行时/测试框架封装：测试命令由项目配置提供（`{{TEST_COMMAND}}`）。
- 不替代产品管理：需求在外部工具；kit 从"可验收"开始，用 `intake` 接收需求卡。
- 不做 Agent 编排运行时：Agent 的选择/调度/并发由宿主或 Agent 平台负责，kit 只维护项目状态与门禁。
- 不做权限 / 工单 / 审批系统：这些在 Git/CI/团队系统。
- 不在模板里写任何 Duiyi 专有名词（仅 `README.md` 的「来源案例」一节可提一次）。
- 不是代码迁移器：存量改造只做只读盘点、骨架与门禁，不自动重写业务代码或文档语义（由人/Agent 完成，门禁验收）。
- 不承诺证据防伪造/防删除：v0.4 证明「仓库内部自洽 + 声明的 artifact 能按当前文件重算」；不证明测试真实执行、authority 环境、独立评审、waiver 合法性，也不提供 tracked evidence ledger（v0.4 未做，属明确边界）。

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
│   │   ├── harness.py             # v0.3.0+：统一入口（status/start/verify/handoff/plan/upgrade）
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
│       ├── docs/README.standard.md.template   # standard 覆盖：登记 harness-scorecard
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
│       └── makefiles/Makefile.{minimal,standard,strict}.template
│       └── gitignore.append
├── adapters/
│   ├── dsh/README.md
│   ├── claude-code/{CLAUDE.md.template,settings.hooks.example.json,agents/red-team.md}
│   ├── ci/verify.yml.template
│   ├── gitattributes/export-ignore.append   # v0.5.2+：发布源码包排除 harness 过程文件（append 到 .gitattributes）
│   └── githooks/pre-push
├── profiles/
│   ├── minimal.json
│   ├── standard.json
│   └── strict.json
├── scripts/harness-init      # 可执行 Python3 脚手架（无扩展名）
├── scripts/harness-adopt     # kit 侧只读盘点 + 改造计划草稿（无扩展名）
├── scripts/harness-selftest  # kit 侧门禁自测：临时副本注入 → 断言门禁非 0 → 恢复复核（无扩展名）
├── scripts/harness-prompt    # 提示词库 CLI：list / show / copy / render（按场景拼前置、填路径；无扩展名）
├── scripts/harness-upgrade   # kit 侧只读升级：--check（版本/漂移）与 --plan（三方 diff）；无 --apply（无扩展名）
├── scripts/harness-skill     # kit 侧入口 skill：install/check/list/uninstall（--scope user/project；无扩展名）
├── skills/harness/           # 单入口 SKILL.md + references/（10 个按场景 playbook，含 feedback；随 harness-skill 安装；v0.5.0 起文档默认入口）
├── prompts/                  # 提示词单源（2 前置 + 20 场景 + 2 附加片段；front matter 契约见 §9）
├── .github/
│   ├── workflows/verify.yml            # 镜像仓 CI：kit 自身测试
│   └── ISSUE_TEMPLATE/kit-feedback.yml # v0.5.2+：宿主问题反馈 issue 表单（随镜像发布）
├── docs/adoption.md          # 接入与日常使用（skill 优先 + 场景路由 + 手动/兜底 + 前后评分）
├── docs/agent-prompts.md     # 由 prompts/ 生成的提示词库（勿手改；render --check 防漂移）
├── docs/playbook.md          # 五步改造法 + 存量项目七步法 + 常见坑 + 升级路径
├── docs/governance.md        # 演化与治理（反臃肿、版本策略、多人协作）
├── docs/why.md               # 定位/卖点/边界（与 Claude Code 自管的关系）
├── docs/cases/fcnsystem-adoption.md  # 真实案例：存量接入反馈 K01–K17 与 v0.5.2 反哺
└── tests/                    # kit 自身的 unittest（仅标准库）
```

## 2. 目标项目产物（init 后）

```
<target>/
├── AGENTS.md                         # 根指令（rendered）
├── HARNESS.md                        # standard/strict：系统地图（rendered）
├── CONTRIBUTING.md                   # standard/strict：环境/验证/PR（rendered）
├── Makefile 或 Makefile.harness      # 见 §5
├── .harness-manifest.json            # v0.2.13+：kit 管理面基线（kitVersion/profile/options/files/append hashes）
├── docs/README.md, docs/AGENTS.md    # rendered
├── references/{contracts,verification,workflow}.md
├── harness/
│   ├── config.json                   # 目标项目配置（工具唯一读取源）
│   ├── requirements/_template.md     # standard+：需求卡模板（harness.py intake 读取）
│   ├── README.md, AGENTS.md
│   ├── plans/_template.md
│   ├── plans/_adoption.md            # 可选：harness-adopt --write-plan 生成的改造计划草稿
│   ├── evidence/{schema.json,TEMPLATE.json,README.md}
│   ├── test-baseline.json            # standard/strict
│   └── reviews/…                     # strict
├── tools/*.py                        # 按 profile 复制；standard+ 另含 check_hygiene.py / check_layers.py
├── tools/harness.py                  # v0.3.0+：统一入口（status / start / verify / handoff；所有 profile）
├── .gitignore                        # append 块
├── .githooks/pre-push                # standard/strict（可选初始化）
├── .github/workflows/verify.yml      # standard/strict（可选初始化）
├── .gitattributes                    # 可选（--adapters gitattributes）：export-ignore 发布排除块（append）
├── .dsh/skills/harness/              # 可选：入口 skill 项目级安装（harness-skill --scope project）；用户级装在 ~/.agents/skills/harness
└── .claude/…                         # strict + claude-code adapter（可选初始化）
```

## 3. `harness/config.json`（目标项目配置）

> v0.4.0 可选段：`claims[].required`（默认 true）/`environment`/`floorByEnvironment`、
> `scorecard.maxAgeDays|maxCommits`、`harden.maxSkippedRange`、`waiver.maxDays|exceptionMaxDays`、
> `layers.exclude`；JSON Schema 见 `core/config.schema.json`。

由 `core/templates/harness/config.json.template` 渲染生成，**所有 core 脚本只读这一份配置**（不接受硬编码路径）。字段：

```json
{
  "kitVersion": "0.5.2",
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
    "nestedMaxTokens": 1000,
    "budgets": { "AGENTS.md": 1200, "references/contracts.md": 700, "references/verification.md": 700, "references/workflow.md": 700, "docs/README.md": 1000, "HARNESS.md": 1500 },
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
      "requireArtifact": true, "command": "{{TEST_COMMAND}}" },
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
- `instructions.nestedMaxTokens`（v0.5.2+，可选）：嵌套 AGENTS 的 token 上限；模板默认 1000，未配置时只查 `nestedMaxBytes`（向后兼容）。
- `budgets` 中的 `HARNESS.md` 只由 standard/strict 模板渲染（minimal 无该文件，故不登记，避免“登记文件不存在”误报）。
- 可选段：`hygiene` / `layers`（宿主按需添加，模板默认不生成；字段契约见 §4，`core/config.schema.json` 中 `additionalProperties: true`）。
- 路径一律相对目标项目根；不接受绝对路径。

## 4. 脚本 CLI 契约（宿主 `tools/`；kit 侧 `scripts/*` 例外，见本节末）

| 脚本 | 用法 | 输出/语义 |
| --- | --- | --- |
| `token_estimate.py` | import 用：`estimate_tokens(text) -> int` | v2 估算：CJK/全角=1，ASCII=1/4 |
| `check_docs.py` | `python3 tools/check_docs.py [--root PATH]` | a) `paths.rootDocs` 必须存在；b) `docs.rootMarkdownAllowed` 中**实际存在**的根 md 也检查（不强制存在）；c) 链接/围栏/docs 索引/公开白名单/上限/token 预算（逐文件输出 used/budget/remain）；`[OK]/[FAIL]`，exit 1。空 docs 索引只有 README 视为通过 |
| `check_agents.py` | 同上 | 根/嵌套 AGENTS 存在与字节上限、`nestedMaxTokens` token 上限（可选）、token 预算（逐文件输出 used/budget/remain）、敏感串扫描、`§N`/`第 N 节` 引用解析（目标标题存在）；exit 1 |
| `check_plan.py` | `python3 tools/check_plan.py [check\|new TOPIC\|brief] [--lenient-uncommitted\|--strict] [--root PATH]` | 计划 front matter（status/level/owner/updated/scope.allow/acceptance/verify）、唯一 active、必填节、验证证据表（命令/结果/环境/证据ID）、evidence id 必须存在且 PASS、done 必须有 `submitted` 且证据 commit 绑定、未提交改动与 `git status` 一致；**v0.4：submitted 每个 commit 按提交时点 scope 审计（merge 只与第一父比较）**；`_archive/*.md` 也扫描，`status` 非 done/archived 硬 FAIL；done「未验证项」需「未验证豁免」表逐条覆盖（理由≥5 字、到期≤`waiver.maxDays`）；`--strict` 把归档计划的 error 级问题升 FAIL（仅 warn 时头行标 WARN、不阻断）；exit 1 |
| `harness.py` | `python3 tools/harness.py {status\|start\|intake\|verify\|release\|handoff\|plan check\|upgrade} [--json] [--scope P …] [--claims-strict]` | v0.3.0+ 目标侧统一入口：`status` 只读一屏状态 + 建议下一步（`--json`）；**无 active 时回读最近归档计划（lastPlan，注明归档快照/归档后新增 PASS 证据）**；`start` 幂等建计划；`verify` 同步未提交段 → `make verify-static` → `check_plan.py check --strict` → `verify_claim --all` 摘要；`handoff` 无 active 时输出归档回读；`release` fresh 证据；`plan check`；`upgrade` 指引。exit：0 通过 / 1 门禁或计划失败 / 2 用法或能力缺失 |
| `harness-skill`（kit 侧） | `python3 harness-kit/scripts/harness-skill [--target PATH] {install\|check\|list\|uninstall} [--scope project\|user] [--agent dsh,agents,claude-code] [--force] [--dry-run] [--json]` | 把 `skills/harness/` 渲染到 `--scope project`（`<target>/.dsh/skills`、`.agents/skills`、`.claude/skills`，manifest 记录）或 `--scope user`（`~/.agents/skills`、`$DSH_HOME/skills`、`~/.claude/skills`，元数据 `~/.agents/skills/.harness-kit-skill.json` 记录 kitRoot/version/hashes，不入库）；check 漂移 exit 1、未安装 exit 2；uninstall 默认拒绝删除有本地修改的目录（`--force` 才行）。**v0.5.0 起文档默认入口是 `--scope user` 一次安装（v0.5.1 起默认同时写 `~/.agents/skills` 与 `~/.claude/skills`）；行为级 A/B 后置。** |
| `evidence.py` | `python3 tools/evidence.py {ls\|validate\|write} [--claim NAME …] [--allow-untracked-under PATH …] [--root PATH]` | 读写 `harness/evidence/<UTC>-<claim>.json`（schema 见 `harness/evidence/schema.json`）；自动填 `git.commit/dirty`；`write` 要求 clean tree，但**证据目录下的未跟踪/已修改文件默认豁免**（只 WARN；其他目录用 `--allow-untracked-under`，错误信息给 `git add` 解法，v0.5.2 修首次证据死锁）；`validate` 对 > 3KB 的证据文件输出 `[WARN]`（不阻断，汇总显示 warn 数） |
| `verify_claim.py` | `python3 tools/verify_claim.py --all [--fresh] [--strict] [--allow-untracked] [--root PATH]` | 三值：`CLAIM <id>: PASS|FAIL|UNVERIFIED — reason`；聚合 exit：任一 FAIL→1，否则任一 UNVERIFIED→2，全 PASS→0。test-count 的 PASS 复核：`git.commit` 可解析且为 HEAD 祖先、`git.dirty=false`；`result.artifacts`（或 legacy `result.xcresultPath`）必须存在，JUnit XML 从 XML 独立重算 passed/failed/skipped 且与自报值一致，缺 artifact / 只有非 XML artifact → UNVERIFIED；`claim.requireArtifact` 缺省 **true**（显式 false 为 legacy opt-out，原因标注“未重算”）。**v0.4：递归扫描证据并分类 `_archive`（输出 SUPERSEDED、不参与聚合）；当前证据与 artifact 必须 git tracked（未跟踪 PASS→UNVERIFIED，`--strict` 下 `--allow-untracked` 无效）；必需 claim（`required` 默认 true）缺当前证据→UNVERIFIED；归档 FAIL/UNVERIFIED 必须有当前 PASS 证据 `supersedes` 合法接管；claim `environment`/`floorByEnvironment` 不匹配→UNVERIFIED；`expectedSkipped` 支持 int/区间/byEnvironment 且区间宽度受 `harden.maxSkippedRange` 限制；static claim 不做 freshness 判定**；`--fresh` 按 config.freshness 比较证据 commit 与工作树（evidence/plans/reviews 过程目录不计入）；`--strict` 时 STALE→UNVERIFIED |
| `scorecard.py` | `python3 tools/scorecard.py [--generate] [--check-stale] [--strict] [--json] [--root PATH]` | standard+：`--generate` 跑门禁快照并写 `harness/reviews/<UTC-date>-scorecard.md`（checkedAt/commit/证据 ID/测试与文档计数/五子系统自评+独立复评 TBD，**不自动打分**）；`--check-stale` 对缺失/超 30 天/超 50 commits/commit 非 HEAD 祖先 WARN，`--strict` exit 1；`--json` 供测试 |
| `doctor.py` | `python3 tools/doctor.py [--root PATH]` | OK/WARN/FAIL/SKIP：python3、git 仓库、config.commands.test 可执行性、可选适配器；缺必需项 exit 2，否则 0 |
| `adapters.py` | `python3 tools/adapters.py {sync\|check} [--root PATH]` | `.dsh/skills` 单源 → `.claude/skills` 生成/哈希比对；exit 1 |
| `evidence_from_junit.py` | `python3 tools/evidence_from_junit.py --xml GLOB [--xml GLOB …] --claim NAME --command CMD [--environment KEY=VALUE …] [--notes TEXT] [--output PATH] [--keep-raw] [--allow-outside-root] [--artifacts-dir PATH] [--root PATH]` | standard+：聚合 JUnit XML 为 `evidence.py write --from-json` 可接受的 JSON；`passed = tests − failures − errors − skipped`；**v0.4 默认脱敏并复制**：删除 system-out/err、hostname、敏感 property，failure/error `message/type` 与 testcase `classname/file`/文本做仓库根相对化/`$HOME` 替换；写 `<evidence>/artifacts/<UTC>-<n>-<name>.xml`（原子写、重名追加、5 MiB 上限、拒绝 symlink）；脱敏后重算 counts 不一致 exit 2；`--keep-raw` 为显式逃生口（仓库外输入另需 `--allow-outside-root`，产出可能被判 UNVERIFIED）；`--xml` 缺失/解析失败 exit 2，缺 `--command` exit 2 |
| `check_hygiene.py` | `python3 tools/check_hygiene.py [--root PATH]` | standard+：读 `harness/config.json` 的**可选** `hygiene` 段（缺失 → `[SKIP]` exit 0）。字段：`trackedArtifactGlobs`（被跟踪构建产物 glob）、`rootAllowlist`（根目录文件白名单）、`localPathPatterns`（本机路径；以 `/` 开头且以 `/` 结尾的目录型条目按字面前缀 + 标识符边界匹配，避免 `features/home/` 误报；其他条目按正则解析）、`skipLocalPathScan`（前缀跳过）、`maxTrackedFileBytes`、`forbidAbsoluteSymlinks`（默认 true）。检查 `git ls-files` 的构建产物 / 根文件白名单（仅配置了 `rootAllowlist` 时生效）/ 绝对符号链接（mode `120000` 且 `cat-file` 目标以 `/` 开头）/ 跟踪文本文件中的本机路径 / 超大跟踪文件；`[OK]/[FAIL]`，违规 exit 1；非 git 仓库 → SKIP exit 0 |
| `check_layers.py` | `python3 tools/check_layers.py [--root PATH] [--strict] [--verbose]` | standard+：读可选 `layers` 段（缺失 → `[SKIP]` exit 0）。字段：`sourceRoot`、`extensions`、`rules`、`symbolGuards`、`exclude`（路径前缀/glob）。**v0.4 文件发现 = `git ls-files` + `git ls-files --others --exclude-standard`**（同过滤），默认排除 `.git/.venv/venv/node_modules/build/dist/__pycache__/...`；输出 tracked/untracked 与每规则 `eligible/matched/violations`；规则/守卫 0 匹配 WARN，`--strict` 升 FAIL；未跟踪源文件违规同样 FAIL；违规输出 `file:rule`，exit 1。语义：eligible=扫描源文件数；matched=pathPrefix 命中文件数；coverage=matched/eligible |

通用约定：脚本自行 `Path(__file__).resolve().parent.parent` 定位根，或 `--root` 覆盖；不要读取 kit 源目录；不写目标项目之外的文件（tempfile 除外）；不联网。

kit 侧脚本（**不复制到宿主**）：`python3 harness-kit/scripts/harness-adopt --target PATH [--report PATH] [--json] [--write-plan] [--root KIT_ROOT]`。默认**只读盘点**（0 写入 target）；`--report` 写 Markdown 报告、`--json` 输出机器可读 JSON、`--write-plan` 渲染 `core/templates/harness/plans/_adoption.md.template` 到 `<target>/harness/plans/<DATE>-adopt-harness.md`（要求该目录已存在，否则 exit 1；模板缺失/未知占位符给可读错误；目标文件已存在则拒绝覆盖）。盘点内容：概览（git/语言/构建/既有门禁）、文档（索引缺口/断链/疑似过期；v0.5.2 起「磁盘存在」即算有索引并区分是否跟踪）、卫生（被跟踪产物/绝对符号链接/本机路径/大文件/按语言判定的 `.gitignore` 缺失项）、**v0.5.2 接入诊断**（根 AGENTS tokens vs 默认预算 + 推荐 `--agents-mode`、当前分支 vs 默认分支 `origin/HEAD`、测试命令「可执行探测」只跑 `--version` 并标 `smoke=not-run`）、建议 profile 与下一步（含带入 init 的 flags）、**v0.5.2 起反馈入口**（报告末尾与 JSON `feedback` 字段：镜像仓 issue 地址 + 必附信息）。exit 0=盘点完成；1=用法错误、目标不存在或 `--write-plan` 前置不满足。

kit 侧升级工具（**不复制到宿主**）：`python3 harness-kit/scripts/harness-upgrade --target PATH {--check|--plan} [--json] [--fail-on-conflict] [--profile P] [--name N] [--language L] [--test-command CMD] [--adapters LIST] [--root KIT_ROOT]`。**只读，不写目标仓**：`--check` 对比 `.harness-manifest.json`、目标文件 sha256 与 kit `VERSION`，exit 0=in sync / 1=本地漂移 / 3=版本不符（manifest 或 config.kitVersion）/ 2=用法或 manifest 非法；`--plan` 按 manifest 的 profile/options（legacy 可用 `--profile` 等覆盖）在临时目录运行 `harness-init` 重渲染新版，输出 SAME/LOCAL_ONLY/UPGRADE/ALREADY/CONFLICT/ADD/OBSOLETE/NOT_MANAGED/APPEND 表，`--fail-on-conflict` 时 CONFLICT→exit 1；`--apply` 未实现（exit 2，v0.4）。legacy 目标（无 manifest）`--check` exit 2 提示手工路径，`--plan` 可预览。

kit 侧门禁自测（**不复制到宿主**）：`python3 harness-kit/scripts/harness-selftest --target PATH [--keep] [--json]`。`--target` 必须是 git 仓库且工作树干净；脚本 `git clone -q` 到临时目录，先跑 baseline `make check`（baseline 红 → 报告后 exit 2，清理退出），再逐项注入并断言对应门禁**非 0**：M1 新增未登记 `docs/__selftest__.md`（`check_docs.py`）、M2 `docs/README.md` 追加断链（`check_docs.py`）、M3 根目录新增未白名单 md（`check_docs.py`）、M4 `AGENTS.md` 追加超预算文本（`check_agents.py`）、M5 `AGENTS.md` 追加本机路径（`check_agents.py`）、M6 若存在 active 计划则复制出第二个 active；无 active 但有归档计划时用归档计划造两个 active fixture（均断言输出含「同时存在 2 个 active」；两者都无才 SKIP）、M7 若存在证据 JSON 则临时移走后 `verify_claim.py --all` 期望非 0、M8 若配置了 `hygiene` 段则在跟踪文件追加本机路径（`check_hygiene.py`）、M9 若存在 `requireArtifact=true` 的 test-count 证据则伪造 PASS（HEAD commit、虚报 counts、无 artifact），期望 `verify_claim.py --all` 非 0。每项注入后 `git checkout -- .` 并删除新增文件恢复；最后再跑一次 `make check` 复核为 0。输出 `mutation | gate | 注入 exit | 期望 | PASS/FAIL` 表：全部符合 exit 0，任一不符 exit 1，target 脏或 baseline 红 exit 2；`--json` 含 `summary.notApplicable`；汇总注明 **SKIP ≠ PASS**（不适用项单列）；默认清理临时目录，`--keep` 保留并打印路径；**默认不写 `--target` 仓库**。

空状态语义（新接入项目必须能一次通过）：`harness/plans/` 无计划、`harness/evidence/` 无证据、`docs/` 只有 README、`.dsh/skills/` 不存在，均视为 **OK（带提示）**，不得因此 FAIL。

## 5. Makefile 与 profile 分层

`init` 的 Makefile 规则：

- 目标没有 `Makefile` → 写入 `Makefile`（对应 profile 模板）。
- 目标已有 `Makefile` → 写 `Makefile.harness`（同名模板），并打印「在 Makefile 末尾加 `include Makefile.harness`」；**不覆盖**已有 Makefile。

各 profile 的 target：

| profile | files / tools | Makefile targets |
| --- | --- | --- |
| minimal | AGENTS + docs IA + 3 references + harness/{README,AGENTS,config} + `token_estimate` `check_docs` `check_agents` `harness` | `status`、`verify`（harness.py verify）、`check`（docs+agents）、`verify-static`（=check） |
| standard | minimal + plans/evidence/test-baseline + requirements 模板 + `check_plan` `evidence` `verify_claim` `evidence_from_junit` `check_hygiene` `check_layers` **`scorecard` `harness_selftest`** + 评分卡模板 + HARNESS/CONTRIBUTING + githooks/CI（可选） | `status`、`start TOPIC= [GOAL= SCOPE=]`、`verify`、`handoff`、`check`（docs+agents+plan；`check_plan --lenient-uncommitted`；**`scorecard --check-stale` 只 WARN**）、`check-plan-strict`（`check_plan check --strict`）、`verify-static`（check + check-plan-strict + check-host + check-evidence；**不含证据三值判定**，末尾打 `[INFO]` 提示）、`check-host`（`check_hygiene` + `check_layers`，缺配置 SKIP）、`verify-claim`、**`verify-all`（= verify-static + verify-claim，完成声明/PR 前推荐）**、`release`（harness.py release --check）、`plan TOPIC=`、**`selftest`（`tools/harness_selftest --target .`）、`upgrade-check`（需 `KIT_ROOT`）、`scorecard`（`tools/scorecard.py --generate`）** |
| strict | standard + doctor/adapters + reviews/red-team skill + adapters（可选；评分卡继承 standard） | 以上（`verify-static` 含 `check-host` + `check-plan-strict`）+ `release-check`（verify-static + **`scorecard --check-stale --strict`** + `verify_claim --fresh --strict`）、`doctor`、`adapters-sync/check` |

`check-host` 在 standard/strict 的 Makefile 中定义为 `python3 tools/check_hygiene.py` + `python3 tools/check_layers.py`，`verify-static` 依赖它；两个脚本读 `harness/config.json` 的**可选** `hygiene` / `layers` 段，未配置时 SKIP，空白项目 init 后 `make check` 仍应通过。

注意：`docs/README.md.template` 是 minimal 索引（只能列 minimal 存在的文件）；standard 用 `core/templates/docs/README.standard.md.template` 覆盖 `docs/README.md` 并登记 `harness-scorecard.md`；strict 用 `core/templates/docs/README.strict.md.template` 再覆盖一次（profile 合并按 `dst` 覆盖）。

## 6. 模板占位符（渲染时替换；未知占位符必须报错而不是留空）

`{{PROJECT_NAME}}` `{{PROJECT_LANGUAGE}}` `{{TEST_COMMAND}}` `{{CHECK_COMMAND}}` `{{VERIFY_COMMAND}}` `{{KIT_VERSION}}` `{{YEAR}}` `{{DOCS_DIR}}` `{{REFERENCES_DIR}}` `{{HARNESS_DIR}}` `{{ROOT_AGENTS}}` `{{DEFAULT_BRANCH}}` `{{DATE}}` `{{HARNESS_BUDGET}}` `{{GITIGNORE_LANGUAGE_LINES}}`

`{{HARNESS_BUDGET}}` 由 `harness-init` 按 profile 注入（standard/strict 生成 `HARNESS.md` 预算项，minimal 为空），仅 config 模板使用；它是 **JSON 片段**，渲染时不做 JSON 字符串转义。
`{{GITIGNORE_LANGUAGE_LINES}}` 由 `harness-init` 按 `--language` 注入（node→`node_modules/`、python→`.pytest_cache/`+`.venv/`、swift→`.build/`+`.swiftpm/`、android→`.gradle/`+`local.properties`、其他为空；`__pycache__/`/`*.pyc` 始终保留），仅 `.gitignore` 追加模板使用。

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
  "makeTargets": ["check", "verify-static", "verify-claim", "verify-all"],
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
  [--test-command "make test"] [--adapters dsh,claude-code,ci,githooks,gitattributes] \
  [--default-branch BRANCH] [--agents-mode replace|keep|move] \
  [--agents-archive-path docs/legacy-agents.md] [--install-hooks] \
  [--dry-run] [--force] [--no-check] [--backup-dir PATH] [--root KIT_ROOT]
```

行为：

1. 校验 `--profile` 存在、manifest schema 合法、所有 `src` 存在、目标目录存在（否则报错）。
2. 探测/推断：语言（`settings.gradle|settings.gradle.kts|build.gradle|build.gradle.kts`→android（**优先判定**，避免混合仓被误判为 python）；`Package.swift` / `*.xcodeproj`→swift；`package.json`→node；`pyproject.toml|setup.py|requirements.txt|*.py`→python；`go.mod`→go；否则 other）；`--test-command` 缺省按语言/工具链推断并打印来源提示：android（`./gradlew testDebugUnitTest`；JDK 17–21 与 wrapper 版本由项目固定，wrapper 路径/NDK/多模块边界由项目自管，kit 不代跑、不解析输出）、node（有 `scripts.test`→`npm test`，否则 `node --test`）、swift（`Package.swift`→`swift test`；`*.xcodeproj`→提示必须用 `--test-command` 显式给 `xcodebuild test -scheme …`）、其他→`make test`。kit 不解析测试输出，计数由宿主写入 evidence（结构化 JUnit XML 可用 `tools/evidence_from_junit.py` 聚合后交给 `evidence.py`）。
3. 冲突：目标已有同名文件 → 默认 `fail` 并列出；**冲突预检在任何移动/写入之前完成**（避免 `--agents-mode move` 的半改造状态）；`--force` 时把被覆盖文件备份到 `<target>/.harness-init-backup/<UTC>/` 后写入。
4. `--dry-run`：只打印 `CREATE / SKIP / CONFLICT / RENDER / APPEND / MOVE` 计划，不写文件、不跑 check。
   `.gitignore` 追加块只包含通用项（`harness/runs/`、`.harness-init-backup/`、`__pycache__/`、`*.pyc`）+ `--language` 对应条目（node→`node_modules/`、python→`.pytest_cache/`+`.venv/`、swift→`.build/`+`.swiftpm/`、android→`.gradle/`+`local.properties`），并对目标文件已有行去重；保证测试后的 clean tree 可用于写证据。
   JSON 语义：渲染 `.json` 目标时，占位符值按 JSON 字符串转义（`json.dumps`），渲染后 `json.loads` 回读校验，非法即 `ERROR` 且不写文件（K01）。
   默认分支：`--default-branch` 优先；否则 `refs/remotes/origin/HEAD` → `init.defaultBranch` → 当前分支 → `main`（K05）；结果写入 CI 模板与 manifest `options.branch/branchSource`。
5. 存量指令：`--agents-mode replace`（默认；已有 AGENTS.md 时按冲突处理）/ `keep`（保留现有文件、记入 manifest `skipped`，预算门禁可能红）/ `move`（`git mv AGENTS.md <archive>`，保留历史；随后渲染模板，并登记 `config.docs.publicWhitelist` 与 `docs/README.md` 索引；归档路径默认 `docs/legacy-agents.md`）。
6. `--install-hooks`：写入后对 git 仓执行 `git config --local core.hooksPath .githooks`（生成的 pre-push 才真正生效）；未指定且 `.githooks/pre-push` 存在但未配置时打印 WARN（K10）。
7. 写完打印「下一步」（v0.5.2 起含 kit 问题反馈入口：镜像仓 issue + 必附信息）；非 `--no-check` 时在目标目录执行 `make check`（或按 profile 的命令链），透传退出码。manifest `options` 记录 `branch/branchSource/agentsMode/hooksPath`。
8. 幂等：重复 init（无 `--force`）应报冲突而不是重复追加；`gitignore.append` 需去重。
9. 安全：不打印/写入密钥；不访问网络；不修改 git 历史（`--agents-mode move` 的 `git mv` 只移动工作树 + index）。

## 9. 测试契约（`harness-kit/tests/`）

- 全部 `unittest` + 标准库；命令行方式跑：`python3 -m unittest discover -s harness-kit/tests -q`（从仓库根）或 `cd harness-kit && python3 -m unittest discover -s tests -q`。
- 必须覆盖：
  - `test_kit_profiles.py`（Lead）：每个 profile 在 tmp 空白 git 仓 init 后：`make check` exit 0 且输出逐文件 token 用量（`（余 `）且根 `AGENTS.md` 含反馈入口（v0.5.2）；init summary 含反馈步骤；standard/strict 的 `make verify-static` exit 0 且输出「不含证据三值判定」提示，`make verify-all` 在无证据时非 0；渲染的 config：`docs/README.md` 预算恒有、`HARNESS.md` 预算仅 standard/strict 有、`nestedMaxTokens=1000`；**v0.5.2 接入反馈回归**：含引号/反斜杠的 `--test-command` 渲染为合法 JSON 且原样保留、`.gitignore` 按语言且去重、`--default-branch` 写 CI/manifest、`--install-hooks` 设 `core.hooksPath`、`--agents-mode move` 保留历史 + 登记白名单/索引、`keep` 不覆盖并记 skipped、其他冲突时在移动前失败；`--adapters gitattributes` 生成 `.gitattributes` export-ignore 块、重复 init 幂等、`git archive` 实际排除 `harness/`/`tools/`（tar 解析断言）；证据链端到端（JUnit XML artifact → evidence write → verify_claim / strict release-check PASS）；dry-run 不写文件；冲突报错；`--force` 产生备份；无残留 `{{`；Android 推断：tmp 放 `settings.gradle.kts` 时 `--dry-run` 推断 `language=android`、建议 `./gradlew testDebugUnitTest` 并打印 Gradle 边界提示。
  - `test_kit_prompts.py`（Lead）：`prompts/*.md` front matter 完整、id 等于文件名、number 唯一、占位符声明与正文一致；`render --check` 与 `docs/agent-prompts.md` 同步（漂移 / 未声明占位符负向 exit 1）；`list/show/copy` 按场景自动拼前置（0A/0B）、目标阶段不符与 kit 目录 target 给 WARN、替换 kit 与目标绝对路径、缺失占位符与残留尖括号提示、无剪贴板回退、addon 不拼前置；**v0.5.2 反馈场景**：`stage: both` 不拼前置、不因目标未接入/已接入给阶段 WARN，`feedback` 出现在 `list --stage both`、§21 场景表与生成文档中，`render` 的 §21 表覆盖编号 > 21 的 task 场景。
  - `test_kit_hygiene.py`（Lead）：`core/` `adapters/` `profiles/` `scripts/` `prompts/` 中不得出现 `Duiyi|duiyi|对译|TranslationSession|SwiftData|DuiyiTests`（仅 `harness-kit/README.md` 的来源一节允许一次）；kit 顶层文档相对链接可解析；`VERSION`/profiles 结构一致；README/SPEC 中的版本引用与 `VERSION` 一致；模板预算常量（1200/700/1000/1500）与 README/governance 的预算说明一致；`profiles/*.json` 与 `adapters/manifest.json` 引用的 src 文件都存在；**v0.5.2 反馈通道**：宿主可见的反馈入口（README/SPEC/adoption/skill/feedback/prompt/init/adopt/AGENTS 模板）指向同一公开 issue 地址，镜像仓 `.github/ISSUE_TEMPLATE/kit-feedback.yml` 存在且含必附字段。
  - `test_harness_adopt.py`（gates）：tmp git fixture（断链/未登记文档/根 `NOTES.md`/被跟踪构建产物/绝对符号链接/本机路径）上 `scripts/harness-adopt` 的报告命中、默认 0 写入、`--json` 键、`--write-plan` 在存在 `harness/plans/` 时渲染计划、非法 target exit 1；**v0.5.2 回归**：探测只称「可执行探测」且 `testCommandSmoke=not-run`、AGENTS 超预算推荐 `--agents-mode move`、默认分支漂移给 `--default-branch`、未跟踪 docs 索引算存在、按语言的 gitignore 期望、tsx 项目建议 `tsx --test`（`ERR_MODULE_NOT_FOUND` 提示）、报告末尾「## 反馈 kit 问题」与 JSON `feedback` 入口；不依赖网络/Xcode。
  - `test_evidence_junit.py`（gates）：JUnit XML 单/多 suite、`failures`/`errors`/`skipped` 计数、duration 聚合、malformed/missing exit 2、`--output` 必需键（`passed = tests − failures − errors − skipped`）。
  - `test_kit_host_tools.py`（gates）：tmp git fixture + `harness/config.json`；`check_hygiene.py` 覆盖被跟踪构建产物 / 根文件白名单 / 绝对符号链接 / 本机路径四类违规与正常情况、缺 `hygiene` 段 SKIP；`check_layers.py` 覆盖违规 import / `allowedImports` 覆盖 / `symbolGuards`、缺 `layers` 段 SKIP；≥8 用例。
  - `test_harness_upgrade.py`（state）：`harness-init` 写 manifest（schema/kitVersion/profile/options/文件 sha256/append 块/skipped；dry-run 不写）；`harness-upgrade --check` 的 in sync（0）、本地漂移（1）、config.kitVersion 伪造（3）、append 块缺失（1）、legacy 无 manifest（2）；`--plan` 的 SAME/LOCAL_ONLY/UPGRADE/CONFLICT/ADD/OBSOLETE 分类、legacy 预览、`--fail-on-conflict`、只读（git status 不变）、`--json` 契约、`--apply` exit 2。
  - `test_harness_cli.py`（state）：`tools/harness.py` 的 status（无计划/JSON/只读；**v0.5.2：hooks 未安装告警、manifest 分支漂移告警**）、start（幂等、owner/scope 自动填充、建完 `make check` exit 0）、intake（需求卡→计划 / 模糊判据拒绝且不建计划）、verify（同步「未提交改动」+ `== verify: PASS ==`）、release（无证据 exit 2 / fresh 可重算证据 PASS）、handoff（`--json` 契约）、plan check（默认宽松）、upgrade 指引（`--apply` exit 2）、minimal profile（status 可用、start exit 2）；`check_plan.py check --lenient-uncommitted` 的 WARN 负向用例。
  - `test_harness_skill.py`（state）：`scripts/harness-skill install/check/list/uninstall`（单/双 agent、manifest 记录、漂移检测、冲突/--force、dry-run、legacy 无 manifest、未安装 exit 2、`--scope user` 元数据/隔离环境/卸载、`.agents` 目标、删除保护）；SKILL.md front matter / ≤120 行 / references ≥6 且总行 ≤1200；**v0.5.2**：SKILL.md 路由与硬约束含 `feedback`，`references/feedback.md` 含上游 issue 与「对外先问」。
  - `test_harness_selftest.py`（gates）：`harness-init --profile standard` 生成临时宿主 + git commit；正常 target → `scripts/harness-selftest` exit 0 且输出含 mutation 行；条件宿主（active 计划 + 证据 + hygiene）→ M6/M7/M8/M9 均被执行；target 脏 → exit 2；baseline 红（预先提交未登记 docs）→ exit 2。
  - `test_core_evidence_chain_v04.py`（v0.4）：证据归档 SUPERSEDED/必需 claim/未跟踪证据与 artifact/`supersedes` 接管/environment/`floorByEnvironment`/skipped 区间与宽度/static freshness。
  - `test_kit_scorecard_v04.py`（v0.4）：scorecard 生成、过期与 `--strict`、缺文件行为。
  - `test_core_plan_evidence_claim.py`（state）：check_plan/evidence/verify_claim 的通过、失败、三值、freshness、done/submitted 负向；**v0.5.2 回归**：`- dir/：中文说明` 路径解析、rename 只审目标且普通删除仍拦截、证据写入豁免证据目录/`--allow-untracked-under`、非 ASCII 路径 freshness 命中；伪造 PASS 证据（0 测试 / 虚报 counts / 无 artifact）必须被拒；artifact 重算不一致 → FAIL；commit 非祖先 / 不存在、dirty PASS → FAIL；JUnit XML 重算一致 → PASS；legacy `requireArtifact=false` → 原因标注“未重算”；check_plan 对无扩展名根文件（`Makefile`/`GNUmakefile`/`Dockerfile`/`LICENSE`/`NOTICE`）的未提交改动声明：声明 → PASS，不声明 → FAIL；归档计划 strict 下仅 WARN 时头行必须是 `[WARN]`（不得误标 `[FAIL]`）；证据 > 3KB 时 `validate` 输出 WARN 且 exit 0。
  - `test_core_docs_agents_doctor.py`（gates）：check_docs/check_agents/doctor 的链接/围栏/预算（逐文件 used/budget/remain + 超预算）/§ 引用/敏感串/exit code；`nestedMaxTokens` 缺省兼容、超限失败、用量输出；`doctor --agent` 只读输出 Agent/CLI/skill 根/manifest。
- 测试禁止依赖本机 Xcode/真机/网络；临时目录用 `tempfile.TemporaryDirectory`。

## 10. 版本与迁移

- `KIT_VERSION` 单一来源 `harness-kit/VERSION`（kit 自身）与目标项目 `harness/config.json.kitVersion`。
- 向后兼容：新增 config 字段必须可选；破坏性变更需在 README 的 changelog 记录。
- 仓库改名：`harness-kit` → `harness-engineering-kit`（2026-11-10，GitHub 301 重定向；目录、命令、tag 前缀沿用短名 `harness-kit`）。
- v0.5.2：`check_plan --strict` 归档计划仅 WARN 时头行改 `[WARN]`；`check_docs`/`check_agents` 的 token 预算逐文件输出 used/budget/remain，模板预算纳入 `docs/README.md` 与 `HARNESS.md`（standard/strict），新增可选 `nestedMaxTokens`（默认 1000）；`evidence.py validate` 对 > 3KB 证据输出 WARN；修正 README/governance 与模板预算数值漂移；新增 opt-in 适配器 `gitattributes`（`--adapters gitattributes` 向 `.gitattributes` 追加 `export-ignore` 块，`git archive` / GitHub Source zip 排除 `/harness/`、`/tools/`、`/HARNESS.md`、`/.harness-manifest.json`），adoption 增加 git/npm/Docker/Python/Xcode 打包排除食谱。**fcnsystem 存量接入反馈（K01–K17）收口**：JSON 安全渲染 + 回读校验；证据目录豁免 + `--allow-untracked-under`；`AGENTS.md` 模板瘦身（约 1172→730 tokens）与 `--agents-mode replace|keep|move`；adopt 探测语义（`smoke=not-run`）与 AGENTS/默认分支/gitignore 诊断；默认分支 `origin/HEAD` 探测 + `--default-branch` + CI `pull_request` 不限分支；`verify-static` 未跑三值判定提示 + `verify-all`；`--install-hooks` + status 检查 `core.hooksPath`；`.gitignore` 按语言 + 去重；`check_plan` rename 配对审计与 `- dir/：说明` 解析；`verify_claim` 非 ASCII 路径 `-z`；`harness.py status` 分支/hooks 漂移告警；`verify-static` 描述对齐；**反馈通道**：入口 skill 新增 `feedback` 场景（`stage: both`，不拼 0A/0B；提示词库同步第 20 个场景）、根 `AGENTS.md`/init summary/adopt 报告与 JSON/`docs/adoption.md` §3.6/README 写明「kit 问题 → 公开镜像仓 issue（<https://github.com/DavidTeam2008/harness-engineering-kit/issues>；附版本/profile/命令/退出码/最小复现），不私改 kit 门禁」、镜像仓发布 `.github/ISSUE_TEMPLATE/kit-feedback.yml`。无破坏性变更（新 flags 可选、`gitignore` 内容变化只在 init 时发生，已接入仓升级需人工回写 Makefile/模板）。
- v0.5.0：入口改为 skill 优先（`harness-skill --scope user` 一次安装、任意仓库会话可见；`--scope project` 供团队 pin 版本），`uninstall`/`--scope` 与用户级元数据；`harness-adopt`/`harness-init`/`harness-prompt` 引导 skill 优先、提示词降级为兜底；SKILL.md 增加 kit 定位与版本地板（min_version），`references/adopt.md` 自足（不再依赖提示词）；门禁/`tools/`/config schema 无行为变更。行为级 A/B 后置（v0.5.x），未执行前不声称 skill 提升 Agent 表现。
- v0.4.0：接入反馈 15 项 + 红队 P0 收口（submitted 按提交时点 scope、归档计划审计/回读、证据与 artifact 入库、required claim、SUPERSEDED/接管、JUnit 默认脱敏、environment/floorByEnvironment、layers tracked+untracked、scorecard、Makefile selftest/upgrade-check/scorecard、`check-plan-strict --strict`）。升级前按 `docs/playbook.md` 迁移矩阵自检；新增证据/config 字段均为可选。
- v0.3.0：目标侧统一入口 `tools/harness.py`（status/start/intake/verify/release/handoff）；`check_plan.py check --lenient-uncommitted` 供日常 `make check`，严格校验由 `check-plan-strict`（verify-static/CI）承担；升级时需回写 Makefile 增加 `status/start/verify/release/handoff/check-plan-strict` 与 `harness/requirements/` 模板（旧仓不升级则行为不变）。router skill 是显式安装（`harness-skill`），不进入 init 默认产物。
- 升级：kit 不提供 in-place 迁移命令（设计决定，避免覆盖宿主文档）。v0.2.13 起提供 `.harness-manifest.json` 基线 + `scripts/harness-upgrade --check/--plan`（只读；`--apply` 未实现）：`--check` 判 in sync / 本地漂移 / 版本不符，`--plan` 给出三方 diff；人工按 plan 回写 kit 管理面后跑 `verify-static` + `harness-selftest`。该路径已由真实 Android/Gradle 存量仓 v0.2.2→v0.2.3 验证（2026-11-10），profile 升级与 `harness-upgrade` 在真实仓的完整演练仍未验证（v0.3.0 候选）。

# harness-kit v0.4.0 · 存量接入反馈收口方案（冻结稿）

> 输入：`barra/harness/reports/2026-11-11-harness-kit-feedback.md`（kit 0.3.0，standard 档，外部接入）
> 目标：修复报告 P0/P1/P2 共 15 项，把「可验证交付」从「门禁能跑」推进到「闭环可回读、绕过路径被封、接入体验一致」。
> 发布：v0.4.0（行为变更：更严的审计与默认脱敏；升级仓需按迁移清单自检）。
> 冻结日期：2026-11-11。实现前不改结论；实现中发现的偏差写 §8。

## 1. 决策

| 编号 | 决策 | 理由 |
| --- | --- | --- |
| V1 | 一次发布 v0.4.0，不拆 v0.3.x | 15 项互相咬合（证据 tracked/扫描、done/归档回读、scope 审计）；拆开发布验证成本高于收益 |
| V2 | `submitted` 越界默认 FAIL；归档计划降级 WARN 但仍输出 | 已提交越界是安全边界问题；历史归档不应阻断升级，但不能静默 |
| V3 | 证据文件默认要求 git 跟踪；未跟踪 PASS → UNVERIFIED | UNVERIFIED 不是「通过」，且保留本地写证据后未提交的可用性；`--allow-untracked` 仅作显式逃生口 |
| V4 | `_archive` 证据一律 `SUPERSEDED`，不参与三值聚合，但必须列出 | 移动文件不能变绿；审计链保留 |
| V5 | JUnit 默认脱敏并复制进仓库；`--keep-raw` 显式退出 | 隐私/可复核优先；保留旧行为逃生口 |
| V6 | 测试环境声明不满足 → UNVERIFIED（不是 FAIL，也不是 PASS） | 环境缺失不等于代码回归 |
| V7 | standard 默认；strict 只能显式选择并给理由 | 统一 adopt/playbook/prompt 三处口径 |
| V8 | layers 优先 `git ls-files`；0 匹配规则 WARN | 传感器覆盖范围必须可见；WARN 不阻断接入 |
| V9 | done 未验证项必须清零，或有「未验证豁免」表（理由/负责人/到期日） | 交接最需要知道「哪些还没验证」 |
| V10 | status/handoff 无 active 计划时回读最近归档计划 | 冷启动不能失忆 |
| V11 | selftest M6 无 active 时用归档计划造两个 active fixture；无归档才 SKIP，且 SKIP≠PASS | 矩阵可比较，不静默降级 |
| V12 | scorecard 进 standard；`make scorecard` 生成草稿，`check` 对过期只 WARN | 自评可追溯，不把自评当认证 |

## 2. 工作流与写作用域（互不重叠）

- **E（evidence）**：`core/tools/verify_claim.py`、`core/tools/evidence_from_junit.py`、`core/templates/harness/evidence/{schema.json,README.md.template,TEMPLATE.json}`、`tests/test_evidence_junit.py`、新增 `tests/test_core_evidence_chain_v04.py`
- **O（onboarding）**：`scripts/harness-adopt`、`scripts/harness-init`、`scripts/harness-prompt`、`core/tools/check_layers.py`、`core/tools/check_hygiene.py`、新增 `core/tools/scorecard.py`、`profiles/{standard,strict}.json`、`core/templates/makefiles/{Makefile.standard,Makefile.strict}.template`、`core/templates/harness/config.json.template`、`core/templates/HARNESS.md.template`、`core/templates/AGENTS.md.template`、`core/templates/docs/harness-scorecard.md.template`、`docs/{playbook,adoption}.md`、`prompts/adopt-brownfield.md`、`tests/{test_harness_adopt,test_harness_prompt,test_kit_profiles,test_kit_host_tools}.py`、新增 `tests/test_kit_scorecard_v04.py`
- **P（plan/state，Lead）**：`core/tools/check_plan.py`、`core/tools/harness.py`、`scripts/harness-selftest`、`core/templates/harness/plans/_template.md`、`tests/{test_core_plan_evidence_claim,test_harness_cli,test_harness_selftest}.py`、新增 `tests/test_core_plan_state_v04.py`
- **Lead 收口**：`VERSION`、`CHANGELOG.md`、`README.md`、`SPEC.md`、`docs/why.md`、`skills/harness/references/*`、跨文件冲突、全量门禁、barra 实仓验证、发布循环。
- 任何成员不改 `VERSION`/`CHANGELOG.md`；发现跨域问题时报告给 Lead，不越界改。

## 3. 证据链（E）

### E1 · 证据扫描/归档/跟踪（P0-3）

1. `evidence_files()` 递归扫描 `config.paths.evidence/**/*.json`，按文件名 `^\d{8}T\d{6}Z-[a-z0-9-]+$` 过滤；路径含 `_archive` 段 → 归档，否则当前。
2. 主流程先输出 `验证 N 条当前证据（fresh=…）；归档 M 条（只列出，不参与判定）`。
3. 归档证据逐个输出 `CLAIM <id>: SUPERSEDED — <原因>`：
   - 当前证据 doc 的 `supersedes`（字符串或数组）包含该 id → `已被 <current-id> 取代`；
   - 归档 doc 的 `supersededBy` 指向当前 id → 同上；
   - 其它 → `位于 _archive（未声明取代关系）`。
   - 归档证据不改变退出码；无法解析也要输出 SUPERSEDED 行，不静默。
4. 当前证据必须被 git 跟踪：`git ls-files --error-unmatch -- <rel>`；非 git 仓库 → 全局 WARN 一次，跳过跟踪校验。
   - 未跟踪且最终 verdict=PASS → 降为 `UNVERIFIED — …；证据文件未被 git 跟踪（CI 无法复核）`；
   - 未跟踪且 verdict 已是 FAIL/UNVERIFIED → 保持 verdict，原因追加未跟踪说明；
   - `--allow-untracked`：不降级，只追加 `[WARN]` 输出（显式逃生口，文档说明风险）。
5. 只有归档证据、没有当前证据 → 输出 `CLAIM <none>: UNVERIFIED — 未找到当前证据…`，exit 2。
6. 帮助/文档串更新；`evidence.py` 不改。

### E2 · JUnit 默认脱敏 + 入库复制（P0-4）

1. 新参数：`--keep-raw`（保留旧行为）、`--allow-outside-root`、`--artifacts-dir PATH`（默认从 `harness/config.json` 的 `paths.evidence` 推 `<evidence>/artifacts`，无 config 回退 `harness/evidence/artifacts`）。
2. 默认模式（sanitize-copy）：
   - 解析 XML（用于计数，计数规则不变）；
   - 清理：删除所有 `system-out`/`system-err` 元素；删除 `hostname` 属性；`properties/property` 的 name/value 命中本机路径或主机名 → 删除该 property；
   - 路径归一：`str(root)`（含尾部分隔符）→ 空串（变仓库相对）；`str(Path.home())` → `$HOME`；Windows 分隔符一并处理；`file` 等属性同样处理；
   - 序列化到 artifacts 目录，文件名 `<UTC>-<n>-<原 stem>.xml`（UTC 在运行开始取一次；重名追加 `-2`）；
   - payload `result.artifacts` 写仓库相对路径；`result.artifactMode = "sanitized-copy"`。
3. 大小上限 5 MiB：输入或脱敏后产物超限 → exit 2，可读报错。
4. `--keep-raw`：不脱敏不复制，`artifacts` 保留原路径；原文件在仓库外时必须同时给 `--allow-outside-root`，否则 exit 2 并提示默认模式；`artifactMode="raw"`。
5. 文档串/帮助更新；测试 fixture 含 hostname、system-out、绝对路径 property，断言产物无这些内容且计数不变。

### E3 · claim 环境模型 + skipped 容差（P0-6）+ static freshness（P1-3）

1. `claim.environment`（可选 object）：`{id, requires[], os, python}`。
   - 证据 `environment` 缺 `id` 或 id 不等 → `UNVERIFIED — 环境不匹配…`；
   - `requires`：证据 `environment.requires`（数组或逗号分隔字符串）必须覆盖 claim.requires；
   - `os`/`python` 给出时，证据同名字段需前缀匹配；
   - 任一不满足 → UNVERIFIED（在计数校验前判定），原因列出差集。
2. `expectedSkipped`：
   - 字符串 → 点号路径；baseline 值可为 int、`{min,max}`、`{byEnvironment:{env:int|{min,max}}}`；
   - object → 直接使用（支持 `min/max`、`byEnvironment`）；
   - `byEnvironment` 需要证据 `environment.id`；缺 id 或未定义该环境 → UNVERIFIED；
   - 区间闭区间；失败信息写清 `skipped=<n> 不在 [min,max]` / `!= expected`；非法配置 → FAIL。
3. `type=static` 的 claim 不再做 freshness STALE 判定/标注（命令每次重跑），原因追加 `；static claim 复跑通过，freshness 不适用`。
4. `expectedSkipped` 仍保留点号路径的向后兼容；文档/证据 README 说明新字段。

## 4. 计划 / 状态（P）

### P0-1 · `submitted` 增量 scope 审计

- 新增 `check_submitted_scope(plan, root, config)`：
  - 对 `submitted` 每个 token 解析 commit；用 `git rev-list --parents -n1` 判断 merge：
    - 普通/根提交：`git diff-tree --no-commit-id --name-only -r --root <sha>`；
    - merge：`git diff-tree -r --no-commit-id -m --first-parent <sha>`（只与第一父比较）。
  - 路径必须命中 `scope.allow` ∪ `scope.exceptions`（front matter 标量列表）∪ 过程目录（`paths.evidence/plans/reviews`）；否则 FAIL：`submitted commit <tok> 修改了 scope.allow 之外的文件：<path>`。
  - git 不可用/读取失败 → WARN（不伪造通过）；merge 无法 diff → WARN。
- 扫描范围：顶层计划硬校验；`harness/plans/_archive/*.md` 也扫描但所有问题降级 WARN，输出前缀 `[archived]`（Barra 的越界提交必须可见，不阻断升级）。
- docstring/计划模板说明 `scope.exceptions` 写法。

### P0-2 · done 零未验证 + 归档回读

- `check_evidence` done 分支：
  - 读 `## 未验证项`（别名：未验证）去占位后的正文；非空时要求 `## 未验证豁免` 表（列：项目/理由/负责人/到期日）。
  - 每行非空、到期日 `YYYY-MM-DD` 且不早于今天；每个未验证正文行必须被子串匹配某个「项目」；否则 FAIL。
  - 无豁免或行无效 → FAIL。
- `harness.py`：
  - 新增 `load_archived_plans()`（`plans/_archive/*.md`，按文件名倒序）；
  - `build_status` 增加 `lastPlan`（id/status/updated/path/unverified/next/evidence 摘要）与 `archivedPlans`；无 active 时 nextActions 指向「先读上一计划」，不再说「创建首个计划」；`git.inSync=null` 并注明不做范围校验；
  - `status` 文本输出「上一计划 + 未验证项 + 下一步 + 归档路径」；
  - `handoff` 无 active 时输出同一摘要（JSON 含 lastPlan），exit 0。
- `plans/_template.md` 增加「未验证豁免」占位节与说明。

### P2-1 · selftest M6 归档 fixture

- 有 active：现状（复制为第二个 active），断言输出含 `同时存在 2 个 active`。
- 无 active 但有归档计划：复制最近归档计划为两个 active fixture（`status: done|archived` → `active`），跑 `check_plan check`，断言输出含 `同时存在 2 个 active`；cleanup 删除 fixture。
- 两者都无：SKIP，reason 明确「无 active/归档计划」；汇总输出 `PASS x / FAIL y / SKIP z（不适用）` 并注明 `SKIP ≠ PASS`；JSON 增加 `notApplicable`。
- Mutation 增加 `expect_contains` 字段（现有 mutation 只有 exit 非零断言时保持行为）。

## 5. 接入体验 / 传感器（O）

### O1 · check_layers（P0-5）

- 默认排除目录/后缀：`.git .venv venv node_modules build dist __pycache__ .mypy_cache .pytest_cache .tox .eggs *.egg-info target .idea .vscode`；`layers.exclude` 追加（路径前缀或 glob）。
- 文件发现：git 仓库优先 `git ls-files`（按 extensions、sourceRoot 过滤）；非 git 或失败回退 rglob（同样排除）。输出区分「git 跟踪 / 文件系统」。
- 输出每条规则 `eligible/matched/violations`（matched=规则前缀命中文件数）；eligible 或 matched 为 0 → `[WARN] 规则 … 未匹配任何源文件（检查 pathPrefix）`；符号守卫同理。违规仍 exit 1。
- `check_layers()` 返回结构化结果供测试；main 打印扫描数/排除数/每规则覆盖。

### O2 · check_hygiene（P2-2）

- 统计 `skipLocalPathScan` 跳过的文件数与命中 pattern；输出 `扫描 S / 跳过 K（pattern=count…）`；`--verbose` 列出最多 20 个跳过路径；返回统计结构；违规仍 exit 1。

### O3 · harness-adopt / init / prompt（P1-1、P1-5、P1-6、P2-3）

- `recommend_profile` → `recommended`（minimal/standard，永不为 strict）+ `alternative`（strict，仅当 score≥4 且写明「仅当需要 adapters/red-team/release-check」）+ `why`；报告与 `--write-plan` 适配。
- Python 测试命令探测顺序：`.venv/bin/python`（pytest 存在→`-m pytest -q`，否则 unittest）→ `uv run …`（有 uv.lock）→ `poetry run …`（有 poetry.lock）→ `python3 …`；同时在 requirements.txt 里找 pytest。`suggest_test_command` 返回 `(command, source_note)`。
- `harness-adopt --test-command CMD` 覆盖；报告标「建议命令 / 是否可执行（探测）」；探测只做可执行性（相对路径存在或 `shutil.which`），不跑全量。
- `harness-adopt --archive-report PATH`：只复制既有报告到 `harness/reports/adoption-<YYYY-MM-DD>.md`（拒绝覆盖），不重新扫描；`harness-init` 成功摘要提示归档命令。
- `detect_target_stage` → `(stage, missing)`；信号：`.harness-manifest.json`、`harness/config.json`、`harness/plans/_template.md`、`tools/check_plan.py`、`tools/verify_claim.py`、Makefile/Makefile.harness 含 harness 目标；缺失 → `partial` + 明确缺项 WARN。
- `prompts/adopt-brownfield.md`：默认 standard、strict 需用户明确要求并写理由；新增「接入后：归档盘点报告 → 生成 scorecard → selftest → 未验证项清零或 waiver」步骤。

### O4 · scorecard + Makefile + profile（P1-2、P1-4）

- 新增 `core/tools/scorecard.py`：
  - `--generate`（默认）：跑 `check_docs/check_agents/check_plan --lenient-uncommitted/check_hygiene/check_layers/verify_claim --all`，记录命令/exit/关键输出，生成 `harness/reviews/<YYYY-MM-DD>-scorecard.md`（含 checkedAt、commit、证据 ID、测试计数、文档计数、五子系统表「自评 / 独立复评」两列与 TBD）。
  - `--check-stale`：读 reviews 下最新 scorecard，`checkedAt` 超过 `scorecard.maxAgeDays`（默认 30）或 `commit` 之后提交数超过 `scorecard.maxCommits`（默认 50）→ WARN；无 scorecard → WARN；`--strict` 时 exit 1；默认 exit 0。
  - `--json` 供测试。
- `profiles/standard.json`：加入 `core/tools/scorecard.py → tools/scorecard.py`、`scripts/harness-selftest → tools/harness_selftest`、`core/templates/docs/harness-scorecard.md.template → docs/harness-scorecard.md`；`strict.json` 移除重复的 scorecard 条目（继承 standard）。
- `Makefile.standard/strict`：`.PHONY` 与目标增加 `selftest`（`python3 tools/harness_selftest --target .`）、`upgrade-check`（要求 `KIT_ROOT`，否则可读提示 exit 2）、`scorecard`；`check` 增加 `python3 tools/scorecard.py --check-stale`（只 WARN）。
- `config.json.template`：`freshness.docs-pass` 拆为 `docs/** references/** AGENTS.md harness/AGENTS.md harness/README.md`；新增 `scorecard` 阈值段；`claims` 说明环境字段（JSON 无注释，用 README/文档承载）。
- `HARNESS.md.template` / `AGENTS.md.template` 命令表同步；`docs/playbook.md` 33/205 行统一口径；`docs/adoption.md` 评分卡改为 standard 自带 + `make scorecard`。

## 6. 验收

1. kit 全量 unittest 通过（含新增 negative；预计 175 → ≥205）。
2. `make verify-static`（iOS 仓）PASS。
3. 迁移实仓验证（只读）：对 `barra` 跑新版 `check_layers`（应约 171 tracked，不含 .venv）、`verify_claim`（应显示归档 `SUPERSEDED`、不改变退出码）、`check_plan`（`_archive` 降级 WARN 可见越界提交）、`status`（无 active 时回读归档）。
4. 负向用例（至少）：submitted 越界 FAIL；**提交后放宽 scope 仍 FAIL（按提交时点 scope 审计）**；**计划与提交同批修改 strict FAIL**；done+未验证项无 waiver FAIL、有有效 waiver（≤90 天）PASS；**归档计划 status 非 done/archived FAIL**；**归档 done 问题 daily WARN / `--strict` FAIL**；**归档 FAIL/UNVERIFIED 证据无合法 `supersedes` → UNVERIFIED**；**必需 claim 缺失 → UNVERIFIED**；**未跟踪 PASS 证据/artifact → UNVERIFIED（strict 下 `--allow-untracked` 无效）**；JUnit 泄漏 fixture 脱敏后无 hostname/绝对路径且计数一致；`expectedSkipped` 区间/byEnvironment/宽度上限；layers `.venv` 不参与、未跟踪源文件也扫描、规则 0 匹配 WARN（strict FAIL）；M6 无 active 用归档 fixture。
5. 发布门禁与镜像验证按既有 release playbook（提交/推送前逐次确认）。

## 7. 不做（本轮）

- A/B 行为实验、跨 Agent 交接演练、多 Agent 并发（仍 v0.4.x/v0.5）。
- `harness-upgrade --apply`（仍只读）。
- `check_plan` 全面复用 `verify_claim`（仍各自实现，契约测试兜底）。
- DSH 插件产品化。

## 8. 红队审查回应与实现偏差（2026-11-11）

审查报告：`harness/reviews/2026-11-11-adoption-feedback-v04/red-team-plan-review.md`（P0×5 / P1×11 / P2×10）。

| 编号 | 结论 | 处理 |
| --- | --- | --- |
| P0-1 归档即免检 | **接受** | 归档 `status` 非 done/archived → 硬 FAIL（daily 也 FAIL）；归档 done 内容问题 daily WARN、`check-plan-strict`（`--strict`）FAIL；未引入 `archivedAt` legacy 白名单，迁移矩阵明确「升级后 pre-push 会拦，补 waiver/纠正后通过」 |
| P0-2 证据静默消失 | **部分接受** | 采纳 required claims 完整性 + 归档 FAIL/UNVERIFIED 无合法 `supersedes` → UNVERIFIED；**不采纳** tracked `ledger.json`（本轮不做，README/SPEC 记为边界） |
| P0-3 scope 自放宽 | **接受** | submitted 审计改用**提交时点**的计划 scope（`git show <sha>:<plan>`）；计划 scope 在提交后修改 → WARN（strict FAIL）；计划与提交同批修改 → strict FAIL；`scope.exceptions` 改为「提交范围例外」表（路径/理由/负责人/到期日，理由≥5 字、到期≤上限） |
| P0-4 多环境不足 | **部分接受** | 采纳 `floorByEnvironment` + `required` claims + skipped 区间宽度上限 + os/python 边界匹配；**不采纳**工具采集 `capturedBy`（环境仍自报，README 写明不能证明真实执行环境）；**不采纳**双 claim 完整性之外的 env 证明 |
| P0-5 artifact 未绑定 | **部分接受** | 采纳 artifact 必须 git tracked；证据 commit/artifact sha256 绑定列入 v0.4.x（本轮不做）；`--keep-raw --allow-outside-root` 明确产出会被 verifier 判 UNVERIFIED 并告警 |
| P1-1 merge diff 写错 | **接受** | 改为 two-tree：merge 用 `git diff --name-only <sha>^1 <sha>`；补 merge fixture（含第一父侧新增文件） |
| P1-2 JUnit 安全边界 | **接受** | stat/size 前置、symlink 拒绝、artifacts dir 必须在 root 内、failure/error message/type/classname/file 脱敏、sanitize 后重算一致、原子写 |
| P1-3 证据 JSON 隐私 | **部分接受** | `--environment` 值命中 IP/本机路径/hostname → WARN；tracked evidence 的历史 IP（barra）不在本仓清理，迁移时人工处理并记录；`check_hygiene` 的 evidence 扫描列入 v0.4.x |
| P1-4 `--allow-untracked` 逃生 | **接受** | `--strict` 下强制 UNVERIFIED；Makefile/release 模板不传该 flag；输出标记 `ESCAPE=untracked` |
| P1-5 layers 盲区 | **接受** | tracked + `git ls-files --others --exclude-standard`；未跟踪违规 FAIL；规则 0 匹配 WARN，strict FAIL |
| P1-6 scorecard 发布约束 | **部分接受** | `--check-stale --strict` FAIL；独立复评列强制列入 v0.4.x；`--generate` 只填事实不评分 |
| P1-7 迁移矩阵 | **接受** | `docs/playbook.md` 增加 v0.3.0→v0.4.0 迁移矩阵（行为变更/旧仓预期/修复命令/回滚）；barra 只读复验作为实测 |
| P1-8 archive-report 未脱敏 | **接受** | 归档前脱敏（仓库根/主目录/用户段）+ UTC 日期 + 拒绝覆盖 + 头部标注 |
| P1-9 归档回读误导 | **接受** | status/handoff 标注「归档时点快照」+ 列出归档后新增 PASS 证据 + 区分历史/当前 |
| P1-10 阶段检测误判 | **接受** | 以 manifest profile 为真源；adopted/partial/mismatch/legacy/unadopted；minimal 不误判 |
| P1-11 测试命令未验证 | **接受** | 候选命令实际跑 `--version`（10s 超时），报告「建议/探测/已验证」三列 |
| P2-1 计数口径 | 接受 | 统一「反馈 15 项（P0×6/P1×6/P2×3）+ 红队 P1/P2 附加」 |
| P2-2 os/python 裸 startswith | 接受 | 边界匹配 |
| P2-3 区间宽度 | 接受 | `harden.maxSkippedRange` 默认 5 |
| P2-4 两套判定逻辑 | 部分接受 | check_plan 对未跟踪证据加 WARN，与 verify_claim 对齐；契约测试列入 v0.4.x |
| P2-5 归档扫描上限 | 接受 | 逐条输出上限 20，超出提示 |
| P2-6 layers 语义 | 接受 | SPEC 固定 eligible/matched/coverage 定义 |
| P2-7 archive-report 日期 | 接受 | UTC |
| P2-8 scorecard 时钟/commit | 接受 | checkedAt UTC；commit 必须 HEAD 祖先 |
| P2-9 验收覆盖 | 接受 | 已补入 §6 验收 |
| P2-10 supersedes 回填 | 部分接受 | barra 迁移说明给出回填方法；不自动生成 |

其他偏差：
- `harness.py verify/release` 的计划严格校验改用 `check_plan.py check --strict`（含归档 strict）。
- 新的 `check-plan-strict` Makefile target 加 `--strict`。
- 未做：ledger、artifact sha256/commit 绑定、环境采集、scorecard 独立复评强制、hygiene evidence 扫描、`check_plan` 委托 verify_claim、`harness-upgrade --apply`。


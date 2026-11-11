# Changelog

## 0.4.0 — 2026-11-11

> 来源：真实存量仓库（Python/MySQL 单体，standard 档）接入反馈 15 项（P0×6 / P1×6 / P2×3）+
> 独立红队对冻结方案的 P0×5 / P1×11 审查。主题：**闭环可回读、绕过路径收口、接入体验一致**。

### 安全边界与状态真源

- **`submitted` 增量 scope 审计**：`check_plan` 对每个 submitted commit 读取**提交时点**的计划
  scope；越界 FAIL；计划 scope 在提交后被修改 → WARN（`--strict` FAIL）；计划与提交同批修改
  → `--strict` FAIL；merge 只与第一父比较（two-tree diff）。`scope.exceptions` 改为
  「提交范围例外」表（路径/理由/负责人/到期日，理由≥5 字、到期≤上限）。
- **归档计划不再免检**：`_archive/*.md` 扫描；`status` 非 done/archived → 硬 FAIL；归档 done
  的内容问题日常 WARN、`check-plan-strict`（`--strict`）FAIL，并提示「先归档再跑门禁」不可用。
- **done 零未验证**：「未验证项」非空时必须有「未验证豁免」表，逐条覆盖（去 markdown 修饰后
  匹配）、理由非空泛、到期 ≤ `config.waiver.maxDays`（默认 90 天）且未过期。
- **归档回读**：无 active 计划时 `harness.py status` / `handoff` 回读最近归档计划，标注
  「归档时点快照」+ 列出归档后新增 PASS 证据；`git.inSync=null` 不再伪造「一致」。
- **证据入库**：当前证据 JSON 与其 artifact 都必须被 git 跟踪，否则 PASS → UNVERIFIED
  （`--strict` 下 `--allow-untracked` 无效）；递归扫描证据目录，`_archive` 证据输出
  `SUPERSEDED` 不参与聚合；归档 FAIL/UNVERIFIED 必须由当前 PASS 证据 `supersedes` 合法接管，
  否则聚合 UNVERIFIED；**必需 claim 完整性**（`required` 默认 true）缺失 → UNVERIFIED。
- **JUnit 默认脱敏**：`evidence_from_junit` 默认复制脱敏产物到 `<evidence>/artifacts/`
  （删 system-out/err、hostname、敏感 property；failure/error message/type 与 testcase
  classname/file/文本脱敏；仓库根相对化、`$HOME`）；5 MiB 上限、symlink 拒绝、原子写、
  脱敏后重算计数不一致 exit 2；`--keep-raw` 为显式逃生口（仓库外路径会判 UNVERIFIED）。
- **测试环境模型**：claim `environment`（id/requires/os/python，边界匹配）、
  `floorByEnvironment`、`expectedSkipped` int/{min,max}/{byEnvironment} + 区间宽度上限
  （`harden.maxSkippedRange`，默认 5）；环境不匹配 → UNVERIFIED；static claim 不再做 freshness
  STALE 判定。
- **传感器可信度**：`check_layers` 文件发现改为 `git ls-files` + 未跟踪源文件，默认排除
  `.venv/node_modules/build/...`，输出 tracked/untracked、每规则 eligible/matched/violations；
  规则 0 匹配 WARN（`--strict` FAIL）；`check_hygiene` 输出跳过文件数与 pattern，`--verbose`
  列出跳过路径。
- **接入体验**：profile 口径统一为「standard 默认；strict 显式选择 + 理由」；Python 测试命令
  候选链 `.venv→venv→uv→poetry→python3` 并逐候选探测可执行性；`harness-adopt --archive-report`
  UTC 日期归档 + 脱敏；`harness-prompt` 阶段检测升级为
  adopted/partial(缺项)/mismatch/legacy/unadopted（以 manifest 为真源）。
- **评分卡进 standard**：新增 `tools/scorecard.py`（`--generate` 记录门禁快照/证据 ID/测试与
  文档计数，不自动打分；`--check-stale` 缺省/超 30 天/超 50 commits/commit 非祖先 → WARN，
  `--strict` exit 1），`make scorecard`；strict `release-check` 增加 scorecard 时效门禁。
- **Makefile/标准档**：新增 `selftest`（`tools/harness_selftest`）、`upgrade-check`
  （需 `KIT_ROOT`）、`scorecard`；`check-plan-strict` 使用 `check_plan.py check --strict`。
- **selftest**：M6 无 active 时用归档计划构造两个 active fixture（不再静默 SKIP）；注入断言支持
  `expect_contains`；汇总区分「不适用」并注明 SKIP ≠ PASS。

### 兼容与迁移

- 已接入 v0.3.0 的仓库升级后可能出现新的红/WARN：submitted 越界、done 计划未验证项、证据/artifact
  未入库、归档计划内容问题、layers 未跟踪源文件；迁移矩阵与修复命令见 `docs/playbook.md`
  「v0.3.0 → v0.4.0 升级自检」。legacy 归档计划的 scope 审计使用当前 scope 并 WARN（提交早于
  计划文件无法回溯）；建议补「未验证豁免」/「提交范围例外」后重跑 strict。
- 新增证据字段（可选）：`environment.id/requires/os/python`、`supersedes/supersededBy`、
  `artifactMode`；新增 config 段（可选）：`scorecard`、`harden.maxSkippedRange`、
  `waiver.maxDays`、`claims[].required/environment/floorByEnvironment`、`layers.exclude`。
- 测试：kit 175 → **270**。

## 0.3.0 — 2026-11-11

- **router skill（显式安装，默认不启用）**：新增 `skills/harness/`（`SKILL.md` + 9 个 references：
  status/adopt/plan/build/verify/review/release/collaborate/upgrade）与 `scripts/harness-skill`
  （install/check/list；写入 `.dsh/skills/harness/`、`.claude/skills/harness/`，并在 manifest 记录版本/哈希）。
  A/B 未完成，因此 skill 是 opt-in，主入口仍是 `tools/harness.py`。
- **需求卡 intake**：`tools/harness.py intake --file <卡>` 机检「目标 + 验收判据」（命令+期望，或可复核链接+复核者），
  模糊判据直接拒绝；标准档新增 `harness/requirements/_template.md`。
- **发布分级检查**：`tools/harness.py release [--check] [--strict]`（静态门禁 + `verify_claim --fresh`），
  Makefile 新增 `release`；strict 现有 `release-check` 保留。
- **Agent 能力探测**：`tools/doctor.py --agent` 只读输出 Agent/CLI/模型/skill 根/manifest 信息。
- **文档定位重写**：新增 `docs/why.md`（定位、与 Claude Code 自管的关系、卖点成熟度、边界、不适用场景）；
  README 开篇改为「Harness Engineering 项目管理工具」，SPEC §0 明确不做产品管理/不编排 Agent/不做权限系统。
- 测试：新增 `test_harness_skill.py`（7 用例）、intake/release 4 用例、doctor `--agent` 1 用例；
  kit 测试 163 → **175**。
- 兼容：init/profile 新增 `harness/requirements/_template.md` 与 Makefile `release` target；
  升级仓需回写 Makefile（playbook 升级路径）；skill 安装是显式动作，不自动注入。

## 0.3.0-alpha.1 — 2026-11-11

- **目标侧统一入口 `tools/harness.py`（v0.3.0-alpha 第一步）**：`status`（一屏状态 + 建议下一步，`--json`）、
  `start`（幂等建 active 计划，自动 owner/scope/验收骨架，建完 `make check` 即绿）、`verify`
  （自动同步计划「未提交改动」段 → 运行 `make verify-static` → 计划严格校验 → 证据三值摘要；`--claims-strict` 可阻断）、
  `handoff`（交接摘要，`--json`）、`plan check`（默认日常宽松，`--strict` 严格）、`upgrade`（指引 kit 侧只读升级）。
- **计划↔git 双状态对账改造**：`check_plan.py check --lenient-uncommitted`（日常 `make check` 对未提交段差异只告警）；
  新增 Makefile `check-plan-strict`（`verify-static` 依赖它），`verify`/CI 走严格模式；`harness verify` 自动回写计划未提交段。
- **Makefile / AGENTS 入口**：三档 Makefile 增加 `status` / `start` / `verify` / `handoff`（minimal 仅 `status`/`verify`）；
  根 `AGENTS.md` 模板新增「一屏状态 / 开工 / 交接」命令行与冷启动第一命令提示。
- 新增 `tests/test_harness_cli.py`（6 用例：status 只读/JSON、start 幂等且 make check 即绿、verify 同步、handoff、plan check、minimal 降级）；
  `check_plan` 新增 lenient 负向用例；kit 测试 156 → **163**。
- 未在本版：router skill 与 A/B（需先有 CLI，顺延至 v0.3.0）；`--apply`、`check_plan` 委托 `verify_claim` 仍在 v0.3.0 候选。
- 兼容：新增 `tools/harness.py` 与目标 Makefile target；`check` 的语义从「严格」转为「日常宽松 + 独立严格 target」，
  升级时需回写 Makefile（playbook 升级路径）。旧仓不升级则行为不变。

## 0.2.13 — 2026-11-11

- **升级基线（只读）**：`harness-init` 现在在目标根写 `.harness-manifest.json`——记录 `kitVersion` / `profile` /
  `options`（name/language/testCommand/adapters/branch）+ 每个 kit 管理文件的 sha256 + `.gitignore` 追加块哈希 +
  init 时被跳过的文件；manifest 是可提交文件，作为升级与漂移检查的基线。
- **新增 `scripts/harness-upgrade`（kit 侧，只读）**：`--check` 校验 manifest/目标文件/kit 版本
  （in sync exit 0；本地漂移 exit 1；版本不符 exit 3；用法或 manifest 非法 exit 2），支持 `--json`；
  `--plan` 用 manifest 的 profile/options 在临时目录重渲染新版并输出三方 diff
  （SAME / LOCAL_ONLY / UPGRADE / ALREADY / CONFLICT / ADD / OBSOLETE / NOT_MANAGED / APPEND），
  **不写目标仓**；legacy 目标（无 manifest）也可 `--plan` 预览。`--apply` 明确未实现（v0.3.0）。
- 升级流程仍要求人工应用 diff + `make verify-static` + `harness-selftest`；kit 不提供 in-place 覆盖。
- 测试新增 `test_harness_upgrade.py`（14 用例：manifest 契约/漂移/版本 exit 3/追加块/legacy/plan 分类/只读/JSON）；
  kit 测试 142 → **156**。
- 兼容：v0.2.13 之前接入的仓没有 manifest，`harness-upgrade --check` 提示走 playbook 手工升级路径；
  init/模板/门禁行为无破坏性变化（新增 manifest 与 kit 侧脚本）。

## 0.2.12 — 2026-11-11

- **证据链加固（P0 安全修复）**：`verify_claim.py` 不再信任证据自报的 counts。
  test-count 的 PASS 现在要求：`git.commit` 可解析且是 HEAD 或其祖先、`git.dirty=false`；
  `result.artifacts`（JUnit XML）必须存在，并从 XML **独立重算** passed/failed/skipped，
  与自报值不一致即 FAIL；缺 artifact 或只有 xcresult 等不可重算产物 → UNVERIFIED。
  `claim.requireArtifact` 缺省改为 `true`（显式 `false` 仅为 legacy opt-out，原因中标注“未重算”）。
- **`harness-selftest` 新增 M9**：在临时副本中伪造 PASS 证据（HEAD commit、虚报 counts、无 artifact），
  断言 `verify_claim.py --all` 必须非 0；仅当宿主存在 `requireArtifact=true` 的 test-count 证据时执行。
- 测试：新增伪造 PASS / artifact 重算不一致 / commit 非祖先 / dirty PASS 负向用例；
  profile 证据链测试改用 JUnit XML artifact；kit 测试 140 → 142。
- 计划模板补 `submitted` 说明与 `_archive/` 完成流程；README 定位改为
  「给 AI Coding Agent 用的 Harness Engineering 项目管理工具」。
- 兼容性：已有宿主若 `claim.requireArtifact=false` 且无 artifact 仍可判 PASS（标注未重算）；
  仅有 xcresult 证据的宿主会从 PASS 降为 UNVERIFIED，需先用 `tools/evidence_from_junit.py`
  生成 JUnit XML。无 profile / 模板结构变更。

## 0.2.11 — 2026-11-11

- **提示词库改为单源生成**：新增 `prompts/`（2 份阶段前置 + 19 个场景模板 + 2 个附加片段），
  `docs/agent-prompts.md` 改为 `scripts/harness-prompt render` 生成；新增 `test_kit_prompts.py`
  校验 front matter、占位符声明与生成文档同步（漂移/未声明占位符即 exit 1）。
- **新增 `scripts/harness-prompt` CLI**：`list` / `show` / `copy` / `render --check`。`show` / `copy`
  按场景自动拼接前置（接入场景 0B / 日常 0A）、替换 kit 与目标仓库绝对路径、列出待补占位符；
  目标仓库与场景阶段不符、target 指向 kit 克隆目录时给 WARN；
  `copy` 写剪贴板（pbcopy / clip / wl-copy / xclip / xsel），无剪贴板时打印提示词回退。
- **提示词"直接可用"修复**：接入存量项目模板补上缺失的 kit 路径；公共前置拆为 0A（已接入）/
  0B（未接入），未接入项目不再被要求跑 `make check`/`harness/plans`；19 个场景统一标注
  「阶段 / 前置 / 需替换 / 复制命令」；命令统一为 kit 脚本真实路径；接入/计划模板去掉未声明的尖括号占位，`show` 会扫描残留尖括号并提示。
- README/adoption/playbook 接入说明改为「一条命令复制」优先；adoption 修正裸 `harness-adopt`
  路径与失效的 `§5 分工` 锚点；kit 测试 122 → 140。
- 无 profile / 模板 / config schema / 门禁行为变更；向后兼容。

## 0.2.10 — 2026-11-11

- **README 结构调整**：接入路径上移到能力清单前，命令行新项目/存量项目命令收进「接入路径」对应小节；
  顶部导航拆分为「Agent 接入 / 提示词模板」「命令行 playbook」「演化治理 / SPEC」；命令示例统一用 `<kit>` 占位符。
- **提示词模板扩充**（`docs/agent-prompts.md`）：公共前置区分"已接入/未接入"；新增冷启动接手、方案评估、
  修 Bug、重构、PR 前自检、**新开会话对抗性评审**、依赖升级、文档/ADR、性能验证、安全自查、**发布前操作**；
  场景对照表扩到 19 个场景。
- **文档一致性修复**：SPEC §5 去重、SPEC 测试说明补版本一致性、README 案例锚点/目录树/profile 表、
  adoption 场景索引分组与 `<kit>` 路径修正。
- config schema 补齐可选 `hygiene`/`layers` 字段契约（无行为影响）；无脚本/模板/门禁行为变更；向后兼容。

## 0.2.9 — 2026-11-10

- **接入文档改为 AI coding Agent 优先**：README 首页主入口改为「AI coding Agent 接入指南 + 提示词模板」；
  adoption 章节重排为「Agent 接入（推荐）→ 命令行手动接入」，原「两条人类路径」更名「命令行手动接入」。
- **新增 `docs/agent-prompts.md`**：可复制的提示词模板集——公共前置、接入新项目、接入存量项目、提需求、
  提新计划、多人/多 Agent 分工、结束会话、项目交接、结束项目、完成声明，附「场景 → Agent 应返回什么」对照表。
- adoption 新增「接入后：场景提示词模板」索引；README 目录树/SPEC 文档清单/playbook 导航/index 链接检查同步。
- 无脚本、模板、config schema 与门禁行为变更；向后兼容。

## 0.2.8 — 2026-11-10

- README 开篇精简：三行内讲清定位（Harness Engineering 脚手架 / 五子系统 / 证据说了算），接入指南、playbook、
  治理与 SPEC 入口合并为一行。
- 修复版本引用漂移：README 版本行、License 版本与 SPEC 配置示例统一到 `0.2.8`；新增
  `test_version_references_consistent`（kit 测试 121 → 122），把版本漂移纳入门禁。
- 无脚本、模板、config schema 与门禁行为变更；向后兼容。

## 0.2.7 — 2026-11-10

- **仓库改名 `harness-kit` → `harness-engineering-kit`**（GitHub 301 重定向；tags/releases 保留；
  目录、命令、Makefile 目标、`kitVersion` 与 tag 前缀沿用短名 `harness-kit`）。
- README 标题与对外链接、`docs/adoption.md` clone 命令、维护镜像 URL 更新为新仓库；
  README 增加"原名 harness-kit"说明；SPEC §10 记录改名契约。
- 来源仓库 `Makefile` 的镜像 remote、HARNESS/README/docs 的当前链接同步更新。
- 无脚本、模板、config schema 与门禁行为变更；向后兼容。

## 0.2.6 — 2026-11-10

- **README 显式定位为 Harness Engineering 项目脚手架**：新增「它是什么：Harness Engineering 脚手架」——五子系统
  （Instructions / State / Verification / Scope / Session Lifecycle）到 kit 资产的映射表 + 脚手架能力矩阵
  （新项目初始化 / 存量改造 / 版本升级 × 支持与边界）；适合人群补充"按五子系统搭/改项目"。
- playbook 标题与说明、SPEC 目标与 §0 非目标、adoption/governance 开头统一使用五子系统术语；SPEC 明确
  "不是代码迁移器（存量改造只做盘点/骨架/门禁，语义由人/Agent 完成）"。
- 无脚本、模板、config schema 与门禁行为变更；向后兼容。

## 0.2.5 — 2026-11-10

- **新增接入指南 `docs/adoption.md`**：面向人类团队与 AI coding Agent 的接入路径（新项目 10 分钟 /
  存量项目七步法 / Agent-first 接入、按 Agent 能力分层、bootstrap 提示、反模式），并给出
  **接入前后五子系统评分**的真实案例（存量 Android/Gradle 仓自评 6/25 → 20/25；来源 iOS 仓独立复评
  2.5/5 → ≈4.0/5），附评分口径与复现方法。
- **新增演化与治理 `docs/governance.md`**：反臃肿九原则（计算型优先/规则付租金/预算即设计/渐进披露/
  最小核心+薄适配/删除优先…）、版本演化与删除降级流程、行为级评估（v0.3+ 议题）、多人与多 Agent
  协作（机制层 vs 治理层、并行策略、诚实边界）。
- **README 重写**：以"AI Coding Agent / Vibe Coding 失控项目"为目标读者，新增症状→机制映射、
  适合/不适合、前后评分案例、反臃肿与多人协作摘要；接入指南/治理文档入口前置。
- 文档新增 `adoption.md`/`governance.md` 相对链接纳入 kit 链接检查；VERSION `0.2.5`。
- 无脚本、模板、config schema 与门禁行为变更；向后兼容。

## 0.2.4 — 2026-11-10

- **文档：升级路径实证**。`docs/playbook.md` 新增「升级路径」：版本升级 = 临时目录渲染新版 → 逐文件 diff →
  只回写 kit 管理面（`tools/`、`harness/config.json` 的 `kitVersion`/配置、Makefile kit 目标段、CI/hook）→
  `make verify-static` + kit `harness-selftest` 负向注入复核。已在真实 Android/Gradle 存量仓完成
  **v0.2.2→v0.2.3** 验证（`harness-selftest` 从 5 PASS / 2 FAIL / 1 SKIP 变为 **8/8 PASS**）；profile 升级
  （minimal→standard→strict）仍未验证。
- README/SPEC 同步：版本升级路径已验证、profile 升级未验证；来源案例补充 Android/Gradle 存量仓。
- 无接口、脚本、模板与 config schema 变更；向后兼容。

## 0.2.3 — 2026-11-10

- **宿主传感器上游化（C5/C6）**：新增 `tools/check_hygiene.py`（被跟踪构建产物 / 根文件白名单 /
  绝对符号链接 / 跟踪文件中的本机路径 / 超大跟踪文件；全部由 `harness/config.json` 的可选 `hygiene`
  段配置，缺段 `[SKIP]` exit 0）与 `tools/check_layers.py`（`sourceRoot` / `extensions` / `rules` /
  `symbolGuards` 配置驱动，解析 Kotlin/Java/Python import 与符号使用；可选 `layers` 段，缺段 SKIP）。
- **`check-host` 接入（C7）**：standard profile 复制上述两个工具；Makefile standard/strict 新增
  `check-host`（`check_hygiene.py` + `check_layers.py`），`verify-static` 依赖它。
- **`check_plan.py` 修复**：`normalize_path_token` 支持无扩展名根文件声明（`Makefile` / `GNUmakefile` /
  `Dockerfile` / `LICENSE` / `NOTICE`），计划「未提交改动」可正确声明这些路径。
- **门禁自测工具（C9）**：新增 `scripts/harness-selftest`——对目标仓的临时副本做基线检查、逐项注入
  （文档/指令/计划/证据/卫生），断言对应门禁非 0，再恢复并复核全绿；默认不写目标仓，`--keep` 保留副本。
- **Android / Gradle 试点转正**：在真实 Android/Gradle 仓完成完整 brownfield 试点（init → 文档蒸馏 →
  宿主传感器 → 证据链 → 负向注入 → 计划归档），语言矩阵 Android 行由「只读盘点」改为 ✅；
  JDK 17–21 / wrapper / NDK 边界仍由宿主项目自管。
- 测试：新增宿主门禁与 selftest 用例；kit 用例数 121（Lead 校正精确值）；
  SPEC 同步 §2/§4/§5/§9，README 更新能力表、接入流程与语言矩阵，playbook 第⑥步补 `check-host`/selftest。

## 0.2.2 — 2026-11-09

- **C1 存量项目接入**：新增 kit 侧 `scripts/harness-adopt`（默认只读盘点；`--report` / `--json` / `--write-plan`），
  覆盖概览（git/语言/构建/既有门禁）、文档（索引缺口/断链/疑似过期）、卫生（被跟踪产物/绝对符号链接/本机路径/大文件）
  与 profile / test 命令建议。
- **C2 Android / Gradle**：`harness-init --language` 增加 `android`；探测 `settings.gradle(.kts)` /
  `build.gradle(.kts)`，建议 `./gradlew testDebugUnitTest`（JDK 17–21 与 wrapper 版本由项目固定，
  wrapper 路径/NDK/多模块边界由项目自管；kit 不代跑、不解析测试输出）。
- **C3 JUnit XML 证据适配器**：新增 `tools/evidence_from_junit.py`（standard+），聚合多 suite JUnit XML
  为 `evidence.py write --from-json` 可接受的 evidence JSON，再交给 `verify_claim.py` 做三值判定。
- **C4/C8 文档与契约**：playbook 新增「存量项目（brownfield）改造」七步法；新增改造计划模板
  `core/templates/harness/plans/_adoption.md.template`（占位符 `{{PROJECT_NAME}}`/`{{KIT_VERSION}}`/`{{DATE}}`）；
  SPEC 同步 §4 脚本契约、§5 standard files、§6 `{{DATE}}`、§8 `android`、§9 测试契约。
- 测试与语言矩阵：新增 `test_harness_adopt.py`、`test_evidence_junit.py` 与 Android 推断用例；
  README 能力表、语言矩阵与版本引用更新；kit 用例数 98。

## 0.2.1 — 2026-11-09

- 来源仓库改名 `realtimeTranslatorOptimize` → `realtime-translator-ios`（GitHub 旧链接 301）；
  README 中的案例与试点报告链接同步更新；纯文档变更，接口不变。

## 0.2.0 — 2026-11-09

- 维护方式固化为「上游唯一源 + 独立仓只读镜像」：来源仓库新增 `make kit-publish`
  （subtree split → 镜像 `main`）与 `make kit-drift`（一致性检查，漂移 exit 1）；
  README 增加维护契约（禁止直接改镜像仓，Issue/PR 先回上游）。
- 修正 README 测试计数（67 → 69）与版本引用；`SPEC.md` 配置示例同步 `kitVersion`。

## 0.1.0 — 2026-11-07

首个公开版本：从真实 iOS 项目（Duiyi）的 harness 实践中抽取。

- `profiles/` minimal / standard / strict，`extends` 继承与按 `dst` 覆盖。
- `core/tools/` 8 个标准库脚本：token 估算、docs/agents/plan/evidence 门禁、三值
  claim 判定、doctor、adapters 同步/校验。
- `core/templates/` 项目无关模板：AGENTS、docs IA、references、harness 工作区、
  Makefile（三档）、证据 schema/TEMPLATE、plans 模板、strict 的 scorecard/reviews/skills。
- `adapters/` githooks / ci / claude-code / dsh（预留）。
- `scripts/harness-init`：dry-run、冲突拒绝与 `--force` 备份、已有 Makefile →
  `Makefile.harness`、语言/测试命令推断、首次 `make check` 透传。
- 69 个端到端测试：三档 init、`make check`/`verify-static`、证据生命周期、
  strict `release-check`、dry-run/冲突/备份、standalone 复制、语言推断、无专有引用。
- 实测语言矩阵：Python（unittest）、Node 24（`node --test` / `npm test`）、SwiftPM
  （`swift test`）；Xcode 工程需显式 `--test-command`；Go 未实测。

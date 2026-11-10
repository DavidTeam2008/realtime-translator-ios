# Changelog

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

# Changelog

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

# Changelog

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

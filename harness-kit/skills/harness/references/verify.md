# 验证 / 证据 / 三值判定

## 一键
`python3 tools/harness.py verify`：自动同步计划「未提交改动」→ 跑 `make verify-static`（含 `check_plan --strict`）→ `verify_claim --all` 三值摘要。
`--claims-strict` 让证据非全 PASS 也阻断；发布前用 `release --check`（fresh/strict）。

## 按变更类型选最小充分验证（细节见 `references/verification.md`）
| 变更 | 命令 |
| --- | --- |
| 文档 / 规则 / 工具 / skills | `make verify-static` |
| 领域逻辑 / 单测 | 项目测试命令（config.commands.test） |
| UI / 端到端 | 项目 UI/集成测试命令 |
| 真机 / 性能 / 设备相关 | 项目专用脚本（无环境时写“未验证 + 手动步骤”） |

## 证据（v0.4 规则）
- test-count：先 `tools/evidence_from_junit.py --xml <glob> --command "<测试命令>" --output <tmp.json>`，再 `tools/evidence.py write --from-json <tmp.json>`（要求 clean tree）。
  - 默认会**脱敏并复制** JUnit 到 `<evidence>/artifacts/`；不需要手写清洗脚本，产物是仓库相对路径。
- **证据 JSON 和 artifacts 都必须 `git add` 入库**；未跟踪的证据/artifact 会让 PASS 变 UNVERIFIED（`--allow-untracked` 只是显式逃生口，`--strict` 下无效）。
- 三值：PASS / FAIL / UNVERIFIED；没有 evidence id 的“已验证”按未验证处理。
- **必需 claim**：`config.claims` 每项 `required` 默认 true；某 claim 没有当前证据 → UNVERIFIED（不能只交一条）。
- **归档**：旧证据移入 `harness/evidence/_archive/` 只会显示 SUPERSEDED；若归档证据是 FAIL/UNVERIFIED，必须由当前 PASS 证据的 `supersedes` 声明接管，否则聚合仍 UNVERIFIED。
- **环境**：claim 可声明 `environment`（id/requires/os/python）与 `floorByEnvironment`；环境不匹配判 UNVERIFIED，不是 PASS/FAIL。多环境用 `expectedSkipped.byEnvironment`。
- 报告写：命令 + 退出码 + 环境 + evidence id；UNVERIFIED 单列。

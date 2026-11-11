# 验证 / 证据 / 三值判定

## 一键
`python3 tools/harness.py verify`：自动同步计划「未提交改动」→ 跑 `make verify-static` → 计划严格校验 → `verify_claim --all` 三值摘要。
`--claims-strict` 让证据非全 PASS 也阻断；发布前用 `release --check`（fresh/strict）。

## 按变更类型选最小充分验证（细节见 `references/verification.md`）
| 变更 | 命令 |
| --- | --- |
| 文档 / 规则 / 工具 / skills | `make verify-static` |
| 领域逻辑 / 单测 | 项目测试命令（config.commands.test） |
| UI / 端到端 | 项目 UI/集成测试命令 |
| 真机 / 性能 / 设备相关 | 项目专用脚本（无环境时写“未验证 + 手动步骤”） |

## 证据
- test-count：先 `tools/evidence_from_junit.py --xml <glob> --command "<测试命令>" --output <tmp.json>`，再 `tools/evidence.py write --from-json <tmp.json>`（要求 clean tree）。
- 证据必须是仓库相对 artifact（JUnit XML 可被独立重算）；只有 xcresult 会判 UNVERIFIED。
- 三值：PASS / FAIL / UNVERIFIED；没有 evidence id 的“已验证”按未验证处理。
- 报告写：命令 + 退出码 + 环境 + evidence id；UNVERIFIED 单列。

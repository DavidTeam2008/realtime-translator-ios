# 发布

1. 发布前：`python3 tools/harness.py verify` 全绿；然后 `python3 tools/harness.py release --check`
   - 会跑静态门禁 + `verify_claim --all --fresh`（strict profile 用 `make release-check`：含 scorecard `--check-stale --strict` + `--fresh --strict`）。
   - UNVERIFIED / STALE / 必需 claim 缺失 / 未入库证据都不算通过；发布声明必须附 evidence id。
   - 评分卡过期的项目先 `make scorecard`；自评≠认证，独立复评列 TBD 不算完成。
2. 版本与变更：改版本号/CHANGELOG/计划 evidence 表；确认 tag 前先问用户。
3. 安全检查：无密钥/Token/本机路径；依赖变更已确认来源与许可证。
4. 性能/真机：按项目 references/verification.md 的矩阵执行；无环境写“未验证 + 手动步骤”。
5. push / tag / 部署前必须得到用户明确确认；发布后回填计划（CI run、tag、未验证项）。

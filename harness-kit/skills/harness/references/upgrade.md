# 升级 harness-kit

1. 只读检查：`python3 <kit>/scripts/harness-upgrade --target . --check`
   - exit 0 = in sync；1 = 本地漂移；3 = 版本不符（manifest/config vs kit VERSION）；2 = 用法或 manifest 非法。
2. 预览：`python3 <kit>/scripts/harness-upgrade --target . --plan`
   - 输出 SAME / LOCAL_ONLY / UPGRADE / ALREADY / CONFLICT / ADD / OBSOLETE / APPEND；不写目标仓。
3. 应用（人工）：按 plan 逐文件回写 kit 管理面；CONFLICT 必须人工合并；不要整文件覆盖宿主文档。
4. 复核：`make verify-static` + `python3 <kit>/scripts/harness-selftest --target .`；然后更新 `.harness-manifest.json`（按新版 kit 重新 init 到临时目录后比对）。
5. `--apply` 尚未实现（v0.3.0 前只读）；升级前先问用户并记录计划。

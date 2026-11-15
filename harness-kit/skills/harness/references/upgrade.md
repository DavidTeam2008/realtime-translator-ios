# 升级 harness-kit

1. 只读检查：`python3 <kit>/scripts/harness-upgrade --target . --check`
   - exit 0 = in sync；1 = 本地漂移；3 = 版本不符（manifest/config vs kit VERSION）；2 = 用法或 manifest 非法。
2. 预览：`python3 <kit>/scripts/harness-upgrade --target . --plan`
   - 输出 SAME / LOCAL_ONLY / UPGRADE / ALREADY / CONFLICT / ADD / OBSOLETE / APPEND；不写目标仓。
3. 行为变更先对照 `docs/playbook.md` 的「版本升级」与「vX → vY 升级自检」表逐项处理；不要为了变绿删检查或放宽配置。
4. 应用（人工）：按 plan 逐文件回写 kit 管理面；CONFLICT 必须人工合并；不要整文件覆盖宿主文档。
5. 复核：`make verify-static` + `python3 <kit>/scripts/harness-selftest --target .`；然后更新 `.harness-manifest.json`（按新版 kit 重新 init 到临时目录后比对）。
6. **同步 skill**：升级后重装入口 skill（用户级一次即可）：
   `python3 <kit>/scripts/harness-skill install --scope user --force`；
   项目级安装的仓库改用 `install --force` 覆盖并提交，`check` 应报 in sync。
7. `--apply` 尚未实现（只读）；升级前先问用户并记录计划。

## v0.5.3 起的追加说明

- `.harness-manifest.json` 的 `appends[]` 新增 `templateSha256`（去重前模板块 sha）；`--plan` 优先按它比较，
  旧 manifest 无该字段时按 SAME + legacy 提示处理，不再把宿主 `.gitignore` 去重差异报成 CONFLICT。
- 升级后建议用新版 kit 重渲染 manifest（临时 init），写入 `templateSha256` 以便后续升级精确比较。
- 宿主 CI 的 verify checkout 需要 `fetch-depth: 0`（0.5.3 模板已带）；浅克隆会让归档计划的 `submitted` /
  证据 `git.commit` 在 CI 里解析失败。
- `check_plan` 现在可从 `harness/evidence/_archive/` 解析计划引用的证据（输出 WARN）；此前归档旧证据需把
  done 计划改 `archived` 的 workaround 可在回写新 `tools/` 后撤销。
- HARNESS 模板已瘦身（约 1182/1500 tokens），可保留宿主本地说明；证据政策细节以 `harness/evidence/README.md` 为准。

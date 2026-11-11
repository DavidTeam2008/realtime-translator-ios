# 接手 / 冷启动（只读定位）

1. `python3 tools/harness.py status --json`：读 `plan` / `lastPlan` / `git` / `evidence` / `nextActions` / `manifestKitVersion`。
2. 有 active 计划：读计划 front matter 与「目标与非目标」「验收」「未验证项」「下一步」；只读核对 `git status --short` 与 `git log -5 --oneline`。
3. 无 active 计划但 `lastPlan` 非空：读 `lastPlan.unverified` / `lastPlan.next`（**归档时点快照**，不是当前计划；status 会列出归档后新增的 PASS 证据）；确认上一轮遗留后再用 `start` 建新计划。
4. 计划与 git 不一致：跑 `harness.py verify`（自动同步未提交段），不要手抄第二份状态。
5. 报告固定五段（结论/证据/未验证/下一步/需人决策）；只读阶段不改文件、不写计划、不往 `_archive` 写。

## 常见失败
- `status` 报缺少配置 → 仓库未接入：走 `adopt.md`。
- 版本不一致：`manifestKitVersion != kitVersion` → 检查 `.harness-manifest.json` 与 `harness/config.json`，升级走 `upgrade.md`。
- evidence 全部 UNVERIFIED / 归档证据有 FAIL：按 `verify.md` 补真实证据或合法 `supersedes`，不要写“通过”。
- `git.inSync=null`：没有 active 计划，不做范围校验；不是“一致”。

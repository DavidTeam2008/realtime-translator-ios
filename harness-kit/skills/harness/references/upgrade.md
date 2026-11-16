# 升级 harness-kit

1. 只读检查：`python3 <kit>/scripts/harness-upgrade --target . --check`
   - exit 0 = in sync；1 = 本地漂移；3 = 版本不符（manifest/config vs kit VERSION）；2 = 用法或 manifest 非法。
2. 预览：`python3 <kit>/scripts/harness-upgrade --target . --plan`
   - 输出 SAME / LOCAL_ONLY / UPGRADE / ALREADY / CONFLICT / ADD / OBSOLETE / APPEND；不写目标仓。
3. 行为变更先对照 `docs/playbook.md` 的「版本升级」与「vX → vY 升级自检」表逐项处理；不要为了变绿删检查或放宽配置。
4. 应用（人工）：按 plan 逐文件回写 kit 管理面；CONFLICT 必须人工合并；不要整文件覆盖宿主文档。
5. 复核：`make verify-static` + `python3 <kit>/scripts/harness-selftest --target .`；然后更新 `.harness-manifest.json`（按新版 kit 重新 init 到临时目录后比对）。
6. **同步 skill**（按当前安装方式二选一，不要混用）：
   - npx 安装（首选）：`npx skills update harness -g`（或重新 `npx skills add ...`）；
     核对布局：`~/.agents/skills/harness` 为真目录、其余 agent 为符号链接。
   - harness-skill 安装：`python3 <kit>/scripts/harness-skill install --scope user --force`；
     项目级安装的仓库改用 `install --force` 覆盖并提交，`check` 应报 in sync。
   - 切换安装方式前先清理：旧安装 `harness-skill uninstall --scope user --force` →
     `npx skills add ...`；或 `npx skills remove harness -g -y` → `harness-skill install`。
     混合状态下 `harness-skill` 会检测到 npx 管理并拒绝写入（`--force` 才会接管，npx lock 残留）。
7. `--apply` 尚未实现（只读）；升级前先问用户并记录计划。

## v0.5.4 起的追加说明

- 入口 skill 支持 npx 一等入口：`npx --yes skills@1.8.1 add DavidTeam2008/harness-engineering-kit --skill harness -g -a claude-code -a codex -y`；
  首次在未接入仓库使用 skill 时，`scripts/kit-resolve.py` 会按 `SKILL.md` metadata 的 `kit_version`
  clone annotated tag 到 `$XDG_CACHE_HOME/harness-kit`（未设置则 `~/.cache/harness-kit`），
  cache 命中只做本地校验（marker + VERSION + HEAD），不联网；`--offline` / `--refresh` 控制。
- 已接入仓库（有 `tools/harness.py`）走 adopted 快路径：不需要 kit、不联网；只有 adopt / upgrade 才 `--require-kit`。
- **0.5.4 会更新宿主渲染文件**（模板内嵌 `{{KIT_VERSION}}`）：`harness/config.json`、`Makefile` 注释、
  `docs/harness-scorecard.md`（若宿主保留渲染行）、`tools/harness.py`（status 增加用户级 skill 识别）。
  按 `--plan` 逐文件回写 kit 管理面，不要整文件覆盖宿主自定义的 `Makefile` / 评分卡；
  manifest 用新版临时渲染结果整份重写（files sha 全量），再复核 `--plan`（0 CONFLICT）与 `--check`（仅 LOCAL_ONLY 漂移）。
- 镜像仓发布要求 annotated tag；`kit-resolve.py` 拒绝轻量 tag（无法校验 commit sha）。

## v0.5.3 起的追加说明

- `.harness-manifest.json` 的 `appends[]` 新增 `templateSha256`（去重前模板块 sha）；`--plan` 优先按它比较，
  旧 manifest 无该字段时按 SAME + legacy 提示处理，不再把宿主 `.gitignore` 去重差异报成 CONFLICT。
- 升级后建议用新版 kit 重渲染 manifest（临时 init），写入 `templateSha256` 以便后续升级精确比较。
- 宿主 CI 的 verify checkout 需要 `fetch-depth: 0`（0.5.3 模板已带）；浅克隆会让归档计划的 `submitted` /
  证据 `git.commit` 在 CI 里解析失败。
- `check_plan` 现在可从 `harness/evidence/_archive/` 解析计划引用的证据（输出 WARN）；此前归档旧证据需把
  done 计划改 `archived` 的 workaround 可在回写新 `tools/` 后撤销。
- HARNESS 模板已瘦身（约 1182/1500 tokens），可保留宿主本地说明；证据政策细节以 `harness/evidence/README.md` 为准。

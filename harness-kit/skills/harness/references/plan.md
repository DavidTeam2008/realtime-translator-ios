# 需求 / 计划 / 验收

## 建计划
- 快速：`python3 tools/harness.py start --topic <topic> --goal "<一句话目标>" --scope <文件或目录> ...`
  - 幂等：同 topic 已存在则 SKIP；自动填 owner、plan 自身与 scope；建完 `make check` 即绿（未提交段差异只告警）。
- 需求卡：`python3 tools/harness.py intake --file <需求卡.md>`；卡内必须有 `## 目标`、`## 验收判据`，每条判据需是“命令 + 期望结果”或“可复核链接 + 复核者”，模糊判据会被拒绝。
- 手工：`make plan TOPIC=<topic>` 后补 front matter；同一时间只允许一个 active 计划。

## 计划质量
- `scope.allow` 覆盖要改的路径与计划文件自身；越界先停。submitted 的每个 commit 会按**提交时点**的 scope 审计（提交后改 allow 不会追溯洗白）；确实需要例外时用「提交范围例外」表（路径/理由/负责人/到期日）。
- `acceptance` 每条可执行（命令/结果/阈值）；`verify` 写项目真实验证命令。
- 正文：目标与非目标、验收、改动范围、进度、验证证据、未验证项、未提交改动、下一步。
- `harness.py plan check`（日常宽松）/ `--strict`（未提交段严格）；`harness.py verify` 自动同步未提交段。

## 完成
- 证据表填 evidence id → 更新计划 → `harness.py verify` → `harness.py handoff`。
- done 计划：`status: done`、`submitted: <commit>`、**「未验证项」清零**（或「未验证豁免」表逐条覆盖，理由/负责人/到期日 ≤90 天）、移入 `_archive/`；`make check-plan` 通过后再收尾。
- 归档计划 status 必须是 done/archived；归档内容问题日常 WARN、`check-plan-strict` FAIL（先归档再跑门禁不可用）。

# 接入新项目 / 存量项目（Agent-first）

前置：确认 kit 路径 `<kit>`（用户给或仓内 `harness-kit/`）与目标仓库路径；未接入仓库没有 `tools/harness.py`，只能走 kit 脚本。

## 新项目
1. `python3 <kit>/scripts/harness-init --profile standard --target <路径> --dry-run`：给用户看 RENDER/COPY/APPEND 计划。
2. 用户确认后去掉 `--dry-run` 执行；init 会跑首次 `make check`。
3. `git add -A && git commit`（先问用户）；然后 `python3 tools/harness.py status`，用 `start` 建第一份计划。

## 存量项目（先只读）
1. `python3 <kit>/scripts/harness-adopt --target <路径> --report <仓库外路径> --json`：只读盘点，不改目标仓。
2. 按报告定 profile（存量优先 standard）、真实测试命令、文档蒸馏与清洁顺序。
3. `harness-init --dry-run` → 用户确认 → init（已有文件默认 CONFLICT，不 `--force`）→ 首次 `make check`。
4. 用 `harness.py status` 接手；后续按 playbook 七步法推进，每步一个可验证点。

## 硬约束
- 先只读、先 dry-run；`--force` 必须用户明确同意并先备份。
- 不自动重写业务代码；文档语义蒸馏由人或 Agent 完成后由门禁验收。
- 接入完成后：`git commit`（问用户）→ `test-count` 证据需要真实 JUnit XML（见 `verify.md`）。

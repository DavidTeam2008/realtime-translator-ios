# 接入新项目 / 存量项目（Agent-first）

> 本文自足：不需要生成或粘贴提示词，按步骤执行并在确认点停下。

## 0. 前置：定位 kit 并核对版本

- kit 位置：用户级安装记录 `~/.agents/skills/.harness-kit-skill.json` 的 `kitRoot` → 仓库内或父目录 `harness-kit/VERSION` → 问用户一次。
- 核对：`<kit>/VERSION`；低于 skill 的 `min_version` 先提示用户升级 kit 或重装 skill。
- 目标仓库可能还没有 `Makefile` / `harness/` / `tools/`，这是正常状态；不要假设 `make check` 可用。
- 全程不联网；只读阶段不改目标仓库任何文件。

## 1. 存量项目：先只读盘点（不改目标仓）

```bash
python3 <kit>/scripts/harness-adopt --target . --report /tmp/adoption-report.md --json
```

- 报告写到仓库外（`/tmp`），不要写进被盘点仓库。
- 读报告：文档（断链/未登记/疑似过期/索引缺失）、卫生（构建产物/绝对符号链接/本机路径/大文件）、现有门禁与 CI、推荐 profile、建议测试命令与可执行性探测。
- 给用户「盘点摘要 + 改造顺序」并**等确认**；确认前不改任何文件。

## 2. 定参数（依据盘点，不凭默认值猜）

- **profile**：默认 `standard`；`strict` 只有用户明确要求（需要 adapters / red-team / release-check）并写清理由时才用。
- **测试命令**：报告给出「建议 / 探测 / 已验证」；不可执行时先在宿主修，或用 `--test-command` 覆盖。
- **改造顺序**：文档蒸馏 → 清洁 → `config hygiene/layers` → CI/hooks → JUnit 证据 → `harness-selftest`。

## 3. dry-run → 用户确认 → init

```bash
python3 <kit>/scripts/harness-init --profile standard --target . --dry-run \
    [--language <lang>] [--test-command "<cmd>"]
```

- 复核 `RENDER` / `COPY` / `APPEND` / `CONFLICT` 动作；只有已有文件冲突才出现 `CONFLICT`，不要 `--force` 覆盖既有文档。
- 用户确认后去掉 `--dry-run` 执行；首次 `make check` 红就修内容，不删检查、不放宽配置。

## 4. 新项目

跳过盘点：`harness-init --dry-run` → 确认 → 执行 → `make check` → `python3 tools/harness.py start TOPIC=... GOAL=... SCOPE=...` 建第一份计划。

## 5. 接入后收口（顺序固定）

1. 归档盘点报告：`python3 <kit>/scripts/harness-adopt --target . --archive-report /tmp/adoption-report.md`（自动脱敏）。
2. 评分卡草稿：`make scorecard`（自评 / 独立复评两列填证据，不把自评当认证）。
3. 负向注入：`make selftest`（证明门禁会红；`SKIP ≠ PASS`）。
4. 「未验证项」清零，或写计划「未验证豁免」表（理由 / 负责人 / 到期日 ≤90 天）。
5. 证据落库：`test-count` 用真实 JUnit XML 重生成（默认脱敏），证据 JSON 与 artifact 都 `git add`。
6. `make verify-static`（strict 加 `make release-check`）；提交前问用户，确认无密钥 / 本机路径。

## 6. 每步交付格式

命令 + exit code + 产物路径 + 未验证项；结论按固定五段（结论 / 证据 / 未验证 / 下一步 / 需人决策）。

## 硬约束

- 先只读、先 dry-run；不自动重写业务代码；历史文档只归档不改写。
- 不删除或弱化既有检查；不为了变绿放宽 `config` / 跳过测试。
- 接入完成后的日常任务改用已接入流程（`status` / `plan` / `verify` / `handoff`）；skill 只需安装一次，不需要再生成提示词。

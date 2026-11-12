---
name: harness
description: Harness Engineering 项目管理入口（接入 / 升级 / 接手 / 计划 / 验证 / 评审 / 发布 / 交接）。未接入的仓库先走 adopt：定位 kit → 只读盘点 → dry-run → init；已接入先运行 python3 tools/harness.py status。触发：用 harness-kit 接入或改造存量项目、接手项目、建计划、完成前验证、发布前检查、交接、升级 kit。
license: MIT
compatibility: 已接入仓库用仓库内工具（tools/harness.py）；未接入仓库用 kit 脚本（kit 位置见用户级 install.json、仓内/父目录 harness-kit/，或问用户一次）。
metadata: {kit: harness-kit, entry: tools/harness.py, min_version: 0.5.0}
---
# harness · 项目入口

## 0. 先定位 kit，再看状态

1. **kit 位置**（按顺序，找到即停，不要猜）：
   - 用户级安装记录：`~/.agents/skills/.harness-kit-skill.json` 的 `kitRoot`；
   - 仓库内或父目录的 `harness-kit/VERSION`；
   - 都没有：问用户一次 kit 路径。
2. **版本核对**：读 `<kit>/VERSION`；低于 front matter 的 `min_version` 时提示升级 kit 并重装 skill（`<kit>/scripts/harness-skill install --scope user --force`），不自行改仓库。
3. **已接入**（仓库有 `tools/harness.py`）：运行 `python3 tools/harness.py status --json`，按输出路由。
4. **未接入**（没有 `tools/harness.py`）：走 `references/adopt.md`；不要伪造 `make` / 门禁输出。

> 宿主支持斜杠调用时（DSH / Qoder CN / Claude Code 的输入框有「技能」补全），用 `/harness` 显式加载本 skill；也按 description 自动触发。
>
> 本 skill 是默认入口。只有不支持 skills 的宿主才用提示词兜底：
> `<kit>/scripts/harness-prompt copy <场景>`（或 `docs/agent-prompts.md`）。两者冲突时以本 skill + kit 文档为准。

## 1. 按意图路由

| 意图 | 动作 |
| --- | --- |
| 接入新项目 / 改造存量项目 | `references/adopt.md` |
| 接手 / 继续 / 做到哪了 | status + `references/status.md` |
| 提需求 / 建计划 / 需求验收 | `references/plan.md`（`start` 或 `intake`） |
| 实现 / 修 bug / 重构 / 依赖升级 | `references/build.md` |
| 完成前验证 / 证据 / 三值判定 | `references/verify.md`（`verify`） |
| Code Review / PR 前自检 / 对抗评审 | `references/review.md` |
| 发布 / 安全检查 / 性能 | `references/release.md`（`release --check`） |
| 交接 / 换 Agent / 多 Agent 分工 | `references/collaborate.md`（`handoff`） |
| 升级 harness-kit | `references/upgrade.md` |

## 2. 硬约束（不可协商）

- **作用域**：只改计划 `scope.allow` 覆盖的文件；越界先停下更新计划并说明。
- **证据**：没有证据不写“已完成/已验证”；未运行写“未验证 + 手动步骤”。test-count PASS 需要可重算 artifact（JUnit XML），**证据 JSON 与 artifact 都必须 git 入库**；归档证据不参与判定。
- **归档**：`_archive` 计划/证据是历史快照，不是当前状态；没有 active 计划时先读 status/handoff 的归档回读，再决定新建计划。
- **门禁**：`make check` / `harness.py verify` 红了先修根因；不删除、不弱化、不绕过门禁。
- **问人**：push、发布、删除、改规则/门禁、`--force` 覆盖前先问。
- **单一状态源**：计划与证据是仓库文件；不把进度只留在对话里。
- **不装 skill 也能工作**：skill 只是入口；所有事实与流程都在仓库文件和 kit 文档里。

## 3. 输出协议（固定五段）

1. 结论（做了什么/当前判断）
2. 证据（命令 + 退出码 + evidence id；没有就写未验证）
3. 未验证项
4. 下一步（1 条可执行动作）
5. 需要人决策的点

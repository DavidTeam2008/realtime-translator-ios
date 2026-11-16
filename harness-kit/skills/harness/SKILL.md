---
name: harness
description: Harness Engineering 项目管理入口（接入 / 升级 / 接手 / 计划 / 验证 / 评审 / 发布 / 交接 / 反馈 kit 问题）。未接入的仓库先走 adopt：定位 kit → 只读盘点 → dry-run → init；已接入先运行 python3 tools/harness.py status。触发：用 harness-kit 接入或改造存量项目、接手项目、建计划、完成前验证、发布前检查、交接、升级 kit、反馈 kit 缺陷或文档不一致。
license: MIT
compatibility: 已接入仓库用仓库内工具（tools/harness.py，离线可用）；未接入/升级用本 skill 的 scripts/kit-resolve.py：npx 安装时按固定 annotated tag 自动 clone kit 到 XDG 缓存，也可用 HARNESS_KIT_ROOT 或仓内/父目录 harness-kit/ 指定。
metadata: {kit: harness-kit, entry: tools/harness.py, min_version: 0.5.0, kit_version: 0.5.4, kit_repo: https://github.com/DavidTeam2008/harness-engineering-kit.git}
---
# harness · 项目入口

## 0. 先定位 kit（必做第一步）

1. **运行本 skill 自带的解析脚本**（优先；缓存/首次 clone 都由它处理）：

   ```bash
   python3 <本 skill 目录>/scripts/kit-resolve.py --target . --json
   ```

   - 输出 `kitRoot` / `version` / `source` / `adopted`；`source=clone` 表示首次自动 clone 到缓存（需网络，按 annotated tag 校验 commit）。
   - 首次自动 clone 前先用一句话告知用户：正在把 kit 下载到缓存（版本 / 路径）；用户拒绝就改用手动路径（`HARNESS_KIT_ROOT`）。
   - 已接入仓库（有 `tools/harness.py`）会返回 `adopted: true`：**不需要 kit、不联网**，直接看第 3 步。
   - `<本 skill 目录>` 按安装位置找：项目 `.dsh/skills/harness`、`.agents/skills/harness`、`.claude/skills/harness`；用户级 `~/.agents/skills/harness`、`~/.claude/skills/harness`。
2. **脚本不可用时人工定位**（旧安装 / 无 python）：项目内或父目录 `harness-kit/VERSION` → 用户级安装记录 `~/.agents/skills/.harness-kit-skill.json` 的 `kitRoot` → 问用户一次。
3. **版本核对**：`kitRoot` 为空只允许「已接入」仓库；kit 版本低于 skill 的 `min_version` 时提示升级 kit 并重装 skill，不自行改仓库；低于 skill 期望版本可继续但提示升级。
4. **已接入**（仓库有 `tools/harness.py`）：运行 `python3 tools/harness.py status --json`，按输出路由。
5. **未接入**（没有 `tools/harness.py`）：走 `references/adopt.md`（需要 kit，用 `--require-kit` 解析）；不要伪造 `make` / 门禁输出。

> 宿主支持斜杠调用时（DSH / Qoder CN / Claude Code 的输入框有「技能」补全），用 `/harness` 显式加载本 skill；也按 description 自动触发。
>
> 本 skill 是默认入口。安装方式：`npx skills add DavidTeam2008/harness-engineering-kit --skill harness -g -a claude-code -a codex -y` 为首选（见 kit README），无 Node / 离线 / 项目级 pin 用 `<kit>/scripts/harness-skill install`（需先有 kit 克隆）。
> 只有不支持 skills 的宿主才用提示词兜底：`<kit>/scripts/harness-prompt copy <场景>`（或 `docs/agent-prompts.md`）。两者冲突时以本 skill + kit 文档为准。

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
| 反馈 kit 缺陷 / 文档不一致 / 需要新能力 | `references/feedback.md` |

## 2. 硬约束（不可协商）

- **作用域**：只改计划 `scope.allow` 覆盖的文件；越界先停下更新计划并说明。
- **证据**：没有证据不写“已完成/已验证”；未运行写“未验证 + 手动步骤”。test-count PASS 需要可重算 artifact（JUnit XML），**证据 JSON 与 artifact 都必须 git 入库**；归档证据不参与判定。
- **归档**：`_archive` 计划/证据是历史快照，不是当前状态；没有 active 计划时先读 status/handoff 的归档回读，再决定新建计划。
- **门禁**：`make check` / `harness.py verify` 红了先修根因；不删除、不弱化、不绕过门禁。
- **反馈上游**：kit 自身缺陷/文档不一致先按 `references/feedback.md` 交回上游（<https://github.com/DavidTeam2008/harness-engineering-kit/issues>）；不改宿主 `tools/` 或 kit 模板来绕过（升级会覆盖）。
- **问人**：push、发布、删除、改规则/门禁、`--force`、首次自动 clone 前先问/告知。
- **单一状态源**：计划与证据是仓库文件；不把进度只留在对话里。
- **不装 skill 也能工作**：skill 只是入口；所有事实与流程都在仓库文件和 kit 文档里。

## 3. 输出协议（固定五段）

1. 结论（做了什么/当前判断）
2. 证据（命令 + 退出码 + evidence id；没有就写未验证）
3. 未验证项
4. 下一步（1 条可执行动作）
5. 需要人决策的点

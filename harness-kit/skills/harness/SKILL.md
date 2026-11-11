---
name: harness
description: Harness Engineering 项目管理入口。接入/接手项目、建计划、实现、完成前验证与证据、评审、发布、交接换 Agent、kit 升级——一律先运行 `python3 tools/harness.py status`，按输出与路由执行；未接入仓库先走 adopt。
license: MIT
compatibility: 目标仓库需已接入 harness-kit（harness/config.json + tools/harness.py）；未接入时先走 references/adopt.md
metadata: {kit: harness-kit, entry: tools/harness.py, min_version: 0.3.0}
---
# harness · 项目入口

## 0. 永远先看状态

运行 `python3 tools/harness.py status --json`；失败或没有该脚本 = 仓库未接入 → `references/adopt.md`。
不要凭对话记忆判断进度；平台/版本以 status 输出为准。

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
- **证据**：没有证据不写“已完成/已验证”；未运行写“未验证 + 手动步骤”。test-count PASS 需要可重算 artifact（JUnit XML）。
- **门禁**：`make check` / `harness.py verify` 红了先修根因；不删除、不弱化、不绕过门禁。
- **问人**：push、发布、删除、改规则/门禁、`--force` 覆盖前先问。
- **单一状态源**：计划与证据是仓库文件；不把进度只留在对话里。

## 3. 输出协议（固定五段）

1. 结论（做了什么/当前判断）
2. 证据（命令 + 退出码 + evidence id；没有就写未验证）
3. 未验证项
4. 下一步（1 条可执行动作）
5. 需要人决策的点

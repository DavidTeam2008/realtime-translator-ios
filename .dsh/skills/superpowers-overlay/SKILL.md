---
name: superpowers-overlay
description: Duiyi 的 Superpowers 仓库 overlay：在调用 Superpowers 前强制单一计划/唯一任务状态、brainstorming 不写第二份 plan、TDD/调试/完成前验证回执与 review 执行器分层。触发：Superpowers、TDD、红绿、调试、完成前验证、代码评审纪律。
---

# superpowers-overlay · Duiyi

> 本 skill 是仓库级 overlay，不替代固定版本 Superpowers；先读 [harness/superpowers-overlay.md](../../../harness/superpowers-overlay.md)，再按上游 `SKILL.md` 执行。

## 使用顺序

1. 读 [overlay](../../../harness/superpowers-overlay.md) 与 [根指令](../../../AGENTS.md)。
2. 用固定版本入口解析 Superpowers：`python3 ~/.agents/skills/superpowers/scripts/resolve.py --json`。
3. 按 overlay 的路由读上游 `SKILL.md`（TDD / systematic-debugging / verification-before-completion 等）。
4. 需要留痕时运行 `make skill-receipt ...`；回执绑定 overlay hash，不替代真实执行。

## 边界

- 不写第二份计划、checklist 或完成状态；`tasks.md` 是唯一任务状态。
- 不自动 commit / push / tag / archive。
- 完成声明前必须跑本轮验证命令，未运行写 UNVERIFIED。

# Superpowers 仓库 Overlay · Duiyi

> **作用**：把固定版本 Superpowers v7.0.2（commit `22f0b463e7a5e579904dd6211a520321035526f7`）接到本仓的单一真源上。
> **优先级**：用户当次指令 > 仓库 `AGENTS.md` > 本 overlay > Superpowers 上游 `SKILL.md`。
> **绑定**：`make skill-receipt` 会把本文件路径与 sha256 写进 skill receipt；`make delivery-check` 复算，overlay 改动未重签即失败。
> **上游入口**：`~/.agents/skills/superpowers`（薄入口）→ 固定版本缓存 `~/.cache/ai-delivery-toolchain/superpowers/22f0b463e7a5e579904dd6211a520321035526f7`。

## 1. 单一计划与唯一任务状态

- **唯一任务状态**：`openspec/changes/<id>/tasks.md`（含 Delivery Contract）。复选框只在该文件维护。
- **Harness active 计划**：持有 scope、验收、证据、完成判定与未提交改动；**不复制** checkbox、完成百分比或第二份任务表。
- **禁止**创建/保留：`docs/superpowers/plans/`、`.superpowers/sdd/`、`plan.md`、progress ledger、独立完成状态。delivery lint L10 会直接失败。
- `full` 模式下禁用 stock `writing-plans` / `executing-plans` / `subagent-driven-development` 作为执行计划；仅 `light-agent` 模式（P3）可临时使用，且该模式不维护 tasks.md。

## 2. brainstorming（需求澄清）

- 触发条件：新行为、跨模块、写不出可验证判据、≥2 个合理方案、外部依赖不明。
- 产出写入 `proposal.md` 的 Why/What 与 `design.md` 的 Decisions；问题、选项、代价、决策要可复核。
- **不写第二份 plan**，不直接改 `tasks.md` 复选框，不创建 `docs/superpowers/plans`。
- 若判定无需澄清：在 `proposal.md` 写一行 `无需澄清：<理由>`；否则用 `make change-clarify` 留 clarification receipt。

## 3. TDD / 调试 / 完成前验证

- 每个实现任务先写失败测试并确认失败原因，再做最小实现；没有先失败的红测试，不写生产代码。
- 失败/回归先用 `systematic-debugging` 定位根因，不用随机改动掩盖。
- 完成声明前用 `verification-before-completion` 跑本轮真实命令；未运行 = UNVERIFIED。
- 每个实现任务用 `make skill-receipt ...` 留下绑定 task/phase/source/hostSkill/overlay 的回执；回执不替代执行。

## 4. Review 执行器（DD-7 / D-AI16）

- L2 独立 review 固定 `claude-code-code-review-skill`：`make review-execute CHANGE=<id>` 显式调用 `/code-review`（Claude Code + Skill/Task，两个并行 sub-agent），落 `execution_receipt`。
- gate-runner 用 `make review-gates CHANGE=<id>` 实际复跑 required commands，落 `gate_receipt`；reviewer 不得自证门禁。
- 单上下文手写报告、手写 gate PASS、任意 executor 字符串均不通过 `delivery-check`。

## 5. 硬禁止

- 不自动 commit / push / tag / archive / 发布；每次单独确认。
- 不删除、放宽或跳过既有测试断言来变绿。
- 不用“应该通过 / 之前跑过 / 看起来正确”代替本轮验证。
- 不把 OpenSpec `status.isComplete` 或 `remaining==0` 当完成判据。

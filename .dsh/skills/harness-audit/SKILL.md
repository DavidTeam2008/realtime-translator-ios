---
name: harness-audit
description: 对译 Duiyi 的 harness 月度/大改后自审：跑 make check-all、make doctor、make evidence、make verify-static，按 HARNESS.md 审计清单给五子系统打分并输出改进项；Phase 3 前人工执行、不自动判绿，结果写 harness/reviews/ 并回写 issue。
whenToUse: 每月一次；改 AGENTS/嵌套 AGENTS/skills/tools/Makefile/CI/evidence 之后；用户问"harness 还健康吗/门禁还有效吗"。
---

# harness-audit · harness 自审

对象是"约束 agent 的工程设施"本身，不是业务功能。Phase 3 前**人工**执行，不自动打绿。

## 动作（按序）

1. `make check-all`：本地门禁 + 团队基线；无模板仓时 `check-agents` SKIP，SKIP 不算验证。
2. `make doctor`：环境检查。退出码 2 → 动态验证层记"不可用"，不记 PASS/FAIL。
3. `make evidence`：证据可列、schema 校验（子命令语义见 `make help`）。
4. `make verify-static`：必须 PASS，且无脚本语法 / 编译检查输出。
5. 按 `HARNESS.md` 审计清单逐项打分；该文件由 Phase 1 交付，若不存在则用下方降级清单，每项写 PASS/WARN/FAIL + 证据（命令或文件）。
6. 结论写入 `harness/reviews/harness-YYYY-MM.md`（目录按需创建）；改进项写计划下一步（带 missingGuide / missingSensor / action 字段）。

## 五子系统降级清单（HARNESS.md 缺失时）

- Instructions：AGENTS 预算、嵌套 AGENTS 存在、§ 引用命中、skills frontmatter 合法（`make check-harness`）。
- State：active 计划唯一、验证证据行非空、未验证项单列（`make check-plan`）。
- Verification：静态门禁全绿、测试计数 ≥ 基线；最近一次动态验证有 evidence id，或明确写"未验证"。
- Scope：计划 `scope.allow` 与实际改动一致；越界时是否先停。
- Lifecycle：`make doctor/resume/end` 可用；交接摘要能让新会话 ≤3 次读取定位下一步。

## 三指标（月度对照，不追单点）

- 首次门禁通过率 = 一次 PASS 的次数 / 总门禁次数。
- 返工轮次 = 同一失败修复-验证的轮数（≥2 触发停止规则）。
- 未验证声明覆盖率 = 显式标"未验证"的交付项 / 全部未运行项（目标 100%）。

## 硬约束

- 结论必须有命令 / 文件证据；没有就写"未运行 / 未验证"。
- 不给"文档写得多"打高分；看门禁能否否证错误声明。
- 发现规则与门禁漂移：先记 issue，再按 L1/L2 走规则变更，不在审计里顺手改规则。

# Harness 评分卡

> 对象：对译 Duiyi 仓库（main @ 2026-11-07，Phase 2.5 整改后）。方法：五子系统 1–5 分，每分必须有可复核证据；**自评与独立复评分开记录**。
> 相关：[`../HARNESS.md`](../HARNESS.md)（系统地图）、[`decisions.md`](decisions.md)、[`04-roadmap.md`](04-roadmap.md)。

## 当前评分

| 子系统 | 自评 | 独立复评 | 判据与证据 |
| --- | --- | --- | --- |
| Instructions | **4.0** | **4.0** | `AGENTS.md` ≈1576/1650 token；6 个嵌套 AGENTS；6 个 skills frontmatter；`make check-harness` 19 项（§/第N节 引用 7 处 / 13 文件） |
| State | **4.0** | **4.0** | 计划 front matter/唯一 active/未提交交叉核对（`make check-plan`）；`make resume/end`；Phase 2.5 后独立复评：resume 与「下一步」已对齐（`harness/reviews/2026-11-07-phase2.5-reaudit.md`） |
| Verification | **4.5** | **4.3** | `make check` 6 组门禁；`verify-static` 含 91 个脚本单测 + 69 个 kit 端到端测试；本机 5 条 evidence（3 历史 + 2 发布前重跑）；`verify-claim` 三值 + freshness（含未提交工作树）/ID/done 绑定硬校验；四层验证矩阵 |
| Scope | **3.5** | **3.5** | L0/L1/L2；计划 `scope.allow/deny`；allow 外改动 → `plan.py check` FAIL（独立 clone 已实测）；并发/持久化/发布工程强制红队；allow 本身仍可被修改 |
| Session Lifecycle | **4.0** | **4.0** | 6 个 skills；`make doctor/resume/end`；doctor 失败给影响/如何补/必需性；handoff 协议；未验证项单列 |
| **综合** | **≈4.0 / 5（80%）** | **≈4.0 / 5（79%）** | 等级判定：**L3 达成（有条件）**——本地 `make end`/`make release-check` 可对计划内完成声明做三值否证；保留 P1：`make end` 对 STALE 只告警（`release-check` 阻断）、CI/pre-push 不跑 claim 判定、行为/性能门禁仍缺；未达 L4/L5 |

## 对照

| 口径 | 分数 | 说明 |
| --- | --- | --- |
| 改造前独立审计（2026-11-04） | **2.5 / 5** | 文档型 harness：有规则、无结构化证据；验证层不可否证 |
| 对外标杆成熟度（2026-11-06 独立只读 → 2026-11-07 独立复评） | **17/35 → ≈25.5/35（3.6/5）** | 文档/包装/叙事/可复现均提升；clean clone 与 CI 已独立验证；release、issue/PR 模板、真实人类陌生人首访仍缺 |
| 当前独立复评（Phase 2.5 后） | **≈4.0 / 5（79%）** | 独立核实 P0×3 关闭 + 静态机制全绿；扣分集中在 end 对 STALE 非阻断、CI/pre-push 不跑 claim、行为/性能门禁缺失 |

## 证据索引

- 静态门禁：`make check`（6 组，约 1s）/ `make verify-static`（约 15–25s，含 91 个脚本单测 + 69 个 kit 端到端测试；浅克隆需先 `git fetch --unshallow`）。
- 证据链：`harness/evidence/*.json`（本机 5 条 PASS：unit/UI/device 3 条历史 + 发布前重跑 2 条；换机缺 xcresult 时按设计 UNVERIFIED）。
- 规则机检：`tools/check-harness.py`（预算/嵌套/引用/skills/敏感信息）。
- 证据 schema：`harness/evidence/schema.json`（含可选 `agent` / `model` / `harnessVersion` 字段；schemaVersion 仍为 1，向后兼容）。
- 落地矩阵：`HARNESS.md` §3；采用指南：`HARNESS.md` §6。

## 评分细则（为什么不是更高）

- **Instructions 4.0**：预算与嵌套已机检；仍为中文单语，无规则"过期/负载"元数据。
- **State 4.0**：状态机可用；但状态依赖每轮自觉更新计划，非自动采集。
- **Verification 4.5**：静态/证据闭环强；缺 P0-1/P0-3 行为测试，CI 动态层默认跳过。
- **Scope 3.5**：scope 声明已有机检（未提交改动 vs 计划声明），但"改动是否越界"仍是人工判断。
- **Lifecycle 4.0**：skills + 命令闭环；handoff 仍是自由文本 + 计划摘要。

## 独立复评记录

| 日期 | 复评者 | 结论 | 证据/说明 |
| --- | --- | --- | --- |
| 2026-11-06 | 独立只读审计（子代理） | 对外标杆 17/35；首访 5 问仅 1 问可答 | 静态只读；未复跑动态门禁 |
| 2026-11-07 | 独立复评（Phase 2.3，非作者） | **4.0 / 3.5 / 4.0 / 3.0 / 3.5；综合 3.6（72%）**；L3 条件成立 | [`../harness/reviews/2026-11-07-harness-reaudit.md`](../harness/reviews/2026-11-07-harness-reaudit.md)；已独立复跑 check/verify-static/verify-claim/adapters-check |
| 2026-11-07 | 独立复核（Phase 2.5 后，非作者） | **4.0 / 4.0 / 4.3 / 3.5 / 4.0；综合 ≈4.0（79%）**；L3 达成（有条件）；对外标杆 ≈25.5/35 | [`../harness/reviews/2026-11-07-phase2.5-reaudit.md`](../harness/reviews/2026-11-07-phase2.5-reaudit.md)；P0×3 关闭经临时 clone 负向实测；工作树与 HEAD clone 双口径 |

## 局限

- 分数是工程判断，不是标准认证；自评存在乐观偏差，必须看独立复评列。
- 独立复评为只读：未跑 xcodebuild/真机；`verify-claim` 只在 `make end`/`make release-check` 接线（CI/pre-push 不跑动态判定）；`make end` 对 STALE 只告警，`release-check` strict 阻断；行为/性能门禁（P0-1/P0-3）仍缺。
- 真实人类陌生人首访仍缺：Phase 4 的 4/5 可由无上下文 AI 代理复现，但 AI 代理不计入“陌生人”达标，需另招募 1 名人类复核。
- 静态门禁不证明行为正确；真机/性能/体验仍依赖人工。
- 评分随仓库变化，月度或大改后需重评；分数变化必须附证据。

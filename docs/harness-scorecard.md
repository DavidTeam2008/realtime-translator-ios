# Harness 评分卡

> 对象：对译 Duiyi 仓库（2026-11-07 工作树）。方法：五子系统 1–5 分，每分必须有可复核证据；**自评与独立复评分开记录**。
> 相关：[`../HARNESS.md`](../HARNESS.md)（系统地图）、[`decisions.md`](decisions.md)、[`04-roadmap.md`](04-roadmap.md)。

## 当前评分

| 子系统 | 自评 | 独立复评 | 判据与证据 |
| --- | --- | --- | --- |
| Instructions | **4.0** | **4.0** | `AGENTS.md` ≈1576/1650 token；6 个嵌套 AGENTS；6 个 skills frontmatter；`make check-harness` 19 项（§/第N节 引用 7 处 / 13 文件） |
| State | **4.0** | **3.5** | 计划 front matter/唯一 active/未提交交叉核对（`make check-plan`）；`make resume/end`；`harness/README.md` |
| Verification | **4.5** | **4.0** | `make check` 6 组门禁；`verify-static` 含 88 个脚本单测；3 条 clean-tree evidence PASS；`verify-claim` 三值 + 时效/ID/done 绑定硬校验；四层验证矩阵 |
| Scope | **3.5** | **3.0** | L0/L1/L2；计划 `scope.allow/deny`；并发/持久化/发布工程强制红队；无"改动 vs 声明范围"自动机检 |
| Session Lifecycle | **4.0** | **3.5** | 6 个 skills；`make doctor/resume/end`；handoff 协议；未验证项单列 |
| **综合** | **≈4.0 / 5（80%）** | **≈3.6 / 5（72%）** | 等级判定：**L3 条件成立**——`verify-claim` 已接入 `make end`（fresh 告警）与 `make release-check`（strict）；仍缺 commit==HEAD 绑定、证据 ID 硬校验与 pre-push/CI 接线；未达 L4/L5 |

## 对照

| 口径 | 分数 | 说明 |
| --- | --- | --- |
| 改造前独立审计（2026-11-04） | **2.5 / 5** | 文档型 harness：有规则、无结构化证据；验证层不可否证 |
| 对外标杆成熟度（2026-11-06 独立只读 → 2026-11-07 独立复评） | **17/35 → ≈24/35（3.4/5）** | 文档 2→4、包装 1→3、叙事 2→4、可复现 2→3；证据 3、产品 3；外部首访与 clean clone 仍「未验证」 |
| 当前独立复评 | **≈3.6 / 5** | 独立核实所有静态机制通过；扣分集中在验证接线、状态准确性、scope 越界可检性（详见复评报告） |

## 证据索引

- 静态门禁：`make check`（6 组，约 0.3s）/ `make verify-static`（约 4.3s，含 88 个脚本单测）。
- 证据链：`harness/evidence/*.json`（unit / UI / device 三条 PASS，`make verify-claim`）。
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

## 局限

- 分数是工程判断，不是标准认证；自评存在乐观偏差，必须看独立复评列。
- 独立复评为只读：未跑 xcodebuild/真机/clean clone；`verify-claim` 尚未接入 pre-push/CI，旧 evidence 跨 commit 仍可 PASS；§ 引用 sensor 与 scope 越界检测仍需补强（P0/P1 清单见计划 Phase 2.5）。
- 静态门禁不证明行为正确；真机/性能/体验仍依赖人工。
- 评分随仓库变化，月度或大改后需重评；分数变化必须附证据。

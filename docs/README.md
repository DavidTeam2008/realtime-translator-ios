# 文档索引

> 代码是事实来源。文档中的版本号、行号、性能数字如果与代码或最新证据冲突，
> 以代码和 `.apm/` 下的测量记录为准。更新代码时请顺手更新对应文档。

## 先读哪几篇

| 你的目的 | 阅读顺序 |
| --- | --- |
| 刚接手项目 | [`../HANDOFF.md`](../HANDOFF.md) → 本页 → [`13-architecture-analysis.md`](13-architecture-analysis.md) |
| 改语音/翻译链路 | [`13`](13-architecture-analysis.md) §2 → [`06`](06-simultaneous-architecture.md) → [`14`](14-device-test-iphone13.md) |
| 跑真机/补 UI 测试 | [`../HANDOFF.md`](../HANDOFF.md) §3 → [`20`](20-ui-test-hittable-fix.md) |
| 做启动/性能 | [`17`](17-startup-optimization-paused.md) → [`18`](18-startup-feasibility-verification.md) → [`16`](16-startup-measurement-verification.md)；**先看结论，方向已暂停** |
| 看产品设计 | [`09`](09-platform-prototype.md) → [`10`](10-platform-architecture.md) → [`12`](12-platform-roadmap.md) |

## 当前有效

| 文档 | 内容 | 备注 |
| --- | --- | --- |
| [`../HANDOFF.md`](../HANDOFF.md) | 接手说明：环境、构建、测试、坑、架构、下一步 | 2026-10-29 更新 |
| [`13-architecture-analysis.md`](13-architecture-analysis.md) | 分层架构、语音→翻译→持久化全链路、23 条潜在问题、优化分期 | 2026-09-23，仍是最完整的架构分析；行号可能漂移 |
| [`14-device-test-iphone13.md`](14-device-test-iphone13.md) | iPhone 13 真机安装、Instruments/XCUITest 性能、英→中翻译抽测 | 2026-09-23/24 的历史数据；工具限制仍有效 |
| [`19-ended-translation-persistence-fix.md`](19-ended-translation-persistence-fix.md) | 已结束任务译文只更新内存、重进丢失的修复 | 已合入；含一个导出刷新 follow-up |
| [`20-ui-test-hittable-fix.md`](20-ui-test-hittable-fix.md) | UI 测试“存在但不可点击”、权限弹窗、模拟器无听写能力、真机 automation 预热 | 已合入；真机测试入口 `.apm/tools/device-test.sh` |

## 启动优化（已暂停，保留证据）

按阅读顺序：**先看 17/18 的结论，不要直接照 15 的假设开工。**

| 文档 | 内容 |
| --- | --- |
| [`15-startup-optimization.md`](15-startup-optimization.md) | 最初的优化方案（SwiftData 延迟开库、懒加载、二进制重排）。**开头有订正：收益已被实测推翻** |
| [`16-startup-measurement-verification.md`](16-startup-measurement-verification.md) | 真机 A/B：280ms → 279ms，p=0.605；阶段拆分与空白 App 对照；模拟器不能用于启动结论 |
| [`17-startup-optimization-paused.md`](17-startup-optimization-paused.md) | 暂停决定：可优化空间约 64ms，ROI 不划算；已排除方向清单 |
| [`18-startup-feasibility-verification.md`](18-startup-feasibility-verification.md) | 200ms 目标可行性：control p50=210ms，判定 `blocked_by_control_floor` |

## 产品与架构设计历史

`01`–`12` 是 2026-08 的设计稿，大部分已落地。它们解释“为什么这样设计”，
但**不应作为当前实现的逐字规范**：部分文档仍写 iOS 26.0、路线图日期也已过；
当前工程统一为 iOS 26.4。

| 主题 | 文档 |
| --- | --- |
| 面对面 | [`01`](01-product-prototype.md) 原型 · [`02`](02-architecture.md) 架构 · [`03`](03-tech-choices.md) 选型 · [`04`](04-roadmap.md) 路线图 |
| 同声传译 | [`05`](05-simultaneous-prototype.md) 原型 · [`06`](06-simultaneous-architecture.md) 架构 · [`07`](07-simultaneous-tech-choices.md) 选型 · [`08`](08-simultaneous-roadmap.md) 路线图 |
| 平台化（三模块/任务/历史） | [`09`](09-platform-prototype.md) 原型 · [`10`](10-platform-architecture.md) 架构 · [`11`](11-platform-tech-choices.md) 选型 · [`12`](12-platform-roadmap.md) 路线图 |

可交互原型在 [`../prototype/`](../prototype/)，浏览器直接打开。

## 证据与工具（`.apm/`）

`.apm/` 不是运行时依赖，是性能和问题的证据库：

| 路径 | 内容 |
| --- | --- |
| `.apm/tools/device-test.sh` | 真机测试唯一入口：强制先预热 `testmanagerd`，再跑单元/UI |
| `.apm/tools/measure-launch.sh` | 真机冷启动测量：固定命令、warmup、分层口径 |
| `.apm/baseline/README.md` | 哪个 baseline 可用、哪个已作废 |
| `.apm/issues/` | 问题单（含根因、证据、修复状态） |
| `.apm/runs/` | 历次测量原始数据（gitignore，可由脚本重建） |
| `.apm/report.md` | 启动 200ms 演练的完整复盘 |

## 维护约定

- 新文档按 `docs/NN-topic.md` 编号递增，并在本页登记。
- 已完成的修复写“发现 → 红测 → 修复 → 绿测 → 未混入本次的 follow-up”。
- 性能结论必须写清口径（设备、构建、样本量、起止点），否则视为无效。
- 未验证的推断要标注“待验证”，不要把设计意图写成已实现事实。

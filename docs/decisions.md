# 决策记录（D 系列）

> **唯一决策表**：其他文档只引用 D 编号，不复制内容。确认后更新本表并标注日期；未确认前不按假设实现。
> 排期与验收见 [`04-roadmap.md`](04-roadmap.md)；工程决策的完整论证见执行计划与 `references/`。

## D1–D7（产品 / 工程，状态：待确认）

| ID | 决策点 | 当前事实 / 已实现 | 未定问题 | 影响 |
| --- | --- | --- | --- | --- |
| D1 | 启动目标与口径 | 真机冷启动 240–280ms（`AppLaunchTracker`：进程创建 → 首帧提交）；XCTest 口径 0.31–0.33s；200ms 经对照判定不可达（最小对照 p50=210ms，见 [`case-startup-performance.md`](case-startup-performance.md)） | 200ms 是硬指标还是"尽量快"？改判 p50≤300ms 则当前已达标，但需先写入口径 | 性能验收标准；是否重启启动优化（当前暂停） |
| D2 | 发布形态 | App Store / TestFlight / 企业分发均未定；无 Archive/Export 流程、无 PrivacyInfo、无发布 CI | 首发走哪种分发？ | 发布工程、隐私清单、发版验收 |
| D3 | 设备矩阵 | 最低 iOS 26.4、仅 iPhone 竖屏；参考机 iPhone 13（无 Apple 智能），总结走本地回退是预期 | 最低版本是否下调？是否必须覆盖 iPhone 13 与全部六语？ | Speech/Translation 可用性与 UI 适配、真机矩阵 |
| D4 | 语言优先级 | 6 语（中/英/日/韩/泰/越）；听写/翻译依赖系统资源，泰/越需真机抽测 | 六语是否都首发？还是中英先行？ | 质量工作优先级、发布范围与验收 |
| D5 | 数据保留策略 | 历史默认永久保留（本机 SwiftData）；同传 `historyLimit=50`、会议 2 万字符硬停；无自动清理 | 50 条是产品要求还是历史实现？是否提供自动清理？ | P0-2 方案与"导出取全量" |
| D6 | Apple 智能范围 | 总结优先 Apple 智能，不支持时本地摘要回退；iPhone 13 走回退 | 是否要求 iPhone 13 也有"总结"？Apple 智能只用于总结吗？ | P1/P2 产品行为与验收 |
| D7 | 长会策略 | 会议 2 万字符硬停；P0-2 目标为"结束并开续集任务"（同组 ID 关联） | 2 万字是硬限制还是续集触发点？ | P0-2 实现与验收（与 D5 共同决定留存行为） |

## 2026-11 开源标杆化决策（状态：已确认 2026-11-07）

| ID | 决策点 | 结论 |
| --- | --- | --- |
| D-B1 | 许可证 | MIT |
| D-B2 | 公开面语言 | 中文为主 + README 英文概览 |
| D-B3 | 历史过程文档 | 蒸馏后从树中删除，git 历史保留 |
| D-B4 | HANDOFF | 删除并拆分：事实 → docs/CONTRIBUTING，状态 → active 计划 |
| D-B5 | prototype / Order | 删除 `prototype/`；`Order/` 暂留 |
| D-B6 | 仓库改名 | 本轮不改，发布前再定 |
| D-B7 | 发布节奏 | 文档 / 叙事 / 可复现完成后发 `v1.0.0` |
| D-B8 | 产品行为测试 | 独立排期，不阻塞标杆化 |
| D-B9 | 脱敏 | 移除 Team / 设备 ID / 绝对路径；Bundle ID 保留为示例 |
| D-B10 | 过程区目录 | 原 APM 工作区 `.apm/` 更名为 `harness/`（可见、与模板一致） |
| D-B11 | 多 Agent 适配 | 单源 AGENTS + skills 同步 + Claude Code hooks 示例 |
| D-B12 | 模板抽取 | 抽出独立 `harness-kit`（profiles + 脚手架 + 外部试点） |
| D-B13 | 证据 schema v2 | 增加可选 `agent` / `model` / `harnessVersion` 字段 |

## 2026-11 AI Coding 交付改造决策（状态：已确认 2026-11-17）

| ID | 决策点 | 结论 |
| --- | --- | --- |
| D-AI1 | 项目边界 | 保留 `harness-kit` 为仓库级治理内核；新建独立 `ai-delivery-toolchain` 集成 OpenSpec / Superpowers / ECC 与移动端适配；宿主拥有业务规则、契约、CI 与证据，不另造 Harness 内核 |
| D-AI2 | 工件真源 | L0/L1 走 Harness 轻量流程；L2 由 OpenSpec 管行为契约、Harness 管执行/范围/证据、Superpowers 管执行纪律；L3 拆为 L2；ECC 仅为固定版本且经审查的可选素材 |
| D-AI3 | 交付形态 | 第一阶段只交付仓库文件、CLI、skills 与 CI 模板；复用现有 Git/CI，不做 Dashboard、RBAC、审批、Agent 调度或独立后端 |
| D-AI4 | 试点路径 | P0 在 Duiyi 验证单仓流程与 iOS 证据链；P1 在真实 OC + 自研 RN 多仓架构跑通跨仓变更；P2 复制到第二个业务团队后才声称可推广 |
| D-AI5 | 多仓协同 | Change Set 由业务或平台责任仓持有，关联受影响仓库、兼容基线、契约、集成顺序与总验收；各仓保留 Harness 计划与证据，工具链只提供 schema 和校验 |
| D-AI6 | 契约分层 | OpenSpec 只描述外部可观察行为；OC/RN 桥接、原生模块与组件 API 使用版本化技术契约、兼容策略和契约测试，不为每个内部方法编写 Scenario |
| D-AI7 | P0 范围 | 产品切片选择 P1-2 导出竞态与内容不刷新；基础设施切片选择 `xcresult → JUnit → Harness evidence`；只渐进迁移导出模块，不自动生成全 APP OpenSpec 基线 |
| D-AI8 | iOS 证据 | 新产生的测试 PASS 必须具有可独立重算的 artifact，否则为 UNVERIFIED；历史 `requireArtifact:false` 仅作 legacy 保留，不复制到新目标项目 |
| D-AI9 | 工具与组织边界 | P0 只验证 QoderCN 与 Claude Code；外部工具固定版本，桥接能力先 spike；公共通用层与公司私有 Organization Overlay 分离，P1 前确认模型、源码与凭证合规 |
| D-AI10 | 评价与计划 | P0 只评价机制有效性、证据完整性与流程成本，不承诺效率提升；先收口或归档当前开源标杆化 active 计划，再建立独立 P0 L2 计划 |
| D-AI11 | 原生 OpenSpec 执行模式 | 自 P0 收口后的下一个 L2 Change 起，OpenSpec `tasks.md` 为唯一执行计划与任务状态；必须携带 Delivery Contract（base/scope/acceptance/verify/evidence/review/archive gate）。Superpowers 负责执行纪律，Harness 负责 scope、验收、证据与完成判定；ECC 仅为固定版本可选素材。不得同时存在 Harness 任务清单、Superpowers `plan.md` 或可独立决定状态的 ledger。首个原生 Change 前必须先落地 delivery-check、Change Record 单一真源与回滚路径；`status.isComplete` 和仅 `remaining==0` 均不能判定完成。P0 旧 Change 不追溯改写，验收后单独确认归档 |
| D-AI12 | 原生工具参与与 provenance | OpenSpec 工件必须由 `openspec new change` 创建并留下 scaffold/instructions/validate 回执；Superpowers 必须显式调用并留 skill receipt；回执由 delivery-check fail-closed 复算。本地回执只证明“声明/版本/哈希/顺序”，不证明 Agent 真实遵守，最终由 Git 历史 + 独立 review + CI 兜底 |
| D-AI13 | 可移植工具链 | 外部 `ai-delivery-toolchain` 以 annotated tag + PIN（tag/commit/tree/逐文件哈希）固定；宿主只保留配置与薄适配；P3 迁移到全局 CLI + lock + cache，保留 vendored hermetic 选项 |
| D-AI14 | 术语/ADR 落点 | 暂不引入 `GLOSSARY.md` / `docs/adr`；P3 评估 `grill-with-docs` 前先决定术语表与 ADR 的唯一落点；当前持久决策仍只写 `docs/decisions.md` |

# 04 当前问题与优化路线

> 本文是**当前**的工程待办与风险清单，替代早期的 04/08/12 路线图与 13 的问题清单。
> 架构见 [`02-architecture.md`](02-architecture.md)，选型见 [`03-tech-choices.md`](03-tech-choices.md)。
> 每条都尽量给出代码依据；行号会漂移，以类型/函数名为准。
> **真源声明**：本文件的 P0/P1 验收判据与排期是唯一真源；[`decisions.md`](decisions.md) 的 D1–D7 只是决策记录，不影响排期判定；
> 所有待确认决策统一见 [`decisions.md`](decisions.md) 的 **D1–D7**（本文件 §7 只保留指针）。

## 0. 状态

| 项 | 状态 |
| --- | --- |
| 启动优化 | 已暂停；200 ms 目标判定不可达，见 [`case-startup-performance.md`](case-startup-performance.md) |
| 已结束任务译文回填 | 已修复（历史修复记录见 git 历史） |
| UI 测试“存在但不可点击” | 已闭环（结论并入 [`../references/verification.md`](../references/verification.md)） |
| 文档整理 | 2026-11-02 合并 01–13 为 01–04；05–13 已退休 |
| 死代码清理 | 2026-11-02 删除未引用函数/常量/本地化键（见 §5） |
| 测试基线 | 120 单元 + 3 UI = 真机 123；只增不减 |

---

## 1. P0：会丢数据或卡死主链路

### P0-1 单引擎无全局仲裁（最高优先）

**现象**：三个常驻 ViewModel（面对面、同传、会议）共享同一个 `BilingualSpeechEngine` actor。快速切模块、前后台切换、或旧 `stop()` 晚到时，可能出现 A 已 `start`、B 的 `stop()` 后到，把 A 的流 finish 掉。

**代码依据**：

- `RootView` 在首帧后创建三个 VM，都注入 `environment.speechEngine`。
- `BilingualSpeechEngine.stop()` finish 外发流；VM 的 `for await` 退出后走 `handleStreamEnded()`。
- 各 VM 用 `isStopping` 局部缓解，但没有跨 VM 的 generation/owner。

**目标**：引入 App 层 `SpeechSessionGate`（actor 或 `@MainActor` 协调器）：

- 持全局 generation + 当前 owner `FeatureID`。
- `request(owner:)` 先停旧 owner，再启动新 owner；旧流事件因 generation 不匹配被丢弃。
- VM 的 `start/stop` 都经 gate，不直接调 engine。

**验收**：

- 单元测试：A start → B start → A stop 不影响 B；A/B 快速交替 20 次，最终 owner 与状态一致。
- 真机：三模块连续切换 + 前后台 10 次，无“识别暂停”误报、无流被掐断。

### P0-2 长会话的数据留存

**现象**：

| 模块 | 当前 | 风险 |
| --- | --- | --- |
| 面对面 | `transcript` 无上限 | 长会话内存增长，`append` 全量 upsert 变慢 |
| 同传 | `historyLimit = 50`，超出 `removeFirst` | 结束前早期内容已从内存消失，落盘也可能缺失 |
| 会议 | 20,000 字符硬停 | 长会无法继续，只能结束重开 |

**目标**：

- 统一“内存近期窗口 + Store 全量”的策略；同传截断只影响 UI，不丢已 settled 的落盘内容。
- 会议达到上限时提供“结束并新开续集任务”，用组 ID 关联，而不是硬停。
- 历史详情分页加载，避免一次渲染全量。

**验收**：模拟 1 小时文字稿，内存稳定；结束后历史能读回全部行；同传不再丢早期 settled 行。

### P0-3 持久化可靠性与写放大

**现象**：

- `DeferredTaskStore.resolved()` 容器失败时静默降级 `InMemoryTaskStore`，用户以为已保存。
- `SwiftDataTaskStore.append` 每次对传入 entries 全量 upsert 并 `save()`；主线程 `ModelContext`，`autosaveEnabled = true` 又叠加自动保存。
- 无 `SchemaMigrationPlan`，字段变更可能崩库/丢库。

**目标**：

- 降级显性化：首页/历史显示“本机存储不可用”，并打点；不静默丢历史。
- 增量落盘：`append` 只传新增/变更行，或维护脏 ID 集合批量 flush；明确 autosave 与显式 save 二选一。
- 加 v1→v2 迁移演练与自动化测试。

**验收**：注入容器打开失败，UI 有明确提示；长会写入的 save 次数与耗时下降；迁移测试通过。

---

## 2. P1：识别/翻译质量与数据一致性

### P1-1 翻译队列积压

**现象**：`TranslationJobBridge.pending` 只有 1 个槽位，但 host 就绪后 `AsyncStream` 无界；高频 volatile 会排队。`fulfill` 用 `lastAppliedSourceCount` 丢弃过期结果，但积压仍占 session、抬高延迟。同传 voiceOut 档防抖更激进（25/50 ms）。

**目标**：Bridge 改为“每个 utteranceID 只保留最新 job”；`pump` 取最新后清空同 ID 积压；必要时按 session 繁忙度自适应防抖。

**验收**：连续快速说话时，最终译文延迟不随时间增长；无旧 job 在新句之后才返回。

### P1-2 导出竞态与导出内容不刷新

**现象**：

- `TranscriptExportService.cleanupOldExports` 每次导出删除全部 `Duiyi-*.txt`；`ShareLink` 还在读取时可能被删。
- `TaskDetailView` 的 `ExportShareButton` 用 `.task(id: task.id)` 准备文件；任务译文更新后 `task.id` 不变，分享 URL 可能仍是旧内容。

**目标**：

- 文件名带 `taskID`，只清理 7 天前或分享完成后的文件。
- `ExportShareButton` 以 `task` 内容签名（如 `id + entries hash/updatedAt`）触发重新准备，或在分享前同步重写。

**验收**：连续导出/分享不失败；在详情页翻译后立即导出，内容包含新译文。

### P1-3 切换语言后的旧翻译状态

**现象**：语言对变化时 `ConversationView` / `InterpretationView` 用 `.id` 重建 Host，旧 session 取消；但 VM 的 `outboundJob`、`sentSourceText`、`lastAppliedSourceCount`、`utteranceAliases` 等状态可能残留（`resetCaptions` 会清，但 `setUserLanguage` / `handlePairChange` 的时序可能漏一句）。

**目标**：`applyDirectionChange` / `setUserLanguage` / `handlePairChange` 统一清空翻译态：`outboundJob = nil`、取消防抖、清 `sentSourceText`/`lastApplied`/`utteranceAliases`，再重建配置。

**验收**：切换语言立即说话，不出现旧语言译文写入新行；无串行/重复。

### P1-4 中英混读与短句质量

**现象**：

- `UtteranceAssembler.matchesClaimedLanguage` 纯度要求较严（中文路要求 `han ≥ latin`，英文路要求无汉字等），中英混读句可能被两路同时丢弃。
- 面对面 final 后 1 秒内的非自信异语会被 `shouldIgnoreCrosstalk` 丢弃，快速 code-switch 会丢合法内容。
- 文档曾提的 `NLLanguageRecognizer` 第三票未实现。

**目标**：混句不直接丢，按 `resolvedLanguage` 重判；crosstalk 窗口按置信度动态；用固定音频夹具做路由准确率回归。

**验收**：中英混读夹具命中率提升且不增加串音；快速切换说话人不丢整句。

---

## 3. P2/P3：可观测性、音频、TTS、国际化

| # | 问题 | 代码依据 | 建议 |
| --- | --- | --- | --- |
| P2-1 | Detector 失败静默 | `consume(detector:)` catch 只日志 | 降级提示或打点，切句退化可观测 |
| P2-2 | 单路漂移丢句 | `restartSingle` 全量 reset | 切 locale 时保留最后 final，或提示用户 |
| P2-3 | `BufferConverter` 非 float/int16 静默 nil | `copy` 双分支 | 加计数/日志 |
| P2-4 | 双头管理 AudioSession | Capturer 与 Policy 都 `setActive` | 统一走 Policy gate |
| P2-5 | TTS 参数写死 | `rate = default * 1.28` | 语速档/试听；补 `prefersAssistiveTechnologySettings` |
| P2-6 | `StaticLanguageCatalog` 是桩 | `speech/translate/speak` 恒 true | 改为缓存型实查，`LanguageChipGrid` 读目录 |
| P2-7 | 界面文案 `pick` 六参 | `Copy.swift` 遍布六参 | 迁移到 String Catalog，冻结新增 `pick` 参数 |
| P2-8 | MainActor 上的 LCS/compact | `SpokenText.isRefinement` 等在 VM 主线程 | 下沉后台纯函数，缓存 compact 结果 |
| P2-9 | 恢复任务不恢复语言对 | `restore(from:)` 只回放文本 | 恢复 `source/target`，或明确提示使用当前语言 |
| P3-1 | 无迁移计划 | `TaskEntity.schemaVersion` 只写不读 | 加 `SchemaMigrationPlan` 与演练 |
| P3-2 | 空稿/误触结束 | `TaskSessionController.finish` 删除空稿 | 已有确认弹窗，保持 |
| P3-3 | 重复能力检查/摘要/胶囊样式 | 5 套能力检查、4 套摘要、10+ 处 chip | 先抽 `ChipStyle` 与 `ModelPreparation` 协调器，再逐项迁移 |

---

## 4. 明确不做 / 不再投入

- **不重启启动微优化**：200 ms 目标已被控制组地板否定；不要用模拟器证明性能；不要手写 `Order/App.order`。
- **不引入云后端/账号/同步**：违背本机优先与离线承诺。
- **不引入 TCA/RIBs**：三个模块体量不够。
- **不做外放朗读**：回声自激，产品明确禁止。
- **不做实时说话人分离**：当前以语种为路由键；声纹/分离只做技术 spike，不承诺 v1。
- **不在会议记录里做实时同传朗读**：会议目标是全文稿与会后总结。
- **不为了“实时感”无限提高翻译频率**：先解决 P1-1 的队列问题。

---

## 5. 已完成的清理（2026-11-02）

- 文档合并：`01` 产品、`02` 架构、`03` 选型、`04` 本文件；删除已完成的路线图与重复设计稿（05–13），git 历史仍可追溯。
- 删除未引用代码：`CaptionTypography.controlFont`、`Copy.exportHeader`、`Copy.languageUnavailable`、`Copy.summaryLocalFallback`、`TaskSession.characterCount`、`AppLaunchTracker.launchDurationToNow`、`UtteranceAssembler.isShort`、`UtteranceAssembler.finalizeCurrentIfNeeded`、`ConversationLayout.captionAnimationDuration` / `captionAppearOffset`、`DuiyiError.translationUnavailable`。
- 删除 8 个无引用的 `platform.*` 本地化键；保留被 `Text` 字面量使用的键。
- 合并 `ConversationViewModel` / `InterpretationViewModel` 中完全重复的 `failTranslation` 分支，删除仅用于该分支的取消错误分类；`BilingualSpeechEngine.fail` 去掉未使用参数（原 P2-2）。
- 删除仓库根目录已跟踪的过期 Instruments trace；本地 `build/`、`.hvigor/`、`.DS_Store`、未跟踪 trace 不进入版本库。
- 修正 `docs/02` 对 `.id` 重建、`DeferredTaskStore`、`modelRetention` 的描述；`tools/generate-order-file.sh` 指向现存文档。

---

## 6. 建议排期

> 本节是排期的唯一真源；[`decisions.md`](decisions.md) 的决策记录按同一顺序导航，不重复预估。

| 顺序 | 事项 | 依赖 | 预估 |
| --- | --- | --- | --- |
| 1 | P0-1 `SpeechSessionGate` + 测试 | 无 | 3–5 天 |
| 2 | P0-3 降级显性化 + 增量落盘 | 无 | 3–5 天 |
| 3 | P1-2 导出竞态 + 刷新 | 无 | 1–2 天 |
| 4 | P1-3 语言切换清态 | 无 | 1 天 |
| 5 | P1-1 翻译队列合并 | 无 | 2–3 天 |
| 6 | P0-2 长会话分段 | P0-3 | 1–2 周 |
| 7 | P1-4 混读/短句质量 | 真机夹具 | 1–2 周 |
| 8 | P2-6 语言目录实查 | 无 | 2–3 天 |

同一失败检查修复 2 次仍失败，或同一子任务 3 轮修复-验证无进展时停止上报（团队规则）。

---

## 7. 交接前需要确认的产品/工程决策

决策已合并到 [`decisions.md`](decisions.md) 的 **D1–D7**（唯一真源，含“启动目标/口径”与“长会策略”）；
本文件不再保留重复列表，只在此留指针。未确认前，不按假设实现 P0-2/P0-3 的产品侧行为。

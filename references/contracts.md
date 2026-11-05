# 契约与铁律细则

> 触发：改 `Services/Speech|Audio|Translation|SpeechSynthesis|Persistence|Export`、
> `Features/*/` ViewModel、`Domain/TaskSession*`，或准备发版时读。
> 真源优先级见 [`docs/README.md`](../docs/README.md)；与 `docs/02`/`docs/04` 冲突时，以代码和最新验证为准。

## 1. 分层与依赖方向

Features 只依赖 Domain + Services 协议；Domain 不 import SwiftUI/语音/翻译/SwiftData；Services 不引用 ViewModel。新模块按 HANDOFF §4.4 六步改；`RootView.destination(for:)` 的 switch 手动补。

## 2. 翻译会话锚在 View

`TranslationSession` 不能塞进 Service；现有实现是 `Color.clear` 常驻 + `.translationTask(config)`，语言对变化靠 `.id` 重建。不要绕过 `TranslationHostView` / `OneWayTranslationHostView`。job 合并/过期丢弃在 `TranslationJobBridge`；P1-1 前不扩大缓冲。

## 3. 单一语音引擎与 SpeechSessionGate

- 现行：`RootView` 首帧后创建三个常驻 VM，共用 `AppEnvironment.speechEngine`；不给每个 VM 建引擎（麦克风/`AVAudioSession` 独占），不用“每 VM 加锁”代替仲裁。
- P0-1（未实现）：App 层 `SpeechSessionGate` actor，持 generation + owner(`FeatureID`)；start/stop 经 gate；旧 owner 自动失效；每个 `for await` 校验 token。
- 并发测试：假引擎记录 start/stop 顺序，覆盖 20 次模块切换、10 次前后台。

## 4. 任务语义

显式“新任务 → 结束任务”；只有 `ended` 进历史；空稿结束自动删除；暂停只停麦克风。后台/切模块只停听，不自动结束；结束才全量落盘。

## 5. 实时字幕以内存为准

现场字幕 / `PaneState` 是内存事实；`TaskStore` 落盘异步（250ms debounce）。View 不直接读 SwiftData 当实时状态；历史详情只读，不复用现场 `CaptionLine` 状态机。P0-2 目标：Store 全量、UI 窗口；会议到上限“结束并开续集任务”，不硬停。

## 6. 测试基线只增不减

计数见 `references/verification.md`；新测试放 `DuiyiTests/`。既有断言零修改；方向性翻转须在计划/PR 说明。模拟器无 `SpeechTranscriber`，`testSimultaneousListeningPressure` skip 是预期；不得 mock 能力检查来“修绿”。
## 7. 启动优化已暂停

200ms 不可达（`docs/18`：最小对照 p50 已 210ms）。不重启微优化；不用模拟器证明性能。`Order/App.order` 禁止手写；`ORDER_FILE` 只在 Release 生效，Debug 不开。

## 8. 签名、导出与仓库卫生

- Team `REDACTED_TEAM_ID` / `com.david.Duiyi` 写在工程；不在该 Team 时 App + 两个测试 target 都改，且不提交别人的 Team。
- 导出（P1-2）：不要删全部 `Duiyi-*.txt`；文件名带 taskID + 时间戳。
- 不提交 `build/`、`.apm/runs/`、trace、`xcuserdata/`。

## 9. 未定决策

决策见 `HANDOFF.md` §6 的 D1–D7（唯一真源，含启动口径与长会策略）；D5/D7 未确认前，不按假设实现 P0-2/P0-3 的产品侧行为。先问再写回。

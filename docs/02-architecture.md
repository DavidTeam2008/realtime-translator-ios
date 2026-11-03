# 02 架构（当前实现）

> 本文以 `Duiyi/` 代码为准，描述 2026-11 的现状。
> 产品行为见 [`01-product-design.md`](01-product-design.md)，选型理由见 [`03-tech-choices.md`](03-tech-choices.md)，
> 已知问题与排期见 [`04-roadmap.md`](04-roadmap.md)。

## 0. 基线

| 项 | 当前值 |
| --- | --- |
| 部署目标 | iOS 26.4，仅 iPhone、仅竖屏 |
| 语言/工具链 | Swift 6.0，Xcode 26.4+（本机 27.1） |
| 第三方依赖 | 无；全部系统框架 |
| 系统能力 | SpeechAnalyzer / SpeechTranscriber / SpeechDetector、Translation.framework、AVSpeechSynthesizer、SwiftData、FoundationModels、SwiftUI |
| 离线承诺 | 无后端、无 API Key；音频不上传、不落盘 |

---

## 1. 分层与依赖

```
Duiyi/
  App/            入口、依赖组装、导航、偏好、预览夹具
  Features/       Home / Conversation / Interpretation / Meeting / History / Onboarding / Settings / Shared
  Domain/         纯模型、路由、任务语义、文案、错误
  Services/       Audio / Speech / SpeechSynthesis / Translation / Persistence / Summary / Export / Assets / Permissions / Diagnostics
  DesignSystem/   Tokens、通用卡片、历史行、安全区
DuiyiTests/       120 个 Swift Testing 单元测试
DuiyiUITests/     3 个 XCUITest 用例
```

依赖方向严格单向：

| 层 | 允许依赖 | 禁止 |
| --- | --- | --- |
| App | 全部；负责构造实现并注入 | 编写字幕合并/翻译业务规则 |
| Features | Domain、DesignSystem、`AppEnvironment` 注入的协议 | 直接 `import Speech` / `AVFAudio`；引用其他 Feature 的 ViewModel |
| Domain | Foundation/CoreGraphics 级纯模型 | SwiftUI、Speech、Translation、SwiftData |
| Services | Domain + 系统框架 | 引用任何 Feature ViewModel |
| DesignSystem | SwiftUI | 业务状态机 |

两个系统约束必须写进设计，而不是假装它们不存在：

1. **`TranslationSession` 只能锚在 View 上**（`.translationTask`）。Service 层只产生 `TranslationJob`，由 `TranslationHostView` / `OneWayTranslationHostView` 执行并回调 ViewModel。
2. **`SpeechAnalyzer` 是长生命周期资源**。当前由一个 `BilingualSpeechEngine` actor 统一持有，三个常驻 ViewModel 共享；尚无中央仲裁（P0-1，见 [`04-roadmap.md`](04-roadmap.md)）。

---

## 2. 组装、导航与生命周期

### 2.1 AppEnvironment

`Duiyi/App/AppEnvironment.swift` 是唯一的依赖组装点，`@MainActor @Observable`，持有：

| 依赖 | 默认实现 | 用途 |
| --- | --- | --- |
| `PreferencesStore` | `UserDefaults` | 语言、字号、自动开始、引导进度、模块偏好 |
| `PermissionGranting` | `PermissionService` | 麦克风/语音识别授权 |
| `SpeechModelPreparing` | `SpeechAssetPreparer` | 端侧听写模型安装 |
| `TranslationAvailabilityChecking` | `TranslationAvailabilityService` | 语言对可用性 |
| `SpeechRecognizing` | `BilingualSpeechEngine` | 双/单路听写 |
| `ConversationSummarizing` | `FoundationModelsSummarizer` | Apple 智能摘要 + digest 回退 |
| `AudioSessionConfiguring` | `AudioSessionPolicy` | AVAudioSession 与路由 |
| `SpeechSynthesizing` | `SystemSpeechSynthesizer` | 同传朗读 |
| `TaskStore` | `DeferredTaskStore` | 任务持久化 |
| `ExportSharing` | `TranscriptExportService` | 导出文本 |
| `LanguageCataloging` | `StaticLanguageCatalog` | 语言目录（当前为静态桩） |

`DuiyiApp` 用 `@State` 持有 `AppEnvironment` 和 `AppCoordinator`，通过 `.environment()` 注入。

### 2.2 启动路径

```
DuiyiApp.init
  └─ AppEnvironment.init                    // 不打开数据库
       └─ DeferredTaskStore.init            // 后台 utility 任务开始 openContainer
RootView.body
  ├─ HomeView 首帧
  ├─ onAppear → 下一 runloop markFirstFrame
  └─ .task(priority: .utility)              // 首帧之后
       ├─ DeferredTaskStore.warm()
       └─ rebuildViewModelsIfNeeded()       // 四个常驻 VM
```

启动优化已暂停，结论见 [`15`](15-startup-optimization.md)–[`18`](18-startup-feasibility-verification.md)。当前不重启微优化，也不用模拟器证明性能。

### 2.3 导航

`AppCoordinator` 持有 `NavigationPath`，路由只有：

```swift
enum AppRoute {
    case conversation
    case interpretation
    case meeting
    case history
    case taskDetail(UUID)
}
```

- 首页 `FeatureRegistry.modules` 三张功能卡 + 历史卡；新增模块需加 `FeatureID` case、Feature 目录、`AppRoute` case、`RootView.destination` 分支和 Registry 一行。
- `RootView.destination(for:)` 仍是显式 `switch`；当前只有三模块，可接受。
- 引导用 `fullScreenCover`，由 `PreferencesStore.hasCompletedOnboarding` 驱动。

### 2.4 常驻 ViewModel

`RootView.rebuildViewModelsIfNeeded()` 在首帧后创建：

- `ConversationViewModel`
- `InterpretationViewModel`
- `MeetingViewModel`
- `HistoryViewModel`

三个会话 VM 常驻，保证切模块时任务/字幕不丢；它们共享同一个 `environment.speechEngine`。`scenePhase != .active` 时依次 `stop(restoreIdleTimerAfterDelay: false)`，只停麦克风，不结束任务。

---

## 3. 音频链路

```
麦克风
  → AVAudioEngine inputNode.installTap(bufferSize: 1024)
  → BufferConverter.copy / convert
  → AsyncStream<SendablePCMBuffer>
  → BilingualSpeechEngine
```

### 3.1 AudioEngineCapturer

`actor AudioEngineCapturer`：

- `start()` 先 `stop()` 保证幂等，再 `setActive(true)`、安装 tap、返回 `AsyncStream`。
- tap 回调中复制 buffer 后 `yield`，不切主线程。
- `stop()` finish 流、移除 tap、停引擎、`setActive(false)`。
- `BufferConverter` 只处理 float/int16；其他格式返回 nil（当前静默丢包，P2）。

### 3.2 AudioSessionPolicy

`actor AudioSessionPolicy` 是唯一设置 category 的地方：

| 用例 | category / mode / options |
| --- | --- |
| 面对面 | `.record` / `.measurement` / `[.duckOthers]` |
| 同传（只字幕） | `.record` / `.measurement` / `[.duckOthers]` |
| 同传（读出） | `.playAndRecord` / `.default` / `[.duckOthers, .allowBluetoothA2DP]`，并 `overrideOutputAudioPort(.none)` |

- 优先内置麦克风与底部数据源。
- 通过 `routeChangeNotification` 广播 `AudioRouteSnapshot`。
- `AudioEchoPolicy.canSpeakWithoutEcho`：输出或输入里有耳机类路由才允许朗读；外放不允许。
- 无后台音频模式；失活时 `setActive(false, .notifyOthersOnDeactivation)`。

---

## 4. 听写：BilingualSpeechEngine

`actor BilingualSpeechEngine` 实现 `SpeechRecognizing`，对三个模块提供同一接口：

```swift
func start(
    languages: [AppLanguage],
    fallbackLanguage: AppLanguage,
    style: SpeechRecognitionStyle
) async throws -> AsyncStream<Utterance>
func stop() async
```

### 4.1 管线选择

1. `normalizedLanguages` 去重、补 fallback、最多取前 2 种。
2. 两种语言 → 先试 `startMultiPipeline`：每语言一个 `SpeechTranscriber` + 一个 `SpeechDetector(medium)`。
3. 命中资源上限（`insufficientResources` / `tooManyAssetLocalesAllocated`）→ 逐个丢弃 locale 重试；仍失败则退到单路 fallback。
4. 三模块超限 → 去掉 Detector 重试；再失败退单路。
5. 单路模式运行中若 final 语言漂移 → `restartSingle` 重建管线并 reset assembler；兼容路径，会丢一小段，无用户提示。

`SpeechTranscriber` 配置：`[.volatileResults, .fastResults]`、`[.etiquetteReplacements]`、`[.transcriptionConfidence]`。
会议用 `SpeechAnalyzer.Options(priority: .userInitiated, modelRetention: .whileInUse)`；实时字幕用默认 Options。

### 4.2 切句

- 每个 transcriber 的 partial/final 进入 `UtteranceAssembler.ingest`。
- final 后 `acknowledgeFinal` 保持 1.0 秒，抑制同句尾巴被另一路重复接收。
- Detector 判定无语音超过 `ConversationLayout.silenceCommitMilliseconds = 1100 ms` → `silenceTimedOut` 强制 final，并保持 0.8 秒。
- `publish` 以 `(language, 归一化文本)` 签名去重 final。

### 4.3 UtteranceAssembler

纯值 `struct`，核心职责：

- **语言纯度门禁**：`matchesClaimedLanguage` 按脚本统计拒绝明显不属于该路的文本（如中文路收到纯拉丁、英文路收到汉字）。
- **抢占**：锁定语言后，异语候选只有 `nativeUnits` 明显超过当前句才抢占。
- **同句更新**：同一 `utteranceID` 原地更新；continuation/refinement 合并，不新开行。
- **短句抑制**：`isConfident` 对短确认语不自信，沿用上一句语种，减少「嗯 / um」误切。
- **六语脚本阈值**：中/日/韩/泰/越/英各有独立计数与阈值；`resolvedLanguage` 可按文本重新判定会议行的实际语言。

### 4.4 流结束

`stop()` cancel 静音任务、finish 外发流、停止 analyzer；VM 的 `for await` 退出后走 `handleStreamEnded()`。
`fail()` 只 finish 流、不带错误，ViewModel 统一映射为 `recognitionInterrupted`；当前不区分权限/资源/中断。若将来需要区分，需要给流增加错误通道。

---

## 5. 翻译：View 锚定 + 桥

### 5.1 Host

`Duiyi/Features/Conversation/TranslationHostView.swift`：

- `TranslationHostView`：面对面双向，两个 `TranslationSession.Configuration`（user→peer、peer→user），两个 `TranslationJobBridge`。
- `OneWayTranslationHostView`：同传/会议详情单向，一个 configuration、一个 bridge。
- `TranslationPrepareHost`：引导/换语言时 `prepareTranslation()`，成功后回调。

configuration 使用：

```swift
TranslationSession.Configuration(
    source: from.localeLanguage,
    target: to.localeLanguage,
    preferredStrategy: .lowLatency
)
```

调用方用 `.id("<user>-<peer>")` / `.id("<source>-<target>")` 包住 Host（`ConversationView`、`InterpretationView`、`OnboardingView`），语言对变化时销毁并重建 View，两个 session 和 bridge 一起重建；旧 session 的失败（包括 14/20、`CancellationError`）只清空当前 job，不写入新语言对。`TaskDetailView` 的单向翻译按 `<source>-<utteranceID>` 逐条重建。

### 5.2 TranslationJobBridge

`NSLock` + `AsyncStream` + **一个 pending 槽位**：

- Host 未就绪（`translationTask` 还没启动）时，只保留最后一个 job。
- Host 已就绪时直接 `yield` 到无界 `AsyncStream`，由 `pump` 串行 `session.translate`。
- 因此高频 volatile 在 host 就绪后仍可能排队；`fulfill` 用 `lastAppliedSourceCount` 丢弃源字数倒退的过期译文（P1-1）。

### 5.3 节流与去抖

`ConversationViewModel.enqueueTranslation`（同传复用同一阈值）：

- 空文本剪枝。
- 同一行同文本且非 final → 不重复发送。
- 立即发送：final、文本以从句标点结尾、或首包且文本值得翻译。
- 否则防抖：首包 40 ms，后续 90 ms；同传 voiceOut 开启时 25/50 ms。
- 翻译结果按 `utteranceAliases` 找行；`applyTranslation` 同时尝试写入两侧 pane，再更新 transcript。

### 5.4 取消

`TranslationErrorDomain` 14/20 与 `CancellationError` 视为过期，不弹错。真正失败只记日志/状态，不把系统错误直接丢上字幕板。

---

## 6. 三个 Feature 的流水线

### 6.1 面对面

```
Utterance
  → shouldIgnoreCrosstalk（final 后 1s、异语、非自信 → 丢弃）
  → LanguageRouter.targetSide(detected, userLanguage)
  → 确定 listener / speaker
  → PaneState.applyLive（续句/问候/新句）
  → upsertTranscript
  → enqueueTranslation → TranslationHostView
  → fulfill → PaneState.applyTranslation + transcript
  → settled 时 schedulePersist(250ms)
```

- `routedSideByUtterance` 固定同一句的去向，避免 partial 改语言导致左右跳。
- `SpokenText.isContinuation` / `isDistinctGreeting` 处理 ASR 修订与「嗨 Jack / 嗨 Lucy」独立问候。
- 暂停/后台 `persistNow()`；结束任务 `finish(entries:)` 全量落盘。
- 清屏只清 pane/transcript/翻译状态，不停听、不结束任务。

### 6.2 同声传译

```
Utterance
  → guard utterance.language == sourceLanguage
  → PaneState.applyLive + transcript
  → enqueueTranslation（单向 source→target）
  → fulfill → 字幕
  → settled → ClauseSplitter.consume → TTS 队列
```

- `historyLimit = 50`，超出 `removeFirst`。
- 朗读只接受 settled；volatile 需终止标点 + 最小长度。`speechSettleDelay = 380 ms` 合并 ASR 尾修。
- `pendingJobs` 上限 10；去重使用已读前缀、280 字 `spokenCompactTail` 和队列内 compact 拼接。
- `speechGeneration` 令牌防止旧朗读任务在暂停/换方向后继续。
- 方向/语言变化停听、清 live、清队列、重建配置；历史保留。

### 6.3 会议记录

```
MeetingRecognition.languages(multilingual:pinned:display:)
  → start(languages:..., fallback:..., style: .meetingNotes)
  → accept: 非多语时丢弃非 sourceLanguage
  → UtteranceAssembler.resolvedLanguage 给每行定实际语种
  → PaneState + transcript（无翻译）
  → settled 时 20,000 字符检查
```

- 多语言：`[display, display.defaultPeer]`；单语：只跑 pinned。
- 达到字符上限：`isLengthLimited = true` 并停止；不自动续记。
- 会议详情可逐条单向翻译并 `updateTranslations` 回填，不新增条目。

---

## 7. 任务与持久化

### 7.1 Domain 语义

`TaskSession`：`id / feature / status / startedAt / endedAt / title / subtitle / sourceLanguage / targetLanguage / entries / summary`。

`TaskStatus`：`running / pausedListening / ended`。只有 `ended` 进历史；空稿结束自动删除。

`TaskSessionController` 封装一个 Feature 的当前任务：

- `restore()` 恢复未结束任务。
- `beginNew()` 自动结束上一个任务后新建。
- `persist()` upsert 文字稿。
- `setListening()` 只改 running/pausedListening。
- `finish()` 先 append，空稿 delete，否则 end。

### 7.2 DeferredTaskStore

`DeferredTaskStore` 是 `TaskStore` 的延迟包装：

- `init` 不阻塞主线程，后台 `Task.detached(priority: .utility)` 打开 `ModelContainer`。
- 第一次实际调用（首页未完成任务、历史、恢复）时 `resolved()` 等待容器。
- 容器打开失败 → 静默降级 `InMemoryTaskStore`，仅日志，用户无感知（P0-3）。
- `RootView` 首帧后再 `warm()`，通常用户导航时已就绪。

### 7.3 SwiftData

`schema = [TaskEntity, TranscriptEntity]`：

- `TaskEntity`：任务元数据、状态、摘要、`schemaVersion`。
- `TranscriptEntity`：按 `taskID` 关联、cascade 删除、`sortIndex` 保序。
- `SwiftDataTaskStore` 使用主线程 `ModelContext(autosaveEnabled: true)`。
- `append` 对传入 entries 全量 upsert 后 `save()`；`updateTranslations` 只回填已有条目的译文，允许已结束任务。
- `list` 只取 `ended`，倒序；`end` 补会议 subtitle。
- 尚无 `SchemaMigrationPlan`（P3）。

写入点统一：settled 时 250 ms 防抖、暂停/后台立即、结束全量。实时字幕始终以内存为准，View 不直接读 SwiftData。

---

## 8. 总结、导出、资源、权限

- **总结**：`FoundationModelsSummarizer` 按 `SystemLanguageModel.availability` 分支；可用则 `LanguageModelSession`，失败/不可用回退 `digest`（按 speaker 分组）。
- **导出**：`TranscriptExportService` 写 Caches，UTF-8 原子写；每次导出前删除全部 `Duiyi-*.txt`（P1-2 竞态）；`ShareLink` 分享。
- **模型准备**：`SpeechAssetPreparer` 用 `SpeechTranscriber(preset: .progressiveTranscription)` 占位模块创建 `AssetInventory` 安装请求，200 ms 轮询进度。
- **翻译可用性**：`TranslationAvailabilityService` 双向查 `LanguageAvailability` 并合并状态。
- **权限**：`PermissionService` 映射麦克风/语音识别四态；`requestAccess` 先麦后音后重查。
- **语言目录**：`StaticLanguageCatalog` 目前恒 `speech/translate/speak = true`；真实能力探测仍散在 View。这是 P2 已知问题。

---

## 9. 并发模型

| 组件 | 隔离 | 原因 |
| --- | --- | --- |
| `BilingualSpeechEngine` | `actor` | tap、analyzer 流、任务取消 |
| `AudioEngineCapturer` | `actor` | AVAudioEngine 非线程安全 |
| `AudioSessionPolicy` | `actor` | session/route 通知 |
| `SpeechAssetPreparer` | `actor` | 下载与进度回调 |
| `AppEnvironment` / 三个会话 VM / `HistoryViewModel` | `@MainActor` | 驱动 SwiftUI |
| `TaskSessionController` / `SwiftDataTaskStore` | `@MainActor` | 主上下文 |
| `LanguageRouter` / `UtteranceAssembler` / `SpokenText` / `ClauseSplitter` | `Sendable` 值语义 | 可重入、可单测 |
| `SystemSpeechSynthesizer` | `@MainActor` + delegate | AVSpeechSynthesizer 代理回调 |
| `TranslationJobBridge` | `@unchecked Sendable` + `NSLock` | 跨 View 任务与流 |

`SendablePCMBuffer` 用 `@unchecked Sendable` 包装 `AVAudioPCMBuffer`，跨 actor 传递，责任在音频层。

---

## 10. 测试与验证

| 层级 | 覆盖 | 入口 |
| --- | --- | --- |
| Domain 纯逻辑 | 路由、assembler、spoken 合并、clause、任务映射、摘要 digest | `make test` |
| ViewModel | 三模块状态机、翻译过期丢弃、清屏、任务恢复、TTS 队列 | `make test` |
| 音频策略 | 路由快照/回声判定 | `make test` |
| UI | 冷启动、首页导航、同传听写压力 | `make test-ui` / `make device-test` |
| 真机 | 语音、翻译、TTS、持久化、长会话 | `.apm/tools/device-test.sh` |

基线：120 个单元测试 + 3 个 UI 用例 = 真机 123。模拟器没有 `SpeechTranscriber`，`testSimultaneousListeningPressure` 会 skip，这是预期行为。精确口径见 [`references/verification.md`](../references/verification.md)。

---

## 11. 已知架构风险（摘要）

完整问题、证据与排期见 [`04-roadmap.md`](04-roadmap.md)。

- **P0-1 单引擎无仲裁**：三个常驻 VM 共享一个 `BilingualSpeechEngine`，快速切模块/前后台时 stop/start 可能互相掐断；`SpeechSessionGate` 尚未实现。
- **P0-2 长会话留存**：Conversation transcript 无上限；Interpretation 50 条截断；Meeting 2 万字硬停。
- **P0-3 持久化可靠性与写放大**：容器失败静默降级内存；`append` 全量 upsert；无迁移计划。
- **P1**：翻译桥积压、导出清理竞态、切语言旧翻译状态、中英混读丢弃、单路漂移丢句。
- **P2/P3**：Detector 失败静默、`fail` 吞因、TTS 参数写死、`StaticLanguageCatalog` 为桩、MainActor 上的 LCS 计算、非音频格式静默丢包。

---

## 12. 关键文件索引

| 主题 | 文件 |
| --- | --- |
| 入口/组装 | `Duiyi/App/DuiyiApp.swift`、`AppEnvironment.swift`、`RootView.swift`、`AppCoordinator.swift`、`FeatureRegistry.swift`、`PreferencesStore.swift` |
| 音频 | `Duiyi/Services/Audio/AudioEngineCapturer.swift`、`BufferConverter.swift`、`AudioSessionPolicy.swift` |
| 听写 | `Duiyi/Services/Speech/BilingualSpeechEngine.swift`、`UtteranceAssembler.swift`、`Duiyi/Services/ServiceProtocols.swift` |
| 翻译 | `Duiyi/Features/Conversation/TranslationHostView.swift`、`Duiyi/Domain/Models/TranslationJob.swift`、`Duiyi/Services/Translation/TranslationAvailabilityService.swift` |
| 面对面 | `Duiyi/Features/Conversation/ConversationView.swift`、`ConversationViewModel.swift`、`CaptionPaneView.swift`、`ListeningControl.swift` |
| 同传 | `Duiyi/Features/Interpretation/InterpretationView.swift`、`InterpretationViewModel.swift`、`DirectionBar.swift`、`VoiceOutControl.swift`、`Duiyi/Domain/Models/Clause.swift` |
| 会议 | `Duiyi/Features/Meeting/MeetingView.swift`、`MeetingViewModel.swift` |
| 任务/持久化 | `Duiyi/Domain/TaskSession.swift`、`Duiyi/Services/Persistence/DeferredTaskStore.swift`、`SwiftDataTaskStore.swift`、`TaskEntities.swift`、`InMemoryTaskStore.swift` |
| 总结/导出 | `Duiyi/Services/Summary/FoundationModelsSummarizer.swift`、`Duiyi/Services/Export/TranscriptExportService.swift` |
| 任务详情 | `Duiyi/Features/History/HistoryView.swift`、`HistoryViewModel.swift`、`TaskDetailView.swift` |
| 设计系统 | `Duiyi/DesignSystem/Tokens.swift`、`HomeModuleCard.swift`、`HistoryRow.swift`、`ScreenSafeArea.swift` |

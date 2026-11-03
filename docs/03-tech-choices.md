# 03 技术选型（当前实现）

> 记录**现在采用的方案、理由和边界**，不是早期设计稿。
> 架构细节见 [`02-architecture.md`](02-architecture.md)，问题与排期见 [`04-roadmap.md`](04-roadmap.md)。

## 0. 约束

| 约束 | 值 | 影响 |
| --- | --- | --- |
| 部署目标 | iOS 26.4+ | 直接使用 SpeechAnalyzer / FoundationModels，不维护旧 Speech 兼容路径 |
| 设备 | iPhone，仅竖屏 | 不做 iPad/横屏/分屏布局 |
| 依赖 | 无第三方 | 全部系统框架，包体小、供应链简单 |
| 网络 | 无后端、无密钥 | 听写/翻译/总结都依赖系统端侧能力 |
| 隐私 | 音频不落盘、不上传 | 只持久化文字稿 |

---

## 1. 决策总表

| 问题 | 采用 | 明确不选 | 理由 |
| --- | --- | --- | --- |
| UI | SwiftUI | UIKit 主界面 | 对话字幕是状态驱动；Translation 也锚在 View |
| 状态 | `@Observable` + `@MainActor` | `ObservableObject` + Combine | 更新粒度细，少一层 `objectWillChange` |
| 并发 | Swift 6 严格并发 + `actor` | 自由 GCD / delegate 拼盘 | 音频/识别必须离开主线程且可取消 |
| 听写 | `SpeechAnalyzer` + `SpeechTranscriber` | `SFSpeechRecognizer` | 端侧、远场、长时；旧 API 默认可上云 |
| 多语并行 | 最多两路 transcriber | 每语言一路 / 运行中热切单路 | 双路覆盖面对面双向；资源上限内可降级 |
| 切句 | `SpeechDetector` + 1100 ms 静音 + final 保持 | 只靠 `isFinal` | 对话需要可预期句边界 |
| 语种判定 | 双路脚本融合 + assembler 纯度门禁 | 单独 LID 模型 / 用户按钮选说话人 | 已在算，延迟低；按钮破坏产品承诺 |
| 翻译 | `Translation.framework` | 云翻译 / 端侧 LLM | 离线、无密钥、与系统翻译包共享 |
| TTS | `AVSpeechSynthesizer` | 云 TTS / 自训模型 | 系统离线、六语有声、工程成本低 |
| 朗读策略 | 仅耳机类路由；从句级 | 外放朗读 / 逐 volatile 读 | 外放会回灌麦克风；读半句体验差 |
| 音频会话 | `.record/.measurement`；朗读时 `.playAndRecord/.default` | `.voiceChat` 全程 | measurement 保留干净 PCM；AEC 可能压掉对面 |
| 存储 | SwiftData + `TaskStore` 协议 | Core Data 重栈 / JSON / UserDefaults | 类型映射自然、可注入内存实现 |
| 总结 | FoundationModels，失败回退 digest | 云 LLM | 无网络依赖；13 不支持就明说 |
| 导出 | Caches 文本 + `ShareLink` | 第三方 SDK / 深链 | 系统分享覆盖所有目标 App |
| DI | 手动构造 + 协议注入 | TCA / RIBs / Swinject | 三个模块体量不值得引入框架 |
| 本地化 | `Copy` 六语 `pick` + 少量 xcstrings | 全量 String Catalog（当前未完成） | 现场语言与界面语言共用一套枚举，迁移成本可控 |

---

## 2. 语音：SpeechAnalyzer + SpeechTranscriber

### 2.1 为什么

- **端侧**：音频不出设备，满足产品承诺；`SFSpeechRecognizer` 默认可走服务器。
- **远场/长时**：系统模型按会议/讲座训练，适合桌面距离。
- **模块化**：同一 `SpeechAnalyzer` 可挂多个 `SpeechModule`。
- **资源可预装**：`AssetInventory.assetInstallationRequest(supporting:)` 可在引导期下载。

### 2.2 双路与单路

| 模块 | 听写路数 | 原因 |
| --- | --- | --- |
| 面对面 | 2（用户语言 + 对方语言） | 识别语种就是路由键 |
| 同声传译 | 1（源语言） | 方向由用户定；第二路会把旁路语言写进字幕 |
| 会议单语 | 1（记录语言） | 现场只有一个主声源 |
| 会议多语 | 2（我看的语言 + 默认对侧） | 允许中英混说，每行标实际语种 |

双路不是无条件成功：命中 `insufficientResources` / `tooManyAssetLocalesAllocated` 时逐个丢弃 locale，仍失败退单路。这是明确的兼容路径，不是隐藏行为。

### 2.3 切句

- `SpeechDetector` 提供语音活动；静音 1100 ms 强制 final。
- final 后保持 1.0 秒，抑制另一路把同一句尾巴再吐一遍。
- 短句置信度不足时沿用上一句语种，减少「嗯 / um」误切。
- 单路模式运行中语种漂移会重启管线；会丢一小段，当前无用户提示。

### 2.4 不选

| 方案 | 不选原因 |
| --- | --- |
| 单独端侧 LID | 额外模型、额外延迟；双路脚本融合已够用 |
| 运行中热切单个 recognizer | 会丢当前句；双路更适合中英插话 |
| `DictationTranscriber` | 偏听写/标点，实时对话字幕用 `SpeechTranscriber` 更合适 |
| 打开 `ignoresResourceLimits` | 失败不可预测，不作为默认 |

---

## 3. 翻译：Translation.framework

### 3.1 为什么

- 翻译模型与语言资源由系统统一管理，通常与系统「翻译」App 共用；App 不能访问、打包或替换模型文件。
- `LanguageAvailability.status(from:to:)` 区分 `installed`（可离线）、`supported`（已支持但需下载）、`unsupported`（不支持）。
- `prepareTranslation()` 可在引导期提前触发语言资源准备，避免对话中弹系统下载确认；仍须在 `.translationTask` 的 Host View 内执行。
- `preferredStrategy: .lowLatency` 适合实时字幕。

> 与 Core ML / Core AI 不是同一层：后两者运行开发者自带的模型；Translation.framework 只提供系统翻译任务，模型与语言资产不通过公开 API 暴露。Foundation Models 同样是独立的高层 API，本 App 只用于总结。

### 3.2 强制约束

1. `TranslationSession` 只能由 `.translationTask` 在 View 上创建，不能塞进 Service 当单例。
2. 源/目标使用 `AppLanguage.localeLanguage`（`Locale.Language`），不手写字符串 identifier。
3. 面对面两个方向各一个 configuration；同传/详情只挂需要的方向。
4. 中间结果可送译，但必须节流；final 必送并用 final 覆盖。
5. 失败回调只清空当前 job、不弹错；旧 session 的取消错误（`TranslationErrorDomain` 14/20、`CancellationError`）因此自然被当作过期丢弃。

### 3.3 不选

| 方案 | 不选原因 |
| --- | --- |
| 云翻译 API | 需要网络/密钥/隐私协议，延迟不稳定 |
| 端侧 LLM 翻译 | 包体、发热、质量与系统翻译包相比无优势 |
| 每次识别新建语言对 | 反复 invalidate，闪系统下载界面 |

---

## 4. 朗读：AVSpeechSynthesizer

- 系统离线合成，六种语言都有系统 voice；不引入第三方 TTS。
- 只读**已经切出的从句**：settled 全段；volatile 必须有终止标点且长度达标。
- `speechSettleDelay = 380 ms` 合并 ASR 尾修；队列上限 10，超限先丢短确认语。
- 语速固定 `default * 1.28`（上限钳制）；`prefersAssistiveTechnologySettings` 暂未设置。
- 无对应 voice → 关闭读出，字幕继续；不静默 fallback 成英语。

### 4.1 回声策略

链路：喇叭出译文 → 麦克风再收 → 再识别 → 再翻译 → 再朗读，会自激。

当前实现不靠 AEC 硬扛，而是**路由门禁**：

- `AudioRouteSnapshot.canSpeakWithoutEcho` 要求输出或输入中存在耳机类路由（耳机、A2DP、LE、HFP、听筒、USB、助听器、外接）。
- 外放（builtInSpeaker）时禁止打开读出，并提示需要耳机。
- 同传朗读时 category 用 `.playAndRecord/.default`，`overrideOutputAudioPort(.none)`；不使用 `.voiceChat`，避免把桌面上的对方当回声压掉。

`AVAudioSession.routeChangeNotification` 是耳机状态的唯一真源；不信任用户口头开关。

---

## 5. 音频会话

| 用例 | 配置 | 理由 |
| --- | --- | --- |
| 面对面 / 同传字幕 | `.record` + `.measurement` + `[.duckOthers]` | 少处理，给模型干净 PCM |
| 同传朗读 | `.playAndRecord` + `.default` + `[.duckOthers, .allowBluetoothA2DP]` | 需要播放且允许蓝牙耳机 |
| 停听 | `setActive(false, .notifyOthersOnDeactivation)` | 礼貌让出音频 |

- 优先内置麦克风 + 底部数据源；蓝牙耳机可用但不推荐作为面对面主场景。
- 不申请后台音频；`scenePhase != .active` 即停听。
- `AudioEngineCapturer` 与 `AudioSessionPolicy` 都调用 `setActive`，当前没有统一 gate（P2）。

---

## 6. 持久化：SwiftData + TaskStore

### 6.1 为什么 SwiftData

任务是「一条会话 + 多条文字 + 可选摘要」，需要筛选、删除、杀进程恢复。SwiftData 与 Swift 类型映射自然，`ModelContext` 可注入；测试可换 `InMemoryTaskStore`。

不选：

| 方案 | 原因 |
| --- | --- |
| Core Data 手写 stack | 样板多，与纯 Swift 模型重复一套 NSManagedObject |
| Documents 下 JSON | 列表查询、部分更新、损坏恢复都要自己写 |
| UserDefaults | 不适合长文本稿 |

### 6.2 结构

- `TaskEntity` + `TranscriptEntity` 分表，cascade 删除，`sortIndex` 保序。
- `TaskStore` 协议隔离存储；Feature 不写 `@Query`。
- `DeferredTaskStore` 把 `ModelContainer` 打开移出首帧；失败静默降级 `InMemoryTaskStore`（P0-3）。
- `SwiftDataTaskStore` 使用主线程 `ModelContext(autosaveEnabled: true)`；`append` 全量 upsert。
- 尚无 `SchemaMigrationPlan`；`schemaVersion` 字段已预留。

### 6.3 语义

- 只有 `ended` 进历史；空稿结束自动删除。
- 暂停只改 `pausedListening`，不结束任务。
- 实时字幕以内存为准；落盘异步，View 不直接读 SwiftData 当实时状态。
- 已结束任务的译文通过专用 `updateTranslations` 回填，不放宽 `append` 的写入规则。

---

## 7. 总结与导出

### 7.1 总结

`FoundationModelsSummarizer`：

- `SystemLanguageModel.default.availability` 四态映射：available / deviceNotEligible / appleIntelligenceOff / modelNotReady。
- 可用 → `LanguageModelSession` 生成，非空即返回 `usedAppleIntelligence: true`。
- 不可用/失败/空结果 → `digest`：按「你 / 对方」分组拼接原文/译文，`usedAppleIntelligence: false`。
- 不接云 LLM，不在 iPhone 13 上假装本机摘要。

### 7.2 导出

- Caches 写 UTF-8 文本，`Duiyi-<feature>-yyyyMMdd-HHmm.txt`。
- 内容含标题、时间、方向、文字稿、可选摘要；会议每行带语种。
- `ShareLink` 分享；不内嵌第三方 SDK、不猜 URL Scheme。
- 当前每次导出删除全部 `Duiyi-*.txt`，存在分享竞态（P1-2）。

---

## 8. 架构与本地化

- **手动 DI**：`AppEnvironment` 构造真实实现，测试注入假实现；不引入 TCA/RIBs。
- **模块注册**：`FeatureID` + `FeatureRegistry` + 独立 Feature 目录；`RootView` 仍有显式路由 switch。
- **界面文案**：`Copy.swift` / `Copy+Platform.swift` 用 `AppLanguage.pick(zh:en:ja:ko:th:vi:)`，界面语言跟随「我看的语言」。
- **String Catalog**：`Localizable.xcstrings` 只保留 SwiftUI 自动提取的少量字符串；**不是**主要文案源。新增界面语言目前需要扩展 `AppLanguage` 与 `pick` 调用。
- **语言目录**：`StaticLanguageCatalog` 为静态桩，真实能力探测仍在 View/服务层；扩语言需改枚举、Tokens、脚本阈值、测试（P2）。

---

## 9. 测试与性能

- 单元：Swift Testing，120 个；协议注入使 VM 可用假引擎/假 store/假合成器。
- UI：XCUITest，3 个；模拟器无 `SpeechTranscriber` 时语音用例 skip 是正确行为。
- 真机：语音/翻译/TTS/持久化必须真机验证；统一走 `.apm/tools/device-test.sh`（先预热 testmanagerd）。
- 启动优化：已暂停。`AppLaunchTracker` + `EarlyLaunchMark` 保留口径；`Order/App.order` 是 Release 二进制重排生成物，禁止手写，收益在当前包体下不可测量。

---

## 10. 主要权衡与已知缺口

| 权衡 | 现状 | 影响 |
| --- | --- | --- |
| 单引擎共享 | 三 VM 共用一个 actor，无全局仲裁 | 快速切模块可能互相停流（P0-1） |
| 双路资源 | 超限降级单路/去 Detector | 会丢一句，用户无提示 |
| 翻译桥 | pending 单槽 + host 就绪后无界流 | volatile 高频时积压（P1-1） |
| 持久化 | 主线程 ModelContext + 全量 upsert | 长会写放大（P0-3） |
| 长会话 | Conversation 无上限 / SI 50 条 / Meeting 2 万字 | 内存/截断双极端（P0-2） |
| 语言切换 | config 变化重建 task，旧译文靠字数丢弃 | 可能漏一句/串语言（P1-3） |
| 语种融合 | 脚本纯度门禁较严 | 中英混读可能丢句（P1-4） |
| 目录能力 | `StaticLanguageCatalog` 恒 true | 选到不支持的语言才失败（P2） |
| 界面本地化 | `pick` 六参 | 加界面语言要改多处（P2） |

---

## 11. 明确不选的整套方案

- 云后端 / 账号 / 云同步：违背本机优先与离线承诺。
- 端侧 LLM 替代系统翻译：成本、发热、质量均无优势。
- TCA / RIBs / 重型 DI 框架：三个模块体量不够。
- 每个 Feature 一套 SpeechEngine：资源翻倍且更难仲裁。
- 把 `TranslationSession` 塞进 Service：违反系统约束，必然失效。
- 用模拟器证明启动/音频性能：口径不成立。

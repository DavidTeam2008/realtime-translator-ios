# AGENTS.md · Duiyi/Services

> 触发：改 `Speech` / `Audio` / `Translation` / `SpeechSynthesis` / `Persistence` / `Export` / `Summary` / `Permissions` 前先读本页。
> 本页只写 Services 的增量约束；项目规则见根 [`AGENTS.md`](../../AGENTS.md)，契约细则见 [`references/contracts.md`](../../references/contracts.md)，链路事实见 [`HANDOFF.md`](../../HANDOFF.md) §4 与 [`docs/02-architecture.md`](../../docs/02-architecture.md)。

## 1. 语音：单引擎，Gate 未实现

- 三个常驻 VM 共享 `AppEnvironment.speechEngine`（唯一 `SpeechRecognizing` actor）；**不要给每个 VM 建引擎**，不要把“加锁”当仲裁。
- `BilingualSpeechEngine()` 只在组合根（`AppEnvironment` 默认参数）实例化；其它位置注入协议。
- P0-1 的 `SpeechSessionGate`（owner + generation）是**目标而非现行**：实现前不得在代码/注释/文档/提交信息里声称已有全局仲裁。
- 快速切模块/前后台切换的并发问题仍在；改这块必须配假引擎并发测试（20 次切换 + 10 次前后台）。
- 资源不足降级与 `UtteranceAssembler` 语种锁定是现状（`docs/02` §4），不要顺手改听写策略。

## 2. 翻译：Session 只在 Host View

- `TranslationSession` 只能出现在 `*TranslationHostView` 的 `.translationTask`：`Conversation/TranslationHostView.swift`（含 `OneWayTranslationHostView`）。Services 不持有、不调用 `TranslationSession`。
- job 合并/过期丢弃在 `TranslationJobBridge`；P1-1 前不扩大缓冲、不改队列语义。
- 语言对变化由 `.id` 重建 Host；Service 只提供 availability（`TranslationAvailabilityChecking`）。

## 3. 持久化：内存为准、异步落盘

- 实时字幕/`PaneState` 是内存事实；`TaskStore.append` 由 VM 以 250ms debounce 触发，不要在 Service 里同步写盘，也不要把调 debounce 当优化。
- View/VM 不直读 SwiftData 当实时状态；历史详情只读，不复用现场字幕状态机。
- 任务语义（显式新→结束、只有 ended 入历史、空稿结束删除、暂停只停麦克风）由 VM + Store 共同保证；改 Store 前读 [`references/contracts.md`](../../references/contracts.md) §4。
- `DeferredTaskStore` 延迟开库、失败回退 `InMemoryTaskStore`：不要在 `AppEnvironment.init` 或首帧前同步 open container。
- 改持久化/迁移前：先备份 store 样例（真机拷出或测试 fixture），再写迁移测试；不要用“删库重装”验证数据安全。

## 4. 测试替身与边界

- 单测用假实现：假引擎（记录 start/stop、可手动 emit）、`InMemoryTaskStore`、假合成器、假 audio session；不得连真麦克风/真模型。
- **不得 mock 能力检查**（如 `SpeechTranscriber.isAvailable`）来让模拟器用例变绿；语音/翻译/TTS/音频/持久化的最终验收在真机。
- 新协议放 `ServiceProtocols.swift` 或所属目录，由 `AppEnvironment` 注入；预览替身放 `App/PreviewSupport.swift`。
- 分层：Services 不引用 ViewModel；Domain 不 import SwiftUI/语音/翻译/SwiftData；`make check-arch` 会拦。

## 5. 导出与产物

- 导出（P1-2 未修前）不要删除全部 `Duiyi-*.txt`；文件名带 taskID + 时间戳；不改 `TranscriptExportService` 的共享语义。
- 测试用临时目录；不写仓库内路径；不提交 build/trace/`.apm/runs/`。

## 6. 完成判据

- Service 变更 = 对应单测（`make test`）+ `make verify-static`；涉及真机链路（语音/翻译/TTS/持久化）补 `make device-test` 结果；不能操作设备时写“未验证”+ 手动步骤。

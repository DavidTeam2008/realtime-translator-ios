# AGENTS.md · DuiyiTests

> 触发：新增/修改单元测试、调整测试替身或测试计数前先读本页。
> 本页只写单元测试的增量约束；验证矩阵见 [`references/verification.md`](../references/verification.md)，测试入口与已知坑见 [`HANDOFF.md`](../HANDOFF.md) §3.1。

## 1. 框架与写法

- Swift Testing：`import Testing`、`@MainActor struct XxxTests`、`@Test("English sentence")`、`#expect(...)`。本目录不用 XCTest。
- VM / Store 测试标 `@MainActor`；异步用例直接 `async` + `await`，不用 expectation；一个用例只验证一个行为。
- 测试名写清“输入 → 预期”，与实现细节解耦；不要断言私有实现或日志文案。

## 2. 文件与命名

- 新文件放 `DuiyiTests/<Subject>Tests.swift`，文件名按被测对象；不新建 target。
- 复用现有风格：同文件内定义 `Mock*` / `Fake*` 替身，或使用 `App/PreviewSupport.swift` 的 `Preview*`。

## 3. 测试替身

- 假引擎：记录 start/stop 顺序、可手动 emit `Utterance`、可模拟 finish/error；不连真麦克风、真模型。
- 假 store：任务逻辑用 `InMemoryTaskStore`；SwiftData 行为用内存 container 或临时 store，不碰真实用户数据。
- 假合成器/假 audio session 只做协议实现；不要在测试里发起网络、真实语音资源下载。
- **不得 mock 能力检查**（如 `SpeechTranscriber.isAvailable`）或改断言来“修绿”；模拟器语音 skip 是 UI 用例的预期行为。

## 4. 只增不减

- 测试只增不减：不删除、不改既有测试与断言；不得改期望值让失败变绿。
- 新增测试后同步 `.apm/test-baseline.json` 的 unit floor（计数）与 skip 白名单；计数口径唯一源 [`references/verification.md`](../references/verification.md)。
- `make check-tests` 比对 floor，删测试/计数下降会非 0 退出；`make test` 跑模拟器单元。
- 方向性翻转（真·行为变更）必须在计划/PR 说明理由；修 bug 先补红测再修。

## 5. skip 与 flaky

- 单元测试不允许 skip；skip 只允许 UI 层语音用例并写明原因。
- flaky 先定位根因（时序/环境/共享状态）；不要用加大 sleep 掩盖；环境/网络/已知 flaky 不计入“2 次修复”预算。

## 6. 真实边界

- 单测覆盖 Domain 纯逻辑、VM 策略、Store 行为；导航/布局走 UI 测试。
- 语音/翻译/TTS/持久化跨进程重开必须在真机验证（`make device-test`）；不能操作设备时写“未验证”+ 手动步骤。

## 7. 命令

- `make test` 全量单元；`make test-one TEST=DuiyiTests/ConversationViewModelTests` 单文件/单用例；`make check-tests` 计数门禁。

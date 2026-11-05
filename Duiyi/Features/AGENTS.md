# AGENTS.md · Duiyi/Features

> 触发：改 ViewModel / View / 导航入口 / 任务条交互前先读本页。
> 本页只写 Features 的增量约束；项目规则见根 [`AGENTS.md`](../../AGENTS.md)，依赖理由见 [`references/contracts.md`](../../references/contracts.md)，加模块六步见 [`HANDOFF.md`](../../HANDOFF.md) §4.4。

## 1. 依赖与注入

- Features 只依赖 Domain + Services 协议；VM 通过构造器注入 `any SpeechRecognizing` / `TaskStore` / `SpeechSynthesizing` / `PreferencesStore` 等，不 new 具体 Service。
- 不 import `Speech` / `AVFoundation` / `SwiftData`；`Translation` 只允许在 `TranslationHostView.swift`（`@preconcurrency import Translation`）。
- 不直读 SwiftData；历史详情走 `TaskStore` 的只读查询，不复用现场字幕状态机。

## 2. 并发与主线程

- ViewModel 是 `@MainActor`；UI 状态只在主线程改；`await` 服务返回后回主线程再更新。
- 长 I/O 交给 Service（`DeferredTaskStore` 已延迟开库）；不要在 `body`、`init` 或首帧路径做同步文件/SwiftData 工作。
- 回调用 `Task { @MainActor in ... }`；不要用 `Task.detached` 改 UI 状态；任务取消后不得写入过期状态。

## 3. 翻译锚 View、字幕以内存为准

- 需要翻译时由 VM 产出 `TranslationJob`，交给 `TranslationHostView` / `OneWayTranslationHostView` 的 `.translationTask`；VM 不持有 `TranslationSession`。
- 现场字幕读 VM 的 `PaneState`/内存数组，不读 SwiftData；落盘异步，View 不等待落盘再更新。

## 4. 任务语义（交互必须保持）

- 显式“新任务 → 结束任务”；只有 ended 进历史；空稿结束自动删除；暂停只停麦克风，不结束任务。
- 后台/切模块只停听，不自动结束；不要把“结束任务”改成自动保存。

## 5. UI 入口与可测试性

- 新增 UI 入口必须加 `accessibilityIdentifier`，沿用 kebab-case（`home-module-*`、`nav-*`、`taskbar-*`、`caption-*`、`langchip-*`、`listening-control`）；不靠中文文案或坐标定位。
- 改入口/标识要同步 `DuiyiUITests`；历史返回用 `nav-home`，不要用系统返回键。
- View 保持薄：复用 `Shared/`（`TaskBar`、`ModuleChrome`、`LanguageChipGrid`）与 `DesignSystem`，不要复制布局常量。

## 6. 新增模块（HANDOFF §4.4 六步）

1. `Domain/FeatureID.swift` 加 case 与 `AppMode` 映射；
2. `App/AppCoordinator.swift` 的 `FeatureID.route` 加映射；
3. `App/FeatureRegistry.swift` 登记标题/图标，补 `Copy+Platform` 与 `Tokens`；
4. 新建 `Features/<Name>/` 的 View + ViewModel；
5. `App/AppRoute.swift` + `RootView.destination(for:)` 加分支；
6. 首页 identifier 自动带新 feature id，补对应 UI 测试。

- 三个常驻 VM 在 `RootView` 首帧后创建；不要把 VM 创建或 store 打开放到启动关键路径。

## 7. 完成判据

- VM/纯逻辑：`make test`；导航/布局：`make test-ui`；语音/翻译/TTS 相关：真机验证。不能操作设备写“未验证”。

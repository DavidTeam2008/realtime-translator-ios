# 对译 Duiyi · 接手说明（HANDOFF）

> 最后更新：2026-11-05（Phase 0 单一真源清理：§6 决策合并为 D1–D7、§5 改摘要）
> 代码基线：`main`（以 `git log` 为准）
> 本机复核：Xcode 27.1 构建通过；模拟器单元 **120/120**、UI 3 个（1 个按预期 skip）
> 真机基线（2026-09-26）：iPhone 13 / iOS 26.7，**123/123** 通过（120 单元 + 3 UI）

这是一份“让新同学在一天内能改代码、能跑真机、知道下一步做什么”的文档。
产品行为在 `docs/01`，架构与数据链路在 `docs/02`，选型理由在 `docs/03`，
问题清单与排期在 `docs/04`；本文件只保留接手必需的信息和最关键的结论。

---

## 0. 项目是什么、现在到哪了

**对译 Duiyi** 是一个端侧运行的 iOS 实时翻译 App（首次需联网下载系统语音/翻译
资源）：麦克风 → 端侧听写 → `Translation.framework` 翻译 → 字幕 / 可选 TTS，
任务结束时把文字稿存进本机 SwiftData。没有后端、没有 API Key、没有账号体系，
也不上传音频。

三个功能模块：

| 模块 | 做什么 | 特点 |
| --- | --- | --- |
| 面对面 | 双屏对话，上半屏倒字给对方 | 双向听写 + 双向翻译 |
| 同声传译 | 单栏看译文，可戴耳机听 TTS | 单向听写 + 单向翻译 + 从句朗读 |
| 会议记录 | 单语全文稿，会后总结/导出 | 不做实时翻译；当前 2 万字硬停（见 P0-2） |

公共能力：首页模块注册、任务条（新任务/结束任务）、本机历史、总结
（Apple 智能可用则用，否则原文摘要）、UTF-8 文本导出、6 种语言
（中/英/日/韩/泰/越）、引导与模型下载。

**当前状态：功能闭环已齐，没有已知阻塞性 Bug。** 剩下的工作主要是
可靠性、长会话数据留存、翻译链路延迟和发布工程，见 §5。

运行环境：

| 项 | 值 |
| --- | --- |
| 最低系统 | iOS 26.4（`IPHONEOS_DEPLOYMENT_TARGET = 26.4`，仅 iPhone、竖屏） |
| 语言/工具链 | Swift 6.0，Xcode 26.4+；本机已用 **Xcode 27.1** 验证 |
| 主 App Bundle ID | `com.david.Duiyi` |
| 测试 Bundle ID | `com.david.DuiyiTests` / `com.david.DuiyiUITests` |
| 当前签名 Team | `REDACTED_TEAM_ID`（不是你的 Team 就必须改，见 §1.2） |
| 版本 | `MARKETING_VERSION = 1.0`，`CURRENT_PROJECT_VERSION = 1` |
| 参考测试机 | iPhone 13「菀墨」，iOS 26.7，硬件 UDID `REDACTED_UDID` |
| 第三方依赖 | 无（纯系统框架：Speech / AVFoundation / Translation / SwiftData / FoundationModels） |

> 关于 iPhone 13：它不支持 Apple 智能，总结会走本地摘要回退，这是**预期行为**，
> 不是 Bug。听写、翻译、任务、导出必须在这台设备上完整可用。

---

## 1. 第一次跑起来

### 1.1 前置

- 仓库远端：`git@github.com:davidtan2008/realtimeTranslatorOptimize.git`（找原负责人开权限）。
- macOS + Xcode 26.4 或更新（本仓库最后一次验证是 27.1）。
- 一台 iOS 26.4+ 的真机。**不要只用模拟器验收语音链路**：iOS 模拟器不提供
  `SpeechTranscriber`，同传真实听写用例会自动 skip（见 `docs/20` §4）。
- 真机已开启开发者模式、已信任这台 Mac。
- 如果跑真机 UI 测试：安装 `mobilebuildmcp`（`.apm/tools/device-test.sh` 依赖）：
  `npm i -g mobilebuildmcp`。
- 如果要复测启动：还需要 `idevicesyslog` 和 `timeout`
  （`brew install libimobiledevice coreutils`）。

### 1.2 签名（新开发者最容易卡住的一步）

工程里写死了原开发者的 Team 和 Bundle ID：

```text
DEVELOPMENT_TEAM = REDACTED_TEAM_ID
PRODUCT_BUNDLE_IDENTIFIER = com.david.Duiyi
```

如果你不在这个 Team：

1. 在 Xcode 的 **Signing & Capabilities** 里把 App、`DuiyiTests`、`DuiyiUITests`
   三个 target 都改成**你自己的 Team**；
2. 把 App 的 Bundle ID 改成全局唯一的值（例如 `com.yourname.Duiyi`）；
3. 两个测试 target 的 Bundle ID 也改成唯一值，并确认 UI test 的
   `TEST_TARGET_NAME = Duiyi` 仍指向 App target。

不要把别人的 Team 一起提交回仓库。免费开发者账号还有设备上的 App 数量上限
（本项目实测 3 个自签名 App 就满了，UI Test Runner 也占一个名额），装不下时
先删旧 App。

### 1.3 构建 / 安装 / 启动

```bash
# 查自己的设备 UDID
xcrun devicectl list devices

# Debug 真机构建
xcodebuild -project Duiyi.xcodeproj -scheme Duiyi \
  -destination 'platform=iOS,id=<UDID>' \
  -allowProvisioningUpdates \
  -derivedDataPath /tmp/duiyi-build build

# 安装 + 启动
xcrun devicectl device install app --device <UDID> \
  /tmp/duiyi-build/Build/Products/Debug-iphoneos/Duiyi.app
xcrun devicectl device process launch --device <UDID> com.david.Duiyi
```

Release（启动测量 / 发版前）：

```bash
xcodebuild -project Duiyi.xcodeproj -scheme Duiyi -configuration Release \
  -sdk iphoneos -destination 'generic/platform=iOS' \
  -allowProvisioningUpdates -derivedDataPath build/Release build
```

`ORDER_FILE` 只在 Release 配置生效；`Order/App.order` 是生成物，禁止手写，
需要更新时用 `tools/generate-order-file.sh` 从**真机 Release 二进制**重新生成
（当前文件头显示它来自模拟器构建，属于待修正项）。

### 1.4 首次启动

1. 选界面语言；
2. 允许麦克风、语音识别；
3. 按引导下载听写/翻译资源（需要网络，模型在设备端）；
4. 回到首页，依次点三个模块各走一遍：新任务 → 开始 → 说两句 → 结束 → 历史。

如果只想跳过引导做 UI 自动化，可加启动参数：

```swift
app.launchArguments += ["-duiyi.onboardingComplete", "YES"]
```

注意：这个参数只跳过引导页，**不会**自动授予麦克风/语音识别权限。

---

## 2. 环境与已知坑

这一节是按“实际踩过、会浪费半天”的顺序排的。

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 真机测试找不到设备 | 设备 ID 体系不同：Xcode/devicectl 用硬件 UDID，mobilebuildmcp 用自己的 ID | 分别用 `xcrun devicectl list devices` 和 `mobilebuildmcp device list` 查，不要混用 |
| UI 测试报 `exit code 74` 或 `Timed out while enabling automation mode` | `testmanagerd` 的 automation 通道未就绪，或设备停在「Enable UI Automation」密码弹窗 | **先跑一次设备侧单元测试预热**，再跑 UI；仍失败时在手机上输入一次锁屏密码（见 §3.2） |
| 真机 UI 测试起不来 | 手机锁屏 | 先解锁；`device-test.sh` 会检查并直接退出码 2 |
| `Free provisioning requires at most ... apps` | 免费证书的 App 名额满了（Runner 也占） | 删掉不用的自签名 App，或换付费账号 |
| 首页按钮“存在但不可点击”（`not hittable`） | 全新安装时 `OnboardingView` 以 `fullScreenCover` 盖住首页 | 测试里加 `-duiyi.onboardingComplete YES`；不要靠“模拟器里已经有人点过”的残留状态 |
| 同传测试在模拟器被 skip | 模拟器没有 `SpeechTranscriber`（`SFSpeechRecognizer` 可用不代表它可用） | 这是正确行为，真机验证；不要 mock 能力检查来“修绿” |
| 历史卡片找不到 | 首页历史卡片在首屏下方，需要上滑 | 测试里 `app.swipeUp()`；不要写死坐标 |
| 历史页没有系统返回键 | `HistoryView` 用 `ModuleChrome` 自定义导航、隐藏了系统 toolbar | 点 `nav-home` 返回，不要找 `navigationBars.buttons` |
| 截屏命令失败 | `idevicescreenshot`（旧 screenshotr 服务）在 iOS 26 上报 `Invalid service` | 用 Xcode 截屏、QuickTime，或让 XCUITest 自己读无障碍树 |
| `xctrace` 卡在 `Waiting for device to boot` | 这台网络配对设备的已知问题，时好时坏 | 先解锁/重启设备；尽量用 USB；或改用 `AppLaunchTracker` 日志 + `devicectl` 测量 |
| 启动测量两次差一倍 | 冷启动存在未完全受控的 fast/slow 双峰（约 280ms vs 500ms） | 不要用单次样本；按 `.apm/report.md` 的分层口径，n≥10 并看显著性 |
| bash 报“未绑定的变量” | 全角标点紧邻变量名，`$VAR（说明）` 会被当成变量 `VAR（说明）` | 一律写 `${VAR}（说明）`。`docs/20` / `.apm/tools/device-test.sh` 都踩过 |

其他约定：

- `xcodebuild` 每次都会打印一条无害警告：
  `Failed to load provisioning paramter list ... No provider was found.`
- 真机日志（`idevicesyslog` 随 `libimobiledevice` 提供，未安装可 `brew install libimobiledevice`）：

```bash
idevicesyslog -u <UDID> | grep -a "Launch stages\|EARLY\|STORE open\|first-frame"
```

- 模拟器只用于**功能回归和导航**，不要用它比较启动耗时、开库耗时或语音能力：
  模拟器会把 pre-main 高估 20 倍以上（`docs/16` §4）。

---

## 3. 测试

### 3.1 单元测试（120 个，Swift Testing）

单元测试用的是 **Swift Testing** 的 `@Test`，不是 XCTest。覆盖 Domain 纯逻辑
（路由/切句/合并/文本工具）、三个 ViewModel 的策略、任务 Store、Onboarding 等。

```bash
# 模拟器（无需真机）
xcodebuild test -project Duiyi.xcodeproj -scheme Duiyi \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro Max,OS=26.4.1' \
  -only-testing:DuiyiTests
```

2026-10-29 在本机 iPhone 17 Pro Max / iOS 26.4 模拟器复核：**120 passed, 0 failed**。
本机 `iPhone 17 Pro Max` 只在 iOS 26.4.1 runtime；换机器/runtime 时用
`make test SIM_OS=<version>` 覆盖。

新增测试放 `DuiyiTests/`，文件名按被测对象命名；异步 ViewModel 测试统一注入
`PreviewSupport` 里的假引擎/假 Store/假合成器，不要连真麦克风。

### 3.2 真机测试（推荐唯一入口）

```bash
.apm/tools/device-test.sh                 # 预热 + 完整套件（120 单元 + 3 UI）
.apm/tools/device-test.sh unit            # 只跑单元
.apm/tools/device-test.sh ui              # 预热 + 只跑 UI
.apm/tools/device-test.sh one DuiyiUITests/SimultaneousFlowTests/testHomeModuleNavigation
.apm/tools/device-test.sh warm            # 只预热 testmanagerd
APM_DEVICE=<mobilebuildmcp 设备 ID> .apm/tools/device-test.sh
```

`APM_DEVICE` 用的是 **mobilebuildmcp 自己的设备 ID**（默认值已指向当前 iPhone 13），
和 Xcode / `devicectl` 的 40 位硬件 UDID 可能不是同一个字符串。换设备时先跑
`mobilebuildmcp device list`，不要直接拿 `xcrun devicectl list devices` 的 UDID 套。

重跑前确认手机**亮屏解锁**。脚本已带 `-allowProvisioningUpdates`，新环境首次跑会
自动生成 UI runner profile。iOS 15+ 的真机 UI 测试还要求设备有锁屏密码：首次运行
会在手机上弹「为 “XCTest” 输入 iPhone 密码 / Enable UI Automation」，输入一次即可
（重启后会再次要求）。脚本失败时会按证据强度打印排查顺序。

参考结果（2026-09-26，iPhone 13 / iOS 26.7）：

```text
warmup: SUCCEEDED  passed=5
all:    SUCCEEDED  passed=123  failed=0  skipped=0
```

### 3.3 UI 测试做什么

`DuiyiUITests/` 只有 3 个用例：

| 用例 | 覆盖 | 环境要求 |
| --- | --- | --- |
| `LaunchPerformanceTests/testColdLaunch` | 冷启动 3 次迭代，`XCTApplicationLaunchMetric` | 真机/模拟器都可，真机数据才有意义 |
| `SimultaneousFlowTests/testHomeModuleNavigation` | 首页 → 面对面 → 首页 → 历史 → 首页 | 任何环境 |
| `SimultaneousFlowTests/testSimultaneousListeningPressure` | 首页 → 同传 → 设英→中 → 新任务 → 监听 20s → 抓字幕 → 停止 → 导航；同时采内存/CPU/时钟 | **必须真机**（需要 `SpeechTranscriber`） |

稳定性相关的实现细节（不要随手改）：

- 启动加 `-duiyi.onboardingComplete YES`；
- 麦克风/语音识别权限通过轮询 SpringBoard 显式点“允许”，不能只靠
  `addUIInterruptionMonitor`（它只在“下一次交互”才触发）；
- 监听是否真的开始，用 `listening-control` 的文案变化断言
  （`轻点开始 → 聆听中`），不能只看按钮存在；
- 历史页返回用 `nav-home`；
- 英文→中文的语音测试：Mac 用 `say -v Samantha "..."` 外放，手机放在扬声器旁
  30–50 cm；测试会在 20s 窗口结束时把 `caption-live` / `caption-history` /
  `caption-source` 文本打到日志里，可直接和原文比对。

当前可用的无障碍标识：

```text
home-module-simultaneous / home-module-faceToFace / home-module-meeting
home-history
taskbar-new-task / taskbar-end-task
listening-control
direction-source / direction-target
langchip-english / langchip-zhHans / ...
caption-live / caption-history / caption-source
nav-home / nav-history
```

新增 UI 入口时优先补 `accessibilityIdentifier`，不要用中文文案或坐标定位。

需要复现“全新安装”状态时：模拟器用
`xcrun simctl uninstall <SIM_UDID> com.david.Duiyi`，真机直接删除 App。
删除会清空 onboarding、权限和本地历史；随后再用启动参数跳过引导。

### 3.4 取测试结果

```bash
X=$(ls -dt <DerivedData>/Logs/Test/*.xcresult | head -1)
xcrun xcresulttool get test-results summary --path "$X"
xcrun xcresulttool get test-results metrics --path "$X"
```

`metrics` 里能看到 `XCTMemoryMetric` / `XCTCPUMetric` / `XCTClockMetric`。注意：

- `testColdLaunch` 的 0.31–0.33s 是“到首页卡片可点”的 XCTest 口径；
- `AppLaunchTracker` 的 240–280ms 是“进程创建 → 首帧提交”的自埋点口径；
- 两者不是同一个终点，**不要混着引用**（`docs/16` §3b 有完整教训）。

### 3.5 性能结论（不要重复劳动）

**启动优化方向已于 2026-09-24 暂停。** 结论（`docs/17`、`docs/18`）：

- 真机冷启动约 **240–280ms**，已经在 Apple 建议的 600ms 以内；
- 目标 200ms **不可达**：最小 `Text("x")` 对照组 p50 已经 210ms，
  判定 `blocked_by_control_floor`；
- 46% 是 SwiftUI 场景引导，属框架固有；可优化空间约 64ms（27%），
  ROI 低于风险与复杂度；
- 二进制重排已正确落地，但在当前包体下**不可测量**；
- 模拟器上的启动数据与真机方向相反，不能作为依据。

如果产品仍然坚持 200ms，正确动作是先做**架构/需求决策**（例如 UIKit +
UIHostingController 换掉 SwiftUI 场景机，或把目标改成可达范围），
而不是继续做局部微优化。任何优化在测量方差修好之前都无法验证。

已有性能数据（iPhone 13，详见 `docs/14`）：

| 指标 | 结果 |
| --- | --- |
| 冷启动（XCTest 口径） | 0.312–0.331s，均值约 0.32s |
| 20s 同传监听 CPU | 0.69–1.1s（31s block，约 2–3.5% 单核） |
| 内存峰值 | 10–13MB，20s 内无增长 |
| Hang | 0 |
| 英→中翻译抽测 | 3 句完全正确；1 句内容正确但 `three eighteen` 被听成 `3:118`；1 句抓屏截断（非翻译错误） |

复测启动前先读 `.apm/baseline/README.md` 和 `.apm/report.md`，用
`.apm/tools/measure-launch.sh` 保证同口径；不要拿模拟器或单次样本下结论。

```bash
# 参数为运行次数；性能结论要求 n≥10；APM_APP 必须指向 Release-iphoneos 的 .app
APM_APP=build/Release/Build/Products/Release-iphoneos/Duiyi.app \
APM_UDID=<硬件 UDID> \
.apm/tools/measure-launch.sh 10
```

---

## 4. 架构速览

### 4.1 分层

```text
App        DuiyiApp / AppEnvironment / AppCoordinator / RootView / PreferencesStore
Features   Home / Conversation / Interpretation / Meeting / History / Onboarding / Shared / Settings
Domain     纯模型与纯函数：TaskSession / AppLanguage / Utterance / CaptionLine / SpokenText / LanguageRouter
Services   Speech / Audio / Translation / SpeechSynthesis / Persistence / Summary / Export / Assets / Permissions
DesignSystem Tokens / HomeModuleCard / HistoryRow / ScreenSafeArea
```

依赖方向是单向的：Features 只依赖 Domain + 协议；Services 不引用 ViewModel；
Domain 不 import SwiftUI/系统语音框架。新增代码请保持这条线。

### 4.2 一条语音的主链路

```text
麦克风
  → AudioEngineCapturer（actor，1024 帧 tap）
  → BufferConverter
  → BilingualSpeechEngine（双路 SpeechTranscriber + SpeechDetector，资源不足自动降级单路）
  → UtteranceAssembler（语种锁定、去抖、切句）
  → Conversation/Interpretation/Meeting ViewModel
  → TranslationHostView / OneWayTranslationHostView（TranslationSession 必须锚在 View 上）
  → PaneState（live/history）+ TranscriptEntry
  → TaskStore（SwiftData；settled/暂停/结束时落盘）
  → 历史 / 总结 / 导出
```

必须知道的四个设计约束：

1. **翻译会话锚在 SwiftUI View 上**：`TranslationSession` 不能塞进 Service 里，
   现有实现是 `Color.clear` 常驻 + `.translationTask(config)`。改翻译链路时
   不要试图绕过 `TranslationHostView`。
2. **三个 ViewModel 共享同一个 `SpeechRecognizing` actor**：`RootView` 在首帧后
   一次性创建三个常驻 VM，都把 `environment.speechEngine` 传进去。目前没有
   全局 owner/generation 仲裁，快速切模块是已知风险（§5 P0-1）。
3. **任务必须显式“新任务 → 结束任务”**：只有 `ended` 任务进历史；空稿结束会
   自动删除；暂停只停麦克风，不结束任务。
4. **现场字幕以内存为准，落盘是异步的**：不要在 View 里直接读 SwiftData 当作
   实时状态。

### 4.3 关键文件（按阅读顺序）

1. `Duiyi/App/AppEnvironment.swift`、`RootView.swift`、`AppCoordinator.swift`、
   `FeatureRegistry.swift`、`PreferencesStore.swift`
2. `Duiyi/Services/Speech/BilingualSpeechEngine.swift`、
   `UtteranceAssembler.swift`、`Duiyi/Services/Audio/`
3. `Duiyi/Features/Conversation/TranslationHostView.swift`、
   `Duiyi/Domain/Models/CaptionLine.swift`、`SpokenText.swift`、`Clause.swift`
4. `Duiyi/Features/Interpretation/InterpretationViewModel.swift`（TTS 队列与截断）
5. `Duiyi/Domain/TaskSession.swift`、`Duiyi/Services/Persistence/`
6. `Duiyi/Features/Home/HomeView.swift`、`History/`、`Shared/`

更细的逐文件分析在 `docs/02`，潜在问题与代码依据在 `docs/04`。

### 4.4 加一个新模块要改什么

1. `Domain/FeatureID.swift` 加 case，并补 `AppMode` ↔ `FeatureID` 的映射
   （`FeatureID.appMode`、`AppMode.featureID`）；
2. `App/AppCoordinator.swift` 的 `FeatureID.route` 加路由映射；
3. `App/FeatureRegistry.swift` 登记标题/副标题/SF Symbol，补
   `Copy+Platform.featureTitle` 与 `Tokens.featureCard/featureAccent`；
4. `Features/<Name>/` 加 View + ViewModel（VM 建议注入现有协议）；
5. `App/AppRoute.swift` + `RootView.destination(for:)` 加路由分支；
6. `HomeView` 的 accessibility identifier 会自动带新 feature id。

任务条、历史筛选、导出会自动复用（前提是使用 `TaskStore` 和 `TaskSession`）。
注意：这不是插件式动态注册，`RootView.destination(for:)` 和若干 `switch`
仍要手动改；好处是编译器会把所有遗漏点报出来。

---

## 5. 下一步做什么（摘要）

没有“必须马上修才能跑”的 Bug；完整验收判据与排期以
[`docs/04-roadmap.md`](docs/04-roadmap.md) 为**唯一真源**（§1–§3 判据、§6 排期），
本节只是按该排期顺序的导航摘要。建议一次只做一个 P0，配一条可验证的测试，
不要同时动语音和持久化。

| 优先级 | 事项 | 一句话状态 | 详细验收 |
| --- | --- | --- | --- |
| P0-1 | 语音引擎全局仲裁（`SpeechSessionGate`） | 未实现；三 VM 共享 actor，无跨 VM owner/generation | [§1](docs/04-roadmap.md) |
| P0-3 | 持久化可靠性与写放大 | 未修；失败静默降级内存、全量 upsert、无迁移计划 | [§1](docs/04-roadmap.md) |
| P1-2 | 导出竞态与导出内容不刷新 | 未修；导出前删全部 txt，`task.id` 不变时分享旧内容 | [§2](docs/04-roadmap.md) |
| P1-3 | 切换语言后的旧翻译状态 | 未修；VM 翻译态未统一清空 | [§2](docs/04-roadmap.md) |
| P1-1 | 翻译队列积压 | 未修；单 pending 槽 + 无界 `AsyncStream` | [§2](docs/04-roadmap.md) |
| P0-2 | 长会话的数据留存 | 未修；三条路径策略不一致；依赖 P0-3 | [§1](docs/04-roadmap.md) |
| P1-4 | 中英混读与短句质量 | 未修；需真机音频夹具 | [§2](docs/04-roadmap.md) |
| P2-6 | 语言目录实查 | 未修；`StaticLanguageCatalog` 是桩 | [§3](docs/04-roadmap.md) |

### 明确不要做的

- ⛔ 不要继续做启动微优化（`docs/17`/`docs/18` 已给出不可达证明）；
- ⛔ 不要用模拟器数据证明性能改善；
- ⛔ 不要为了让模拟器 UI 测试变绿而 mock `SpeechTranscriber` 能力检查；
- ⛔ 不要手写 `Order/App.order`，也不要在 Debug 打开 `ORDER_FILE`；
- ⛔ 不要把“结束任务”改成自动保存——当前产品语义是显式结束才入历史。

---

## 6. 交接前需要确认的产品/工程决策（唯一真源）

> **本表是决策的唯一真源**：`docs/04` §7、`AGENTS.md`、`references/contracts.md`
> 只引用 D 编号，不复制内容。确认后更新本表并标注日期；未确认前，不按假设实现
> P0-2/P0-3 的产品侧行为。

| ID | 决策 | 当前已知事实 | 未定问题 | 影响范围 |
| --- | --- | --- | --- | --- |
| D1 | 启动目标 / 口径 | 真机冷启动 240–280ms（`AppLaunchTracker`：进程创建 → 首帧提交）；XCTest 冷启动 0.31–0.33s（到首页卡片可点）；200ms 经对照判定不可达（最小 `Text("x")` 对照 p50=210ms，`docs/17`/`docs/18`） | 200ms 是硬指标还是“尽量快”？若改为 p50≤300ms（或 XCTest 口径 ≤400ms），当前实现已达标，但要先把口径写进验收；硬指标 200ms 需架构改造（如换掉 SwiftUI 场景机） | 性能验收标准、是否重启启动优化（当前已暂停） |
| D2 | 发布形态 | App Store / TestFlight / 企业分发均未定；当前没有 Archive/Export 流程、没有隐私清单（PrivacyInfo.xcprivacy）、没有 CI | 首发走 App Store、TestFlight 还是企业内部分发？ | 发布工程工作量、隐私清单与 CI 排期、发版验收 |
| D3 | 设备矩阵 | 最低 iOS 26.4、仅 iPhone 竖屏；参考机 iPhone 13 / iOS 26.7（无 Apple 智能，总结走本地回退是预期行为） | 最低 iOS 26.4 是否下调？是否必须覆盖 iPhone 13 与全部六语？ | Speech/Translation API 可用性与 UI 适配、真机测试矩阵 |
| D4 | 语言优先级 | 6 种语言（中/英/日/韩/泰/越）；听写/翻译能力依赖系统资源，泰/越的实际体验需真机抽测 | 六语是否都要达到“可发布”质量、全部首发？还是中英先行？ | P1-4 质量工作优先级、发布范围与验收 |
| D5 | 数据保留策略 | 历史默认永久保留（本机 SwiftData）；同传 `historyLimit = 50`、会议 2 万字符硬停；无自动清理 | 同传只留 50 条是产品要求还是历史实现？历史是否提供自动清理？ | P0-2 方案（Store 全量 + UI 窗口、续集任务）与“导出取全量” |
| D6 | Apple 智能范围 | 总结优先 Apple 智能，设备不支持时本地摘要回退（文案已按能力区分）；iPhone 13 走回退 | 是否要求 iPhone 13 也有“总结”？Apple 智能只用于总结，还是未来用于翻译/润色？ | P1/P2 产品行为、文案与验收（不改变本机/离线承诺） |
| D7 | 长会策略 | 会议 2 万字符硬停；P0-2 目标改为“结束并开续集任务”（同组 ID 关联），而不是直接停止 | 2 万字上限是硬限制，还是续集任务的触发点？ | P0-2 实现方式与验收（与 D5 共同决定数据保留行为） |

## 7. 文档地图

| 文档 | 状态 | 用途 |
| --- | --- | --- |
| [`README.md`](README.md) | 当前 | 产品简介、快速开始 |
| [`HANDOFF.md`](HANDOFF.md) | 当前 | 本文件：接手、环境、测试、下一步 |
| [`AGENTS.md`](AGENTS.md) | 当前 | AI Agent 冷启动入口：铁律、命令、验证矩阵、项目级覆盖 |
| [`references/`](references/) | 当前 | Agent 细则：contracts / verification / workflow；按需读取 |
| [`tools/check-docs.py`](tools/check-docs.py) | 当前 | 文档链接 / 围栏 / 索引 / token 预算；`make check-docs` |
| [`tools/`](tools/) | 当前 | 静态门禁：架构铁律、测试计数、harness、环境检查；`make check` / `verify-static` / `doctor` |
| [`Makefile`](Makefile) | 当前 | 测试 / 构建 / 真机 / 文档命令入口 |
| [`.github/workflows/docs.yml`](.github/workflows/docs.yml) | 当前 | CI 只跑文档检查 |
| [`docs/README.md`](docs/README.md) | 当前 | 文档索引与阅读顺序 |
| [`docs/01-product-design.md`](docs/01-product-design.md) | 当前 | 产品行为：三模块、任务、设置、总结/导出 |
| [`docs/02-architecture.md`](docs/02-architecture.md) | 当前 | 架构、数据链路、并发与持久化 |
| [`docs/03-tech-choices.md`](docs/03-tech-choices.md) | 当前 | 系统框架选型、理由与明确不选 |
| [`docs/04-roadmap.md`](docs/04-roadmap.md) | 当前 | P0–P3 问题、验收标准与排期 |
| [`docs/14-device-test-iphone13.md`](docs/14-device-test-iphone13.md) | 历史报告 | 真机性能/同传测试数据与工具限制 |
| [`docs/19-ended-translation-persistence-fix.md`](docs/19-ended-translation-persistence-fix.md) | 已完成 | 已结束任务译文丢失的修复记录 |
| [`docs/20-ui-test-hittable-fix.md`](docs/20-ui-test-hittable-fix.md) | 已完成 | UI 测试假绿/权限/模拟器能力问题的闭环 |
| [`docs/21-cross-session-handoff.md`](docs/21-cross-session-handoff.md) | 当前 | 跨会话任务与交接的人读 SOP：四个动作、命令、示例 |
| [`docs/15`](docs/15-startup-optimization.md)–[`docs/18`](docs/18-startup-feasibility-verification.md) | 历史，已暂停 | 启动优化过程与“200ms 不可达”的证据；只读结论，不要重启微优化 |
| [`.apm/`](.apm/) | 证据库 + 计划 | 基准、问题单、测量脚本、跨会话计划、独立审查；`runs/` 不入库 |
| [`prototype/`](prototype/) | 设计原型 | 浏览器打开的可交互稿 |

约定：真源优先级只在 [`docs/README.md`](docs/README.md) 维护（代码与最新验证 >
当前文档 > 历史）；文档里的行号/数字漂移时顺手更新，不在此重复优先级声明。

---

## 8. 第一天交接清单

- [ ] 拿到仓库权限、签名 Team（或改好自己的 Team + Bundle ID）
- [ ] Xcode 打开工程，Debug 真机构建成功
- [ ] 手机完成引导：语言、麦克风、语音识别、模型下载
- [ ] 三个模块各走一遍：新任务 → 开始 → 说两句 → 结束 → 历史 → 导出
- [ ] 跑 `.apm/tools/device-test.sh`，确认 123 个测试全绿
- [ ] 跑 `make check`；有模板仓再跑 `make check-all`，确认文档门禁、token 预算与团队基线
- [ ] 读 `docs/02`（数据链路、并发）和 `docs/04`（问题清单、排期）
- [ ] 读 `docs/17`/`docs/18` 的结论，明确“启动优化不再投入”
- [ ] 和负责人确认 §6 的 D1–D7 决策（唯一决策表；未确认前不按假设实现）
- [ ] 从 P0-1 开始：先写并发测试，再加 `SpeechSessionGate`

---

## 9. 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-10-29 | 新建接手文档；复核 Xcode 27.1 构建、模拟器 120 个单元测试；整理现状、坑与下一步 |
| 2026-10-30 | 引入 Agent 规则骨架：`AGENTS.md` + `references/` + `tools/check-docs.py` + `Makefile` + docs CI；补跨会话计划模板与接手协议（人读 SOP 见 `docs/21`）；未改业务代码 |
| 2026-10-30 | 按独立审查修复：计划按 mtime 选择、`make check` 去模板仓依赖、token 预算门禁、`SpeechSessionGate` 措辞、红队范围统一；审查报告在 `.apm/reviews/` |
| 2026-10-30 | 真机测试环境加固：模拟器默认 runtime 固定为 iOS 26.4.1；`device-test.sh` 自动带 `-allowProvisioningUpdates`；补 “Enable UI Automation” 密码弹窗说明。真机 123、模拟器 120 + UI 3/1 skip 全过 |
| 2026-11-02 | 文档整合为 01 产品 / 02 架构 / 03 选型 / 04 路线图，删除 05–13 重复稿并修正全仓链接；删除未引用代码、8 个 `platform.*` 本地化键与过期 trace/build 产物；模拟器单元 120/120、UI 3/1 skip 通过 |
| 2026-11-05 | Phase 0 单一真源清理：§6 六决策合并为 D1–D7（唯一决策真源，补“启动目标/口径”与“长会策略”）；§5 改为按 docs/04 §6 排期的摘要表；基线 hash 改为以 `git log` 为准；同步 docs/04、references、docs/README |

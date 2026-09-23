# 14 iPhone 13 真机测试报告（同声传译）· 2026-09-23

## 1. 环境

| 项 | 值 |
| --- | --- |
| Mac | MacBook Pro，macOS 26.6.2 (25G83) |
| Xcode | 26.4.1 (17E202)，SDK iPhoneOS26.4，Swift 6.0 |
| 手机 | 菀墨 · iPhone 13 (iPhone14,5)，iOS 26.7 (23H24)，UDID REDACTED_UDID，开发者模式已开 |
| App | com.david.Duiyi v1.0 (1)，Debug-iphoneos，包体约 8.3MB（Mac 端 .app） |
| 签名 | Apple Development 自动签名，Team Provisioning Profile 正常 |
| DDI | ~/Library/Developer/Xcode/iOS DeviceSupport/iPhone14,5 26.7 (23H24) 已缓存 |

## 2. 安装与启动（已完成）

- `xcodebuild -scheme Duiyi -destination id=00008110… build`：**BUILD SUCCEEDED**
- `devicectl device install app`：**App installed**，`file:///private/var/containers/Bundle/Application/743AD766…/Duiyi.app/`
- `devicectl device process launch com.david.Duiyi`：**Launched**，运行中 PID 1032（经 `device info processes` 二次确认）
- 手机当前停留在**首页/模块列表**（用户确认），未进监听

## 3. Instruments + XCUITest 性能测试（已重做，全绿）

> 用户质疑第一轮“只录静置、没看到启动和进二级页面”是对的。本轮改用 XCUITest 自动化驱动真实操作，
> 覆盖：冷启动、进同传（新任务→开始监听 20s→停止→回首页）、面对面进出、历史进出。

| 用例 | 结果 | 度量（iPhone 13 真机） |
| --- | --- | --- |
| `LaunchPerformanceTests/testColdLaunch`（3 次迭代） | 通过 | AppLaunch 0.331 / 0.314 / 0.312s，均值约 **0.32s**（到首页首卡片可点） |
| `SimultaneousFlowTests/testSimultaneousListeningPressure` | 通过（76.5s） | 31.1s block 内 CPU 时间 **0.69s**（约 2.2% 单核）、CPU 约 8.9e8 cycles、内存增量 +33KB、峰值物理内存 **10.6MB** |
| `DuiyiTests` 单元 118 个 | 通过 | 改工程（加 identifier + UITest target）无回归 |

补充说明：

- XCTApplicationLaunchMetric 0.32s 是到“首页同传卡片可点”的启动耗时；Instruments App Launch life-cycle 880ms 含进程创建/系统开销与 Debug tunnel，两者口径不同，都正常
- 20s 监听在安静房间测得，属**空转基线**；带 Mac 外放英文的一轮（stress3，Duiyi 占全设备采样 4.4%、全 Running 态，主线程 + ASR 工作线程 + SwiftUI 渲染线程活跃）证明管线在有声输入时真实运转
- 压力 trace：`…/duiyi-stress3.trace`（201s，Time Profiler，含 Duiyi PID 1311 + Runner），`…/duiyi-cpu.trace` / `duiyi-mem.trace` / `duiyi-applaunch.trace` 为第一轮静置基线，均已在 Instruments 打开
- hang-risks 0 行；内存峰值 10.6MB 且 20s 内无增长，无泄漏迹象

### 工程改动（已合入）

- `DuiyiUITests/` 新增 target（`com.david.DuiyiUITests`，ui-testing bundle，随 scheme 可跑），用例：`LaunchPerformanceTests.swift`、`SimultaneousFlowTests.swift`
- App 零行为改动，仅加稳定 `accessibilityIdentifier`：`home-module-<feature>` / `home-history`（`HomeView`）、`taskbar-new-task/end-task`（`TaskBar`）、`listening-control`（`ListeningControl`）、`nav-home/nav-history`（`ModuleChrome`）
- 过程中发现并修复：历史卡片在首屏下需上滑；History 页用自定义导航（无系统返回键），经 `nav-home` 返回
- 免费证书槽位满（Duiyi/DuiyiRN/Zhixia）：经用户确认卸载 Zhixia 后 Runner 得以安装

### 已知工具限制（诚实记录）

- `idevicescreenshot`（libimobiledevice 旧 screenshotr 服务）在 iOS 26 上返回 `Invalid service`，无法命令行截屏；iOS 26 截屏需走 Xcode Organizer/QuickTime 手动确认
- `devicectl launch` 的隧道耗时（约 0.26s）不是 App 冷启动耗时，不应引用
- xctrace CLI 可验证结构与 hang，但函数级热点/内存数字请以已打开的 Instruments 窗口为准

## 4. 同声传译英文功能测试（半自动：Mac 外放 + 需人眼确认译文）

2026-09-23 22:33 那轮已在自动化监听窗口内用 Mac 外放英文 4 遍（Samantha）：
`Hello, Lucy…` / `coffee/subway…` / `three eighteen…`。
iPhone 端当时处于自动化启动的监听中，管线运转（stress3 有声输入段 App 采样占比显著高于静置基线）。
但**译文文字准确度无法经命令行截屏/读屏验证**（iOS 26 上 `idevicescreenshot` 旧服务失效），需你在手机上亲眼确认：

前置（需用户在手机上手动完成，因无远程点屏手段）：

1. 首页 → 同声传译 → 新任务（源 English → 目标中文）
2. 点中间按钮开始聆听，确认出现“正在聆听/ speakingHint”
3. 把 iPhone 放在 Mac 扬声器旁约 30–50cm，Mac 音量 60–80%

测试句（准备用 Mac `say -v Samantha` 外放，每句间隔 4s，共三轮）：

1. `Hello, Lucy. Nice to meet you.`
2. `I'd like a cup of coffee, please. Where is the nearest subway station?`
3. `The meeting starts at three eighteen, but they moved it to the fifteenth.`

判定标准：手机 live 区出现中文译文（大意对即可，允许 final 覆盖修正）；source 小字行保留英文原文；无串到面对面/会议任务。

## 5. 待你确认（功能准确度需人眼）

- [ ] 在手机 历史 里打开刚才的同传任务（标题含 `English → 中文`），看三句英文的中文译文是否准确、大意是否对
- [ ] 若译文缺失/错乱，告诉我看到的原文与译文，我对照 `UtteranceAssembler`/`TranslationJob` 链路排查
- [ ] Zhixia 已按你的选择卸载，如需装回告诉我

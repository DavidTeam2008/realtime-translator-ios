# AGENTS.md · DuiyiUITests

> 触发：新增/修改 UI 测试或无障碍标识前先读本页。
> 本页只写 UI 测试的增量约束；真机入口与坑见 [`references/verification.md`](../references/verification.md) 与 [`HANDOFF.md`](../HANDOFF.md) §3.2–§3.3。

## 1. 基本事实

- 用 XCTest（`XCTestCase`），不是 Swift Testing；`continueAfterFailure = false`。
- 现有用例集中在 `LaunchPerformanceTests.swift` / `SimultaneousFlowTests.swift`；后者含需要真机 `SpeechTranscriber` 的压力用例。
- 模拟器入口 `make test-ui`；真机入口 `.apm/tools/device-test.sh`（`make device-test-ui`）。

## 2. 启动前置

- 每次 `app.launch()` 前加 `-duiyi.onboardingComplete YES`，否则 `fullScreenCover` 盖住首页、按钮 not hittable。
- 该参数只跳过引导，不授予麦克风/语音识别权限；权限用 SpringBoard 轮询显式点“允许”，不要只靠 `addUIInterruptionMonitor`。
- 依赖全新安装状态时先卸载 App（模拟器 `simctl uninstall`），不要依赖残留状态。

## 3. 定位与导航

- 只用 `accessibilityIdentifier`：`home-module-<feature>`、`home-history`、`taskbar-new-task` / `taskbar-end-task`、`listening-control`、`caption-live` / `caption-history` / `caption-source`、`nav-home` / `nav-history`、`langchip-*`。
- 不用中文文案或坐标定位；历史卡片可能在首屏下方，需要 `swipeUp()`。
- 历史页无系统返回键，返回用 `nav-home`；新增 UI 入口先补 identifier 再写断言。

## 4. 真机顺序与故障

1. 手机亮屏解锁；首次跑 UI 需过一次“Enable UI Automation”密码弹窗。
2. 先预热 `testmanagerd`（脚本 `warm`），顺序是 warm → 单元 → UI；不要手敲 xcodebuild UI 命令，否则易复现 exit 74。
3. `exit 74` / automation 超时 = 环境问题（预热/密码弹窗），不是代码失败；锁屏时脚本 exit 2。
4. `mobilebuildmcp` 的设备 ID 与 Xcode/`devicectl` 的硬件 UDID 不同，别混用；本地设备信息写 `AGENTS.local.md`（如存在，不入库）。

## 5. 语音用例

- `testSimultaneousListeningPressure` 在模拟器 `XCTSkip` 是预期（无 `SpeechTranscriber`），skip 原因必须写清；不得 mock 能力检查或改断言变绿。
- 真机验证：Mac 用 `say -v Samantha` 外放，手机放扬声器旁 30–50 cm；用 `listening-control` 文案变化判断真的开始听，不能只看按钮存在。
- 该用例抓到的字幕会打到日志，可直接与原句比对；不要放宽断言掩盖识别差异。

## 6. 性能用例

- `testColdLaunch` 用 `XCTApplicationLaunchMetric`，0.31–0.33s 是“到首页卡片可点”口径；`AppLaunchTracker` 240–280ms 是“进程创建 → 首帧提交”口径，两者不可混引。
- 模拟器会把 pre-main 高估 20 倍以上；性能结论必须 Release 真机、n≥10、同口径（见 [`references/verification.md`](../references/verification.md)）。

## 7. 完成判据

- 导航/布局：模拟器 `make test-ui`；语音/真机行为：`make device-test-ui` 或 `make device-test`。
- 不能操作设备时写“未验证”+ 手动步骤，不得声称已验证；测试产物（截图/trace）不提交。

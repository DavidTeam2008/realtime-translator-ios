# 20. UI 测试「存在但不可点击」闭环

> 2026-09-26。修 `ISSUE-UI-001`，过程中连带查出两个独立缺陷。
> 结论先说：**App 没有 bug，是测试在依赖它控制不了的环境。**

## 1. 确定性复现

原失败：

```text
Failed to not hittable: Button, {{20.0, 224.0}, {362.0, 78.0}},
identifier: 'home-module-simultaneous'
```

先卸载 App 拿到干净状态，再跑 —— 稳定在同一行失败：

```bash
xcrun simctl uninstall REDACTED_DEVICE_ID com.david.Duiyi
```

说明失败与「模拟器残留状态」强相关，不是偶发。

## 2. 根因一：引导页盖住了首页

从 xcresult 导出的失败瞬间 UI 层级：

```text
第 20 行    Button {{20,224},{362,78}} 'home-module-simultaneous'   ← 存在，但在下层
第 38-47 行 另一棵顶层子树：'DUIYI' / '对译' /
            '把手机平放在中间，对面就能看懂你说的话。' / Button '开始'
```

第二棵子树就是 `RootView` 的 `fullScreenCover`（`OnboardingView`）。
全新安装时 `duiyi.onboardingComplete = false`，于是首页按钮
**在无障碍树里存在、但被覆盖** → `waitForExistence` 通过、`tap()` 抛 not hittable。

这个用例此前只在「模拟器里已有人工跑过的残留状态」下才通过 —— 属于依赖环境的假绿。

**修法**（不动产品代码）：

```swift
app.launchArguments += ["-duiyi.onboardingComplete", "YES"]
```

走 `UserDefaults` 的 argument domain（优先级最高），不依赖引导页的文案与结构。

## 3. 根因二：权限弹窗无人处理

修完根因一，测试推进到下一行失败：

```text
XCTAssertNotEqual failed: ("轻点开始") is equal to ("轻点开始")
```

屏幕录像显示屏幕上正是「"对译"想访问麦克风」弹窗。

原有 `addUIInterruptionMonitor` 失效的原因：monitor 只在**下一次交互**时被 XCTest 调用；
而 `tap()` 之后测试直接 `sleep(3)` + 读 label，中间没有交互，monitor 永远等不到时机。
于是「权限没授予」被伪装成「App 没进入监听」。

**修法**：显式轮询 SpringBoard，只点白名单按钮（不误点「不允许」）：

```swift
private func grantPermissionsIfNeeded(rounds: Int = 6, timeout: TimeInterval = 8) {
    let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
    ...
}
```

诊断输出确认两个弹窗都被处理：

```text
PERM-CHECK round=1 exists=true   → PERM-TAP tapped=允许
PERM-CHECK round=2 exists=true   → PERM-TAP tapped=允许
PERM-CHECK round=3 exists=false alerts=[]
```

## 4. 根因三：模拟器根本没有端侧转写器

权限都给齐了，label 仍不变。录像显示 App 显示：

```text
这台设备暂时不能离线识别这段语言。
```

这不是 App 的 bug —— `SpeechAssetPreparer.isDeviceCapable` 的判断是**正确**的。
用临时探针实测平台 API：

```text
SpeechTranscriber.isAvailable              = false   ← 唯一失败项
supportedLocale(en-US)                     = en_US   （受支持）
supportedLocale(zh-CN)                     = zh_CN   （受支持）
SFSpeechRecognizer.available               = true
SFSpeechRecognizer.supportsOnDeviceRecognition = true
```

即：**iOS 模拟器不提供 `SpeechTranscriber`**，而经典 `SFSpeechRecognizer` 反而是可用的。
探针文件已删除。

**修法**：按运行环境要求拆成两个用例，而不是放宽断言：

| 用例 | 要求 | 模拟器结果 |
|---|---|---|
| `testHomeModuleNavigation` | 纯导航 | **passed** |
| `testSimultaneousListeningPressure` | 真实端侧听写 | **skipped**（附实测原因） |

**没有做**：改弱断言、mock 掉能力检查、让产品代码迎合模拟器。

## 5. 最终状态

模拟器（iPhone 17 Pro / iOS 26.4.1）：

```text
122 passed, 0 failed, 1 skipped   ← skip 为根因三的端侧转写能力缺失
```

真机（iPhone 13 / iOS 26.7）：

```text
123 passed, 0 failed, 0 skipped
  testSimultaneousListeningPressure  1分59秒   ← 真实听写路径确实执行，未跳过
  testHomeModuleNavigation           11秒
  testColdLaunch                     24秒
```

Release device build：`SUCCEEDED`

## 6. 真机跑通的过程（ISSUE-UI-003）

设备上原本还有一道坎：免费 provisioning 的 App 数量上限（用户清理后降到 4 个）。
清掉之后出现了新的失败：

```text
run 1: Early unexpected exit ... exited with code 74
       [DTXConnection] Connection peer refused channel request for
         "dtxproxy:XCTestDriverInterface:XCTestManager_IDEInterface"
       [Default] Exiting due to IDE disconnection.

run 2: The test runner failed to initialize for UI testing.
       (Timed out while enabling automation mode.)
```

判别实验：同设备同会话先只跑单元测试 → **5/5 通过**，说明 `testmanagerd` 本身健康，
问题专属 UI automation 通道。旁证：

```text
xctrace list devices  → 菀墨 (26.7) 处于 Devices Offline
~/Library/Developer/Xcode/DeviceSupport  → 空（从未为该设备准备）
设备 iOS 26.7 (23H24)  >  Xcode SDK 26.4 (23E252)
USB  → 未连接
```

设备只有网络配对，Xcode 无法通过 USB 触发 DeviceSupport 准备。
设备上还留着 3 份历史 `DuiyiUITests-Runner` 崩溃日志，全是
`XCTRunnerDaemonSession sharedSession` 断言后 abort —— 同一失败模式。

**解法**：先用设备侧单元测试预热 `testmanagerd`，再跑 UI 测试：

```bash
# 1) 预热
mobilebuildmcp device test --device-id <DEV> \
  --json '{"extraArgs":["-only-testing:DuiyiTests/TaskStoreTests"]}'

# 2) 完整真机套件
mobilebuildmcp device test --device-id <DEV>
```

预热后 `testHomeModuleNavigation` 立刻通过（`Setting up automation session 3.68s`）。

### 已固化成脚本

顺序约定如果只写在文档里，迟早有人直接跑 UI 目标而重现 `exit 74`。所以做了
`.apm/tools/device-test.sh` —— **没有预热就不允许进入 UI 阶段**：

```bash
.apm/tools/device-test.sh                      # 预热 + 完整真机套件（推荐入口）
.apm/tools/device-test.sh ui                   # 预热 + 只跑 UI
.apm/tools/device-test.sh one <Target/Class/test>
.apm/tools/device-test.sh warm                 # 只预热
```

它还会在跑之前检查设备是否锁屏（锁屏直接退出码 2，不浪费一次完整构建），
预热失败则立即中止，失败时按证据强度打印排查顺序。

脚本自身端到端验证过：

```text
[1/2] 预热 testmanagerd（DuiyiTests/TaskStoreTests）
    warmup: SUCCEEDED  passed=5 failed=0 skipped=0
[2/2] 目标测试
    all: SUCCEEDED  passed=123 failed=0 skipped=0
✅ 真机测试通过        exit=0
```

> 写这个脚本时还踩了本仓库 `references/verification.md` 记录过的坑：变量紧邻中文全角标点时，
> bash 会把标点当成变量名的一部分，`echo "预热（$WARMUP）"` 在 `set -u` 下直接报
> 「未绑定的变量」。已全部改成 `${WARMUP}`。

## 7. 顺带修掉的一个自造缺陷

把听写用例改成 `async` 以做能力检查后，真机上立刻暴露：

```text
-[XCUIApplication _launchUsingXcode:...] must be called on the main thread
```

`async` 用例不在主线程执行，而 `launch()` 强制要求主线程。
模拟器上没暴露，是因为 skip 发生在 `launch()` **之前** —— 这正是
「只在能跑通的那条路径上验证」的典型盲区。已改回同步的能力检查。

## 8. 仍未解决

无。`testSimultaneousListeningPressure` 的真实听写路径已在物理设备验证通过。

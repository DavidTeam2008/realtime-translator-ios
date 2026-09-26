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

```text
UI 套件：  122 passed, 0 failed, 1 skipped
单元套件： 120 passed, 0 failed
Release device build：SUCCEEDED
```

## 6. 仍未解决

真机 UI test runner 仍因免费 provisioning profile 达到 App 安装上限而无法安装；
`testSimultaneousListeningPressure` 的真实听写路径**必须在真机上验证**。

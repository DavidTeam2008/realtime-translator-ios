import Speech
import XCTest

/// 端到端压力 + 翻译自验证脚本。
///
/// 拆成两个用例，因为两件事对**运行环境**的要求不同：
/// - `testSimultaneousListeningPressure`：需要真实端侧听写，只能在支持
///   `SpeechTranscriber` 的真机跑；模拟器上显式 skip 并写明原因。
/// - `testHomeModuleNavigation`：纯导航，任何环境都能跑，保留覆盖率。
final class SimultaneousFlowTests: XCTestCase {
    private let timeout: TimeInterval = 15

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    /// 启动 App 并声明前置条件：引导页已完成。
    ///
    /// 起因：全新安装时 `duiyi.onboardingComplete` 为 false，RootView 会用
    /// fullScreenCover 盖一层 OnboardingView。首页按钮在无障碍树里「存在」，
    /// 但被覆盖层挡住 → `waitForExistence` 通过、`tap()` 抛
    /// "Failed to not hittable"。这个用例之前靠模拟器里残留的旧状态才通过，
    /// 属于依赖环境的假绿。
    ///
    /// 走 UserDefaults 的 argument domain（优先级最高），不需要改生产代码，
    /// 也不需要依赖 OnboardingView 的文案与结构。
    private func launchApp() -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments += ["-duiyi.onboardingComplete", "YES"]
        app.launch()
        handleSystemAlerts(app)
        return app
    }

    /// 与 App 的 `SpeechAssetPreparer.isDeviceCapable` 保持同一套判据。
    /// 返回 nil 表示能力齐备，否则返回不可用的具体原因。
    private func speechCapabilityGap() async -> String? {
        guard SpeechTranscriber.isAvailable else {
            return "SpeechTranscriber.isAvailable=false（该运行时没有端侧转写器；iOS 模拟器属于此类）"
        }
        for tag in ["en-US", "zh-CN"] {
            if await SpeechTranscriber.supportedLocale(equivalentTo: Locale(identifier: tag)) == nil {
                return "SpeechTranscriber 不支持 locale \(tag)"
            }
        }
        return nil
    }

    func testSimultaneousListeningPressure() async throws {
        if let gap = await speechCapabilityGap() {
            throw XCTSkip("""
                跳过真实听写路径：\(gap)。
                实测依据见 .apm/issues/ISSUE-UI-002-simulator-speech-unavailable.json：
                locale(en-US)=en_US、locale(zh-CN)=zh_CN 均受支持，SFSpeechRecognizer
                .available/.onDevice 均为 true，但 SpeechTranscriber.isAvailable=false，
                App 因此正确显示「这台设备暂时不能离线识别这段语言。」。
                该路径请在真机验证。
                """)
        }

        let app = launchApp()

        // 内存/CPU/时钟度量：只跑 1 次迭代
        let options = XCTMeasureOptions()
        options.iterationCount = 1
        measure(metrics: [XCTMemoryMetric(), XCTCPUMetric(), XCTClockMetric()], options: options) {
            enterSimultaneousAndStart(app)
            sleep(20)
            dumpCaptions(app, tag: "AFTER-20S")
            tapListeningControl(app)
            app.buttons["nav-home"].tap()
        }

        try assertHomeModuleNavigation(app)
    }

    /// 纯导航覆盖：面对面进出 → 历史进出 → 回到首页。
    /// 不依赖端侧听写，因此在模拟器上也应稳定通过。
    func testHomeModuleNavigation() throws {
        let app = launchApp()
        try assertHomeModuleNavigation(app)
    }

    private func assertHomeModuleNavigation(_ app: XCUIApplication) throws {
        // 进出二级页面覆盖：面对面进出、历史进出
        let f2f = app.buttons["home-module-faceToFace"]
        XCTAssertTrue(f2f.waitForExistence(timeout: timeout), "home faceToFace entry missing")
        f2f.tap()
        XCTAssertTrue(app.buttons["nav-home"].waitForExistence(timeout: timeout))
        app.buttons["nav-home"].tap()

        let history = app.buttons["home-history"]
        if !history.waitForExistence(timeout: 5) {
            app.swipeUp()
        }
        XCTAssertTrue(history.waitForExistence(timeout: timeout), "home history entry missing")
        history.tap()
        // 历史页用 ModuleChrome 自定义导航（系统 toolbar 隐藏），经 nav-home 返回
        let historyHome = app.buttons["nav-home"]
        XCTAssertTrue(historyHome.waitForExistence(timeout: timeout), "history nav home missing")
        historyHome.tap()
        XCTAssertTrue(app.buttons["home-module-simultaneous"].waitForExistence(timeout: timeout),
                      "did not return to home")
    }

    private func enterSimultaneousAndStart(_ app: XCUIApplication) {
        // 1. 首页 → 同声传译
        let siEntry = app.buttons["home-module-simultaneous"]
        XCTAssertTrue(siEntry.waitForExistence(timeout: timeout), "home simultaneous entry missing")
        siEntry.tap()

        // 2. 方向固定为 English → 中文（幂等：已是该方向时跳过点选）
        setDirection(app, badge: "direction-source", chip: "langchip-english")
        setDirection(app, badge: "direction-target", chip: "langchip-zhHans")
        sleep(8)

        // 3. 新任务（如已有任务会弹确认框，统一处理）
        let newTask = app.buttons["taskbar-new-task"]
        XCTAssertTrue(newTask.waitForExistence(timeout: timeout), "new task button missing")
        newTask.tap()
        confirmReplaceTaskIfNeeded(app)

        // 4. 开始监听，并用控制钮文案变化证明已进入 listening（而非静默失败）
        let micLabelBefore = listeningLabel(app)
        tapListeningControl(app)
        grantPermissionsIfNeeded()
        sleep(3)
        let micLabelAfter = listeningLabel(app)
        print("MIC-LABEL before=[\(micLabelBefore)] after=[\(micLabelAfter)]")
        XCTAssertNotEqual(micLabelBefore, micLabelAfter, "mic tap did not change state; listening never started")
    }

    /// 显式授予麦克风 / 语音识别权限。
    ///
    /// 为什么不能只靠 `addUIInterruptionMonitor`：monitor 只在**下一次交互**时
    /// 才被 XCTest 调用。这里的时序是 —— `tap()` 先落地，App 的
    /// `PermissionService.requestAccess()` 随后才 await 权限弹窗；此后测试直接
    /// `sleep` + 读 label，中间没有任何交互，monitor 永远等不到触发时机，
    /// 断言就会以「按钮文案没变」的形式失败，掩盖真正的「权限没授予」。
    ///
    /// 首次安装会连续弹两个：麦克风 → 语音识别，所以这里循环处理。
    /// 只点明确匹配到白名单文案的按钮，不乱点「不允许」。
    private func grantPermissionsIfNeeded(rounds: Int = 6, timeout: TimeInterval = 8) {
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let allowTitles = ["允许", "Allow", "好", "OK", "好，允许"]

        for round in 1...rounds {
            let alert = springboard.alerts.firstMatch
            let found = alert.waitForExistence(timeout: timeout)
            let labels = springboard.alerts.allElementsBoundByIndex.map { $0.label }
            print("PERM-CHECK round=\(round) exists=\(found) alerts=\(labels)")
            guard found else { return }

            let allow = alert.buttons.allElementsBoundByIndex.first { button in
                allowTitles.contains(button.label)
            }
            guard let allow else {
                XCTFail("出现未识别的权限弹窗，按钮文案：\(labels)")
                return
            }
            print("PERM-TAP round=\(round) tapped=\(allow.label)")
            allow.tap()
        }
    }

    private func setDirection(_ app: XCUIApplication, badge: String, chip: String) {
        let badgeButton = app.buttons[badge]
        XCTAssertTrue(badgeButton.waitForExistence(timeout: timeout), "\(badge) missing")
        // 已是目标语言时徽章 label 含该语言名，跳过（避免触发重复的模型准备）
        if badgeButton.label.contains(chipLabel(chip)) { return }
        badgeButton.tap()
        let chipButton = app.buttons[chip]
        XCTAssertTrue(chipButton.waitForExistence(timeout: timeout), "\(chip) missing")
        chipButton.tap()
    }

    private func chipLabel(_ chip: String) -> String {
        switch chip {
        case "langchip-english": return "English"
        case "langchip-zhHans": return "中文"
        case "langchip-japanese": return "日本語"
        case "langchip-korean": return "한국어"
        case "langchip-thai": return "ไทย"
        case "langchip-vietnamese": return "Tiếng Việt"
        default: return chip
        }
    }

    private func dumpCaptions(_ app: XCUIApplication, tag: String) {
        print("===CAPTIONS-\(tag)-LIVE===")
        for e in app.staticTexts.matching(identifier: "caption-live").allElementsBoundByIndex {
            print("live: [\(e.label)]")
        }
        print("===CAPTIONS-\(tag)-HISTORY===")
        for e in app.staticTexts.matching(identifier: "caption-history").allElementsBoundByIndex {
            print("hist: [\(e.label)]")
        }
        print("===CAPTIONS-\(tag)-SOURCE===")
        for e in app.staticTexts.matching(identifier: "caption-source").allElementsBoundByIndex {
            print("src: [\(e.label)]")
        }
        print("===CAPTIONS-\(tag)-MIC===")
        print("mic: [\(listeningLabel(app))]")
    }

    private func listeningLabel(_ app: XCUIApplication) -> String {
        if app.buttons["listening-control"].waitForExistence(timeout: 5) {
            return app.buttons["listening-control"].label
        }
        return app.otherElements["listening-control"].label
    }

    // MARK: - helpers

    private func handleSystemAlerts(_ app: XCUIApplication) {
        addUIInterruptionMonitor(withDescription: "system permission") { alert in
            for title in ["允许", "Allow", "好", "OK", "好，允许"] {
                if alert.buttons[title].exists {
                    alert.buttons[title].tap()
                    return true
                }
            }
            return false
        }
    }

    private func confirmReplaceTaskIfNeeded(_ app: XCUIApplication) {
        // beginTask 的二次确认框（confirmationDialog），仅在已有任务时出现
        sleep(1)
        let sheets = app.sheets
        if sheets.count > 0 {
            for button in sheets.buttons.allElementsBoundByIndex {
                let label = button.label
                if label.contains("新任务") || label.contains("New") || label.contains("新建") {
                    button.tap()
                    return
                }
            }
            // 兜底：点 sheet 第一个非取消按钮
            if sheets.buttons.count > 1 {
                sheets.buttons.element(boundBy: 0).tap()
            }
        }
        // 触发一次中断监控（权限弹窗等）
        app.tap()
    }

    private func tapListeningControl(_ app: XCUIApplication) {
        // 先按 button 查，再按其他元素查（ZStack + gesture 的曝光形态按系统版本略有差异）
        if app.buttons["listening-control"].waitForExistence(timeout: timeout) {
            app.buttons["listening-control"].tap()
            return
        }
        let other = app.otherElements["listening-control"]
        XCTAssertTrue(other.waitForExistence(timeout: timeout), "listening control missing")
        other.tap()
    }
}

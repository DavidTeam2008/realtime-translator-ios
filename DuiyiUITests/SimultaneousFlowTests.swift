import XCTest

/// 端到端压力脚本：
/// 首页 → 同传（新任务 → 开始监听 20s → 停止 → 回首页，带内存/CPU/时钟度量）→
/// 面对面进出 → 历史进出。覆盖进出二级页面、二级页面功能运行、App 内页面跳转。
final class SimultaneousFlowTests: XCTestCase {
    private let timeout: TimeInterval = 15

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testSimultaneousListeningPressure() throws {
        let app = XCUIApplication()
        app.launch()
        handleSystemAlerts(app)

        // 内存/CPU/时钟度量：只跑 1 次迭代，覆盖“进同传 → 新任务 → 开始监听 20s → 停止 → 回首页”
        let options = XCTMeasureOptions()
        options.iterationCount = 1
        measure(metrics: [XCTMemoryMetric(), XCTCPUMetric(), XCTClockMetric()], options: options) {
            enterSimultaneousAndStart(app)
            sleep(20)
            tapListeningControl(app)
            app.buttons["nav-home"].tap()
        }

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
        if !history.waitForExistence(timeout: 10) {
            print("===DUMP-BUTTONS-AT-HISTORY-STEP===")
            for b in app.buttons.allElementsBoundByIndex {
                print("button id=\(b.identifier) label=\(b.label.prefix(40)) hittable=\(b.isHittable)")
            }
        }
        XCTAssertTrue(history.exists, "home history entry missing")
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

        // 2. 新任务（如已有任务会弹确认框，统一处理）
        let newTask = app.buttons["taskbar-new-task"]
        XCTAssertTrue(newTask.waitForExistence(timeout: timeout), "new task button missing")
        newTask.tap()
        confirmReplaceTaskIfNeeded(app)

        // 3. 开始监听（ListeningControl 是带 .isButton trait 的无障碍元素）
        tapListeningControl(app)
        sleep(3)
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

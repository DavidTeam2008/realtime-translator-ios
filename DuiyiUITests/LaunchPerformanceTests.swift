import XCTest

/// 冷启动性能：系统级度量，由 Xcode 在真机上采集。
final class LaunchPerformanceTests: XCTestCase {
    func testColdLaunch() throws {
        let options = XCTMeasureOptions()
        options.iterationCount = 3
        measure(metrics: [XCTApplicationLaunchMetric()], options: options) {
            let app = XCUIApplication()
            app.launch()
            XCTAssertTrue(app.buttons["home-module-simultaneous"].waitForExistence(timeout: 15))
            app.terminate()
        }
    }
}

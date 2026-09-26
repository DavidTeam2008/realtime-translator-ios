import Foundation
import MetricKit
import os

/// Lightweight startup instrumentation following the Douyin实战篇 approach:
/// process-start (sysctl) -> first init -> SwiftData ready -> view-models ready -> first frame.
enum AppLaunchStage: String {
    case processStart
    case appInit
    /// SwiftUI Scene 首次求值（DuiyiApp.body）
    case appBody
    case environmentReady
    /// RootView.body 首次求值
    case rootBody
    /// HomeView.body 首次求值
    case homeBody
    case storeReady
    case viewModelsReady
    /// RootView.onAppear 进入
    case rootAppear
    /// HomeView.onAppear 进入
    case homeAppear
    /// HomeView.task 开始
    case homeTaskStart
    /// HomeView.task 完成（赋值 @State 之后）
    case homeTaskEnd
    case firstFrame
}

final class AppLaunchTracker: NSObject, MXMetricManagerSubscriber, @unchecked Sendable {
    static let shared = AppLaunchTracker()

    private let log = OSLog(subsystem: "com.david.Duiyi", category: "launch")
    private let lock = NSLock()
    private var marks: [(stage: AppLaunchStage, at: CFAbsoluteTime)] = []
    private let processStart: CFAbsoluteTime

    private override init() {
        self.processStart = Self.processStartTime()
        super.init()
        record(.processStart)
        // 记录埋点自身被触碰的时刻 —— 它与 pre-main 打点之间的差，
        // 就是「dyld 之后、Swift 首个初始化器之前」的耗时（如 AppCoordinator 构造）。
        let offset = (CFAbsoluteTimeGetCurrent() - processStart) * 1000
        DuiyiLog.session.info("TRACKER init at +\(Int(offset), privacy: .public)ms since process start")
        MXMetricManager.shared.add(self)
    }

    // MARK: - Public API (call from startup path only)

    func begin(_ stage: AppLaunchStage) {
        record(stage)
    }

    /// 只在**首次**记录该阶段。
    /// 用于 SwiftUI `body` —— body 会被多次求值，我们只关心首次进入渲染的时刻。
    @discardableResult
    func beginOnce(_ stage: AppLaunchStage) -> Bool {
        lock.lock()
        let seen = marks.contains { $0.stage == stage }
        lock.unlock()
        guard !seen else { return false }
        record(stage)
        return true
    }

    func markFirstFrame() {
        record(.firstFrame)
        let elapsed = CFAbsoluteTimeGetCurrent() - processStart
        DuiyiLog.session.info("App launch first-frame: \(Int(elapsed * 1000), privacy: .public)ms since process start")

        // 临时：阶段拆分（原实现记录了 6 个阶段却只打印总数，导致无法定位瓶颈）
        lock.lock()
        let snapshot = marks
        lock.unlock()
        var prev: CFAbsoluteTime = processStart
        var parts: [String] = []
        for m in snapshot {
            let since = Int((m.at - processStart) * 1000)
            let delta = Int((m.at - prev) * 1000)
            parts.append("\(m.stage.rawValue)=\(since)/+\(delta)")
            prev = m.at
        }
        DuiyiLog.session.info("Launch stages (since/+delta ms): \(parts.joined(separator: " "), privacy: .public)")
    }

    func launchDurationToNow() -> TimeInterval {
        CFAbsoluteTimeGetCurrent() - processStart
    }

    // MARK: - MXMetricManagerSubscriber

    func didReceive(_ payloads: [MXMetricPayload]) {
        for payload in payloads {
            if let launch = payload.applicationLaunchMetrics {
                DuiyiLog.session.info(
                    "MetricKit launch histogram: \(String(describing: launch.histogrammedTimeToFirstDraw), privacy: .public)"
                )
            }
        }
    }

    // MARK: - Private

    private func record(_ stage: AppLaunchStage) {
        let now = CFAbsoluteTimeGetCurrent()
        lock.withLock { marks.append((stage, now)) }
        // Static signpost name "launch", dynamic stage in message (StaticString requirement).
        os_signpost(.event, log: log, name: "launch", "%{public}s", stage.rawValue)
    }

    /// True process creation time via sysctl kern.proc.pid.<pid>, fallback to "now" on failure.
    /// Matches the article's recommended start point (vs. App init which misses dyld time).
    static func processStartTime() -> CFAbsoluteTime {
        var mib: [Int32] = [CTL_KERN, KERN_PROC, KERN_PROC_PID, getpid()]
        var info = kinfo_proc()
        var size = MemoryLayout<kinfo_proc>.size
        let result = mib.withUnsafeMutableBufferPointer { ptr -> Int32 in
            sysctl(ptr.baseAddress, 4, &info, &size, nil, 0)
        }
        guard result == 0 else { return CFAbsoluteTimeGetCurrent() }
        var tv = info.kp_proc.p_starttime
        let sec = Double(tv.tv_sec) + Double(tv.tv_usec) / 1_000_000.0
        // Convert Unix epoch to CFAbsoluteTime (seconds since 2001-01-01).
        let cfReferenceOffset = 978307200.0
        return sec - cfReferenceOffset
    }
}

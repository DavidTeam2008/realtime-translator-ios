import Foundation
import MetricKit
import os

/// Lightweight startup instrumentation following the Douyin实战篇 approach:
/// process-start (sysctl) -> first init -> SwiftData ready -> view-models ready -> first frame.
enum AppLaunchStage: String {
    case processStart
    case appInit
    case environmentReady
    case storeReady
    case viewModelsReady
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
        MXMetricManager.shared.add(self)
    }

    // MARK: - Public API (call from startup path only)

    func begin(_ stage: AppLaunchStage) {
        record(stage)
    }

    func markFirstFrame() {
        record(.firstFrame)
        let elapsed = CFAbsoluteTimeGetCurrent() - processStart
        DuiyiLog.session.info("App launch first-frame: \(Int(elapsed * 1000), privacy: .public)ms since process start")
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

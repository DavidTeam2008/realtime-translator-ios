import Foundation

enum SessionState: Equatable, Sendable {
    case idle
    case preparing
    case ready
    case listening
    case paused
    case failed(DuiyiError)

    var isListening: Bool {
        self == .listening
    }

    var isFailed: Bool {
        if case .failed = self { return true }
        return false
    }
}

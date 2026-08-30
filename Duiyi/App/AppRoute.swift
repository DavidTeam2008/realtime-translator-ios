import Foundation

enum AppRoute: Hashable, Sendable {
    case conversation
    case interpretation
    case meeting
    case history
    case taskDetail(UUID)
}

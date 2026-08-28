import Foundation

enum SpeakerSide: String, Sendable, Hashable {
    case user
    case peer

    var opposite: SpeakerSide {
        switch self {
        case .user: return .peer
        case .peer: return .user
        }
    }
}

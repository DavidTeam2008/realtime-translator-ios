import Foundation

enum AppMode: String, Codable, CaseIterable, Sendable {
    case faceToFace
    case simultaneous
    case meeting

    var featureID: FeatureID {
        switch self {
        case .faceToFace: return .faceToFace
        case .simultaneous: return .simultaneous
        case .meeting: return .meeting
        }
    }
}

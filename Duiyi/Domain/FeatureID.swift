import Foundation

enum FeatureID: String, Codable, CaseIterable, Sendable, Hashable {
    case faceToFace
    case simultaneous
    case meeting

    var appMode: AppMode {
        switch self {
        case .faceToFace: return .faceToFace
        case .simultaneous: return .simultaneous
        case .meeting: return .meeting
        }
    }
}

struct FeatureDescriptor: Identifiable {
    var id: FeatureID
    var title: @Sendable (AppLanguage) -> String
    var subtitle: @Sendable (AppLanguage) -> String
    var symbolName: String
}

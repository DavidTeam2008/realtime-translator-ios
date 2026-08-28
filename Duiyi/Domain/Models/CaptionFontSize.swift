import CoreGraphics
import Foundation

enum CaptionFontSize: String, Codable, CaseIterable, Sendable {
    case standard
    case larger
    case largest

    var livePoints: CGFloat {
        switch self {
        case .standard: return 20
        case .larger: return 24
        case .largest: return 28
        }
    }

    var previousPoints: CGFloat {
        switch self {
        case .standard: return 15
        case .larger: return 16
        case .largest: return 18
        }
    }
}

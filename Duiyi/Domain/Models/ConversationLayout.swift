import CoreGraphics
import Foundation

enum ConversationLayout {
    static let midBarHeight: CGFloat = 72
    static let micSize: CGFloat = 64
    static let micHitSize: CGFloat = 88
    static let horizontalPadding: CGFloat = 22
    static let captionAnimationDuration: Double = 0.18
    static let captionAppearOffset: CGFloat = 4
    static let translationDebounceMilliseconds: UInt64 = 90
    static let firstTranslationDebounceMilliseconds: UInt64 = 40
    static let liveFontCap: CGFloat = 32
    static let silenceCommitMilliseconds: UInt64 = 1100
    static let idleRestoreSeconds: Double = 30
}

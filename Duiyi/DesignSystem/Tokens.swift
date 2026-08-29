import SwiftUI
import UIKit

enum Tokens {
    static let canvas = Color(hex: 0x12141A)
    static let userPane = Color(hex: 0x161920)
    static let peerPane = Color(hex: 0x1A1714)
    static let textPrimary = Color(hex: 0xF4EFE6)
    static let textSecondary = Color(hex: 0xF4EFE6).opacity(0.58)
    static let listen = Color(hex: 0xE8B86D)
    static let languageZH = Color(hex: 0xE8B86D)
    static let languageEN = Color(hex: 0x7EC8C3)
    static let languageJA = Color(hex: 0xE07A7A)
    static let languageKO = Color(hex: 0x7EA0E8)
    static let languageTH = Color(hex: 0xC49BE8)
    static let languageVI = Color(hex: 0x7ECF9A)
    static let danger = Color(hex: 0xE07070)
    static let controlIdle = Color(hex: 0x2A2E38)
    static let sheet = Color(hex: 0x23262F)
    static let sheetChip = Color(hex: 0x2F3340)

    static func languageBadge(_ language: AppLanguage) -> Color {
        switch language {
        case .zhHans: return languageZH
        case .english: return languageEN
        case .japanese: return languageJA
        case .korean: return languageKO
        case .thai: return languageTH
        case .vietnamese: return languageVI
        }
    }

    static let horizontalPadding = ConversationLayout.horizontalPadding
    static let midBarHeight = ConversationLayout.midBarHeight
    static let micSize = ConversationLayout.micSize
    static let micHitSize = ConversationLayout.micHitSize
}

extension Color {
    init(hex: UInt32, alpha: Double = 1) {
        self.init(
            .sRGB,
            red: Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255,
            opacity: alpha
        )
    }
}

enum CaptionTypography {
    static func liveFont(size: CaptionFontSize, settled: Bool) -> Font {
        let metrics = UIFontMetrics(forTextStyle: .title1)
        let points = min(metrics.scaledValue(for: size.livePoints), ConversationLayout.liveFontCap)
        return .system(size: points, weight: settled ? .semibold : .regular, design: .default)
    }

    static func previousFont(size: CaptionFontSize) -> Font {
        let metrics = UIFontMetrics(forTextStyle: .callout)
        let points = min(metrics.scaledValue(for: size.previousPoints), size.previousPoints + 4)
        return .system(size: points, weight: .regular, design: .default)
    }

    static func badgeFont() -> Font {
        .system(size: 13, weight: .medium, design: .default)
    }

    static func controlFont() -> Font {
        .system(size: 15, weight: .medium, design: .default)
    }

    static func sourceLineFont() -> Font {
        .system(size: 13, weight: .regular, design: .default)
    }
}

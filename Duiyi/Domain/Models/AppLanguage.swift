import Foundation

enum AppLanguage: String, Codable, CaseIterable, Sendable, Hashable {
    case zhHans
    case english
    case japanese
    case korean
    case thai
    case vietnamese

    var defaultPeer: AppLanguage {
        self == .english ? .zhHans : .english
    }

    var localeIdentifier: String {
        switch self {
        case .zhHans: return "zh-Hans"
        case .english: return "en"
        case .japanese: return "ja"
        case .korean: return "ko"
        case .thai: return "th"
        case .vietnamese: return "vi"
        }
    }

    var speechLocaleIdentifier: String {
        switch self {
        case .zhHans: return "zh_CN"
        case .english: return "en_US"
        case .japanese: return "ja_JP"
        case .korean: return "ko_KR"
        case .thai: return "th_TH"
        case .vietnamese: return "vi_VN"
        }
    }

    var locale: Locale {
        Locale(identifier: speechLocaleIdentifier)
    }

    var localeLanguage: Locale.Language {
        Locale.Language(identifier: localeIdentifier)
    }

    var badge: String {
        switch self {
        case .zhHans: return "ZH"
        case .english: return "EN"
        case .japanese: return "JA"
        case .korean: return "KO"
        case .thai: return "TH"
        case .vietnamese: return "VI"
        }
    }

    var nativeName: String {
        switch self {
        case .zhHans: return "中文"
        case .english: return "English"
        case .japanese: return "日本語"
        case .korean: return "한국어"
        case .thai: return "ไทย"
        case .vietnamese: return "Tiếng Việt"
        }
    }

    var usesLatinScript: Bool {
        switch self {
        case .english, .vietnamese: return true
        default: return false
        }
    }

    var speechVoiceLanguage: String {
        switch self {
        case .zhHans: return "zh-CN"
        case .english: return "en-US"
        case .japanese: return "ja-JP"
        case .korean: return "ko-KR"
        case .thai: return "th-TH"
        case .vietnamese: return "vi-VN"
        }
    }

    func pick(zh: String, en: String, ja: String, ko: String, th: String, vi: String) -> String {
        switch self {
        case .zhHans: return zh
        case .english: return en
        case .japanese: return ja
        case .korean: return ko
        case .thai: return th
        case .vietnamese: return vi
        }
    }

    static func inferredFromSystem() -> AppLanguage {
        let preferred = (Locale.preferredLanguages.first ?? Locale.current.identifier).lowercased()
        if preferred.hasPrefix("zh") { return .zhHans }
        if preferred.hasPrefix("ja") { return .japanese }
        if preferred.hasPrefix("ko") { return .korean }
        if preferred.hasPrefix("th") { return .thai }
        if preferred.hasPrefix("vi") { return .vietnamese }
        return .english
    }
}

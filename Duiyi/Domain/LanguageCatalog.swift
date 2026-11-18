import Foundation

struct LanguageCapability: Sendable, Equatable {
    var speechLocale: String
    var translation: Locale.Language
    var ttsVoice: String
    var speech: Bool
    var translate: Bool
    var speak: Bool
}

protocol LanguageCataloging: Sendable {
    var all: [AppLanguage] { get }
    func capability(_ language: AppLanguage) -> LanguageCapability
    func speechSupported(_ language: AppLanguage) async -> Bool
    func translationPair(from: AppLanguage, to: AppLanguage) async -> TranslationPairStatus
}

struct StaticLanguageCatalog: LanguageCataloging {
    var all: [AppLanguage] { AppLanguage.allCases }

    func capability(_ language: AppLanguage) -> LanguageCapability {
        LanguageCapability(
            speechLocale: language.speechLocaleIdentifier,
            translation: language.localeLanguage,
            ttsVoice: language.speechVoiceLanguage,
            speech: true,
            translate: true,
            speak: true
        )
    }

    func speechSupported(_ language: AppLanguage) async -> Bool {
        capability(language).speech
    }

    func translationPair(from: AppLanguage, to: AppLanguage) async -> TranslationPairStatus {
        from == to ? .unsupported : .supported
    }
}

enum LanguageCatalogSelection {
    static func unavailableLanguages(
        capabilities: [AppLanguage: LanguageCapability]
    ) -> Set<AppLanguage> {
        Set(
            capabilities.compactMap { language, capability in
                capability.speech && capability.translate && capability.speak ? nil : language
            }
        )
    }

    static func unavailableLanguages(from catalog: any LanguageCataloging) -> Set<AppLanguage> {
        unavailableLanguages(
            capabilities: Dictionary(
                uniqueKeysWithValues: catalog.all.map { ($0, catalog.capability($0)) }
            )
        )
    }
}

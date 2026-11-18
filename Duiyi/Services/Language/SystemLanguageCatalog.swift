import AVFoundation
import Foundation
import Speech
import Translation

protocol SpeechLocaleChecking: Sendable {
    func supportedLocale(for language: AppLanguage) async -> Bool
}

protocol TTSVoiceChecking: Sendable {
    func hasVoice(for language: AppLanguage) async -> Bool
}

struct SystemSpeechLocaleChecker: SpeechLocaleChecking {
    func supportedLocale(for language: AppLanguage) async -> Bool {
        guard SpeechTranscriber.isAvailable else { return false }
        return await SpeechTranscriber.supportedLocale(equivalentTo: language.locale) != nil
    }
}

struct SystemTTSVoiceChecker: TTSVoiceChecking {
    func hasVoice(for language: AppLanguage) async -> Bool {
        AVSpeechSynthesisVoice(language: language.speechVoiceLanguage) != nil
    }
}

/// Lock-protected mutable catalog state.  All methods are synchronous so async
/// probe code never holds the lock across suspension.
private final class SystemLanguageCatalogState: @unchecked Sendable {
    private let lock = NSLock()
    private var capabilities: [AppLanguage: LanguageCapability] = [:]
    private var pairStatuses: [OrderedLanguagePair: TranslationPairStatus] = [:]
    private var refreshed = false

    var hasRefreshed: Bool {
        lock.lock()
        defer { lock.unlock() }
        return refreshed
    }

    func capability(_ language: AppLanguage) -> LanguageCapability {
        lock.lock()
        defer { lock.unlock() }
        return capabilities[language] ?? LanguageCapability(
            speechLocale: language.speechLocaleIdentifier,
            translation: language.localeLanguage,
            ttsVoice: language.speechVoiceLanguage,
            speech: true,
            translate: true,
            speak: true
        )
    }

    func cachedPair(_ key: OrderedLanguagePair) -> TranslationPairStatus? {
        lock.lock()
        defer { lock.unlock() }
        return pairStatuses[key]
    }

    func publish(
        capabilities: [AppLanguage: LanguageCapability],
        pairStatuses: [OrderedLanguagePair: TranslationPairStatus]
    ) {
        lock.lock()
        defer { lock.unlock() }
        self.capabilities = capabilities
        self.pairStatuses = pairStatuses
        self.refreshed = true
    }
}

/// System-backed catalog.  Probing is explicit; reads are cache lookups so
/// SwiftUI can call `capability(_:)` from the main actor.
final class SystemLanguageCatalog: LanguageCataloging, @unchecked Sendable {
    private let state = SystemLanguageCatalogState()
    private let speechChecker: any SpeechLocaleChecking
    private let translationChecker: any TranslationAvailabilityChecking
    private let ttsChecker: any TTSVoiceChecking

    init(
        speechChecker: any SpeechLocaleChecking = SystemSpeechLocaleChecker(),
        translationChecker: any TranslationAvailabilityChecking = TranslationAvailabilityService(),
        ttsChecker: any TTSVoiceChecking = SystemTTSVoiceChecker()
    ) {
        self.speechChecker = speechChecker
        self.translationChecker = translationChecker
        self.ttsChecker = ttsChecker
    }

    var all: [AppLanguage] { AppLanguage.allCases }

    func capability(_ language: AppLanguage) -> LanguageCapability {
        state.capability(language)
    }

    func speechSupported(_ language: AppLanguage) async -> Bool {
        capability(language).speech
    }

    func translationPair(from: AppLanguage, to: AppLanguage) async -> TranslationPairStatus {
        if from == to { return .unsupported }
        let key = OrderedLanguagePair(from: from, to: to)
        if let cached = state.cachedPair(key) { return cached }
        let status = await translationChecker.pairStatus(from: from, to: to)
        return status
    }

    func refreshCapabilities() async {
        guard !state.hasRefreshed else { return }

        var speechValues: [AppLanguage: Bool] = [:]
        var voiceValues: [AppLanguage: Bool] = [:]
        for language in AppLanguage.allCases {
            speechValues[language] = await speechChecker.supportedLocale(for: language)
            voiceValues[language] = await ttsChecker.hasVoice(for: language)
        }

        var pairValues: [OrderedLanguagePair: TranslationPairStatus] = [:]
        for source in AppLanguage.allCases {
            for target in AppLanguage.allCases where source.rawValue < target.rawValue {
                let key = OrderedLanguagePair(from: source, to: target)
                pairValues[key] = await translationChecker.pairStatus(from: key.from, to: key.to)
            }
        }

        var values: [AppLanguage: LanguageCapability] = [:]
        for language in AppLanguage.allCases {
            let participatesInTranslation = pairValues.contains { key, status in
                status != .unsupported && (key.from == language || key.to == language)
            }
            values[language] = LanguageCapability(
                speechLocale: language.speechLocaleIdentifier,
                translation: language.localeLanguage,
                ttsVoice: language.speechVoiceLanguage,
                speech: speechValues[language] == true,
                translate: participatesInTranslation,
                speak: voiceValues[language] == true
            )
        }
        state.publish(capabilities: values, pairStatuses: pairValues)
    }
}

struct OrderedLanguagePair: Hashable, Sendable {
    let from: AppLanguage
    let to: AppLanguage

    init(from: AppLanguage, to: AppLanguage) {
        if from.rawValue < to.rawValue {
            self.from = from
            self.to = to
        } else {
            self.from = to
            self.to = from
        }
    }
}

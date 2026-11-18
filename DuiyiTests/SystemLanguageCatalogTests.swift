import Foundation
import Testing
@testable import Duiyi

actor RecordingSpeechLocaleChecker: SpeechLocaleChecking {
    private let supported: Set<AppLanguage>
    private(set) var callCount = 0

    init(supported: Set<AppLanguage>) {
        self.supported = supported
    }

    func supportedLocale(for language: AppLanguage) async -> Bool {
        callCount += 1
        return supported.contains(language)
    }

    func currentCallCount() async -> Int { callCount }
}

actor RecordingTTSVoiceChecker: TTSVoiceChecking {
    private let supported: Set<AppLanguage>
    private(set) var callCount = 0

    init(supported: Set<AppLanguage>) {
        self.supported = supported
    }

    func hasVoice(for language: AppLanguage) async -> Bool {
        callCount += 1
        return supported.contains(language)
    }

    func currentCallCount() async -> Int { callCount }
}

actor RecordingTranslationAvailability: TranslationAvailabilityChecking {
    private let unsupportedSources: Set<AppLanguage>
    private(set) var callCount = 0

    init(unsupportedSources: Set<AppLanguage> = []) {
        self.unsupportedSources = unsupportedSources
    }

    func pairStatus(from: AppLanguage, to: AppLanguage) async -> TranslationPairStatus {
        callCount += 1
        if from == to || unsupportedSources.contains(from) {
            return .unsupported
        }
        return .supported
    }

    func currentCallCount() async -> Int { callCount }
}

@MainActor
struct SystemLanguageCatalogTests {
    @Test("Capabilities stay permissive before the first refresh")
    func preRefreshCapabilitiesArePermissive() async {
        let catalog = SystemLanguageCatalog(
            speechChecker: RecordingSpeechLocaleChecker(supported: []),
            translationChecker: RecordingTranslationAvailability(unsupportedSources: AppLanguage.allCases),
            ttsChecker: RecordingTTSVoiceChecker(supported: [])
        )
        let capability = catalog.capability(.english)

        #expect(capability.speech)
        #expect(capability.translate)
        #expect(capability.speak)
        #expect(await catalog.speechSupported(.english))
    }

    @Test("Refresh maps supported probes to a capable language")
    func refreshMapsSupportedLanguage() async {
        let catalog = makeCatalog(
            speech: [.english],
            voices: [.english],
            unsupportedSources: [.thai]
        )
        await catalog.refreshCapabilities()
        let capability = catalog.capability(.english)

        #expect(capability.speech)
        #expect(capability.translate)
        #expect(capability.speak)
    }

    @Test("Unsupported probes map to false capabilities")
    func refreshMapsUnsupportedLanguage() async {
        let catalog = makeCatalog(
            speech: [.english],
            voices: [],
            unsupportedSources: [.thai]
        )
        await catalog.refreshCapabilities()
        let capability = catalog.capability(.thai)

        #expect(!capability.speech)
        #expect(!capability.translate)
        #expect(!capability.speak)
        let speechSupported = await catalog.speechSupported(.thai)
        #expect(!speechSupported)
    }

    @Test("A language with no supported pair is not translation-capable")
    func unsupportedSourceHasNoTranslationCapability() async {
        let catalog = makeCatalog(
            speech: [.thai],
            voices: [.thai],
            unsupportedSources: [.thai]
        )
        await catalog.refreshCapabilities()

        #expect(!catalog.capability(.thai).translate)
    }

    @Test("Repeated refresh does not probe the system again")
    func repeatedRefreshUsesCache() async {
        let speech = RecordingSpeechLocaleChecker(supported: [.english])
        let translation = RecordingTranslationAvailability()
        let voices = RecordingTTSVoiceChecker(supported: [.english])
        let catalog = SystemLanguageCatalog(
            speechChecker: speech,
            translationChecker: translation,
            ttsChecker: voices
        )
        await catalog.refreshCapabilities()
        await catalog.refreshCapabilities()

        #expect(await speech.currentCallCount() == AppLanguage.allCases.count)
        #expect(await voices.currentCallCount() == AppLanguage.allCases.count)
        #expect(await translation.currentCallCount() == 15)
    }

    @Test("Capability lookup does not perform system probes")
    func capabilityLookupUsesCache() async {
        let speech = RecordingSpeechLocaleChecker(supported: [.english])
        let translation = RecordingTranslationAvailability()
        let voices = RecordingTTSVoiceChecker(supported: [.english])
        let catalog = SystemLanguageCatalog(
            speechChecker: speech,
            translationChecker: translation,
            ttsChecker: voices
        )
        await catalog.refreshCapabilities()
        let beforeSpeech = await speech.currentCallCount()
        let beforeVoices = await voices.currentCallCount()

        _ = catalog.capability(.english)
        _ = catalog.capability(.english)
        _ = await catalog.speechSupported(.english)

        #expect(await speech.currentCallCount() == beforeSpeech)
        #expect(await voices.currentCallCount() == beforeVoices)
    }

    @Test("Same-language translation is rejected without a probe")
    func sameLanguagePairIsUnsupported() async {
        let translation = RecordingTranslationAvailability()
        let catalog = SystemLanguageCatalog(
            speechChecker: RecordingSpeechLocaleChecker(supported: [.english]),
            translationChecker: translation,
            ttsChecker: RecordingTTSVoiceChecker(supported: [.english])
        )

        let status = await catalog.translationPair(from: .english, to: .english)

        #expect(status == .unsupported)
        #expect(await translation.currentCallCount() == 0)
    }

    @Test("Selection derives disabled languages from false capabilities")
    func selectionDerivesDisabledLanguages() async {
        let capabilities: [AppLanguage: LanguageCapability] = [
            .english: LanguageCapability(
                speechLocale: "en_US",
                translation: .english,
                ttsVoice: "en-US",
                speech: true,
                translate: true,
                speak: true
            ),
            .thai: LanguageCapability(
                speechLocale: "th_TH",
                translation: .thai,
                ttsVoice: "th-TH",
                speech: false,
                translate: true,
                speak: false
            ),
        ]

        let disabled = LanguageCatalogSelection.unavailableLanguages(capabilities: capabilities)

        #expect(disabled == [.thai])
    }

    private func makeCatalog(
        speech: Set<AppLanguage>,
        voices: Set<AppLanguage>,
        unsupportedSources: Set<AppLanguage>
    ) -> SystemLanguageCatalog {
        SystemLanguageCatalog(
            speechChecker: RecordingSpeechLocaleChecker(supported: speech),
            translationChecker: RecordingTranslationAvailability(unsupportedSources: unsupportedSources),
            ttsChecker: RecordingTTSVoiceChecker(supported: voices)
        )
    }
}

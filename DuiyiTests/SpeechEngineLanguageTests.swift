import Foundation
import Testing
@testable import Duiyi

struct SpeechEngineLanguageTests {
    @Test("Meeting multilingual keeps every requested locale")
    func keepsAllRequestedLanguages() {
        let languages = BilingualSpeechEngine.normalizedLanguages(
            languages: [.japanese, .korean, .thai, .vietnamese],
            fallback: .zhHans
        )
        #expect(languages.prefix(2).count == 2)
        #expect(languages == [.japanese, .korean, .thai, .vietnamese])
    }

    @Test("Empty request falls back to the display language")
    func emptyUsesFallback() {
        let languages = BilingualSpeechEngine.normalizedLanguages(languages: [], fallback: .english)
        #expect(languages == [.english])
    }
}

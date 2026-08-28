import Foundation
import Testing
@testable import Duiyi

struct TranscriptDigestTests {
    @Test("Local digest groups speakers in the reader language")
    func digestGroupsSpeakers() {
        let entries = [
            TranscriptEntry(
                id: UUID(),
                speaker: .peer,
                source: .english,
                sourceText: "See you at three",
                translatedText: "三点见",
                isFinal: true
            ),
            TranscriptEntry(
                id: UUID(),
                speaker: .user,
                source: .zhHans,
                sourceText: "好的",
                translatedText: "Okay",
                isFinal: true
            )
        ]
        let text = FoundationModelsSummarizer.digest(entries: entries, outputLanguage: .zhHans)
        #expect(text.contains("对方"))
        #expect(text.contains("三点见"))
        #expect(text.contains("你"))
        #expect(text.contains("好的") || text.contains("Okay"))
    }
}

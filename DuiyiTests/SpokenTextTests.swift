import Foundation
import Testing
@testable import Duiyi

struct SpokenTextTests {
    @Test("A longer restatement of the same English sentence is a continuation")
    func englishGrowsAsContinuation() {
        let previous = "The more inference added to the database"
        let incoming = "The more inference added to the database of media from plot TV to games"
        #expect(SpokenText.isContinuation(incoming, of: previous, language: .english))
    }

    @Test("A different English sentence is not a continuation")
    func differentEnglishSentencesAreDistinct() {
        #expect(
            !SpokenText.isContinuation(
                "I'd like a cup of coffee please",
                of: "See you at three in the lobby",
                language: .english
            )
        )
    }

    @Test("Hello and Goodbye stay distinct")
    func helloAndGoodbyeAreDistinct() {
        #expect(!SpokenText.isContinuation("Goodbye", of: "Hello", language: .english))
    }
}

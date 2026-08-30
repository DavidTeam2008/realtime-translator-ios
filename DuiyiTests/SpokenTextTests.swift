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

    @Test("A longer translation covers the shorter one")
    func longerTranslationCoversShorter() {
        #expect(SpokenText.covers("嗨，Jack。嗨，Lucy", of: "嗨，Jack"))
        #expect(!SpokenText.covers("嗨，Lucy", of: "嗨，Jack"))
        #expect(SpokenText.isRewrite("嗨，Jack", incoming: "嗨，Lucy"))
        #expect(SpokenText.isShortRewrite("嗨，Jack", incoming: "嗨，Lucy"))
    }

    @Test("Preferred translation does not shrink")
    func preferredTranslationDoesNotShrink() {
        #expect(
            SpokenText.preferredTranslation("嗨，Jack。嗨，Lucy", "嗨，Lucy") == "嗨，Jack。嗨，Lucy"
        )
    }

    @Test("Growing movie-title translations are the same sentence")
    func movieTitleFragmentsAreRefinements() {
        #expect(
            SpokenText.isRefinement(
                "好吧，我们错过了一部叫《幸运的日子》的电影，我想看",
                of: "好吧，我们错过了一部叫《幸运》的电影"
            )
        )
        #expect(
            SpokenText.preferredTranslation(
                "好吧，我们错过了一部叫《幸运》的电影",
                "好吧，我们错过了一部叫《幸运的日子》的电影，我想看"
            ) == "好吧，我们错过了一部叫《幸运的日子》的电影，我想看"
        )
        #expect(
            !SpokenText.isRefinement("嗨，Lucy", of: "嗨，Jack")
        )
        #expect(
            !SpokenText.isRefinement("See you later Lucy", of: "See you later Jack")
        )
        #expect(
            SpokenText.isRefinement(
                "好吧，我们错过了一部叫《幸运的日子》的电影，我想看，但另一部叫《船》的电影本周上映。",
                of: "好吧，我们错过了一部叫《幸运的日子》的电影，我想看，但另一部叫《船》的电影就在这上面"
            )
        )
        #expect(
            SpokenText.isRefinement(
                "好吧，我们错过了一部叫《幸运的日子》的电影，我想看",
                of: "好吧，我们错过了一部叫《幸运日》的电影，它"
            )
        )
        #expect(
            SpokenText.preferredTranslation(
                "好吧，我们错过了一部叫《幸运的日子》的电影，我想看，但另一部叫《船》的电影就在这上面",
                "好吧，我们错过了一部叫《幸运的日子》的电影，我想看，但另一部叫《船》的电影本周上映。"
            ).contains("本周上映")
        )
    }
}

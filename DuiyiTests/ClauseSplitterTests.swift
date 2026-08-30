import Foundation
import Testing
@testable import Duiyi

struct ClauseSplitterTests {
    @Test("Volatile text without punctuation is not spoken")
    func volatileWithoutPunctuationIsSilent() {
        let result = ClauseSplitter.consume(
            translated: "欢迎来到京都",
            utteranceID: UUID(),
            language: .zhHans,
            alreadySpoken: "",
            isSettled: false
        )
        #expect(result.clauses.isEmpty)
        #expect(result.spokenPrefix.isEmpty)
    }

    @Test("Punctuation releases the clause up to the last terminator")
    func punctuationReleasesClause() {
        let result = ClauseSplitter.consume(
            translated: "欢迎来到京都，今天我们",
            utteranceID: UUID(),
            language: .zhHans,
            alreadySpoken: "",
            isSettled: false
        )
        #expect(result.clauses.map(\.text) == ["欢迎来到京都，"])
        #expect(result.spokenPrefix == "欢迎来到京都，")
    }

    @Test("The same utterance only speaks the new suffix")
    func sameUtteranceSpeaksSuffixOnly() {
        let id = UUID()
        let first = ClauseSplitter.consume(
            translated: "欢迎来到京都，",
            utteranceID: id,
            language: .zhHans,
            alreadySpoken: "",
            isSettled: false
        )
        let second = ClauseSplitter.consume(
            translated: "欢迎来到京都，今天我们先去清水寺。",
            utteranceID: id,
            language: .zhHans,
            alreadySpoken: first.spokenPrefix,
            isSettled: false
        )
        #expect(second.clauses.map(\.text) == ["今天我们先去清水寺。"])
        #expect(second.spokenPrefix == "欢迎来到京都，今天我们先去清水寺。")
    }

    @Test("Settled text without punctuation is still spoken")
    func settledWithoutPunctuationSpeaks() {
        let result = ClauseSplitter.consume(
            translated: "请把手机调成静音",
            utteranceID: UUID(),
            language: .zhHans,
            alreadySpoken: "",
            isSettled: true
        )
        #expect(result.clauses.map(\.text) == ["请把手机调成静音"])
    }

    @Test("Empty text yields no clauses")
    func emptyText() {
        let result = ClauseSplitter.consume(
            translated: "   ",
            utteranceID: UUID(),
            language: .zhHans,
            alreadySpoken: "",
            isSettled: true
        )
        #expect(result.clauses.isEmpty)
    }

    @Test("A later fuller translation only speaks the new tail")
    func growingSentenceDoesNotRepeatTheHead() {
        let id = UUID()
        let first = ClauseSplitter.consume(
            translated: "和其他人一样",
            utteranceID: id,
            language: .zhHans,
            alreadySpoken: "",
            isSettled: true
        )
        #expect(first.clauses.map(\.text) == ["和其他人一样"])

        let second = ClauseSplitter.consume(
            translated: "和其他人一样，当我开始这份工作时，我必须审视和理解自己对财富和金钱的感受。",
            utteranceID: id,
            language: .zhHans,
            alreadySpoken: first.spokenPrefix,
            isSettled: true
        )
        let spoken = second.clauses.map(\.text).joined()
        #expect(!spoken.contains("和其他人一样"))
        #expect(spoken.contains("当我开始这份工作时"))
        #expect(spoken.contains("财富和金钱"))
    }

    @Test("Punctuation changes do not cause a full re-read")
    func periodThenCommaStillSpeaksSuffixOnly() {
        let id = UUID()
        let first = ClauseSplitter.consume(
            translated: "和其他人一样。",
            utteranceID: id,
            language: .zhHans,
            alreadySpoken: "",
            isSettled: true
        )
        let second = ClauseSplitter.consume(
            translated: "和其他人一样，当我开始这份工作时，我必须审视和理解自己对财富和金钱的感受。",
            utteranceID: id,
            language: .zhHans,
            alreadySpoken: first.spokenPrefix,
            isSettled: true
        )
        let spoken = second.clauses.map(\.text).joined()
        #expect(!spoken.hasPrefix("和其他人一样"))
        #expect(spoken.contains("当我开始这份工作时"))
    }

    @Test("A carried prefix from a new utterance id still skips the head")
    func carriedPrefixAcrossUtteranceIDs() {
        #expect(
            ClauseSplitter.shouldCarry(
                "和其他人一样",
                into: "和其他人一样，当我开始这份工作时，我必须审视和理解自己对财富和金钱的感受。",
                language: .zhHans
            )
        )
        let result = ClauseSplitter.consume(
            translated: "和其他人一样，当我开始这份工作时，我必须审视和理解自己对财富和金钱的感受。",
            utteranceID: UUID(),
            language: .zhHans,
            alreadySpoken: "和其他人一样",
            isSettled: true
        )
        #expect(!result.clauses.map(\.text).joined().contains("和其他人一样"))
    }

    @Test("A stem in the middle of a revised sentence is skipped")
    func middleStemIsSkippedWhenTranslationPrependsWords() {
        #expect(
            ClauseSplitter.shouldCarry(
                "那是3月18日",
                into: "是的，那是 3月18日，但他们把它改成了 15日。",
                language: .zhHans
            )
        )
        let result = ClauseSplitter.consume(
            translated: "是的，那是 3月18日，但他们把它改成了 15日。",
            utteranceID: UUID(),
            language: .zhHans,
            alreadySpoken: "那是3月18日",
            isSettled: true
        )
        let spoken = result.clauses.map(\.text).joined()
        #expect(!spoken.contains("3月18日"))
        #expect(spoken.contains("改成了"))
        #expect(spoken.contains("15日"))
    }

    @Test("A short filler in front of an already-read clause is not spoken")
    func shortPrependedFillerIsNotSpoken() {
        let spoken = ClauseSplitter.unspokenSuffix(
            speakable: "是的，那是 3月18日，但他们把它改成了 15日。",
            alreadySpoken: "那是3月18日",
            language: .zhHans
        )
        #expect(!spoken.contains("是的"))
        #expect(!spoken.contains("3月18日"))
        #expect(spoken.contains("但他们把它改成了"))
    }

    @Test("Streaming text without punctuation keeps the carried prefix")
    func volatileTextDoesNotDropCarriedPrefix() {
        let result = ClauseSplitter.consume(
            translated: "当我开始这份工作",
            utteranceID: UUID(),
            language: .zhHans,
            alreadySpoken: "和其他人一样",
            isSettled: false
        )
        #expect(result.clauses.isEmpty)
        #expect(result.spokenPrefix == "和其他人一样")
    }

    @Test("A fullwidth colon is a clause boundary")
    func fullwidthColonReleasesClause() {
        let result = ClauseSplitter.consume(
            translated: "他说：今天我们先去清水寺，还有别的安排",
            utteranceID: UUID(),
            language: .zhHans,
            alreadySpoken: "",
            isSettled: false
        )
        #expect(result.clauses.map(\.text) == ["他说：", "今天我们先去清水寺，"])
        #expect(result.spokenPrefix.hasSuffix("清水寺，"))
    }

    @Test("A short punctuated filler is not spoken until the clause is long enough")
    func shortVolatileFillerIsSilent() {
        let result = ClauseSplitter.consume(
            translated: "好吧。我们错过了一部叫《幸运的日子》的电影",
            utteranceID: UUID(),
            language: .zhHans,
            alreadySpoken: "",
            isSettled: false
        )
        #expect(result.clauses.isEmpty)
    }

    @Test("A later movie-title restatement does not repeat the already-read clause")
    func movieTitleRestatementSkipsSpokenClause() {
        let first = ClauseSplitter.consume(
            translated: "我们错过了一部叫《幸运的日子》的电影",
            utteranceID: UUID(),
            language: .zhHans,
            alreadySpoken: "",
            isSettled: true
        )
        let second = ClauseSplitter.consume(
            translated: "好吧。我们错过了一部叫《幸运的日子》的电影，但一部叫《船》的电影本周上映。",
            utteranceID: UUID(),
            language: .zhHans,
            alreadySpoken: first.spokenPrefix,
            isSettled: true
        )
        let spoken = second.clauses.map(\.text).joined()
        #expect(!spoken.contains("幸运的日子"))
        #expect(spoken.contains("船"))
    }

    @Test("An inserted movie title does not re-speak the already-read stem")
    func insertedMovieTitleSpeaksOnlyTheNewTail() {
        let first = ClauseSplitter.consume(
            translated: "好吧，我们错过了一部叫《幸运》的电影",
            utteranceID: UUID(),
            language: .zhHans,
            alreadySpoken: "",
            isSettled: true
        )
        let second = ClauseSplitter.consume(
            translated: "好吧，我们错过了一部叫《幸运的日子》的电影，我想看，但另一部叫《船》的电影本周上映。",
            utteranceID: UUID(),
            language: .zhHans,
            alreadySpoken: first.spokenPrefix,
            isSettled: true
        )
        let spoken = second.clauses.map(\.text).joined()
        #expect(!spoken.contains("我们错过了一部叫"))
        #expect(spoken.contains("船") || spoken.contains("我想看"))
    }
}

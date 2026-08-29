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

    @Test("A stem in the middle of a new sentence is not treated as already spoken")
    func doesNotCarryWhenStemIsOnlyInTheMiddle() {
        #expect(
            !ClauseSplitter.shouldCarry(
                "和其他人一样",
                into: "我觉得和其他人一样，所以才来。",
                language: .zhHans
            )
        )
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
            translated: "他说：今天我们先去清水寺",
            utteranceID: UUID(),
            language: .zhHans,
            alreadySpoken: "",
            isSettled: false
        )
        #expect(result.clauses.map(\.text) == ["他说："])
        #expect(result.spokenPrefix == "他说：")
    }
}

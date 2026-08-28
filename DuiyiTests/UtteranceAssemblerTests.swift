import Foundation
import Testing
@testable import Duiyi

struct UtteranceAssemblerTests {
    @Test("Chinese script wins over latin noise")
    func chineseWins() {
        var assembler = UtteranceAssembler()
        _ = assembler.ingest(language: .english, text: "uh", isFinal: false)
        let result = assembler.ingest(language: .zhHans, text: "我想点一杯咖啡", isFinal: false)
        #expect(result?.language == .zhHans)
        #expect(result?.text == "我想点一杯咖啡")
        #expect(result?.isFinal == false)
    }

    @Test("English words win when there is no Chinese")
    func englishWins() {
        var assembler = UtteranceAssembler()
        let result = assembler.ingest(language: .english, text: "I'd like a cup of coffee", isFinal: false)
        #expect(result?.language == .english)
    }

    @Test("Short filler keeps the previous language")
    func shortFillerKeepsLastLanguage() {
        var assembler = UtteranceAssembler()
        _ = assembler.ingest(language: .zhHans, text: "我们三点见吧啊", isFinal: true)
        assembler.acknowledgeFinal(language: .zhHans)
        let result = assembler.ingest(language: .english, text: "um", isFinal: false)
        #expect(result == nil || result?.language == .zhHans)
    }

    @Test("Final result from one locale is preferred")
    func finalPreferred() {
        var assembler = UtteranceAssembler()
        _ = assembler.ingest(language: .english, text: "hello there", isFinal: false)
        let result = assembler.ingest(language: .zhHans, text: "你好啊朋友们", isFinal: true)
        #expect(result?.isFinal == true)
        #expect(result?.language == .zhHans)
    }

    @Test("Volatile updates keep a stable utterance id")
    func stableIdentity() {
        var assembler = UtteranceAssembler()
        let first = assembler.ingest(language: .english, text: "Hello", isFinal: false)
        let second = assembler.ingest(language: .english, text: "Hello there", isFinal: false)
        #expect(first?.id == second?.id)
    }

    @Test("Silence timeout finalizes and starts a new id")
    func silenceStartsNewUtterance() {
        var assembler = UtteranceAssembler()
        let live = assembler.ingest(language: .zhHans, text: "明天见吧", isFinal: false)
        let finalized = assembler.silenceTimedOut()
        #expect(finalized?.isFinal == true)
        #expect(finalized?.id == live?.id)
        let next = assembler.ingest(language: .zhHans, text: "好的啊啊", isFinal: false)
        #expect(next?.id != live?.id)
    }

    @Test("English speech ignores a Chinese hallucination from the other transcriber")
    func englishSpeechIgnoresChineseHallucination() {
        var assembler = UtteranceAssembler()
        let first = assembler.ingest(language: .english, text: "you are right", isFinal: false)
        let leaked = assembler.ingest(language: .zhHans, text: "你是对的", isFinal: true)
        #expect(first?.language == .english)
        #expect(first?.text == "you are right")
        #expect(leaked == nil || leaked?.language == .english)
        if let leaked {
            #expect(leaked.text == "you are right")
        }
    }

    @Test("Chinese speech ignores English fragments from the other transcriber")
    func chineseSpeechIgnoresEnglishHallucination() {
        var assembler = UtteranceAssembler()
        let first = assembler.ingest(
            language: .zhHans,
            text: "然后我给你介绍一下北京有哪些好玩的",
            isFinal: false
        )
        let leaked = assembler.ingest(language: .english, text: "Yes and", isFinal: true)
        #expect(first?.language == .zhHans)
        #expect(leaked == nil || leaked?.language == .zhHans)
    }

    @Test("Delayed other-language final after a commit is dropped")
    func delayedOtherLanguageAfterFinalIsDropped() {
        var assembler = UtteranceAssembler()
        _ = assembler.ingest(language: .english, text: "you are right", isFinal: true)
        assembler.acknowledgeFinal(language: .english)
        let leaked = assembler.ingest(language: .zhHans, text: "你是对的", isFinal: true)
        #expect(leaked == nil)
    }

    @Test("A later longer hypothesis after a premature final keeps the same utterance id")
    func continuationAfterFinalKeepsIdentity() {
        var assembler = UtteranceAssembler()
        let first = assembler.ingest(
            language: .english,
            text: "The more inference added to the database",
            isFinal: true
        )
        assembler.acknowledgeFinal(language: .english)
        let second = assembler.ingest(
            language: .english,
            text: "The more inference added to the database of media from plot TV to games the better the prediction model",
            isFinal: false
        )
        #expect(first?.id == second?.id)
        #expect(second?.isFinal == false)
    }

    @Test("A new sentence after a final gets a new utterance id")
    func unrelatedSentenceAfterFinalGetsNewIdentity() {
        var assembler = UtteranceAssembler()
        let first = assembler.ingest(language: .english, text: "See you at three in the lobby", isFinal: true)
        assembler.acknowledgeFinal(language: .english)
        let second = assembler.ingest(language: .english, text: "I'd like a cup of coffee please", isFinal: false)
        #expect(second?.id != first?.id)
    }

    @Test("Japanese kana is accepted as Japanese, not Chinese")
    func japaneseKanaIsNotChinese() {
        var assembler = UtteranceAssembler()
        #expect(assembler.ingest(language: .zhHans, text: "コーヒーをください", isFinal: false) == nil)
        let result = assembler.ingest(language: .japanese, text: "コーヒーをください", isFinal: false)
        #expect(result?.language == .japanese)
    }

    @Test("Korean hangul is accepted as Korean")
    func koreanHangulMatches() {
        var assembler = UtteranceAssembler()
        let result = assembler.ingest(language: .korean, text: "커피 주세요", isFinal: false)
        #expect(result?.language == .korean)
    }

    @Test("Thai script is accepted as Thai")
    func thaiScriptMatches() {
        var assembler = UtteranceAssembler()
        let result = assembler.ingest(language: .thai, text: "กาแฟหน่อย", isFinal: false)
        #expect(result?.language == .thai)
    }

    @Test("Vietnamese diacritics are not treated as English")
    func vietnameseDiacriticsAreNotEnglish() {
        var assembler = UtteranceAssembler()
        #expect(assembler.ingest(language: .english, text: "Tôi muốn cà phê", isFinal: false) == nil)
        let result = assembler.ingest(language: .vietnamese, text: "Tôi muốn cà phê", isFinal: false)
        #expect(result?.language == .vietnamese)
    }
}

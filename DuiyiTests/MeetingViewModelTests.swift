import Foundation
import Testing
@testable import Duiyi

@MainActor
struct MeetingViewModelTests {
    @Test("Same-sentence revisions collapse and end writes the full transcript")
    func meetingKeepsFullTranscript() async {
        let store = InMemoryTaskStore()
        let viewModel = makeViewModel(store: store)
        await viewModel.beginTask()
        viewModel.accept(Utterance(language: .zhHans, text: "接下来把预算确认一下", isFinal: false))
        viewModel.accept(Utterance(language: .zhHans, text: "接下来把预算确认一下，本周内发给设计组。", isFinal: true))
        viewModel.accept(Utterance(language: .zhHans, text: "大家同意六点集合。", isFinal: true))
        #expect(viewModel.transcript.count == 2)
        #expect(viewModel.pane.history.count + (viewModel.pane.live == nil ? 0 : 1) <= 2)
        let saved = await viewModel.endTask()
        #expect(saved?.entries.count == 2)
        #expect(saved?.entries.contains { $0.sourceText.contains("设计组") } == true)
        #expect(saved?.entries.contains { $0.sourceText.contains("六点") } == true)
        let listed = await store.list(filter: .meeting)
        #expect(listed.count == 1)
    }

    @Test("Meeting never starts listening on new task")
    func meetingDoesNotAutostart() async {
        let viewModel = makeViewModel()
        await viewModel.beginTask()
        #expect(viewModel.hasActiveTask)
        #expect(viewModel.sessionState != .listening)
    }

    @Test("Default meeting mode pins the reading language")
    func defaultModeUsesPinnedReadingLanguage() async {
        let speech = RecordingSpeechEngine()
        let viewModel = makeViewModel(speech: speech)
        #expect(!viewModel.recognizesMultipleLanguages)
        #expect(viewModel.recognitionLanguages == [.zhHans])
        await viewModel.beginTask()
        await viewModel.start()
        let started = await speech.startedLanguages
        let style = await speech.startedStyle
        #expect(started == [.zhHans])
        #expect(style == .meetingNotes)
    }

    @Test("Multilingual meeting starts the reading language and its pair")
    func multilingualUsesReadingPair() async {
        let speech = RecordingSpeechEngine()
        let viewModel = makeViewModel(speech: speech)
        viewModel.setRecognizesMultipleLanguages(true)
        #expect(viewModel.recognitionLanguages == [.zhHans, .english])
        await viewModel.beginTask()
        await viewModel.start()
        let started = await speech.startedLanguages
        #expect(started == [.zhHans, .english])
    }

    @Test("Chinese and English stay separate transcript lines")
    func mixedLanguagesStaySeparate() async {
        let viewModel = makeViewModel()
        viewModel.setRecognizesMultipleLanguages(true)
        await viewModel.beginTask()
        viewModel.accept(Utterance(language: .zhHans, text: "把预算确认一下。", isFinal: true))
        viewModel.accept(Utterance(language: .english, text: "I can send it this week.", isFinal: true))
        #expect(viewModel.transcript.count == 2)
        #expect(viewModel.transcript[0].source == .zhHans)
        #expect(viewModel.transcript[1].source == .english)
        let saved = await viewModel.endTask()
        #expect(saved?.title.contains("多种语言") == true)
        #expect(saved?.entries.map(\.source) == [.zhHans, .english])
    }

    @Test("Pinning one language ignores the others")
    func pinnedLanguageIgnoresOthers() async {
        let speech = RecordingSpeechEngine()
        let viewModel = makeViewModel(speech: speech)
        viewModel.setSourceLanguage(.japanese)
        #expect(!viewModel.recognizesMultipleLanguages)
        #expect(viewModel.recognitionLanguages == [.japanese])
        await viewModel.beginTask()
        await viewModel.start()
        let started = await speech.startedLanguages
        #expect(started == [.japanese])
        viewModel.accept(Utterance(language: .english, text: "Hello there", isFinal: true))
        viewModel.accept(Utterance(language: .japanese, text: "こんにちは", isFinal: true))
        #expect(viewModel.transcript.count == 1)
        #expect(viewModel.transcript.first?.sourceText == "こんにちは")
    }

    @Test("Recognition order puts the reading language first")
    func recognitionOrderPrefersDisplayLanguage() {
        let languages = MeetingRecognition.languages(
            multilingual: true,
            pinned: .thai,
            display: .korean
        )
        #expect(languages == [.korean, .english])
    }

    @Test("Chinese characters are not stored as English")
    func retagsChineseTextClaimedAsEnglish() async {
        let viewModel = makeViewModel()
        await viewModel.beginTask()
        viewModel.accept(
            Utterance(
                language: .english,
                text: "在那时开始之前呢，我想请大家想象一个画面",
                isFinal: true
            )
        )
        #expect(viewModel.transcript.count == 1)
        #expect(viewModel.transcript.first?.source == .zhHans)
    }

    @Test("The same caption id updates its language when Chinese wins")
    func upsertUpdatesSourceWhenLanguageChanges() async {
        let viewModel = makeViewModel()
        await viewModel.beginTask()
        let id = UUID()
        viewModel.accept(Utterance(id: id, language: .english, text: "Then I want you to imagine", isFinal: false))
        viewModel.accept(
            Utterance(
                id: id,
                language: .zhHans,
                text: "在那时开始之前呢我想请大家想象一个画面假如你是一个穿着校服的高中生",
                isFinal: true
            )
        )
        #expect(viewModel.transcript.count == 1)
        #expect(viewModel.transcript.first?.source == .zhHans)
        #expect(viewModel.transcript.first?.sourceText.contains("想象") == true)
    }

    @Test("Immediate repeated phrases collapse once")
    func collapseStutteredRepeats() async {
        let viewModel = makeViewModel()
        await viewModel.beginTask()
        viewModel.accept(Utterance(language: .zhHans, text: "如果是你们你们会愿意把这个视频发到网上吗？", isFinal: true))
        #expect(viewModel.transcript.first?.sourceText.contains("你们你们") == false)
        #expect(viewModel.transcript.first?.sourceText.contains("你们会愿意") == true)
    }

    private func makeViewModel(
        store: InMemoryTaskStore = InMemoryTaskStore(),
        speech: any SpeechRecognizing = MockSpeechEngine()
    ) -> MeetingViewModel {
        let preferences = PreferencesStore(defaults: UserDefaults(suiteName: UUID().uuidString) ?? .standard)
        preferences.userLanguage = .zhHans
        preferences.meetingLanguage = .zhHans
        return MeetingViewModel(
            speech: speech,
            permissions: MockPermissions(),
            preferences: preferences,
            summarizer: MockSummarizer(),
            taskStore: store
        )
    }
}

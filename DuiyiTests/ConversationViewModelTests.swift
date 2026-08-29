import Foundation
import Testing
@testable import Duiyi

actor MockSpeechEngine: SpeechRecognizing {
    private var continuation: AsyncStream<Utterance>.Continuation?

    func start(languages: [AppLanguage], fallbackLanguage: AppLanguage) async throws -> AsyncStream<Utterance> {
        _ = languages
        _ = fallbackLanguage
        let (stream, continuation) = AsyncStream<Utterance>.makeStream()
        self.continuation = continuation
        return stream
    }

    func stop() async {
        continuation?.finish()
        continuation = nil
    }

    func emit(_ utterance: Utterance) {
        continuation?.yield(utterance)
    }
}

struct MockPermissions: PermissionGranting {
    var status: PermissionStatus = .granted

    func currentStatus() async -> PermissionStatus { status }
    func requestAccess() async -> PermissionStatus { status }
}

struct MockSummarizer: ConversationSummarizing {
    var summary = ConversationSummary(text: "双方约定喝咖啡。", usedAppleIntelligence: true)

    func availability() async -> SummaryAvailability { .available }

    func summarize(
        entries: [TranscriptEntry],
        outputLanguage: AppLanguage
    ) async throws -> ConversationSummary {
        _ = entries
        _ = outputLanguage
        return summary
    }
}

@MainActor
struct ConversationViewModelTests {
    @Test("English speech for a Chinese-reading user lands on the user pane")
    func englishSpeechRoutesToUserPane() async {
        let speech = MockSpeechEngine()
        let viewModel = ConversationViewModel(
            speech: speech,
            permissions: MockPermissions(),
            preferences: PreferencesStore(defaults: UserDefaults(suiteName: UUID().uuidString) ?? .standard),
            summarizer: MockSummarizer()
        )
        viewModel.setUserLanguage(.zhHans)

        let utterance = Utterance(language: .english, text: "See you at three", isFinal: false)
        viewModel.accept(utterance)

        #expect(viewModel.userPane.live?.sourceText == "See you at three")
        #expect(viewModel.peerPane.speakingHint != nil)
        #expect(viewModel.userPane.speakingHint == nil)
    }

    @Test("Chinese speech for a Chinese-reading user lands on the peer pane")
    func chineseSpeechRoutesToPeerPane() async {
        let viewModel = ConversationViewModel(
            speech: MockSpeechEngine(),
            permissions: MockPermissions(),
            preferences: PreferencesStore(defaults: UserDefaults(suiteName: UUID().uuidString) ?? .standard),
            summarizer: MockSummarizer()
        )
        viewModel.setUserLanguage(.zhHans)

        viewModel.accept(Utterance(language: .zhHans, text: "三点见", isFinal: true))

        #expect(viewModel.peerPane.live?.sourceText == "三点见")
        #expect(viewModel.userPane.live == nil)
    }

    @Test("Stale translation jobs are ignored")
    func staleTranslationDropped() async {
        let viewModel = ConversationViewModel(
            speech: MockSpeechEngine(),
            permissions: MockPermissions(),
            preferences: PreferencesStore(defaults: UserDefaults(suiteName: UUID().uuidString) ?? .standard),
            summarizer: MockSummarizer()
        )
        viewModel.setUserLanguage(.zhHans)

        let first = Utterance(id: UUID(), language: .english, text: "Hello", isFinal: false)
        let second = Utterance(id: UUID(), language: .english, text: "Goodbye", isFinal: false)
        viewModel.accept(first)
        viewModel.accept(second)

        viewModel.fulfill(
            job: TranslationJob(utteranceID: first.id, source: .english, target: .zhHans, text: "Hello", isFinal: true),
            text: "你好"
        )

        #expect(viewModel.userPane.live?.id == second.id)
        #expect(viewModel.userPane.live?.translatedText != "你好")
        #expect(viewModel.userPane.history.first?.translatedText == "你好")
    }

    @Test("Clearing captions empties both panes")
    func resetCaptions() async {
        let viewModel = ConversationViewModel(
            speech: MockSpeechEngine(),
            permissions: MockPermissions(),
            preferences: PreferencesStore(defaults: UserDefaults(suiteName: UUID().uuidString) ?? .standard),
            summarizer: MockSummarizer()
        )
        viewModel.accept(Utterance(language: .english, text: "Hello", isFinal: true))
        viewModel.resetCaptions()
        #expect(viewModel.userPane.live == nil)
        #expect(viewModel.peerPane.live == nil)
        #expect(viewModel.outboundJob == nil)
    }

    @Test("Same utterance cannot flip onto the other pane")
    func languageFlipOnSameUtteranceIsDropped() async {
        let viewModel = makeViewModel()
        viewModel.setUserLanguage(.zhHans)
        let id = UUID()
        viewModel.accept(Utterance(id: id, language: .english, text: "you are right", isFinal: false))
        viewModel.accept(Utterance(id: id, language: .zhHans, text: "你是对的", isFinal: false))

        #expect(viewModel.userPane.live?.sourceText == "you are right")
        #expect(viewModel.peerPane.live == nil)
    }

    @Test("Weak opposite-language leftovers after a commit do not overwrite the other pane")
    func weakOppositeLanguageAfterCommitIsDropped() async {
        let viewModel = makeViewModel()
        viewModel.setUserLanguage(.zhHans)
        viewModel.accept(
            Utterance(language: .zhHans, text: "然后我给你介绍一下北京有哪些好玩的", isFinal: true)
        )
        viewModel.accept(Utterance(language: .english, text: "No okay", isFinal: true))

        #expect(viewModel.peerPane.live?.sourceText.contains("北京") == true)
        #expect(viewModel.userPane.live == nil)
    }

    @Test("Pause keeps the screen awake until the restore delay elapses")
    func pauseHoldsIdleTimerThenReleases() async throws {
        let viewModel = makeViewModel(idleRestoreDelay: .milliseconds(40))
        viewModel.autoStartListening = true
        await viewModel.bootstrap()
        #expect(viewModel.sessionState == .listening)
        #expect(viewModel.keepsScreenAwake)

        await viewModel.stop()
        #expect(viewModel.sessionState == .paused)
        #expect(viewModel.keepsScreenAwake)

        try await Task.sleep(for: .milliseconds(80))
        #expect(!viewModel.keepsScreenAwake)
    }

    @Test("Bootstrap stays ready when auto-start is disabled")
    func bootstrapRespectsAutoStartOff() async {
        let preferences = PreferencesStore(defaults: UserDefaults(suiteName: UUID().uuidString) ?? .standard)
        preferences.autoStartListening = false
        let viewModel = ConversationViewModel(
            speech: MockSpeechEngine(),
            permissions: MockPermissions(),
            preferences: preferences,
            summarizer: MockSummarizer()
        )
        await viewModel.bootstrap()
        #expect(viewModel.sessionState == .ready)
        #expect(!viewModel.keepsScreenAwake)
    }

    @Test("Auto-start preference is stored")
    func autoStartPreferencePersists() {
        let viewModel = makeViewModel()
        viewModel.setAutoStartListening(false)
        #expect(viewModel.autoStartListening == false)
    }

    @Test("Settled captions stay in history when a new utterance starts")
    func historyKeepsPreviousCaptions() {
        let viewModel = makeViewModel()
        viewModel.setUserLanguage(.zhHans)
        let first = Utterance(language: .english, text: "See you at three", isFinal: true)
        let second = Utterance(language: .english, text: "I'd like coffee", isFinal: false)
        viewModel.accept(first)
        viewModel.fulfill(
            job: TranslationJob(utteranceID: first.id, source: .english, target: .zhHans, text: first.text, isFinal: true),
            text: "三点见"
        )
        viewModel.accept(second)

        #expect(viewModel.userPane.history.count == 1)
        #expect(viewModel.userPane.history.first?.translatedText == "三点见")
        #expect(viewModel.userPane.live?.sourceText == "I'd like coffee")
        #expect(viewModel.canSummarize)
    }

    @Test("Growing restatements of the same sentence stay on one live line")
    func continuationDoesNotCreateHistoryRows() {
        let viewModel = makeViewModel()
        viewModel.setUserLanguage(.zhHans)
        let first = Utterance(
            language: .english,
            text: "The more inference added to the database",
            isFinal: true
        )
        let second = Utterance(
            language: .english,
            text: "The more inference added to the database of media from plot TV to games the better the prediction model",
            isFinal: true
        )
        viewModel.accept(first)
        viewModel.fulfill(
            job: TranslationJob(utteranceID: first.id, source: .english, target: .zhHans, text: first.text, isFinal: true),
            text: "从数据库中添加的推理越多"
        )
        viewModel.accept(second)
        viewModel.fulfill(
            job: TranslationJob(utteranceID: second.id, source: .english, target: .zhHans, text: second.text, isFinal: true),
            text: "从情节电视到游戏等媒体的数据库中添加的推理越多，预测模型就越好。"
        )

        #expect(viewModel.userPane.history.isEmpty)
        #expect(viewModel.userPane.live?.sourceText == second.text)
        #expect(viewModel.userPane.live?.translatedText.contains("预测模型") == true)
        #expect(viewModel.transcript.count == 1)
    }

    @Test("Japanese speech for a Chinese-reading user lands on the user pane")
    func japaneseSpeechRoutesToUserPane() {
        let viewModel = makeViewModel()
        viewModel.setUserLanguage(.zhHans)
        viewModel.setPeerLanguage(.japanese)
        viewModel.accept(Utterance(language: .japanese, text: "コーヒーをください", isFinal: false))

        #expect(viewModel.userPane.live?.sourceText == "コーヒーをください")
        #expect(viewModel.peerPane.speakingHint != nil)
        #expect(viewModel.userLanguage == .zhHans)
        #expect(viewModel.peerLanguage == .japanese)
    }

    @Test("Picking the peer's language swaps the pair")
    func selectingPeerLanguageSwaps() {
        let viewModel = makeViewModel()
        viewModel.setUserLanguage(.zhHans)
        viewModel.setPeerLanguage(.korean)
        viewModel.setUserLanguage(.korean)

        #expect(viewModel.userLanguage == .korean)
        #expect(viewModel.peerLanguage == .zhHans)
    }

    @Test("Swap exchanges the two reading languages and clears live captions")
    func swapLanguagesExchangesPair() {
        let viewModel = makeViewModel()
        viewModel.setUserLanguage(.zhHans)
        viewModel.setPeerLanguage(.thai)
        viewModel.accept(Utterance(language: .thai, text: "สวัสดี", isFinal: true))
        viewModel.swapLanguages()

        #expect(viewModel.userLanguage == .thai)
        #expect(viewModel.peerLanguage == .zhHans)
        #expect(viewModel.userPane.live == nil)
        #expect(viewModel.peerPane.live == nil)
    }

    @Test("Changing language mid-conversation clears captions for the new pair")
    func changingLanguageClearsCaptions() {
        let viewModel = makeViewModel()
        viewModel.setUserLanguage(.zhHans)
        viewModel.setPeerLanguage(.english)
        viewModel.accept(Utterance(language: .english, text: "See you at three", isFinal: true))
        viewModel.setPeerLanguage(.japanese)

        #expect(viewModel.peerLanguage == .japanese)
        #expect(viewModel.userLanguage == .zhHans)
        #expect(viewModel.userPane.live == nil)
        #expect(viewModel.peerPane.live == nil)
    }

    @Test("Summary uses the on-device summarizer after a conversation")
    func summaryUsesInjectedSummarizer() async {
        let viewModel = makeViewModel()
        viewModel.setUserLanguage(.zhHans)
        viewModel.accept(Utterance(language: .english, text: "Let's get coffee", isFinal: true))
        await viewModel.requestSummary()
        #expect(viewModel.summary?.text == "双方约定喝咖啡。")
        #expect(viewModel.isSummaryPresented)
    }

    @MainActor
    private func makeViewModel(
        idleRestoreDelay: Duration = .seconds(30)
    ) -> ConversationViewModel {
        ConversationViewModel(
            speech: MockSpeechEngine(),
            permissions: MockPermissions(),
            preferences: PreferencesStore(defaults: UserDefaults(suiteName: UUID().uuidString) ?? .standard),
            summarizer: MockSummarizer(),
            idleRestoreDelay: idleRestoreDelay
        )
    }
}

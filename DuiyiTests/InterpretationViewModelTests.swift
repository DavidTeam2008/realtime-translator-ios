import Foundation
import Testing
@testable import Duiyi

actor MockAudioSession: AudioSessionConfiguring {
    var snapshot = AudioRouteSnapshot(outputs: [.headphones])
    private var continuation: AsyncStream<AudioRouteSnapshot>.Continuation?

    init(outputs: [AudioRouteKind] = [.headphones]) {
        snapshot = AudioRouteSnapshot(outputs: outputs)
    }

    func activate(_ useCase: AudioUseCase) async throws {
        _ = useCase
    }

    func deactivate() async {}

    func currentRoute() async -> AudioRouteSnapshot {
        snapshot
    }

    func routeChanges() async -> AsyncStream<AudioRouteSnapshot> {
        AsyncStream { continuation in
            Task { await self.setContinuation(continuation) }
        }
    }

    func emit(_ snapshot: AudioRouteSnapshot) {
        self.snapshot = snapshot
        continuation?.yield(snapshot)
    }

    private func setContinuation(_ continuation: AsyncStream<AudioRouteSnapshot>.Continuation) {
        self.continuation = continuation
    }
}

@MainActor
final class MockSpeechSynthesizer: SpeechSynthesizing {
    var spoken: [String] = []
    var hasVoiceResult = true
    var holdsUntilReleased = false
    private var continuation: CheckedContinuation<Void, Never>?

    func hasVoice(for language: AppLanguage) async -> Bool {
        _ = language
        return hasVoiceResult
    }

    func speak(_ job: SynthesisJob) async {
        spoken.append(job.text)
        guard holdsUntilReleased else { return }
        await withCheckedContinuation { continuation in
            self.continuation = continuation
        }
    }

    func release() {
        continuation?.resume()
        continuation = nil
    }

    func stopAndClear() async {
        continuation?.resume()
        continuation = nil
    }
}

actor RecordingSpeechEngine: SpeechRecognizing {
    var startedLanguages: [AppLanguage] = []
    var startedFallback: AppLanguage?
    private var continuation: AsyncStream<Utterance>.Continuation?

    func start(languages: [AppLanguage], fallbackLanguage: AppLanguage) async throws -> AsyncStream<Utterance> {
        startedLanguages = languages
        startedFallback = fallbackLanguage
        let (stream, continuation) = AsyncStream<Utterance>.makeStream()
        self.continuation = continuation
        return stream
    }

    func stop() async {
        continuation?.finish()
        continuation = nil
    }
}

@MainActor
struct InterpretationViewModelTests {
    @Test("Swap archives live and keeps history")
    func swapDropsLiveKeepsHistory() {
        let viewModel = makeViewModel()
        let first = Utterance(language: .english, text: "Please silence your phones.", isFinal: true)
        viewModel.accept(first)
        viewModel.fulfill(
            job: TranslationJob(
                utteranceID: first.id,
                source: .english,
                target: .zhHans,
                text: first.text,
                isFinal: true
            ),
            text: "请把手机调成静音。"
        )
        viewModel.swapDirection()

        #expect(viewModel.sourceLanguage == .zhHans)
        #expect(viewModel.targetLanguage == .english)
        #expect(viewModel.pane.live == nil)
        #expect(viewModel.pane.history.count == 1)
        #expect(viewModel.pane.history.first?.translatedText == "请把手机调成静音。")
    }

    @Test("Voice out cannot enable on speaker-only routes")
    func noHeadphonesCannotEnableVoiceOut() async {
        let audio = MockAudioSession(outputs: [.builtInSpeaker])
        let viewModel = makeViewModel(audioSession: audio)
        await viewModel.setVoiceOutEnabled(true)
        #expect(viewModel.voiceOutEnabled == false)
        #expect(viewModel.isVoiceOutBlocked)
        #expect(viewModel.voiceOutBlockedMessage != nil)
    }

    @Test("Speech queue keeps the newest two pending clauses")
    func speechQueueCapIsTwo() async throws {
        let synthesizer = MockSpeechSynthesizer()
        synthesizer.holdsUntilReleased = true
        let viewModel = makeViewModel(synthesizer: synthesizer)
        await viewModel.setVoiceOutEnabled(true)

        for text in ["一。", "二。", "三。", "四。"] {
            let utterance = Utterance(language: .english, text: text, isFinal: true)
            viewModel.accept(utterance)
            viewModel.fulfill(
                job: TranslationJob(
                    utteranceID: utterance.id,
                    source: .english,
                    target: .zhHans,
                    text: text,
                    isFinal: true
                ),
                text: text
            )
        }

        try await Task.sleep(for: .milliseconds(30))
        #expect(synthesizer.spoken.first == "一。")
        #expect(viewModel.pendingSpeechCount == 2)

        synthesizer.release()
        try await Task.sleep(for: .milliseconds(30))
        synthesizer.release()
        try await Task.sleep(for: .milliseconds(30))
        synthesizer.release()
        try await Task.sleep(for: .milliseconds(30))
        #expect(synthesizer.spoken.contains("二。") == false)
        #expect(synthesizer.spoken.contains("三。"))
        #expect(synthesizer.spoken.contains("四。"))
    }

    @Test("A fuller translation does not re-speak the already-read head")
    func growingTranslationSpeaksSuffixOnly() async throws {
        let synthesizer = MockSpeechSynthesizer()
        let viewModel = makeViewModel(synthesizer: synthesizer)
        await viewModel.setVoiceOutEnabled(true)

        let first = Utterance(language: .english, text: "Like everyone else", isFinal: true)
        viewModel.accept(first)
        viewModel.fulfill(
            job: TranslationJob(
                utteranceID: first.id,
                source: .english,
                target: .zhHans,
                text: first.text,
                isFinal: true
            ),
            text: "和其他人一样"
        )
        try await Task.sleep(for: .milliseconds(30))
        #expect(synthesizer.spoken == ["和其他人一样"])

        viewModel.fulfill(
            job: TranslationJob(
                utteranceID: first.id,
                source: .english,
                target: .zhHans,
                text: "Like everyone else, when I started out in this work, I had to examine and understand my own feelings about wealth and money.",
                isFinal: true
            ),
            text: "和其他人一样，当我开始这份工作时，我必须审视和理解自己对财富和金钱的感受。"
        )
        try await Task.sleep(for: .milliseconds(40))
        #expect(synthesizer.spoken.filter { $0.contains("和其他人一样") }.count == 1)
        #expect(synthesizer.spoken.joined().contains("当我开始这份工作时"))
    }

    @Test("A restated sentence on a new utterance id still skips the spoken head")
    func growingTranslationAcrossUtteranceIDsSkipsHead() async throws {
        let synthesizer = MockSpeechSynthesizer()
        let viewModel = makeViewModel(synthesizer: synthesizer)
        await viewModel.setVoiceOutEnabled(true)

        let first = Utterance(language: .english, text: "Like everyone else", isFinal: true)
        viewModel.accept(first)
        viewModel.fulfill(
            job: TranslationJob(
                utteranceID: first.id,
                source: .english,
                target: .zhHans,
                text: first.text,
                isFinal: true
            ),
            text: "和其他人一样"
        )
        try await Task.sleep(for: .milliseconds(30))

        let second = Utterance(
            language: .english,
            text: "Like everyone else, when I started out in this work I had to examine money.",
            isFinal: true
        )
        viewModel.accept(second)
        viewModel.fulfill(
            job: TranslationJob(
                utteranceID: second.id,
                source: .english,
                target: .zhHans,
                text: second.text,
                isFinal: true
            ),
            text: "和其他人一样，当我开始这份工作时，我必须审视金钱。"
        )
        try await Task.sleep(for: .milliseconds(40))
        #expect(synthesizer.spoken.filter { $0.contains("和其他人一样") }.count == 1)
        #expect(synthesizer.spoken.joined().contains("当我开始这份工作时"))
    }

    @Test("Prepended words do not cause the already-read date clause to be spoken again")
    func prependedTranslationSkipsAlreadyReadClause() async throws {
        let synthesizer = MockSpeechSynthesizer()
        let viewModel = makeViewModel(synthesizer: synthesizer)
        await viewModel.setVoiceOutEnabled(true)

        let first = Utterance(language: .english, text: "that was March 18th", isFinal: true)
        viewModel.accept(first)
        viewModel.fulfill(
            job: TranslationJob(
                utteranceID: first.id,
                source: .english,
                target: .zhHans,
                text: first.text,
                isFinal: true
            ),
            text: "那是3月18日"
        )
        try await Task.sleep(for: .milliseconds(30))
        #expect(synthesizer.spoken == ["那是3月18日"])

        let second = Utterance(
            language: .english,
            text: "Yes, that was March 18th, but they changed it to the 15th.",
            isFinal: true
        )
        viewModel.accept(second)
        viewModel.fulfill(
            job: TranslationJob(
                utteranceID: second.id,
                source: .english,
                target: .zhHans,
                text: second.text,
                isFinal: true
            ),
            text: "是的，那是 3月18日，但他们把它改成了 15日。"
        )
        try await Task.sleep(for: .milliseconds(40))
        #expect(synthesizer.spoken.filter { $0.contains("3月18日") }.count == 1)
        #expect(synthesizer.spoken.joined().contains("改成了"))
    }

    @Test("An unmatched partial on a new id does not make the next sentence re-read the head")
    func unmatchedPartialDoesNotWipeSpokenPrefix() async throws {
        let synthesizer = MockSpeechSynthesizer()
        let viewModel = makeViewModel(synthesizer: synthesizer)
        await viewModel.setVoiceOutEnabled(true)

        let first = Utterance(language: .english, text: "Like everyone else", isFinal: true)
        viewModel.accept(first)
        viewModel.fulfill(
            job: TranslationJob(
                utteranceID: first.id,
                source: .english,
                target: .zhHans,
                text: first.text,
                isFinal: true
            ),
            text: "和其他人一样"
        )
        try await Task.sleep(for: .milliseconds(30))

        let second = Utterance(language: .english, text: "when I started out in this work", isFinal: false)
        viewModel.accept(second)
        viewModel.fulfill(
            job: TranslationJob(
                utteranceID: second.id,
                source: .english,
                target: .zhHans,
                text: second.text,
                isFinal: false
            ),
            text: "当我开始这份工作"
        )

        viewModel.fulfill(
            job: TranslationJob(
                utteranceID: second.id,
                source: .english,
                target: .zhHans,
                text: "Like everyone else, when I started out in this work, I had to examine money.",
                isFinal: true
            ),
            text: "和其他人一样，当我开始这份工作时，我必须审视金钱。"
        )
        try await Task.sleep(for: .milliseconds(40))
        #expect(synthesizer.spoken.filter { $0.contains("和其他人一样") }.count == 1)
        #expect(synthesizer.spoken.joined().contains("当我开始这份工作时"))
    }

    @Test("Pause clears the speech queue")
    func pauseClearsSpeechQueue() async {
        let synthesizer = MockSpeechSynthesizer()
        synthesizer.holdsUntilReleased = true
        let viewModel = makeViewModel(synthesizer: synthesizer)
        await viewModel.setVoiceOutEnabled(true)
        let utterance = Utterance(language: .english, text: "Hello.", isFinal: true)
        viewModel.accept(utterance)
        viewModel.fulfill(
            job: TranslationJob(
                utteranceID: utterance.id,
                source: .english,
                target: .zhHans,
                text: utterance.text,
                isFinal: true
            ),
            text: "你好。"
        )
        let second = Utterance(language: .english, text: "Goodbye.", isFinal: true)
        viewModel.accept(second)
        viewModel.fulfill(
            job: TranslationJob(
                utteranceID: second.id,
                source: .english,
                target: .zhHans,
                text: second.text,
                isFinal: true
            ),
            text: "再见。"
        )
        #expect(viewModel.pendingSpeechCount == 1)
        await viewModel.stop()
        #expect(viewModel.pendingSpeechCount == 0)
    }

    @Test("Changing language returns to ready instead of listening")
    func languageChangeReturnsToReady() {
        let viewModel = makeViewModel()
        viewModel.sessionState = .listening
        viewModel.setSourceLanguage(.japanese)
        #expect(viewModel.sourceLanguage == .japanese)
        #expect(viewModel.targetLanguage == .zhHans)
        #expect(viewModel.sessionState == .ready)
        #expect(viewModel.pane.live == nil)
    }

    @Test("Utterances that are not the source language are ignored")
    func nonSourceLanguageIsIgnored() {
        let viewModel = makeViewModel()
        viewModel.accept(Utterance(language: .japanese, text: "こんにちは", isFinal: true))
        #expect(viewModel.pane.live == nil)
        viewModel.accept(Utterance(language: .english, text: "Hello there", isFinal: true))
        #expect(viewModel.pane.live?.sourceText == "Hello there")
    }

    @Test("Bootstrap never auto-starts listening")
    func bootstrapDoesNotAutostart() async {
        let viewModel = makeViewModel()
        await viewModel.bootstrap()
        #expect(viewModel.sessionState == .ready)
    }

    @Test("Start asks the speech engine for a single source locale")
    func startUsesSingleSourceLocale() async {
        let speech = RecordingSpeechEngine()
        let viewModel = makeViewModel(speech: speech)
        viewModel.setSourceLanguage(.japanese)
        await viewModel.start()
        let languages = await speech.startedLanguages
        let fallback = await speech.startedFallback
        #expect(languages == [.japanese])
        #expect(fallback == .japanese)
        #expect(viewModel.sessionState == .listening)
    }

    @Test("Unplugging headphones turns voice out off")
    func unplugDisablesVoiceOut() async throws {
        let audio = MockAudioSession()
        let viewModel = makeViewModel(audioSession: audio)
        await viewModel.bootstrap()
        await viewModel.setVoiceOutEnabled(true)
        #expect(viewModel.voiceOutEnabled)
        try await Task.sleep(for: .milliseconds(20))
        await audio.emit(AudioRouteSnapshot(outputs: [.builtInSpeaker]))
        try await Task.sleep(for: .milliseconds(400))
        #expect(viewModel.voiceOutEnabled == false)
        #expect(viewModel.isVoiceOutBlocked)
    }

    @Test("Missing synthesis voice leaves captions running")
    func missingVoiceDisablesOnlySpeech() async {
        let synthesizer = MockSpeechSynthesizer()
        synthesizer.hasVoiceResult = false
        let viewModel = makeViewModel(synthesizer: synthesizer)
        await viewModel.setVoiceOutEnabled(true)
        #expect(viewModel.voiceOutEnabled == false)
        #expect(viewModel.voiceOutBlockedMessage != nil)
        viewModel.accept(Utterance(language: .english, text: "Hello", isFinal: true))
        #expect(viewModel.pane.live?.sourceText == "Hello")
    }

    @Test("Growing translations of the same sentence do not stack duplicate captions")
    func growingMovieCaptionDoesNotStackDuplicates() {
        let viewModel = makeViewModel()
        let fragments = [
            "好吧，我们已经",
            "好吧，我们错过了一部叫《幸运》的电影",
            "好吧，我们错过了一部叫《幸运日》的电影，它",
            "好吧，我们错过了一部叫《幸运的日子》的电影，我想看",
            "好吧，我们错过了一部叫《幸运的日子》的电影，我想看，但另一部叫《船》的电影本周上映。"
        ]
        let id = UUID()
        for (index, chinese) in fragments.enumerated() {
            let source = String(repeating: "Well we missed a movie ", count: index + 1)
            viewModel.accept(
                Utterance(id: id, language: .english, text: source, isFinal: index == fragments.count - 1)
            )
            viewModel.fulfill(
                job: TranslationJob(
                    utteranceID: id,
                    source: .english,
                    target: .zhHans,
                    text: source,
                    isFinal: index == fragments.count - 1
                ),
                text: chinese
            )
        }
        #expect(viewModel.pane.history.isEmpty)
        #expect(viewModel.pane.live?.translatedText.contains("幸运的日子") == true)
        #expect(viewModel.pane.live?.translatedText.contains("船") == true)
        let movieMentions = ([viewModel.pane.live?.translatedText].compactMap { $0 } + viewModel.pane.history.map(\.translatedText))
            .filter { $0.contains("幸运") }
        #expect(movieMentions.count == 1)
    }

    @Test("Movie-title revisions on new utterance ids still become one caption")
    func movieRevisionsOnNewIdsCollapseToOneCaption() {
        let viewModel = makeViewModel()
        let fragments = [
            "好吧，我们已经",
            "好吧，我们错过了一部叫《幸运》的电影",
            "好吧，我们错过了一部叫《幸运日》的电影，它",
            "好吧，我们错过了一部叫《幸运的日子》的电影，我想看",
            "好吧，我们错过了一部叫《幸运的日子》的电影，我想看，但另一部叫《船》的电影就在这上面",
            "好吧，我们错过了一部叫《幸运的日子》的电影，我想看，但另一部叫《船》的电影本周上映。"
        ]
        for (index, chinese) in fragments.enumerated() {
            let source: String
            switch index {
            case 0:
                source = "Well we already"
            case 1:
                source = "Well we missed a movie called Lucky"
            case 2:
                source = "Okay we missed a film called Lucky Day it"
            case 3:
                source = "Well we missed a movie called Lucky Days I want to see"
            case 4:
                source = "Well we missed a movie called Lucky Days I want to see but another movie called The Ship is just on top"
            default:
                source = "Well we missed a movie called Lucky Days I want to see but another movie called The Ship is released this week"
            }
            let utterance = Utterance(language: .english, text: source, isFinal: index == fragments.count - 1)
            viewModel.accept(utterance)
            viewModel.fulfill(
                job: TranslationJob(
                    utteranceID: utterance.id,
                    source: .english,
                    target: .zhHans,
                    text: source,
                    isFinal: index == fragments.count - 1
                ),
                text: chinese
            )
        }
        #expect(viewModel.pane.history.isEmpty)
        #expect(viewModel.pane.live?.translatedText.contains("幸运的日子") == true)
        #expect(viewModel.pane.live?.translatedText.contains("本周上映") == true)
        let movieMentions = ([viewModel.pane.live?.translatedText].compactMap { $0 } + viewModel.pane.history.map(\.translatedText))
            .filter { $0.contains("幸运") }
        #expect(movieMentions.count == 1)
    }

    @Test("Settled refinements wait and are spoken once")
    func settledRefinementsSpeakOnce() async throws {
        let synthesizer = MockSpeechSynthesizer()
        let viewModel = makeViewModel(synthesizer: synthesizer, speechSettleDelay: .milliseconds(80))
        await viewModel.setVoiceOutEnabled(true)

        let fragments = [
            "好吧，我们错过了一部叫《幸运》的电影",
            "好吧，我们错过了一部叫《幸运的日子》的电影，我想看",
            "好吧，我们错过了一部叫《幸运的日子》的电影，我想看，但另一部叫《船》的电影本周上映。"
        ]
        let id = UUID()
        for (index, chinese) in fragments.enumerated() {
            let source = String(repeating: "Well we missed a movie ", count: index + 1)
            viewModel.accept(Utterance(id: id, language: .english, text: source, isFinal: true))
            viewModel.fulfill(
                job: TranslationJob(
                    utteranceID: id,
                    source: .english,
                    target: .zhHans,
                    text: source,
                    isFinal: true
                ),
                text: chinese
            )
        }

        try await Task.sleep(for: .milliseconds(140))
        #expect(synthesizer.spoken.count == 1)
        #expect(synthesizer.spoken[0].contains("幸运的日子"))
        #expect(synthesizer.spoken[0].contains("船"))
        #expect(synthesizer.spoken.filter { $0.contains("我们错过了一部叫") }.count == 1)
    }

    @Test("A second greeting is not dropped from captions")
    func secondGreetingStaysVisible() {
        let viewModel = makeViewModel()
        let jack = Utterance(language: .english, text: "Hi, Jack", isFinal: true)
        viewModel.accept(jack)
        viewModel.fulfill(
            job: TranslationJob(
                utteranceID: jack.id,
                source: .english,
                target: .zhHans,
                text: jack.text,
                isFinal: true
            ),
            text: "嗨，Jack"
        )
        let lucy = Utterance(language: .english, text: "Hi, Lucy", isFinal: true)
        viewModel.accept(lucy)
        viewModel.fulfill(
            job: TranslationJob(
                utteranceID: lucy.id,
                source: .english,
                target: .zhHans,
                text: lucy.text,
                isFinal: true
            ),
            text: "嗨，Lucy"
        )
        let captions = ([viewModel.pane.live?.translatedText].compactMap { $0 } + viewModel.pane.history.map(\.translatedText))
            .joined(separator: " ")
        #expect(captions.contains("Jack"))
        #expect(captions.contains("Lucy"))
    }

    @Test("A longer restatement of the same greeting keeps one caption")
    func concatenatedGreetingsStayOneCaption() {
        let viewModel = makeViewModel()
        let id = UUID()
        viewModel.accept(Utterance(id: id, language: .english, text: "Hi, Jack", isFinal: false))
        viewModel.fulfill(
            job: TranslationJob(
                utteranceID: id,
                source: .english,
                target: .zhHans,
                text: "Hi, Jack",
                isFinal: false
            ),
            text: "嗨，Jack"
        )
        viewModel.accept(Utterance(id: id, language: .english, text: "Hi, Jack Hi, Lucy", isFinal: true))
        viewModel.fulfill(
            job: TranslationJob(
                utteranceID: id,
                source: .english,
                target: .zhHans,
                text: "Hi, Jack Hi, Lucy",
                isFinal: true
            ),
            text: "嗨，Jack。嗨，Lucy"
        )
        #expect(viewModel.pane.history.isEmpty)
        #expect(viewModel.pane.live?.translatedText.contains("Jack") == true)
        #expect(viewModel.pane.live?.translatedText.contains("Lucy") == true)
    }

    private func makeViewModel(
        speech: any SpeechRecognizing = MockSpeechEngine(),
        audioSession: MockAudioSession = MockAudioSession(),
        synthesizer: MockSpeechSynthesizer = MockSpeechSynthesizer(),
        speechSettleDelay: Duration = .milliseconds(0)
    ) -> InterpretationViewModel {
        let preferences = PreferencesStore(defaults: UserDefaults(suiteName: UUID().uuidString) ?? .standard)
        preferences.sourceLanguage = .english
        preferences.targetLanguage = .zhHans
        preferences.voiceOutEnabled = false
        return InterpretationViewModel(
            speech: speech,
            permissions: MockPermissions(),
            preferences: preferences,
            summarizer: MockSummarizer(),
            audioSession: audioSession,
            synthesizer: synthesizer,
            speechSettleDelay: speechSettleDelay
        )
    }
}

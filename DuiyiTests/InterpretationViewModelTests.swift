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

    private func makeViewModel(
        speech: any SpeechRecognizing = MockSpeechEngine(),
        audioSession: MockAudioSession = MockAudioSession(),
        synthesizer: MockSpeechSynthesizer = MockSpeechSynthesizer()
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
            synthesizer: synthesizer
        )
    }
}

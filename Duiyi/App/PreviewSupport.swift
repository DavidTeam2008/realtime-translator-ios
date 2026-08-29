import Foundation
import SwiftUI

actor PreviewSpeechEngine: SpeechRecognizing {
    func start(languages: [AppLanguage], fallbackLanguage: AppLanguage) async throws -> AsyncStream<Utterance> {
        _ = languages
        _ = fallbackLanguage
        return AsyncStream { continuation in
            continuation.finish()
        }
    }

    func stop() async {}
}

struct PreviewPermissions: PermissionGranting {
    var status: PermissionStatus = .granted

    func currentStatus() async -> PermissionStatus { status }
    func requestAccess() async -> PermissionStatus { status }
}

struct PreviewSpeechModels: SpeechModelPreparing {
    func isDeviceCapable(for languages: [AppLanguage]) async -> Bool {
        _ = languages
        return true
    }

    func prepare(languages: [AppLanguage], progress: @escaping @Sendable (Double) -> Void) async throws {
        _ = languages
        progress(1)
    }
}

struct PreviewTranslationAvailability: TranslationAvailabilityChecking {
    func pairStatus(from: AppLanguage, to: AppLanguage) async -> TranslationPairStatus {
        _ = from
        _ = to
        return .installed
    }
}

struct PreviewSummarizer: ConversationSummarizing {
    func availability() async -> SummaryAvailability { .available }
    func summarize(
        entries: [TranscriptEntry],
        outputLanguage: AppLanguage
    ) async throws -> ConversationSummary {
        ConversationSummary(
            text: outputLanguage == .zhHans ? "双方约定见面喝咖啡。" : "You agreed to meet for coffee.",
            usedAppleIntelligence: true
        )
    }
}

@MainActor
enum ConversationPreview {
    static var listening: some View {
        makeView(state: .listening)
    }

    static var idle: some View {
        makeView(state: .ready)
    }

    static var peerSpeaking: some View {
        makeView(state: .listening) { viewModel in
            let utterance = Utterance(language: .english, text: "I'd like a cup of coffee.", isFinal: false)
            viewModel.accept(utterance)
            viewModel.fulfill(
                job: TranslationJob(
                    utteranceID: utterance.id,
                    source: .english,
                    target: .zhHans,
                    text: utterance.text,
                    isFinal: false
                ),
                text: "我想点一杯咖啡。"
            )
        }
    }

    static var userSpeaking: some View {
        makeView(state: .listening) { viewModel in
            let utterance = Utterance(language: .zhHans, text: "我想点一杯咖啡。", isFinal: false)
            viewModel.accept(utterance)
            viewModel.fulfill(
                job: TranslationJob(
                    utteranceID: utterance.id,
                    source: .zhHans,
                    target: .english,
                    text: utterance.text,
                    isFinal: false
                ),
                text: "I'd like a cup of coffee."
            )
        }
    }

    static var paused: some View {
        makeView(state: .paused) { viewModel in
            let previous = Utterance(language: .english, text: "See you in the lobby at 3.", isFinal: true)
            viewModel.accept(previous)
            viewModel.fulfill(
                job: TranslationJob(
                    utteranceID: previous.id,
                    source: .english,
                    target: .zhHans,
                    text: previous.text,
                    isFinal: true
                ),
                text: "三点在酒店大堂见。"
            )
            let english = Utterance(language: .english, text: "I'd like a cup of coffee.", isFinal: true)
            viewModel.accept(english)
            viewModel.fulfill(
                job: TranslationJob(
                    utteranceID: english.id,
                    source: .english,
                    target: .zhHans,
                    text: english.text,
                    isFinal: true
                ),
                text: "我想点一杯咖啡。"
            )
        }
    }

    static var settings: some View {
        makeView(state: .paused) { viewModel in
            viewModel.isSettingsPresented = true
        }
    }

    static var switchingLanguage: some View {
        makeView(state: .listening)
    }

    static var failed: some View {
        makeView(state: .failed(.microphoneDenied))
    }

    private static func makeView(
        state: SessionState,
        configure: ((ConversationViewModel) -> Void)? = nil
    ) -> some View {
        let preferences = PreferencesStore(defaults: UserDefaults(suiteName: "duiyi.preview.\(UUID().uuidString)") ?? .standard)
        preferences.userLanguage = .zhHans
        preferences.peerLanguage = .english
        preferences.autoStartListening = false
        let speech = PreviewSpeechEngine()
        let permissions = PreviewPermissions()
        let summarizer = PreviewSummarizer()
        let environment = AppEnvironment(
            preferences: preferences,
            permissions: permissions,
            speechModels: PreviewSpeechModels(),
            translationAvailability: PreviewTranslationAvailability(),
            speechEngine: speech,
            summarizer: summarizer,
            audioSession: NoOpAudioSession(),
            synthesizer: PreviewSynthesizer()
        )
        let viewModel = ConversationViewModel(
            speech: speech,
            permissions: permissions,
            preferences: preferences,
            summarizer: summarizer
        )
        viewModel.skipsBootstrap = true
        viewModel.sessionState = state
        configure?(viewModel)
        return ConversationView(viewModel: viewModel)
            .environment(environment)
    }
}

actor PreviewAudioSession: AudioSessionConfiguring {
    var snapshot: AudioRouteSnapshot

    init(canSpeak: Bool) {
        snapshot = AudioRouteSnapshot(outputs: canSpeak ? [.headphones] : [.builtInSpeaker])
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
            continuation.finish()
        }
    }
}

@MainActor
enum InterpretationPreview {
    static var idle: some View {
        makeView(state: .ready)
    }

    static var listening: some View {
        makeView(state: .listening) { viewModel in
            let utterance = Utterance(
                language: .japanese,
                text: "京都へようこそ。今日は清水寺からご案内します。",
                isFinal: false
            )
            viewModel.accept(utterance)
            viewModel.fulfill(
                job: TranslationJob(
                    utteranceID: utterance.id,
                    source: .japanese,
                    target: .zhHans,
                    text: utterance.text,
                    isFinal: false
                ),
                text: "欢迎来到京都，今天我们先去清水寺。"
            )
        }
    }

    static var voiceOutBlocked: some View {
        makeView(state: .ready, canSpeak: false) { viewModel in
            viewModel.voiceOutBlockedMessage = DuiyiError.voiceOutNeedsHeadphones.userMessage(for: .zhHans)
        }
    }

    static var failed: some View {
        makeView(state: .failed(.microphoneDenied))
    }

    private static func makeView(
        state: SessionState,
        canSpeak: Bool = true,
        configure: ((InterpretationViewModel) -> Void)? = nil
    ) -> some View {
        let preferences = PreferencesStore(defaults: UserDefaults(suiteName: "duiyi.si.preview.\(UUID().uuidString)") ?? .standard)
        preferences.userLanguage = .zhHans
        preferences.peerLanguage = .english
        preferences.sourceLanguage = .japanese
        preferences.targetLanguage = .zhHans
        preferences.appMode = .simultaneous
        preferences.autoStartListening = false
        let speech = PreviewSpeechEngine()
        let permissions = PreviewPermissions()
        let summarizer = PreviewSummarizer()
        let audioSession = PreviewAudioSession(canSpeak: canSpeak)
        let synthesizer = PreviewSynthesizer()
        let environment = AppEnvironment(
            preferences: preferences,
            permissions: permissions,
            speechModels: PreviewSpeechModels(),
            translationAvailability: PreviewTranslationAvailability(),
            speechEngine: speech,
            summarizer: summarizer,
            audioSession: audioSession,
            synthesizer: synthesizer
        )
        let viewModel = InterpretationViewModel(
            speech: speech,
            permissions: permissions,
            preferences: preferences,
            summarizer: summarizer,
            audioSession: audioSession,
            synthesizer: synthesizer
        )
        viewModel.skipsBootstrap = true
        viewModel.sessionState = state
        viewModel.canSpeakWithoutEcho = canSpeak
        configure?(viewModel)
        return InterpretationView(viewModel: viewModel)
            .environment(environment)
    }
}

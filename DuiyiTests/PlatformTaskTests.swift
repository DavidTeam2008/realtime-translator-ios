import Foundation
import Testing
@testable import Duiyi

@MainActor
struct PlatformTaskTests {
    @Test("Listening does not start without an explicit task")
    func cannotListenWithoutTask() async {
        let viewModel = makeConversation()
        await viewModel.bootstrap()
        await viewModel.start()
        #expect(viewModel.sessionState == .ready)
        #expect(!viewModel.hasActiveTask)
    }

    @Test("New task clears live captions")
    func beginTaskClearsCaptions() async {
        let viewModel = makeConversation()
        await viewModel.beginTask()
        viewModel.accept(Utterance(language: .english, text: "Hello there", isFinal: true))
        #expect(!viewModel.transcript.isEmpty)
        await viewModel.beginTask()
        #expect(viewModel.transcript.isEmpty)
        #expect(viewModel.userPane.live == nil)
        #expect(viewModel.hasActiveTask)
    }

    @Test("Ending a conversation writes the store")
    func endConversationWritesStore() async {
        let store = InMemoryTaskStore()
        let viewModel = makeConversation(store: store)
        viewModel.autoStartListening = false
        await viewModel.beginTask()
        viewModel.accept(Utterance(language: .english, text: "See you at six", isFinal: true))
        viewModel.fulfill(
            job: TranslationJob(
                utteranceID: viewModel.transcript[0].id,
                source: .english,
                target: .zhHans,
                text: "See you at six",
                isFinal: true
            ),
            text: "六点见"
        )
        let saved = await viewModel.endTask()
        #expect(saved != nil)
        let listed = await store.list(filter: .faceToFace)
        #expect(listed.count == 1)
        #expect(listed.first?.entries.contains { $0.translatedText == "六点见" } == true)
    }

    @Test("Simultaneous new task does not auto-start listening")
    func interpretationBeginTaskDoesNotListen() async {
        let viewModel = makeInterpretation()
        await viewModel.beginTask()
        #expect(viewModel.hasActiveTask)
        #expect(viewModel.sessionState != .listening)
    }

    @Test("Device-not-eligible copy never asks to turn Apple Intelligence on")
    func deviceNotEligibleCopyIsHonest() {
        let text = Copy.summaryDeviceNotEligible(for: .zhHans)
        #expect(text.contains("不能使用 Apple 智能"))
        #expect(!text.contains("打开"))
        let english = Copy.summaryDeviceNotEligible(for: .english)
        #expect(english.contains("cannot use Apple Intelligence"))
        #expect(!english.lowercased().contains("turn on"))
    }

    @Test("Export file contains transcript and optional summary")
    func exportIncludesTranscript() throws {
        let task = TaskSession(
            id: UUID(),
            feature: .simultaneous,
            status: .ended,
            startedAt: Date(),
            endedAt: Date(),
            title: "同声传译",
            subtitle: nil,
            sourceLanguage: .english,
            targetLanguage: .zhHans,
            entries: [
                TranscriptEntry(
                    id: UUID(),
                    speaker: .peer,
                    source: .english,
                    sourceText: "See you at six",
                    translatedText: "六点见",
                    isFinal: true
                )
            ],
            summary: ConversationSummary(text: "约六点见面。", usedAppleIntelligence: false)
        )
        let exporter = TranscriptExportService()
        let text = exporter.render(task: task, language: .zhHans)
        #expect(text.contains("六点见"))
        #expect(text.contains("See you at six"))
        #expect(text.contains("约六点见面。"))
        let url = try exporter.makeTranscriptFile(task: task, language: .zhHans)
        #expect(FileManager.default.fileExists(atPath: url.path))
        #expect(url.pathExtension == "txt")
    }

    @Test("Meeting export keeps each spoken language labeled")
    func exportLabelsMeetingLanguages() {
        let task = TaskSession(
            id: UUID(),
            feature: .meeting,
            status: .ended,
            startedAt: Date(),
            endedAt: Date(),
            title: "会议记录 · 多种语言",
            subtitle: nil,
            sourceLanguage: .zhHans,
            targetLanguage: nil,
            entries: [
                TranscriptEntry(
                    id: UUID(),
                    speaker: .user,
                    source: .zhHans,
                    sourceText: "把预算确认一下。",
                    translatedText: "",
                    isFinal: true
                ),
                TranscriptEntry(
                    id: UUID(),
                    speaker: .user,
                    source: .english,
                    sourceText: "I can send it this week.",
                    translatedText: "",
                    isFinal: true
                )
            ],
            summary: nil
        )
        let text = TranscriptExportService().render(task: task, language: .zhHans)
        #expect(text.contains("多种语言"))
        #expect(text.contains("[中文] 把预算确认一下。"))
        #expect(text.contains("[English] I can send it this week."))
    }

    private func makeConversation(store: InMemoryTaskStore = InMemoryTaskStore()) -> ConversationViewModel {
        let preferences = PreferencesStore(defaults: UserDefaults(suiteName: UUID().uuidString) ?? .standard)
        preferences.userLanguage = .zhHans
        preferences.peerLanguage = .english
        preferences.autoStartListening = false
        return ConversationViewModel(
            speech: MockSpeechEngine(),
            permissions: MockPermissions(),
            preferences: preferences,
            summarizer: MockSummarizer(),
            taskStore: store
        )
    }

    private func makeInterpretation() -> InterpretationViewModel {
        let preferences = PreferencesStore(defaults: UserDefaults(suiteName: UUID().uuidString) ?? .standard)
        preferences.sourceLanguage = .english
        preferences.targetLanguage = .zhHans
        return InterpretationViewModel(
            speech: MockSpeechEngine(),
            permissions: MockPermissions(),
            preferences: preferences,
            summarizer: MockSummarizer(),
            audioSession: MockAudioSession(),
            synthesizer: MockSpeechSynthesizer()
        )
    }
}

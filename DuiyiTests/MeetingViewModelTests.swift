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

    private func makeViewModel(store: InMemoryTaskStore = InMemoryTaskStore()) -> MeetingViewModel {
        let preferences = PreferencesStore(defaults: UserDefaults(suiteName: UUID().uuidString) ?? .standard)
        preferences.meetingLanguage = .zhHans
        return MeetingViewModel(
            speech: MockSpeechEngine(),
            permissions: MockPermissions(),
            preferences: preferences,
            summarizer: MockSummarizer(),
            taskStore: store
        )
    }
}

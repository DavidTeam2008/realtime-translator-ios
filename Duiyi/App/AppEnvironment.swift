import Foundation
import SwiftData

@MainActor
@Observable
final class AppEnvironment {
    let preferences: PreferencesStore
    let permissions: any PermissionGranting
    let speechModels: any SpeechModelPreparing
    let translationAvailability: any TranslationAvailabilityChecking
    let speechEngine: any SpeechRecognizing
    let summarizer: any ConversationSummarizing
    let audioSession: any AudioSessionConfiguring
    let synthesizer: any SpeechSynthesizing
    let taskStore: any TaskStore
    let exporter: any ExportSharing
    let languageCatalog: any LanguageCataloging

    init(
        preferences: PreferencesStore = PreferencesStore(),
        permissions: any PermissionGranting = PermissionService(),
        speechModels: any SpeechModelPreparing = SpeechAssetPreparer(),
        translationAvailability: any TranslationAvailabilityChecking = TranslationAvailabilityService(),
        speechEngine: any SpeechRecognizing = BilingualSpeechEngine(),
        summarizer: any ConversationSummarizing = FoundationModelsSummarizer(),
        audioSession: any AudioSessionConfiguring = AudioSessionPolicy(),
        synthesizer: any SpeechSynthesizing = SystemSpeechSynthesizer(),
        taskStore: (any TaskStore)? = nil,
        exporter: any ExportSharing = TranscriptExportService(),
        languageCatalog: any LanguageCataloging = StaticLanguageCatalog()
    ) {
        self.preferences = preferences
        self.permissions = permissions
        self.speechModels = speechModels
        self.translationAvailability = translationAvailability
        self.speechEngine = speechEngine
        self.summarizer = summarizer
        self.audioSession = audioSession
        self.synthesizer = synthesizer
        self.taskStore = taskStore ?? Self.makeTaskStore()
        self.exporter = exporter
        self.languageCatalog = languageCatalog
    }

    static func makeTaskStore() -> any TaskStore {
        do {
            let schema = Schema([TaskEntity.self, TranscriptEntity.self])
            let configuration = ModelConfiguration(schema: schema, isStoredInMemoryOnly: false)
            let container = try ModelContainer(for: schema, configurations: [configuration])
            return SwiftDataTaskStore(container: container)
        } catch {
            DuiyiLog.session.error("SwiftData store unavailable, using memory: \(error.localizedDescription, privacy: .public)")
            return InMemoryTaskStore()
        }
    }
}

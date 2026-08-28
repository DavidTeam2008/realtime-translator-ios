import Foundation

@MainActor
@Observable
final class AppEnvironment {
    let preferences: PreferencesStore
    let permissions: any PermissionGranting
    let speechModels: any SpeechModelPreparing
    let translationAvailability: any TranslationAvailabilityChecking
    let speechEngine: any SpeechRecognizing
    let summarizer: any ConversationSummarizing

    init(
        preferences: PreferencesStore = PreferencesStore(),
        permissions: any PermissionGranting = PermissionService(),
        speechModels: any SpeechModelPreparing = SpeechAssetPreparer(),
        translationAvailability: any TranslationAvailabilityChecking = TranslationAvailabilityService(),
        speechEngine: any SpeechRecognizing = BilingualSpeechEngine(),
        summarizer: any ConversationSummarizing = FoundationModelsSummarizer()
    ) {
        self.preferences = preferences
        self.permissions = permissions
        self.speechModels = speechModels
        self.translationAvailability = translationAvailability
        self.speechEngine = speechEngine
        self.summarizer = summarizer
    }
}

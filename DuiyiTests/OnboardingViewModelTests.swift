import Foundation
import Testing
@testable import Duiyi

@MainActor
struct OnboardingViewModelTests {
    @Test("Skip uses the system language and continues to permissions")
    func skipUsesSystemLanguage() {
        let viewModel = makeViewModel()
        viewModel.skipUsingSystemLanguage()
        #expect(viewModel.step == .permission)
        #expect(viewModel.selectedLanguage == AppLanguage.inferredFromSystem())
        #expect(viewModel.selectedPeerLanguage == AppLanguage.inferredFromSystem().defaultPeer)
        #expect(viewModel.preferences.onboardingStep == OnboardingViewModel.Step.permission.rawValue)
    }

    @Test("Onboarding resumes at the saved step")
    func restoresSavedStep() {
        let defaults = UserDefaults(suiteName: UUID().uuidString) ?? .standard
        let preferences = PreferencesStore(defaults: defaults)
        preferences.hasCompletedOnboarding = false
        preferences.onboardingStep = OnboardingViewModel.Step.assets.rawValue
        let viewModel = OnboardingViewModel(environment: AppEnvironment(
            preferences: preferences,
            permissions: PreviewPermissions(),
            speechModels: PreviewSpeechModels(),
            translationAvailability: PreviewTranslationAvailability(),
            speechEngine: PreviewSpeechEngine()
        ))
        #expect(viewModel.step == .assets)
    }

    @Test("Selecting a language is stored immediately")
    func selectLanguagePersists() {
        let viewModel = makeViewModel()
        viewModel.selectLanguage(.english)
        #expect(viewModel.preferences.userLanguage == .english)
        viewModel.selectPeerLanguage(.japanese)
        #expect(viewModel.preferences.peerLanguage == .japanese)
        #expect(viewModel.selectedLanguage == .english)
    }

    @Test("Picking the same language as the other side swaps")
    func selectingSameLanguageSwaps() {
        let viewModel = makeViewModel()
        viewModel.selectLanguage(.zhHans)
        viewModel.selectPeerLanguage(.thai)
        viewModel.selectLanguage(.thai)
        #expect(viewModel.selectedLanguage == .thai)
        #expect(viewModel.selectedPeerLanguage == .zhHans)
    }

    private func makeViewModel() -> OnboardingViewModel {
        let preferences = PreferencesStore(defaults: UserDefaults(suiteName: UUID().uuidString) ?? .standard)
        return OnboardingViewModel(
            environment: AppEnvironment(
                preferences: preferences,
                permissions: PreviewPermissions(),
                speechModels: PreviewSpeechModels(),
                translationAvailability: PreviewTranslationAvailability(),
                speechEngine: PreviewSpeechEngine()
            )
        )
    }
}

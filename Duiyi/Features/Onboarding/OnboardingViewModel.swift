import Foundation

@MainActor
@Observable
final class OnboardingViewModel {
    enum Step: Int, CaseIterable {
        case welcome
        case language
        case permission
        case assets
    }

    let preferences: PreferencesStore
    private let permissions: any PermissionGranting
    private let speechModels: any SpeechModelPreparing
    private let translationAvailability: any TranslationAvailabilityChecking

    var step: Step
    var selectedLanguage: AppLanguage
    var selectedPeerLanguage: AppLanguage
    var permissionStatus: PermissionStatus = .unknown
    var speechProgress: Double = 0
    var translationPrepared = false
    var shouldPrepareTranslation = false
    var errorMessage: String?
    var isWorking = false
    var didFinish = false

    init(environment: AppEnvironment) {
        preferences = environment.preferences
        permissions = environment.permissions
        speechModels = environment.speechModels
        translationAvailability = environment.translationAvailability
        selectedLanguage = environment.preferences.userLanguage
        selectedPeerLanguage = environment.preferences.peerLanguage
        if !environment.preferences.hasCompletedOnboarding,
           let restored = Step(rawValue: environment.preferences.onboardingStep) {
            step = restored
        } else {
            step = .welcome
        }
    }

    var title: String {
        switch step {
        case .welcome:
            return Copy.appTitle(for: selectedLanguage)
        case .language:
            return Copy.languageQuestion(for: selectedLanguage)
        case .permission:
            return Copy.permissionTitle(for: selectedLanguage)
        case .assets:
            return Copy.assetsTitle(for: selectedLanguage)
        }
    }

    var bodyText: String {
        switch step {
        case .welcome:
            return Copy.welcomeBody(for: selectedLanguage)
        case .language:
            return Copy.languageBody(for: selectedLanguage)
        case .permission:
            return Copy.permissionBody(for: selectedLanguage)
        case .assets:
            return Copy.assetsBody(for: selectedLanguage)
        }
    }

    var primaryButtonTitle: String {
        switch step {
        case .welcome:
            return Copy.getStarted(for: selectedLanguage)
        case .language:
            return Copy.continueButton(for: selectedLanguage)
        case .permission:
            return Copy.allow(for: selectedLanguage)
        case .assets:
            if translationPrepared {
                return Copy.enterConversation(for: selectedLanguage)
            }
            if errorMessage != nil {
                return Copy.retry(for: selectedLanguage)
            }
            if isWorking {
                return Copy.preparing(for: selectedLanguage)
            }
            return Copy.downloadModels(for: selectedLanguage)
        }
    }

    var translationProgress: Double {
        if translationPrepared { return 1 }
        if shouldPrepareTranslation { return max(speechProgress, 0.55) }
        return 0
    }

    var pairLanguages: [AppLanguage] {
        [selectedLanguage, selectedPeerLanguage]
    }

    func persistStep() {
        preferences.onboardingStep = step.rawValue
    }

    func advanceFromWelcome() {
        step = .language
        persistStep()
    }

    func selectLanguage(_ language: AppLanguage) {
        if language == selectedPeerLanguage {
            selectedPeerLanguage = selectedLanguage
            preferences.peerLanguage = selectedPeerLanguage
        }
        selectedLanguage = language
        preferences.userLanguage = language
    }

    func selectPeerLanguage(_ language: AppLanguage) {
        if language == selectedLanguage {
            selectedLanguage = selectedPeerLanguage
            preferences.userLanguage = selectedLanguage
        }
        selectedPeerLanguage = language
        preferences.peerLanguage = language
    }

    func skipUsingSystemLanguage() {
        let system = AppLanguage.inferredFromSystem()
        selectedLanguage = system
        selectedPeerLanguage = system.defaultPeer
        preferences.userLanguage = system
        preferences.peerLanguage = selectedPeerLanguage
        advanceFromLanguage()
    }

    func advanceFromLanguage() {
        if selectedPeerLanguage == selectedLanguage {
            selectedPeerLanguage = selectedLanguage.defaultPeer
        }
        preferences.userLanguage = selectedLanguage
        preferences.peerLanguage = selectedPeerLanguage
        step = .permission
        persistStep()
    }

    func requestPermissions() async {
        isWorking = true
        errorMessage = nil
        let status = await permissions.requestAccess()
        permissionStatus = status
        isWorking = false
        if status.isGranted {
            step = .assets
            persistStep()
            await prepareSpeechModels()
        } else if let error = status.asDuiyiError() {
            errorMessage = error.userMessage(for: selectedLanguage)
        }
    }

    func prepareSpeechModels() async {
        isWorking = true
        errorMessage = nil
        translationPrepared = false
        shouldPrepareTranslation = false
        speechProgress = 0
        do {
            guard await speechModels.isDeviceCapable(for: pairLanguages) else {
                throw DuiyiError.deviceIncapable
            }
            try await speechModels.prepare(languages: pairLanguages) { [weak self] value in
                Task { @MainActor in
                    self?.speechProgress = value
                }
            }
            let pair = await translationAvailability.pairStatus(
                from: selectedLanguage,
                to: selectedPeerLanguage
            )
            if pair == .unsupported {
                throw DuiyiError.languageUnsupported
            }
            shouldPrepareTranslation = true
        } catch let error as DuiyiError {
            errorMessage = error.userMessage(for: selectedLanguage)
            isWorking = false
        } catch {
            errorMessage = DuiyiError.modelsMissing.userMessage(for: selectedLanguage)
            isWorking = false
        }
    }

    func handleTranslationPrepared(_ result: Result<Void, Error>) {
        guard !didFinish else { return }
        switch result {
        case .success:
            translationPrepared = true
            isWorking = false
            finish()
        case .failure:
            errorMessage = DuiyiError.modelsMissing.userMessage(for: selectedLanguage)
            isWorking = false
            shouldPrepareTranslation = false
        }
    }

    func finish() {
        preferences.userLanguage = selectedLanguage
        preferences.peerLanguage = selectedPeerLanguage
        preferences.hasCompletedOnboarding = true
        preferences.onboardingStep = Step.welcome.rawValue
        didFinish = true
    }
}

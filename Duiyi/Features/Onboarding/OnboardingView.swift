import SwiftUI
import UIKit

struct OnboardingView: View {
    @Bindable var viewModel: OnboardingViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("DUIYI")
                .font(.caption.weight(.semibold))
                .tracking(2)
                .foregroundStyle(Tokens.listen)

            Text(viewModel.title)
                .font(.system(size: 32, weight: .semibold))
                .foregroundStyle(Tokens.textPrimary)

            Text(viewModel.bodyText)
                .font(.body)
                .foregroundStyle(Tokens.textSecondary)
                .fixedSize(horizontal: false, vertical: true)

            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    switch viewModel.step {
                    case .welcome:
                        WelcomeSceneIllustration()
                    case .language:
                        LanguagePickView(
                            userLanguage: viewModel.selectedLanguage,
                            peerLanguage: viewModel.selectedPeerLanguage,
                            onSelectUser: viewModel.selectLanguage,
                            onSelectPeer: viewModel.selectPeerLanguage,
                            onSkipSystemLanguage: viewModel.skipUsingSystemLanguage,
                            skipTitle: Copy.useSystemLanguage(for: viewModel.selectedLanguage),
                            iReadTitle: Copy.iReadSection(for: viewModel.selectedLanguage),
                            theyReadTitle: Copy.theyReadSection(for: viewModel.selectedLanguage)
                        )
                    case .permission:
                        PermissionRequestView(userLanguage: viewModel.selectedLanguage)
                    case .assets:
                        AssetDownloadView(
                            speechTitle: Copy.speechModelsTitle(for: viewModel.selectedLanguage),
                            translationTitle: Copy.translationModelsTitle(for: viewModel.selectedLanguage),
                            speechProgress: viewModel.speechProgress,
                            translationProgress: viewModel.translationProgress
                        )
                    }

                    if let errorMessage = viewModel.errorMessage {
                        Text(errorMessage)
                            .font(.footnote)
                            .foregroundStyle(Tokens.danger)
                        if viewModel.permissionStatus == .microphoneDenied || viewModel.permissionStatus == .speechDenied {
                            Button(Copy.openSettings(for: viewModel.selectedLanguage)) {
                                if let url = URL(string: UIApplication.openSettingsURLString) {
                                    UIApplication.shared.open(url)
                                }
                            }
                            .foregroundStyle(Tokens.listen)
                        }
                    }
                }
            }
            .scrollBounceBehavior(.basedOnSize)
            .scrollIndicators(.hidden)
            .frame(maxHeight: .infinity, alignment: .top)

            Button {
                Task { await handlePrimary() }
            } label: {
                Text(viewModel.primaryButtonTitle)
                    .font(.headline)
                    .foregroundStyle(Color(hex: 0x1C1915))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                    .background(Tokens.listen, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
            }
            .disabled(viewModel.isWorking)
            .opacity(viewModel.isWorking ? 0.6 : 1)
        }
        .padding(28)
        .padding(.top, 48)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(Tokens.canvas.ignoresSafeArea())
        .overlay {
            TranslationPrepareHost(
                userLanguage: viewModel.selectedLanguage,
                peerLanguage: viewModel.selectedPeerLanguage,
                shouldPrepare: viewModel.shouldPrepareTranslation,
                onFinished: viewModel.handleTranslationPrepared
            )
            .id("\(viewModel.selectedLanguage.rawValue)-\(viewModel.selectedPeerLanguage.rawValue)")
        }
        .preferredColorScheme(.dark)
    }

    private func handlePrimary() async {
        switch viewModel.step {
        case .welcome:
            viewModel.advanceFromWelcome()
        case .language:
            viewModel.advanceFromLanguage()
        case .permission:
            await viewModel.requestPermissions()
        case .assets:
            if viewModel.translationPrepared {
                viewModel.finish()
            } else {
                await viewModel.prepareSpeechModels()
            }
        }
    }
}

#Preview("Welcome") {
    OnboardingPreview.view(step: .welcome)
}

#Preview("Language") {
    OnboardingPreview.view(step: .language)
}

#Preview("Permission") {
    OnboardingPreview.view(step: .permission)
}

#Preview("Models") {
    OnboardingPreview.view(step: .assets)
}

@MainActor
private enum OnboardingPreview {
    static func view(step: OnboardingViewModel.Step) -> some View {
        let environment = AppEnvironment(
            preferences: PreferencesStore(defaults: UserDefaults(suiteName: "duiyi.onboarding.preview") ?? .standard),
            permissions: PreviewPermissions(),
            speechModels: PreviewSpeechModels(),
            translationAvailability: PreviewTranslationAvailability(),
            speechEngine: PreviewSpeechEngine()
        )
        let viewModel = OnboardingViewModel(environment: environment)
        viewModel.step = step
        return OnboardingView(viewModel: viewModel)
    }
}

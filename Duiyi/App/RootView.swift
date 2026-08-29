import SwiftUI

struct RootView: View {
    @Environment(AppEnvironment.self) private var environment
    @Environment(\.scenePhase) private var scenePhase
    @State private var conversationViewModel: ConversationViewModel?
    @State private var interpretationViewModel: InterpretationViewModel?
    @State private var onboardingViewModel: OnboardingViewModel?

    var body: some View {
        Group {
            switch route {
            case .conversation:
                if let conversationViewModel {
                    ConversationView(viewModel: conversationViewModel)
                } else {
                    Tokens.canvas.ignoresSafeArea()
                }
            case .interpretation:
                if let interpretationViewModel {
                    InterpretationView(viewModel: interpretationViewModel)
                } else {
                    Tokens.userPane.ignoresSafeArea()
                }
            case .onboarding:
                if let onboardingViewModel {
                    OnboardingView(viewModel: onboardingViewModel)
                } else {
                    Tokens.canvas.ignoresSafeArea()
                }
            }
        }
        .onAppear {
            rebuildViewModelsIfNeeded()
        }
        .onChange(of: environment.preferences.hasCompletedOnboarding) { _, completed in
            if completed {
                rebuildViewModelsIfNeeded()
            } else {
                onboardingViewModel = OnboardingViewModel(environment: environment)
            }
        }
        .onChange(of: environment.preferences.appMode) { _, _ in
            Task { await handleModeChange() }
        }
        .onChange(of: scenePhase) { _, phase in
            if phase != .active {
                Task {
                    await conversationViewModel?.stop(restoreIdleTimerAfterDelay: false)
                    await interpretationViewModel?.stop(restoreIdleTimerAfterDelay: false)
                }
            }
        }
    }

    private var route: AppRoute {
        guard environment.preferences.hasCompletedOnboarding else { return .onboarding }
        switch environment.preferences.appMode {
        case .faceToFace:
            return .conversation
        case .simultaneous:
            return .interpretation
        }
    }

    private func handleModeChange() async {
        await conversationViewModel?.stop(restoreIdleTimerAfterDelay: false)
        await interpretationViewModel?.stop(restoreIdleTimerAfterDelay: false)
        rebuildViewModelsIfNeeded()
    }

    private func rebuildViewModelsIfNeeded() {
        if environment.preferences.hasCompletedOnboarding {
            switch environment.preferences.appMode {
            case .faceToFace:
                if conversationViewModel == nil {
                    conversationViewModel = makeConversationViewModel()
                }
            case .simultaneous:
                if interpretationViewModel == nil {
                    interpretationViewModel = makeInterpretationViewModel()
                }
            }
        } else if onboardingViewModel == nil {
            onboardingViewModel = OnboardingViewModel(environment: environment)
        }
    }

    private func makeConversationViewModel() -> ConversationViewModel {
        ConversationViewModel(
            speech: environment.speechEngine,
            permissions: environment.permissions,
            preferences: environment.preferences,
            summarizer: environment.summarizer,
            audioSession: environment.audioSession
        )
    }

    private func makeInterpretationViewModel() -> InterpretationViewModel {
        InterpretationViewModel(
            speech: environment.speechEngine,
            permissions: environment.permissions,
            preferences: environment.preferences,
            summarizer: environment.summarizer,
            audioSession: environment.audioSession,
            synthesizer: environment.synthesizer
        )
    }
}

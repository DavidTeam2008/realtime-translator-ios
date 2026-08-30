import SwiftUI

struct RootView: View {
    @Environment(AppEnvironment.self) private var environment
    @Environment(AppCoordinator.self) private var coordinator
    @Environment(\.scenePhase) private var scenePhase
    @State private var conversationViewModel: ConversationViewModel?
    @State private var interpretationViewModel: InterpretationViewModel?
    @State private var meetingViewModel: MeetingViewModel?
    @State private var historyViewModel: HistoryViewModel?
    @State private var onboardingViewModel: OnboardingViewModel?

    var body: some View {
        @Bindable var coordinator = coordinator
        NavigationStack(path: $coordinator.path) {
            HomeView()
                .navigationDestination(for: AppRoute.self) { route in
                    destination(for: route)
                }
        }
        .fullScreenCover(isPresented: onboardingPresented) {
            if let onboardingViewModel {
                OnboardingView(viewModel: onboardingViewModel)
            } else {
                Tokens.canvas.ignoresSafeArea()
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
        .onChange(of: scenePhase) { _, phase in
            if phase != .active {
                Task {
                    await conversationViewModel?.stop(restoreIdleTimerAfterDelay: false)
                    await interpretationViewModel?.stop(restoreIdleTimerAfterDelay: false)
                    await meetingViewModel?.stop(restoreIdleTimerAfterDelay: false)
                }
            }
        }
    }

    private var onboardingPresented: Binding<Bool> {
        Binding(
            get: { !environment.preferences.hasCompletedOnboarding },
            set: { presented in
                if !presented {
                    environment.preferences.hasCompletedOnboarding = true
                }
            }
        )
    }

    @ViewBuilder
    private func destination(for route: AppRoute) -> some View {
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
        case .meeting:
            if let meetingViewModel {
                MeetingView(viewModel: meetingViewModel)
            } else {
                Tokens.userPane.ignoresSafeArea()
            }
        case .history:
            if let historyViewModel {
                HistoryView(viewModel: historyViewModel)
            } else {
                Tokens.canvas.ignoresSafeArea()
            }
        case .taskDetail(let id):
            TaskDetailView(taskID: id)
        }
    }

    private func rebuildViewModelsIfNeeded() {
        if environment.preferences.hasCompletedOnboarding {
            if conversationViewModel == nil {
                conversationViewModel = makeConversationViewModel()
            }
            if interpretationViewModel == nil {
                interpretationViewModel = makeInterpretationViewModel()
            }
            if meetingViewModel == nil {
                meetingViewModel = makeMeetingViewModel()
            }
            if historyViewModel == nil {
                historyViewModel = HistoryViewModel(store: environment.taskStore)
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
            audioSession: environment.audioSession,
            taskStore: environment.taskStore
        )
    }

    private func makeInterpretationViewModel() -> InterpretationViewModel {
        InterpretationViewModel(
            speech: environment.speechEngine,
            permissions: environment.permissions,
            preferences: environment.preferences,
            summarizer: environment.summarizer,
            audioSession: environment.audioSession,
            synthesizer: environment.synthesizer,
            taskStore: environment.taskStore
        )
    }

    private func makeMeetingViewModel() -> MeetingViewModel {
        MeetingViewModel(
            speech: environment.speechEngine,
            permissions: environment.permissions,
            preferences: environment.preferences,
            summarizer: environment.summarizer,
            audioSession: environment.audioSession,
            taskStore: environment.taskStore
        )
    }
}

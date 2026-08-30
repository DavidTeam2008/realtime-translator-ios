import SwiftUI
import UIKit

struct MeetingView: View {
    @Environment(AppEnvironment.self) private var environment
    @Environment(AppCoordinator.self) private var coordinator
    @Bindable var viewModel: MeetingViewModel

    @State private var isRedownloading = false
    @State private var speechProgress: Double = 0
    @State private var redownloadError: String?
    @State private var confirmNewTask = false
    @State private var confirmEndTask = false

    var body: some View {
        ZStack(alignment: .bottom) {
            VStack(spacing: 0) {
                ModuleChrome(
                    title: Copy.modeMeeting(for: viewModel.sourceLanguage),
                    language: viewModel.sourceLanguage,
                    onHome: { coordinator.popToHome() },
                    onHistory: { coordinator.open(.history) }
                )
                TaskBar(
                    language: viewModel.sourceLanguage,
                    statusText: TaskStatusText.make(
                        hasTask: viewModel.hasActiveTask,
                        startedAt: viewModel.taskStartedAt,
                        language: viewModel.sourceLanguage
                    ),
                    isActive: viewModel.hasActiveTask,
                    onNewTask: { requestNewTask() },
                    onEndTask: { confirmEndTask = true }
                )

                languageChip
                    .padding(.horizontal, Tokens.horizontalPadding)
                    .padding(.bottom, 8)

                transcriptColumn

                ListeningControl(
                    sessionState: viewModel.sessionState,
                    label: viewModel.controlLabel,
                    swapLabel: Copy.meetingLanguage(for: viewModel.sourceLanguage),
                    settingsLabel: Copy.settingsTitle(for: viewModel.sourceLanguage),
                    settingsHint: Copy.settingsHint(for: viewModel.sourceLanguage),
                    isEnabled: viewModel.hasActiveTask && !viewModel.isLengthLimited,
                    showsSwap: false,
                    onTap: {
                        guard viewModel.sessionState != .preparing else { return }
                        Task { await viewModel.toggleListening() }
                    },
                    onOpenSettings: {
                        withAnimation(.easeOut(duration: 0.22)) {
                            viewModel.isSettingsPresented = true
                        }
                    },
                    onSwap: {}
                )
                .padding(.bottom, max(16, ScreenSafeArea.bottom))
            }
            .padding(.top, ScreenSafeArea.top)
            .frame(maxWidth: .infinity, maxHeight: .infinity)

            if viewModel.isSettingsPresented {
                MeetingSettingsSheet(
                    language: viewModel.sourceLanguage,
                    fontSize: viewModel.fontSize,
                    isRedownloading: isRedownloading,
                    speechProgress: speechProgress,
                    redownloadError: redownloadError,
                    canSummarize: viewModel.canSummarize,
                    onSelectLanguage: { language in
                        withAnimation(.easeInOut(duration: 0.2)) {
                            viewModel.setSourceLanguage(language)
                        }
                    },
                    onSelectFont: viewModel.setFontSize,
                    onClear: viewModel.resetCaptions,
                    onSummarize: { Task { await viewModel.requestSummary() } },
                    onRedownload: { Task { await redownloadModels() } },
                    onDone: {
                        withAnimation(.easeOut(duration: 0.18)) {
                            viewModel.isSettingsPresented = false
                        }
                    }
                )
                .transition(.move(edge: .bottom).combined(with: .opacity))
            }

            if viewModel.isSummaryPresented {
                SummarySheet(
                    language: viewModel.sourceLanguage,
                    availability: viewModel.summaryAvailability,
                    isLoading: viewModel.isSummarizing,
                    summary: viewModel.summary,
                    errorText: viewModel.summaryError,
                    exportTask: viewModel.exportableSession,
                    exporter: environment.exporter,
                    onCopy: copySummary,
                    onClose: {
                        withAnimation(.easeOut(duration: 0.18)) {
                            viewModel.isSummaryPresented = false
                        }
                    }
                )
                .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .background(Tokens.userPane)
        .ignoresSafeArea()
        .toolbar(.hidden, for: .navigationBar)
        .task { await viewModel.bootstrap() }
        .onAppear { applyIdleTimer() }
        .onChange(of: viewModel.keepsScreenAwake) { _, _ in applyIdleTimer() }
        .onChange(of: viewModel.sessionState) { _, _ in applyIdleTimer() }
        .onDisappear {
            UIApplication.shared.isIdleTimerDisabled = false
            Task { await viewModel.stop(restoreIdleTimerAfterDelay: false) }
        }
        .confirmationDialog(
            Copy.replaceTaskConfirm(for: viewModel.sourceLanguage),
            isPresented: $confirmNewTask,
            titleVisibility: .visible
        ) {
            Button(Copy.newTask(for: viewModel.sourceLanguage)) {
                Task { await viewModel.beginTask() }
            }
            Button(Copy.cancel(for: viewModel.sourceLanguage), role: .cancel) {}
        }
        .confirmationDialog(
            Copy.endTaskConfirm(for: viewModel.sourceLanguage),
            isPresented: $confirmEndTask,
            titleVisibility: .visible
        ) {
            Button(Copy.endTask(for: viewModel.sourceLanguage)) {
                Task { await finishTask() }
            }
            Button(Copy.cancel(for: viewModel.sourceLanguage), role: .cancel) {}
        }
        .preferredColorScheme(.dark)
    }

    private var languageChip: some View {
        HStack {
            Text(viewModel.sourceLanguage.nativeName)
                .font(.caption.weight(.semibold))
                .foregroundStyle(Tokens.languageBadge(viewModel.sourceLanguage))
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .overlay(
                    Capsule().stroke(Tokens.languageBadge(viewModel.sourceLanguage), lineWidth: 1)
                )
            Text(Copy.transcriptSection(for: viewModel.sourceLanguage))
                .font(.caption)
                .foregroundStyle(Tokens.textSecondary)
            Spacer()
        }
        .accessibilityElement(children: .combine)
    }

    private var transcriptColumn: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 10) {
                    ForEach(viewModel.pane.history) { line in
                        Text(line.sourceText)
                            .font(CaptionTypography.previousFont(size: viewModel.fontSize))
                            .foregroundStyle(Tokens.textSecondary)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    Text(liveText)
                        .font(CaptionTypography.liveFont(size: viewModel.fontSize, settled: liveIsSettled))
                        .foregroundStyle(liveIsSecondary ? Tokens.textSecondary : Tokens.textPrimary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .id("live")
                }
                .padding(.horizontal, Tokens.horizontalPadding)
                .padding(.bottom, 12)
            }
            .scrollIndicators(.hidden)
            .onChange(of: viewModel.pane.live?.sourceText) { _, _ in
                proxy.scrollTo("live", anchor: .bottom)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private var liveText: String {
        if let errorText = viewModel.errorText {
            return errorText
        }
        if let live = viewModel.pane.live, !live.sourceText.isEmpty {
            return live.sourceText
        }
        if let hint = viewModel.pane.speakingHint {
            return hint
        }
        if viewModel.hasActiveTask {
            return Copy.interpretationIdle(for: viewModel.sourceLanguage)
        }
        return Copy.needNewTask(for: viewModel.sourceLanguage)
    }

    private var liveIsSettled: Bool {
        viewModel.errorText != nil || viewModel.pane.live?.phase == .settled
    }

    private var liveIsSecondary: Bool {
        if viewModel.errorText != nil { return false }
        if viewModel.pane.speakingHint != nil { return true }
        return viewModel.pane.live?.phase != .settled
    }

    private func requestNewTask() {
        if viewModel.hasActiveTask {
            confirmNewTask = true
        } else {
            Task { await viewModel.beginTask() }
        }
    }

    private func finishTask() async {
        if let session = await viewModel.endTask() {
            coordinator.showEndedTask(session.id)
        }
    }

    private func applyIdleTimer() {
        UIApplication.shared.isIdleTimerDisabled = viewModel.keepsScreenAwake
    }

    private func redownloadModels() async {
        redownloadError = nil
        isRedownloading = true
        speechProgress = 0
        await viewModel.stop(restoreIdleTimerAfterDelay: false)
        do {
            guard await environment.speechModels.isDeviceCapable(for: [viewModel.sourceLanguage]) else {
                throw DuiyiError.deviceIncapable
            }
            try await environment.speechModels.prepare(languages: [viewModel.sourceLanguage]) { value in
                Task { @MainActor in
                    speechProgress = value
                }
            }
        } catch let error as DuiyiError {
            redownloadError = error.userMessage(for: viewModel.sourceLanguage)
            viewModel.fail(error)
        } catch {
            redownloadError = DuiyiError.modelsMissing.userMessage(for: viewModel.sourceLanguage)
        }
        isRedownloading = false
    }

    private func copySummary() {
        guard let text = viewModel.summary?.text, !text.isEmpty else { return }
        UIPasteboard.general.string = text
    }
}

#Preview("Meeting") {
    MeetingPreview.idle
}

@MainActor
enum MeetingPreview {
    static var idle: some View {
        let preferences = PreferencesStore(defaults: UserDefaults(suiteName: "duiyi.meet.preview") ?? .standard)
        preferences.meetingLanguage = .zhHans
        let store = InMemoryTaskStore()
        let speech = PreviewSpeechEngine()
        let environment = AppEnvironment(
            preferences: preferences,
            speechEngine: speech,
            taskStore: store
        )
        let viewModel = MeetingViewModel(
            speech: speech,
            permissions: PreviewPermissions(),
            preferences: preferences,
            summarizer: PreviewSummarizer(),
            taskStore: store
        )
        viewModel.skipsBootstrap = true
        viewModel.sessionState = .ready
        return MeetingView(viewModel: viewModel)
            .environment(environment)
            .environment(AppCoordinator())
    }
}

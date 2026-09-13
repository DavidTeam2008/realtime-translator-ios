import SwiftUI
import UIKit

struct TaskDetailView: View {
    @Environment(AppEnvironment.self) private var environment
    @Environment(AppCoordinator.self) private var coordinator

    let taskID: UUID

    @State private var task: TaskSession?
    @State private var availability: SummaryAvailability = .unavailable
    @State private var isSummarizing = false
    @State private var summaryError: String?
    @State private var confirmDelete = false
    @State private var translateJob: TranslationJob?
    @State private var pendingTranslate: [TranscriptEntry] = []

    private var language: AppLanguage { environment.preferences.userLanguage }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            ModuleChrome(
                title: Copy.recordTitle(for: language),
                language: language,
                onHome: { coordinator.popToHome() },
                onHistory: { coordinator.pop() }
            )

            if let task {
                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        Text(task.title)
                            .font(.title3.weight(.semibold))
                            .foregroundStyle(Tokens.textPrimary)
                        Text(TaskFormatting.historyMeta(task: task, language: language))
                            .font(.footnote)
                            .foregroundStyle(Tokens.textSecondary)

                        availabilityBanner

                        if let summary = task.summary, !summary.text.isEmpty {
                            Text(summary.text)
                                .font(.body)
                                .foregroundStyle(Tokens.textPrimary)
                        } else if let summaryError {
                            Text(summaryError)
                                .font(.body)
                                .foregroundStyle(Tokens.danger)
                        } else if isSummarizing {
                            Text(Copy.summaryLoading(for: language))
                                .foregroundStyle(Tokens.textSecondary)
                        }

                        Text(Copy.transcriptSection(for: language))
                            .font(.footnote)
                            .foregroundStyle(Tokens.textSecondary)
                        ForEach(task.entries) { entry in
                            VStack(alignment: .leading, spacing: 4) {
                                HStack(alignment: .firstTextBaseline, spacing: 8) {
                                    if task.feature == .meeting {
                                        Text(entry.source.badge)
                                            .font(.caption2.weight(.semibold))
                                            .foregroundStyle(Tokens.languageBadge(entry.source))
                                    }
                                    Text(entry.sourceText)
                                        .foregroundStyle(Tokens.textPrimary)
                                }
                                if !entry.translatedText.isEmpty {
                                    Text(entry.translatedText)
                                        .foregroundStyle(Tokens.textSecondary)
                                }
                            }
                            .font(.body)
                        }

                        if canSummarize {
                            Button(Copy.summarize(for: language)) {
                                Task { await summarize() }
                            }
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(Color(hex: 0x1C1915))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 12)
                            .background(Tokens.listen, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                        }

                        if task.feature == .meeting, needsTranslation(task) {
                            Button(Copy.translateToMine(for: language)) {
                                startTranslation(for: task)
                            }
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(Tokens.listen)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 10)
                        }

                        ExportShareButton(task: task, language: language, exporter: environment.exporter)

                        Button(Copy.delete(for: language)) {
                            confirmDelete = true
                        }
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(Tokens.danger)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                    }
                    .padding(.horizontal, Tokens.horizontalPadding)
                    .padding(.bottom, 32)
                }
            } else {
                Spacer()
            }
        }
        .background(Tokens.canvas.ignoresSafeArea())
        .toolbar(.hidden, for: .navigationBar)
        .overlay {
            if let job = translateJob {
                OneWayTranslationHostView(
                    sourceLanguage: job.source,
                    targetLanguage: language,
                    job: job,
                    onSuccess: handleTranslated,
                    onFailure: { _, _ in advanceTranslation() }
                )
                .id("\(job.source.rawValue)-\(job.utteranceID)")
            }
        }
        .task {
            task = await environment.taskStore.task(id: taskID)
            availability = await environment.summarizer.availability()
        }
        .confirmationDialog(
            Copy.deleteTaskConfirm(for: language),
            isPresented: $confirmDelete,
            titleVisibility: .visible
        ) {
            Button(Copy.delete(for: language), role: .destructive) {
                Task {
                    try? await environment.taskStore.delete(id: taskID)
                    coordinator.popToHome()
                    coordinator.open(.history)
                }
            }
            Button(Copy.cancel(for: language), role: .cancel) {}
        }
        .preferredColorScheme(.dark)
    }

    private var canSummarize: Bool {
        task?.hasTranscript == true && !isSummarizing
    }

    private func needsTranslation(_ task: TaskSession) -> Bool {
        task.entries.contains {
            $0.source != language
                && $0.translatedText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                && !$0.sourceText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        }
    }

    private var availabilityBanner: some View {
        let used = task?.summary?.usedAppleIntelligence == true
        let text = used
            ? Copy.appleIntelligenceGenerated(for: language)
            : Copy.summaryAvailabilityMessage(availability, for: language)
        return Text(text)
            .font(.footnote)
            .foregroundStyle(used ? Color(hex: 0xB8E0C8) : Color(hex: 0xF0D9B0))
            .padding(10)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                (used ? Color(hex: 0x1D2A24) : Color(hex: 0x2A2420)),
                in: RoundedRectangle(cornerRadius: 12, style: .continuous)
            )
    }

    private func summarize() async {
        guard var current = task, current.hasTranscript else { return }
        isSummarizing = true
        summaryError = nil
        if availability == .available {
            do {
                let summary = try await environment.summarizer.summarize(
                    entries: current.entries,
                    outputLanguage: language
                )
                current.summary = summary
                task = current
                await environment.taskStore.saveSummary(taskID: current.id, summary: summary)
            } catch let error as DuiyiError {
                summaryError = error.userMessage(for: language)
            } catch {
                summaryError = DuiyiError.summaryEmpty.userMessage(for: language)
            }
        }
        isSummarizing = false
    }

    private func startTranslation(for task: TaskSession) {
        pendingTranslate = task.entries.filter {
            $0.source != language
                && $0.translatedText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                && !$0.sourceText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        }
        advanceTranslation()
    }

    private func advanceTranslation() {
        guard let next = pendingTranslate.first else {
            translateJob = nil
            return
        }
        pendingTranslate.removeFirst()
        translateJob = TranslationJob(
            utteranceID: next.id,
            source: next.source,
            target: language,
            text: next.sourceText,
            isFinal: true
        )
    }

    private func handleTranslated(job: TranslationJob, text: String) {
        guard var current = task,
              let index = current.entries.firstIndex(where: { $0.id == job.utteranceID }) else {
            advanceTranslation()
            return
        }
        current.entries[index].translatedText = text
        task = current
        Task {
            await environment.taskStore.append(taskID: current.id, entries: [current.entries[index]])
        }
        advanceTranslation()
    }
}

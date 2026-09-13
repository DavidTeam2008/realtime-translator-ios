import SwiftUI
import UIKit

struct HomeSettingsSheet: View {
    @Environment(AppEnvironment.self) private var environment
    @Environment(\.dismiss) private var dismiss

    @State private var isRedownloading = false
    @State private var speechProgress: Double = 0
    @State private var redownloadError: String?

    private var language: AppLanguage { environment.preferences.userLanguage }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text(Copy.iReadSection(for: language))
                        .font(.footnote)
                        .foregroundStyle(Tokens.textSecondary)
                    LanguageChipGrid(selected: language, languages: environment.languageCatalog.all) { selected in
                        environment.preferences.userLanguage = selected
                    }

                    Text(Copy.fontLarger(for: language))
                        .font(.footnote)
                        .foregroundStyle(Tokens.textSecondary)
                    HStack(spacing: 8) {
                        fontChip(Copy.fontStandard(for: language), .standard)
                        fontChip(Copy.fontLarger(for: language), .larger)
                        fontChip(Copy.fontLargest(for: language), .largest)
                    }

                    if isRedownloading {
                        AssetDownloadView(
                            speechTitle: Copy.speechModelsTitle(for: language),
                            translationTitle: Copy.translationModelsTitle(for: language),
                            speechProgress: speechProgress,
                            translationProgress: max(speechProgress, 0.4)
                        )
                    }

                    if let redownloadError {
                        Text(redownloadError)
                            .font(.footnote)
                            .foregroundStyle(Tokens.danger)
                    }

                    Button(Copy.redownloadModels(for: language)) {
                        Task { await redownload() }
                    }
                    .foregroundStyle(Tokens.textSecondary)
                    .disabled(isRedownloading)

                    Button(Copy.openSettings(for: language)) {
                        if let url = URL(string: UIApplication.openSettingsURLString) {
                            UIApplication.shared.open(url)
                        }
                    }
                    .foregroundStyle(Tokens.listen)
                }
                .padding(20)
            }
            .background(Tokens.canvas)
            .navigationTitle(Copy.settingsTitle(for: language))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button(Copy.done(for: language)) { dismiss() }
                        .foregroundStyle(Tokens.listen)
                }
            }
        }
        .preferredColorScheme(.dark)
        .presentationDetents([.medium, .large])
    }

    private func fontChip(_ title: String, _ size: CaptionFontSize) -> some View {
        let selected = environment.preferences.fontSize == size
        return Button {
            environment.preferences.fontSize = size
        } label: {
            Text(title)
                .font(.subheadline.weight(selected ? .semibold : .regular))
                .foregroundStyle(selected ? Color(hex: 0x1C1915) : Tokens.textPrimary)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 10)
                .background(selected ? Tokens.listen : Tokens.sheetChip, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
        .buttonStyle(.plain)
    }

    private func redownload() async {
        redownloadError = nil
        isRedownloading = true
        speechProgress = 0
        let meetingLanguages = MeetingRecognition.languages(
            multilingual: environment.preferences.meetingRecognizesMultipleLanguages,
            pinned: environment.preferences.meetingLanguage,
            display: environment.preferences.userLanguage
        )
        var seen = Set<AppLanguage>()
        var languages: [AppLanguage] = []
        for language in [
            environment.preferences.userLanguage,
            environment.preferences.peerLanguage,
            environment.preferences.sourceLanguage,
            environment.preferences.targetLanguage
        ] + meetingLanguages where seen.insert(language).inserted {
            languages.append(language)
        }
        do {
            try await environment.speechModels.prepare(languages: languages) { value in
                Task { @MainActor in
                    speechProgress = value
                }
            }
        } catch {
            redownloadError = DuiyiError.modelsMissing.userMessage(for: language)
        }
        isRedownloading = false
    }
}

import SwiftUI

struct MeetingSettingsSheet: View {
    let language: AppLanguage
    let recognizesMultipleLanguages: Bool
    let sourceLanguage: AppLanguage
    let fontSize: CaptionFontSize
    let isRedownloading: Bool
    let speechProgress: Double
    let redownloadError: String?
    let canSummarize: Bool
    let onSelectMultilingual: (Bool) -> Void
    let onSelectLanguage: (AppLanguage) -> Void
    let onSelectFont: (CaptionFontSize) -> Void
    let onClear: () -> Void
    let onSummarize: () -> Void
    let onRedownload: () -> Void
    let onDone: () -> Void

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                Text(Copy.settingsTitle(for: language))
                    .font(.headline)
                    .foregroundStyle(Tokens.textPrimary)

                Text(Copy.meetingRecognitionMode(for: language))
                    .font(.footnote)
                    .foregroundStyle(Tokens.textSecondary)
                HStack(spacing: 8) {
                    chip(Copy.meetingMultilingual(for: language), selected: recognizesMultipleLanguages) {
                        onSelectMultilingual(true)
                    }
                    chip(Copy.meetingSingleLanguage(for: language), selected: !recognizesMultipleLanguages) {
                        onSelectMultilingual(false)
                    }
                }
                Text(Copy.meetingMultilingualHint(for: language))
                    .font(.footnote)
                    .foregroundStyle(Tokens.textSecondary)

                if !recognizesMultipleLanguages {
                    Text(Copy.meetingLanguage(for: language))
                        .font(.footnote)
                        .foregroundStyle(Tokens.textSecondary)
                    LanguageChipGrid(selected: sourceLanguage, onSelect: onSelectLanguage)
                }

                HStack(spacing: 8) {
                    chip(Copy.fontStandard(for: language), selected: fontSize == .standard) {
                        onSelectFont(.standard)
                    }
                    chip(Copy.fontLarger(for: language), selected: fontSize == .larger) {
                        onSelectFont(.larger)
                    }
                    chip(Copy.fontLargest(for: language), selected: fontSize == .largest) {
                        onSelectFont(.largest)
                    }
                }

                if isRedownloading {
                    AssetDownloadView(
                        speechTitle: Copy.speechModelsTitle(for: language),
                        translationTitle: Copy.translationModelsTitle(for: language),
                        speechProgress: speechProgress,
                        translationProgress: max(speechProgress, 0.55)
                    )
                }

                if let redownloadError {
                    Text(redownloadError)
                        .font(.footnote)
                        .foregroundStyle(Tokens.danger)
                }

                HStack {
                    Button(Copy.clearCaptions(for: language), action: onClear)
                        .foregroundStyle(Tokens.textPrimary)
                    Spacer()
                    Button(Copy.summarize(for: language), action: onSummarize)
                        .foregroundStyle(canSummarize ? Tokens.listen : Tokens.textSecondary)
                        .disabled(!canSummarize)
                }
                .font(.subheadline)

                HStack {
                    Button(Copy.redownloadModels(for: language), action: onRedownload)
                        .foregroundStyle(Tokens.textSecondary)
                        .disabled(isRedownloading)
                    Spacer()
                    Button(Copy.done(for: language), action: onDone)
                        .fontWeight(.semibold)
                        .foregroundStyle(Color(hex: 0x1C1915))
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .background(Tokens.listen, in: Capsule())
                }
                .font(.subheadline)
            }
            .padding(18)
        }
        .scrollBounceBehavior(.basedOnSize)
        .scrollIndicators(.hidden)
        .background(Tokens.sheet, in: RoundedRectangle(cornerRadius: 22, style: .continuous))
        .padding(.horizontal, 12)
        .padding(.bottom, 24)
    }

    private func chip(_ title: String, selected: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(.subheadline.weight(selected ? .semibold : .regular))
                .foregroundStyle(selected ? Color(hex: 0x1C1915) : Tokens.textPrimary)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 10)
                .background(selected ? Tokens.listen : Tokens.sheetChip, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
        .buttonStyle(.plain)
    }
}

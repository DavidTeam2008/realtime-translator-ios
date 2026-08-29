import SwiftUI

struct InterpretationSettingsSheet: View {
    let viewerLanguage: AppLanguage
    let appMode: AppMode
    let sourceLanguage: AppLanguage
    let targetLanguage: AppLanguage
    let fontSize: CaptionFontSize
    let voiceOutEnabled: Bool
    let showsSourceLine: Bool
    let isVoiceOutBlocked: Bool
    let isRedownloading: Bool
    let speechProgress: Double
    let translationProgress: Double
    let redownloadError: String?
    let canSummarize: Bool
    let onSelectMode: (AppMode) -> Void
    let onSelectSourceLanguage: (AppLanguage) -> Void
    let onSelectTargetLanguage: (AppLanguage) -> Void
    let onSelectFont: (CaptionFontSize) -> Void
    let onToggleVoiceOut: (Bool) -> Void
    let onToggleSourceLine: (Bool) -> Void
    let onClear: () -> Void
    let onSummarize: () -> Void
    let onRedownload: () -> Void
    let onDone: () -> Void

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                Text(Copy.settingsTitle(for: viewerLanguage))
                    .font(.headline)
                    .foregroundStyle(Tokens.textPrimary)

                Text(Copy.modeSection(for: viewerLanguage))
                    .font(.footnote)
                    .foregroundStyle(Tokens.textSecondary)
                HStack(spacing: 8) {
                    chip(Copy.modeFaceToFace(for: viewerLanguage), selected: appMode == .faceToFace) {
                        onSelectMode(.faceToFace)
                    }
                    chip(Copy.modeSimultaneous(for: viewerLanguage), selected: appMode == .simultaneous) {
                        onSelectMode(.simultaneous)
                    }
                }

                Text(Copy.theySpeak(for: viewerLanguage))
                    .font(.footnote)
                    .foregroundStyle(Tokens.textSecondary)
                LanguageChipGrid(selected: sourceLanguage, onSelect: onSelectSourceLanguage)

                Text(Copy.iListen(for: viewerLanguage))
                    .font(.footnote)
                    .foregroundStyle(Tokens.textSecondary)
                LanguageChipGrid(selected: targetLanguage, onSelect: onSelectTargetLanguage)

                HStack(spacing: 8) {
                    chip(Copy.voiceOut(for: viewerLanguage), selected: voiceOutEnabled && !isVoiceOutBlocked) {
                        onToggleVoiceOut(!voiceOutEnabled)
                    }
                    chip(
                        showsSourceLine
                            ? Copy.showSourceLine(for: viewerLanguage)
                            : Copy.hideSourceLine(for: viewerLanguage),
                        selected: showsSourceLine
                    ) {
                        onToggleSourceLine(!showsSourceLine)
                    }
                }

                Text(Copy.voiceOutMicHint(for: viewerLanguage))
                    .font(.footnote)
                    .foregroundStyle(Tokens.textSecondary)

                HStack(spacing: 8) {
                    chip(Copy.fontStandard(for: viewerLanguage), selected: fontSize == .standard) {
                        onSelectFont(.standard)
                    }
                    chip(Copy.fontLarger(for: viewerLanguage), selected: fontSize == .larger) {
                        onSelectFont(.larger)
                    }
                    chip(Copy.fontLargest(for: viewerLanguage), selected: fontSize == .largest) {
                        onSelectFont(.largest)
                    }
                }

                if isRedownloading {
                    AssetDownloadView(
                        speechTitle: Copy.speechModelsTitle(for: viewerLanguage),
                        translationTitle: Copy.translationModelsTitle(for: viewerLanguage),
                        speechProgress: speechProgress,
                        translationProgress: translationProgress
                    )
                }

                if let redownloadError {
                    Text(redownloadError)
                        .font(.footnote)
                        .foregroundStyle(Tokens.danger)
                }

                HStack {
                    Button(Copy.clearCaptions(for: viewerLanguage), action: onClear)
                        .foregroundStyle(Tokens.textPrimary)
                    Spacer()
                    Button(Copy.summarize(for: viewerLanguage), action: onSummarize)
                        .foregroundStyle(canSummarize ? Tokens.listen : Tokens.textSecondary)
                        .disabled(!canSummarize)
                }
                .font(.subheadline)

                HStack {
                    Button(Copy.redownloadModels(for: viewerLanguage), action: onRedownload)
                        .foregroundStyle(Tokens.textSecondary)
                        .disabled(isRedownloading)
                    Spacer()
                    Button(Copy.done(for: viewerLanguage), action: onDone)
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

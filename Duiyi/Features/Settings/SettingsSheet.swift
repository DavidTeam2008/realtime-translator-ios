import SwiftUI

struct SettingsSheet: View {
    let userLanguage: AppLanguage
    let peerLanguage: AppLanguage
    let appMode: AppMode
    let fontSize: CaptionFontSize
    let autoStartListening: Bool
    let isRedownloading: Bool
    let speechProgress: Double
    let translationProgress: Double
    let redownloadError: String?
    let onSelectMode: (AppMode) -> Void
    let onSelectUserLanguage: (AppLanguage) -> Void
    let onSelectPeerLanguage: (AppLanguage) -> Void
    let onSelectFont: (CaptionFontSize) -> Void
    let onToggleAutoStart: (Bool) -> Void
    let onClear: () -> Void
    let onSummarize: () -> Void
    let canSummarize: Bool
    let onRedownload: () -> Void
    let onDone: () -> Void

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
            Text(Copy.settingsTitle(for: userLanguage))
                .font(.headline)
                .foregroundStyle(Tokens.textPrimary)

            Text(Copy.modeSection(for: userLanguage))
                .font(.footnote)
                .foregroundStyle(Tokens.textSecondary)
            HStack(spacing: 8) {
                chip(Copy.modeFaceToFace(for: userLanguage), selected: appMode == .faceToFace) {
                    onSelectMode(.faceToFace)
                }
                chip(Copy.modeSimultaneous(for: userLanguage), selected: appMode == .simultaneous) {
                    onSelectMode(.simultaneous)
                }
            }

            Text(Copy.iReadSection(for: userLanguage))
                .font(.footnote)
                .foregroundStyle(Tokens.textSecondary)
            LanguageChipGrid(selected: userLanguage, onSelect: onSelectUserLanguage)

            Text(Copy.theyReadSection(for: userLanguage))
                .font(.footnote)
                .foregroundStyle(Tokens.textSecondary)
            LanguageChipGrid(selected: peerLanguage, onSelect: onSelectPeerLanguage)

            HStack(spacing: 8) {
                chip(Copy.fontStandard(for: userLanguage), selected: fontSize == .standard) {
                    onSelectFont(.standard)
                }
                chip(Copy.fontLarger(for: userLanguage), selected: fontSize == .larger) {
                    onSelectFont(.larger)
                }
                chip(Copy.fontLargest(for: userLanguage), selected: fontSize == .largest) {
                    onSelectFont(.largest)
                }
            }

            Text(Copy.autoStart(for: userLanguage))
                .font(.footnote)
                .foregroundStyle(Tokens.textSecondary)

            HStack(spacing: 8) {
                chip(Copy.autoStartOn(for: userLanguage), selected: autoStartListening) {
                    onToggleAutoStart(true)
                }
                chip(Copy.autoStartOff(for: userLanguage), selected: !autoStartListening) {
                    onToggleAutoStart(false)
                }
            }

            if isRedownloading {
                AssetDownloadView(
                    speechTitle: Copy.speechModelsTitle(for: userLanguage),
                    translationTitle: Copy.translationModelsTitle(for: userLanguage),
                    speechProgress: speechProgress,
                    translationProgress: translationProgress
                )
            }

            if let redownloadError {
                Text(redownloadError)
                    .font(.footnote)
                    .foregroundStyle(Tokens.danger)
            }

            Text(Copy.tableHint(for: userLanguage))
                .font(.footnote)
                .foregroundStyle(Tokens.textSecondary)

            HStack {
                Button(Copy.clearCaptions(for: userLanguage), action: onClear)
                    .foregroundStyle(Tokens.textPrimary)
                Spacer()
                Button(Copy.summarize(for: userLanguage), action: onSummarize)
                    .foregroundStyle(canSummarize ? Tokens.listen : Tokens.textSecondary)
                    .disabled(!canSummarize)
            }
            .font(.subheadline)

            HStack {
                Button(Copy.redownloadModels(for: userLanguage), action: onRedownload)
                    .foregroundStyle(Tokens.textSecondary)
                    .disabled(isRedownloading)
                Spacer()
                Button(Copy.done(for: userLanguage), action: onDone)
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

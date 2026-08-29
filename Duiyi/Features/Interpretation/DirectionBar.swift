import SwiftUI

enum DirectionPick: Equatable {
    case source
    case target
}

struct DirectionBar: View {
    let sourceLanguage: AppLanguage
    let targetLanguage: AppLanguage
    let viewerLanguage: AppLanguage
    let picking: DirectionPick?
    let onPickSource: () -> Void
    let onPickTarget: () -> Void
    let onSwap: () -> Void

    var body: some View {
        HStack(alignment: .center, spacing: 8) {
            badge(
                language: sourceLanguage,
                caption: Copy.theySpeak(for: viewerLanguage),
                isPicking: picking == .source,
                action: onPickSource
            )
            Button(action: onSwap) {
                Image(systemName: "arrow.left.arrow.right")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(Tokens.textPrimary)
                    .frame(width: 40, height: 40)
                    .background(Tokens.controlIdle, in: Circle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel(Copy.swapDirection(for: viewerLanguage))
            badge(
                language: targetLanguage,
                caption: Copy.iListen(for: viewerLanguage),
                isPicking: picking == .target,
                action: onPickTarget
            )
        }
        .padding(.horizontal, Tokens.horizontalPadding)
    }

    private func badge(
        language: AppLanguage,
        caption: String,
        isPicking: Bool,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            VStack(spacing: 2) {
                Text(caption)
                    .font(.system(size: 10, weight: .medium))
                    .opacity(0.7)
                HStack(spacing: 4) {
                    Text(language.badge)
                        .font(CaptionTypography.badgeFont())
                        .tracking(0.8)
                    Image(systemName: isPicking ? "chevron.up" : "chevron.down")
                        .font(.system(size: 9, weight: .semibold))
                }
            }
            .foregroundStyle(Tokens.languageBadge(language))
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .overlay(
                Capsule()
                    .stroke(Tokens.languageBadge(language), lineWidth: 1)
            )
            .frame(maxWidth: .infinity)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(caption), \(language.nativeName)")
        .animation(.easeInOut(duration: 0.25), value: language)
    }
}

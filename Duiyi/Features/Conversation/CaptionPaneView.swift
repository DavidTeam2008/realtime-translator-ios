import SwiftUI
import UIKit

struct CaptionPaneView: View {
    let viewerLanguage: AppLanguage
    let pane: PaneState
    let fontSize: CaptionFontSize
    let isPeer: Bool
    let sessionState: SessionState
    let errorText: String?
    var isPickingLanguage = false
    var onChooseLanguage: (() -> Void)?
    var onSelectLanguage: ((AppLanguage) -> Void)?
    var onCancelPicking: (() -> Void)?
    var idleOverride: String? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            languageBadge

            if isPickingLanguage {
                languagePicker
            } else {
                currentBlock
                if !pane.history.isEmpty {
                    historyBlock
                } else {
                    Spacer(minLength: 0)
                }
            }
        }
        .padding(.horizontal, Tokens.horizontalPadding)
        .padding(.top, isPeer ? 24 : 28)
        .padding(.bottom, isPeer ? ScreenSafeArea.top : max(36, ScreenSafeArea.bottom + 8))
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(isPeer ? Tokens.peerPane : Tokens.userPane)
        .contentShape(Rectangle())
    }

    private var languageBadge: some View {
        Button {
            if isPickingLanguage {
                onCancelPicking?()
            } else {
                onChooseLanguage?()
            }
        } label: {
            HStack(spacing: 4) {
                Text(viewerLanguage.badge)
                    .font(CaptionTypography.badgeFont())
                    .tracking(0.8)
                Image(systemName: isPickingLanguage ? "chevron.up" : "chevron.down")
                    .font(.system(size: 9, weight: .semibold))
            }
            .foregroundStyle(Tokens.languageBadge(viewerLanguage))
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .overlay(
                Capsule()
                    .stroke(Tokens.languageBadge(viewerLanguage), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(Copy.changeLanguage(for: viewerLanguage)), \(viewerLanguage.nativeName)")
        .animation(.easeInOut(duration: 0.25), value: viewerLanguage)
        .animation(.easeInOut(duration: 0.18), value: isPickingLanguage)
    }

    private var languagePicker: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(Copy.iReadSection(for: viewerLanguage))
                .font(.footnote)
                .foregroundStyle(Tokens.textSecondary)
            LanguageChipGrid(selected: viewerLanguage) { language in
                onSelectLanguage?(language)
            }
            Button(Copy.done(for: viewerLanguage)) {
                onCancelPicking?()
            }
            .font(.subheadline.weight(.semibold))
            .foregroundStyle(Color(hex: 0x1C1915))
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(Tokens.listen, in: Capsule())
            Spacer(minLength: 0)
        }
    }

    @ViewBuilder
    private var currentBlock: some View {
        Text(liveText)
            .font(liveFont)
            .foregroundStyle(liveIsSecondary ? Tokens.textSecondary : Tokens.textPrimary)
            .lineSpacing(fontSize.livePoints * 0.18)
            .frame(maxWidth: .infinity, alignment: .leading)
            .transaction { transaction in
                transaction.animation = nil
            }
            .accessibilityAddTraits(.isStaticText)
    }

    private var historyBlock: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 10) {
                    ForEach(Array(pane.history.reversed())) { line in
                        Text(line.visibleText(forViewer: viewerLanguage))
                            .font(CaptionTypography.previousFont(size: fontSize))
                            .foregroundStyle(Tokens.textSecondary)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .id(line.id)
                    }
                }
            }
            .scrollIndicators(.hidden)
            .onAppear {
                scrollToNewest(proxy)
            }
            .onChange(of: pane.history.last?.id) { _, _ in
                scrollToNewest(proxy)
            }
        }
    }

    private var liveFont: Font {
        CaptionTypography.liveFont(size: fontSize, settled: liveIsSettled)
    }

    private var liveIsSettled: Bool {
        if errorText != nil, !isPeer { return true }
        if pane.speakingHint != nil { return false }
        return pane.live?.phase == .settled && !(pane.live?.translatedText.isEmpty ?? true)
    }

    private var liveText: String {
        if let errorText, !isPeer {
            return errorText
        }
        if let hint = pane.speakingHint {
            return hint
        }
        if let live = pane.live {
            return live.visibleText(forViewer: viewerLanguage)
        }
        return idlePrompt
    }

    private var liveIsSecondary: Bool {
        if errorText != nil, !isPeer { return false }
        if pane.speakingHint != nil { return true }
        if let live = pane.live {
            return live.phase == .streaming || live.translatedText.isEmpty
        }
        return true
    }

    private var idlePrompt: String {
        if let idleOverride { return idleOverride }
        switch sessionState {
        case .ready, .idle, .paused:
            return isPeer
                ? Copy.peerIdlePrompt(for: viewerLanguage)
                : Copy.idlePrompt(for: viewerLanguage)
        case .preparing:
            return Copy.preparing(for: viewerLanguage)
        default:
            return Copy.listening(for: viewerLanguage)
        }
    }

    private func scrollToNewest(_ proxy: ScrollViewProxy) {
        guard let newest = pane.history.last?.id else { return }
        var transaction = Transaction()
        transaction.animation = ReduceMotion.allowed ? .easeOut(duration: 0.18) : nil
        withTransaction(transaction) {
            proxy.scrollTo(newest, anchor: .top)
        }
    }
}

@MainActor
enum ReduceMotion {
    static var allowed: Bool {
        !UIAccessibility.isReduceMotionEnabled
    }
}

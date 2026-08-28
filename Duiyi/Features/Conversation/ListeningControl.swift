import SwiftUI

struct ListeningControl: View {
    let sessionState: SessionState
    let label: String
    let swapLabel: String
    let onTap: () -> Void
    let onLongPress: () -> Void
    let onSwap: () -> Void

    @State private var pulse = false
    @State private var didLongPress = false

    private var isListening: Bool { sessionState.isListening }

    var body: some View {
        ZStack {
            HStack {
                Button(action: onSwap) {
                    Image(systemName: "arrow.up.arrow.down")
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(Tokens.textSecondary)
                        .frame(width: 44, height: 44)
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel(swapLabel)
                .padding(.leading, 14)
                Spacer()
                Text(label)
                    .font(CaptionTypography.controlFont())
                    .foregroundStyle(Tokens.textSecondary)
                    .padding(.trailing, 28)
            }

            controlButton
        }
        .frame(height: Tokens.midBarHeight)
        .background(Tokens.canvas)
        .onAppear(perform: syncPulse)
        .onChange(of: isListening) { _, _ in
            syncPulse()
        }
    }

    private var controlButton: some View {
        let fill: Color = {
            if sessionState.isFailed { return Tokens.danger }
            if isListening { return Tokens.listen }
            return Tokens.controlIdle
        }()
        let symbolColor: Color = {
            if sessionState.isFailed { return Color.white }
            if isListening { return Color(hex: 0x1C1915) }
            return Tokens.textPrimary
        }()

        return ZStack {
            Circle()
                .fill(isListening ? Tokens.listen.opacity(0.18) : Color.clear)
                .frame(width: Tokens.micHitSize, height: Tokens.micHitSize)
                .scaleEffect(isListening && pulse ? 1.08 : 1)
            Circle()
                .fill(fill)
                .frame(width: Tokens.micSize, height: Tokens.micSize)
            Image(systemName: symbolName)
                .font(.system(size: 22, weight: .semibold))
                .foregroundStyle(symbolColor)
        }
        .frame(width: Tokens.micHitSize, height: Tokens.micHitSize)
        .contentShape(Circle())
        .gesture(pressGesture)
        .accessibilityLabel(label)
        .accessibilityAddTraits(.isButton)
    }

    private var symbolName: String {
        switch sessionState {
        case .listening:
            return "waveform"
        case .paused:
            return "mic.fill"
        case .failed:
            return "exclamationmark"
        case .preparing:
            return "ellipsis"
        case .ready, .idle:
            return "mic"
        }
    }

    private var pressGesture: some Gesture {
        DragGesture(minimumDistance: 0)
            .onChanged { _ in }
            .onEnded { _ in
                if didLongPress {
                    didLongPress = false
                } else {
                    onTap()
                }
            }
            .simultaneously(with:
                LongPressGesture(minimumDuration: 0.45)
                    .onEnded { _ in
                        didLongPress = true
                        onLongPress()
                    }
            )
    }

    private func syncPulse() {
        guard ReduceMotion.allowed else {
            pulse = false
            return
        }
        if isListening {
            withAnimation(.easeInOut(duration: 1.15).repeatForever(autoreverses: true)) {
                pulse = true
            }
        } else {
            withAnimation(.easeOut(duration: 0.2)) {
                pulse = false
            }
        }
    }
}

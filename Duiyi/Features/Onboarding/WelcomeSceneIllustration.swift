import SwiftUI

struct WelcomeSceneIllustration: View {
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(Color(hex: 0xD9CFC2))

            VStack(spacing: 10) {
                Text("对方")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(Color(hex: 0x5C564E))

                miniPhone

                Text("用户")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(Color(hex: 0x5C564E))
            }
            .padding(.vertical, 16)
        }
        .frame(maxWidth: .infinity)
        .frame(height: 196)
        .accessibilityHidden(true)
    }

    private var miniPhone: some View {
        VStack(spacing: 0) {
            Text("I'd like a coffee.")
                .font(.system(size: 9, weight: .semibold))
                .foregroundStyle(Tokens.textPrimary)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(Tokens.peerPane)
                .rotationEffect(.degrees(180))

            Circle()
                .fill(Tokens.listen)
                .frame(width: 8, height: 8)
                .frame(maxWidth: .infinity)
                .frame(height: 14)
                .background(Tokens.canvas)

            Text("我想点一杯咖啡。")
                .font(.system(size: 9, weight: .semibold))
                .foregroundStyle(Tokens.textPrimary)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(Tokens.userPane)
        }
        .frame(width: 92, height: 148)
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .stroke(Color(hex: 0x2A2E38), lineWidth: 3)
        )
        .shadow(color: Color.black.opacity(0.18), radius: 16, y: 8)
    }
}

#Preview {
    WelcomeSceneIllustration()
        .padding()
        .background(Tokens.canvas)
}

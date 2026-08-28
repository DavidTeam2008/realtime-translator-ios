import SwiftUI

struct PermissionRequestView: View {
    let userLanguage: AppLanguage

    var body: some View {
        VStack(spacing: 10) {
            permissionRow(
                symbol: "mic.fill",
                title: Copy.microphoneTitle(for: userLanguage),
                detail: Copy.microphoneReason(for: userLanguage)
            )
            permissionRow(
                symbol: "text.bubble.fill",
                title: Copy.speechTitle(for: userLanguage),
                detail: Copy.speechReason(for: userLanguage)
            )
        }
        .padding(.top, 8)
    }

    private func permissionRow(symbol: String, title: String, detail: String) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: symbol)
                .font(.system(size: 16, weight: .semibold))
                .foregroundStyle(Tokens.listen)
                .frame(width: 28, height: 28)
                .padding(.top, 2)
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.headline)
                    .foregroundStyle(Tokens.textPrimary)
                Text(detail)
                    .font(.subheadline)
                    .foregroundStyle(Tokens.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 0)
        }
        .padding(16)
        .background(Tokens.controlIdle, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
    }
}

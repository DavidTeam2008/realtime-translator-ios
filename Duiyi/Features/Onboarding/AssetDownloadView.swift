import SwiftUI

struct AssetDownloadView: View {
    let speechTitle: String
    let translationTitle: String
    let speechProgress: Double
    let translationProgress: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            progressRow(title: speechTitle, value: speechProgress)
            progressRow(title: translationTitle, value: translationProgress)
        }
        .padding(.top, 8)
    }

    private func progressRow(title: String, value: Double) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.subheadline)
                .foregroundStyle(Tokens.textSecondary)
            GeometryReader { proxy in
                ZStack(alignment: .leading) {
                    Capsule().fill(Tokens.controlIdle)
                    Capsule()
                        .fill(Tokens.listen)
                        .frame(width: proxy.size.width * min(max(value, 0), 1))
                }
            }
            .frame(height: 6)
        }
    }
}

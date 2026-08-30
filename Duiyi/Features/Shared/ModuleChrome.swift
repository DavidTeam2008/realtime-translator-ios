import SwiftUI

struct ModuleChrome: View {
    let title: String
    let language: AppLanguage
    let onHome: () -> Void
    let onHistory: () -> Void

    var body: some View {
        HStack {
            Button(Copy.homeButton(for: language), action: onHome)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(Tokens.listen)
            Spacer()
            Text(title)
                .font(.headline)
                .foregroundStyle(Tokens.textPrimary)
            Spacer()
            Button(Copy.historyTitle(for: language), action: onHistory)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(Tokens.listen)
        }
        .padding(.horizontal, Tokens.horizontalPadding)
        .padding(.top, 8)
        .padding(.bottom, 4)
        .accessibilityElement(children: .contain)
    }
}

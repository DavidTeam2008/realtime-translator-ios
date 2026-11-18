import SwiftUI

struct LanguageChipGrid: View {
    let selected: AppLanguage
    var languages: [AppLanguage] = AppLanguage.allCases
    var unavailableLanguages: Set<AppLanguage> = []
    let onSelect: (AppLanguage) -> Void

    private let columns = [
        GridItem(.flexible(), spacing: 8),
        GridItem(.flexible(), spacing: 8),
        GridItem(.flexible(), spacing: 8)
    ]

    var body: some View {
        LazyVGrid(columns: columns, spacing: 8) {
            ForEach(languages, id: \.self) { language in
                let isUnavailable = unavailableLanguages.contains(language)
                Button {
                    onSelect(language)
                } label: {
                    Text(language.nativeName)
                        .font(.subheadline.weight(selected == language ? .semibold : .regular))
                        .foregroundStyle(selected == language ? Color(hex: 0x1C1915) : Tokens.textPrimary)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .background(
                            selected == language ? Tokens.listen : Tokens.sheetChip,
                            in: RoundedRectangle(cornerRadius: 12, style: .continuous)
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 12, style: .continuous)
                                .stroke(selected == language ? Tokens.listen : Color.clear, lineWidth: 1)
                        )
                }
                .buttonStyle(.plain)
                .disabled(isUnavailable)
                .opacity(isUnavailable ? 0.45 : 1)
                .accessibilityIdentifier("langchip-\(language.rawValue)")
                .accessibilityHint(isUnavailable ? "Unavailable language" : "")
            }
        }
    }
}

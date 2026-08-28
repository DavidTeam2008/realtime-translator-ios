import SwiftUI

struct LanguagePickView: View {
    let userLanguage: AppLanguage
    let peerLanguage: AppLanguage
    let onSelectUser: (AppLanguage) -> Void
    let onSelectPeer: (AppLanguage) -> Void
    let onSkipSystemLanguage: () -> Void
    let skipTitle: String
    let iReadTitle: String
    let theyReadTitle: String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(iReadTitle)
                .font(.footnote)
                .foregroundStyle(Tokens.textSecondary)
            LanguageChipGrid(selected: userLanguage, onSelect: onSelectUser)

            Text(theyReadTitle)
                .font(.footnote)
                .foregroundStyle(Tokens.textSecondary)
                .padding(.top, 4)
            LanguageChipGrid(selected: peerLanguage, onSelect: onSelectPeer)

            Button(skipTitle, action: onSkipSystemLanguage)
                .font(.subheadline)
                .foregroundStyle(Tokens.textSecondary)
                .padding(.top, 6)
        }
        .padding(.top, 8)
    }
}

import SwiftUI

struct SummarySheet: View {
    let userLanguage: AppLanguage
    let isLoading: Bool
    let summary: ConversationSummary?
    let errorText: String?
    let onCopy: () -> Void
    let onClose: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(Copy.summaryTitle(for: userLanguage))
                .font(.headline)
                .foregroundStyle(Tokens.textPrimary)

            ScrollView {
                Group {
                    if isLoading {
                        Text(Copy.summaryLoading(for: userLanguage))
                            .foregroundStyle(Tokens.textSecondary)
                    } else if let errorText {
                        Text(errorText)
                            .foregroundStyle(Tokens.danger)
                    } else if let summary {
                        Text(summary.text)
                            .foregroundStyle(Tokens.textPrimary)
                        if !summary.usedAppleIntelligence {
                            Text(Copy.summaryLocalFallback(for: userLanguage))
                                .font(.footnote)
                                .foregroundStyle(Tokens.textSecondary)
                                .padding(.top, 8)
                        }
                    }
                }
                .font(.body)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(maxHeight: 280)

            HStack {
                if summary != nil, !isLoading {
                    Button(Copy.copySummary(for: userLanguage), action: onCopy)
                        .foregroundStyle(Tokens.textPrimary)
                }
                Spacer()
                Button(Copy.done(for: userLanguage), action: onClose)
                    .fontWeight(.semibold)
                    .foregroundStyle(Color(hex: 0x1C1915))
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                    .background(Tokens.listen, in: Capsule())
            }
        }
        .padding(18)
        .background(Tokens.sheet, in: RoundedRectangle(cornerRadius: 22, style: .continuous))
        .padding(.horizontal, 12)
        .padding(.bottom, 24)
    }
}

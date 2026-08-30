import SwiftUI

struct HistoryRow: View {
    let task: TaskSession
    let language: AppLanguage

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Circle()
                .fill(Tokens.featureAccent(task.feature))
                .frame(width: 8, height: 8)
                .padding(.top, 7)
                .accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 4) {
                Text(task.subtitle.map { "\(task.title) · \($0)" } ?? task.title)
                    .font(.body.weight(.medium))
                    .foregroundStyle(Tokens.textPrimary)
                    .multilineTextAlignment(.leading)
                Text(TaskFormatting.historyMeta(task: task, language: language))
                    .font(.footnote)
                    .foregroundStyle(Tokens.textSecondary)
            }
            Spacer(minLength: 0)
        }
        .padding(.vertical, 12)
        .accessibilityElement(children: .combine)
    }
}

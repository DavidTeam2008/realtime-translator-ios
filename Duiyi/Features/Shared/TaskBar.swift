import SwiftUI

struct TaskBar: View {
    let language: AppLanguage
    let statusText: String
    let isActive: Bool
    let onNewTask: () -> Void
    let onEndTask: () -> Void

    var body: some View {
        HStack(alignment: .center, spacing: 12) {
            Text(statusText)
                .font(.caption.weight(.medium))
                .foregroundStyle(isActive ? Tokens.listen : Tokens.textSecondary)
                .accessibilityLabel(statusText)
            Spacer(minLength: 8)
            Button(Copy.newTask(for: language), action: onNewTask)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(Tokens.listen)
            Button(Copy.endTask(for: language), action: onEndTask)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(isActive ? Tokens.danger : Tokens.textSecondary)
                .disabled(!isActive)
        }
        .padding(.horizontal, Tokens.horizontalPadding)
        .padding(.bottom, 8)
    }
}

enum TaskStatusText {
    static func make(hasTask: Bool, startedAt: Date?, language: AppLanguage) -> String {
        guard hasTask else { return Copy.taskIdle(for: language) }
        guard let startedAt else { return Copy.taskRunning(for: language) }
        let elapsed = Date().timeIntervalSince(startedAt)
        if elapsed < 90 {
            return "\(Copy.taskRunning(for: language)) · \(Copy.justNow(for: language))"
        }
        return "\(Copy.taskRunning(for: language)) · \(TaskFormatting.durationText(seconds: elapsed, language: language))"
    }
}

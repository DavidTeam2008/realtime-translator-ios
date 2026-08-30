import SwiftUI

struct ExportShareButton: View {
    let task: TaskSession
    let language: AppLanguage
    let exporter: any ExportSharing
    var title: String? = nil

    @State private var fileURL: URL?

    var body: some View {
        Group {
            if let fileURL {
                ShareLink(item: fileURL) {
                    label
                }
            } else {
                Button(action: prepare) {
                    label
                }
            }
        }
        .buttonStyle(.plain)
        .task(id: task.id) {
            prepare()
        }
    }

    private var label: some View {
        Text(title ?? Copy.exportShare(for: language))
            .font(.subheadline.weight(.bold))
            .foregroundStyle(Color(hex: 0x1C1915))
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(Tokens.listen, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private func prepare() {
        fileURL = try? exporter.makeTranscriptFile(task: task, language: language)
    }
}

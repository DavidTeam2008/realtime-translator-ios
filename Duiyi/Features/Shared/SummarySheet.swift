import SwiftUI
import UIKit

struct SummarySheet: View {
    let language: AppLanguage
    let availability: SummaryAvailability
    let isLoading: Bool
    let summary: ConversationSummary?
    let errorText: String?
    var exportTask: TaskSession? = nil
    var exporter: (any ExportSharing)? = nil
    let onCopy: () -> Void
    let onClose: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(Copy.summaryTitle(for: language))
                .font(.headline)
                .foregroundStyle(Tokens.textPrimary)

            availabilityBanner

            ScrollView {
                Group {
                    if isLoading {
                        Text(Copy.summaryLoading(for: language))
                            .foregroundStyle(Tokens.textSecondary)
                    } else if let errorText {
                        Text(errorText)
                            .foregroundStyle(Tokens.danger)
                    } else if let summary, !summary.text.isEmpty {
                        Text(summary.text)
                            .foregroundStyle(Tokens.textPrimary)
                    }
                }
                .font(.body)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(maxHeight: 240)

            if let exportTask, let exporter {
                ExportShareButton(task: exportSession(exportTask), language: language, exporter: exporter)
            }

            HStack {
                if let summary, !summary.text.isEmpty, !isLoading {
                    Button(Copy.copySummary(for: language), action: onCopy)
                        .foregroundStyle(Tokens.textPrimary)
                }
                Spacer()
                Button(Copy.done(for: language), action: onClose)
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

    private var availabilityBanner: some View {
        let text: String
        if summary?.usedAppleIntelligence == true {
            text = Copy.appleIntelligenceGenerated(for: language)
        } else {
            text = Copy.summaryAvailabilityMessage(availability, for: language)
        }
        return Text(text)
            .font(.footnote)
            .foregroundStyle(summary?.usedAppleIntelligence == true ? Color(hex: 0xB8E0C8) : Color(hex: 0xF0D9B0))
            .padding(10)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                (summary?.usedAppleIntelligence == true ? Color(hex: 0x1D2A24) : Color(hex: 0x2A2420)),
                in: RoundedRectangle(cornerRadius: 12, style: .continuous)
            )
    }

    private func exportSession(_ task: TaskSession) -> TaskSession {
        var copy = task
        copy.summary = summary ?? task.summary
        return copy
    }
}

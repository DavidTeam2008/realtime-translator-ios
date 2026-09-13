import Foundation

struct TranscriptExportService: ExportSharing {
    func makeTranscriptFile(task: TaskSession, language: AppLanguage) throws -> URL {
        let caches = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first
            ?? FileManager.default.temporaryDirectory
        cleanupOldExports(in: caches)
        let url = caches.appendingPathComponent(filename(for: task), isDirectory: false)
        let text = render(task: task, language: language)
        try Data(text.utf8).write(to: url, options: .atomic)
        return url
    }

    func render(task: TaskSession, language: AppLanguage) -> String {
        let app = Copy.appTitle(for: language)
        let feature = Copy.featureTitle(task.feature, for: language)
        let start = task.startedAt.formatted(Date.FormatStyle(date: .abbreviated, time: .shortened).locale(language.locale))
        let end = (task.endedAt ?? task.startedAt).formatted(
            Date.FormatStyle(date: .omitted, time: .shortened).locale(language.locale)
        )
        let range = "\(start)–\(end)"
        let direction: String
        switch task.feature {
        case .faceToFace:
            let target = task.targetLanguage ?? task.sourceLanguage.defaultPeer
            direction = "\(task.sourceLanguage.nativeName) ↔ \(target.nativeName)"
        case .simultaneous:
            let target = task.targetLanguage ?? task.sourceLanguage.defaultPeer
            direction = "\(task.sourceLanguage.nativeName) → \(target.nativeName)"
        case .meeting:
            let spoken = Set(task.entries.map(\.source))
            direction = spoken.count > 1
                ? Copy.meetingMultilingual(for: language)
                : (spoken.first?.nativeName ?? task.sourceLanguage.nativeName)
        }

        var blocks = [
            "\(app) · \(feature)",
            range,
            direction,
            "",
            Copy.transcriptSection(for: language)
        ]
        if task.entries.isEmpty {
            blocks.append("—")
        } else {
            for entry in task.entries {
                let prefix = task.feature == .meeting ? "[\(entry.source.nativeName)] " : ""
                let line = entry.translatedText.isEmpty
                    ? "\(prefix)\(entry.sourceText)"
                    : "\(prefix)\(entry.sourceText)\n→ \(entry.translatedText)"
                blocks.append(line)
            }
        }
        if let summary = task.summary, !summary.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            blocks.append("")
            blocks.append(Copy.summaryTitle(for: language))
            blocks.append(summary.text)
        }
        return blocks.joined(separator: "\n")
    }

    private func filename(for task: TaskSession) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyyMMdd-HHmm"
        return "Duiyi-\(task.feature.rawValue)-\(formatter.string(from: task.startedAt)).txt"
    }

    private func cleanupOldExports(in directory: URL) {
        guard let files = try? FileManager.default.contentsOfDirectory(
            at: directory,
            includingPropertiesForKeys: [.contentModificationDateKey],
            options: [.skipsHiddenFiles]
        ) else { return }
        let stale = files.filter { $0.lastPathComponent.hasPrefix("Duiyi-") && $0.pathExtension == "txt" }
        for file in stale {
            try? FileManager.default.removeItem(at: file)
        }
    }
}

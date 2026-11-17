import CryptoKit
import Foundation

struct TranscriptExportService: ExportSharing {
    private static let retentionInterval: TimeInterval = 7 * 24 * 3_600

    private let exportDirectoryOverride: URL?
    private let now: @Sendable () -> Date

    init(exportDirectory: URL? = nil, now: @escaping @Sendable () -> Date = { Date() }) {
        exportDirectoryOverride = exportDirectory
        self.now = now
    }

    func makeTranscriptFile(task: TaskSession, language: AppLanguage) throws -> URL {
        let directory = try exportDirectory()
        cleanupExpiredExports(in: directory)
        let text = render(task: task, language: language)
        let data = Data(text.utf8)
        let url = directory.appendingPathComponent(filename(for: task, language: language, data: data))
        if !FileManager.default.fileExists(atPath: url.path) {
            try data.write(to: url, options: .atomic)
        }
        PreparedSnapshotRegistry.shared.protect(url)
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

    private func exportDirectory() throws -> URL {
        if let exportDirectoryOverride {
            return exportDirectoryOverride
        }
        let caches = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first
            ?? FileManager.default.temporaryDirectory
        let directory = caches.appendingPathComponent("TranscriptExports", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return directory
    }

    private func filename(for task: TaskSession, language: AppLanguage, data: Data) -> String {
        var versioned = Data(language.rawValue.utf8)
        versioned.append(0)
        versioned.append(data)
        let digest = SHA256.hash(data: versioned).map { String(format: "%02x", $0) }.joined()
        return "Duiyi-\(task.feature.rawValue)-\(task.id.uuidString.lowercased())-\(digest).txt"
    }

    private func cleanupExpiredExports(in directory: URL) {
        guard let files = try? FileManager.default.contentsOfDirectory(
            at: directory,
            includingPropertiesForKeys: [.isRegularFileKey, .contentModificationDateKey],
            options: [.skipsHiddenFiles]
        ) else { return }
        let current = now()
        for file in files {
            guard isSnapshotName(file.lastPathComponent),
                  let values = try? file.resourceValues(forKeys: [.isRegularFileKey, .contentModificationDateKey]),
                  values.isRegularFile == true,
                  let modifiedAt = values.contentModificationDate,
                  modifiedAt <= current,
                  current.timeIntervalSince(modifiedAt) > Self.retentionInterval,
                  !PreparedSnapshotRegistry.shared.isProtected(file)
            else { continue }
            try? FileManager.default.removeItem(at: file)
        }
    }

    private func isSnapshotName(_ name: String) -> Bool {
        guard name.hasPrefix("Duiyi-"), name.hasSuffix(".txt") else { return false }
        let stem = name.dropFirst("Duiyi-".count).dropLast(".txt".count)
        guard let separator = stem.firstIndex(of: "-") else { return false }
        guard FeatureID(rawValue: String(stem[..<separator])) != nil else { return false }
        let identity = stem[stem.index(after: separator)...]
        guard identity.count == 36 + 1 + 64 else { return false }
        let digest = identity.suffix(64)
        guard digest.allSatisfy(\.isHexDigit) else { return false }
        let uuidString = identity.dropLast(65)
        return uuidString.count == 36 && UUID(uuidString: String(uuidString)) != nil
    }
}

private final class PreparedSnapshotRegistry: @unchecked Sendable {
    static let shared = PreparedSnapshotRegistry()

    private let lock = NSLock()
    private var paths: Set<String> = []

    func protect(_ url: URL) {
        lock.lock()
        paths.insert(url.standardizedFileURL.path)
        lock.unlock()
    }

    func isProtected(_ url: URL) -> Bool {
        lock.lock()
        defer { lock.unlock() }
        return paths.contains(url.standardizedFileURL.path)
    }
}

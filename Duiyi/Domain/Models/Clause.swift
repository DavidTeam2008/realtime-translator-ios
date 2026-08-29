import Foundation

struct Clause: Equatable, Sendable, Identifiable {
    var id: UUID
    var utteranceID: UUID
    var text: String
    var language: AppLanguage
}

struct SynthesisJob: Equatable, Sendable, Identifiable {
    var id: UUID
    var utteranceID: UUID
    var text: String
    var language: AppLanguage

    init(clause: Clause) {
        id = clause.id
        utteranceID = clause.utteranceID
        text = clause.text
        language = clause.language
    }
}

enum InterpretationLayout {
    static let historyLimit = 50
    static let speechQueueLimit = 2
}

enum ClauseSplitter {
    static let terminators = CharacterSet(charactersIn: "，。！？；、：…—,;:!?")

    static func consume(
        translated: String,
        utteranceID: UUID,
        language: AppLanguage,
        alreadySpoken: String,
        isSettled: Bool
    ) -> (clauses: [Clause], spokenPrefix: String) {
        let text = translated.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else {
            return ([], alreadySpoken)
        }

        let speakable: String
        if isSettled {
            speakable = text
        } else if let index = lastTerminatorIndex(in: text) {
            speakable = String(text[...index])
        } else {
            return ([], alreadySpoken)
        }

        let suffix = unspokenSuffix(speakable: speakable, alreadySpoken: alreadySpoken, language: language)
        let pieces = splitClauses(stripLeadingTerminators(suffix))
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.trimmingCharacters(in: terminators.union(.whitespacesAndNewlines)).isEmpty }
        let clauses = pieces.map { piece in
            Clause(id: UUID(), utteranceID: utteranceID, text: piece, language: language)
        }
        let nextPrefix = spokenCursor(alreadySpoken: alreadySpoken, speakable: speakable)
        return (clauses, nextPrefix)
    }

    static func shouldCarry(_ alreadySpoken: String, into translated: String, language: AppLanguage) -> Bool {
        let spoken = alreadySpoken.trimmingCharacters(in: .whitespacesAndNewlines)
        let stem = stripIgnorable(spoken)
        guard stem.count >= minimumStemLength(for: language) else { return false }
        if translated.hasPrefix(spoken) || translated.hasPrefix(stem) {
            return true
        }
        return alignmentEndIndex(of: stem, in: translated) != nil
    }

    static func unspokenSuffix(speakable: String, alreadySpoken: String, language: AppLanguage) -> String {
        let spoken = alreadySpoken.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !spoken.isEmpty else { return speakable }
        if speakable.hasPrefix(spoken) {
            return String(speakable.dropFirst(spoken.count))
        }

        let stem = stripIgnorable(spoken)
        guard !stem.isEmpty else { return speakable }
        if speakable.hasPrefix(stem) {
            return String(speakable.dropFirst(stem.count))
        }
        if let endIndex = alignmentEndIndex(of: stem, in: speakable) {
            return String(speakable[endIndex...])
        }

        let shared = longestCommonPrefixCount(speakable, stem)
        if shared >= minimumStemLength(for: language) {
            let index = speakable.index(speakable.startIndex, offsetBy: shared)
            return String(speakable[index...])
        }

        let speakableStem = stripIgnorable(speakable)
        if stem.hasPrefix(speakableStem) {
            return ""
        }
        return speakable
    }

    private static func spokenCursor(alreadySpoken: String, speakable: String) -> String {
        let spoken = alreadySpoken.trimmingCharacters(in: .whitespacesAndNewlines)
        if spoken.isEmpty { return speakable }
        if speakable.count >= spoken.count { return speakable }
        return spoken
    }

    private static func stripLeadingTerminators(_ text: String) -> String {
        String(text.drop(while: isIgnorable))
    }

    private static func stripIgnorable(_ text: String) -> String {
        text.trimmingCharacters(in: terminators.union(.whitespacesAndNewlines))
    }

    private static func isIgnorable(_ character: Character) -> Bool {
        character.unicodeScalars.allSatisfy {
            terminators.contains($0) || CharacterSet.whitespacesAndNewlines.contains($0)
        }
    }

    /// Match `stem` from the start of `text`, skipping punctuation and whitespace in `text`.
    /// Used so "和其他人一样" still lines up with "和其他人一样，当我…".
    private static func alignmentEndIndex(of stem: String, in text: String) -> String.Index? {
        let compactStem = stem.filter { !isIgnorable($0) }
        guard !compactStem.isEmpty else { return nil }

        var stemIndex = compactStem.startIndex
        var textIndex = text.startIndex
        var matched = 0
        while textIndex < text.endIndex, stemIndex < compactStem.endIndex {
            let character = text[textIndex]
            if isIgnorable(character) {
                textIndex = text.index(after: textIndex)
                continue
            }
            guard character == compactStem[stemIndex] else { return nil }
            matched += 1
            stemIndex = compactStem.index(after: stemIndex)
            textIndex = text.index(after: textIndex)
        }
        guard stemIndex == compactStem.endIndex, matched >= 1 else { return nil }
        return textIndex
    }

    private static func minimumStemLength(for language: AppLanguage) -> Int {
        language.usesLatinScript ? 12 : 4
    }

    private static func longestCommonPrefixCount(_ left: String, _ right: String) -> Int {
        zip(left, right).prefix { $0 == $1 }.count
    }

    private static func lastTerminatorIndex(in text: String) -> String.Index? {
        text.lastIndex { character in
            character.unicodeScalars.allSatisfy { terminators.contains($0) }
        }
    }

    private static func splitClauses(_ text: String) -> [String] {
        var clauses: [String] = []
        var current = ""
        for character in text {
            current.append(character)
            if character.unicodeScalars.allSatisfy({ terminators.contains($0) }) {
                clauses.append(current)
                current = ""
            }
        }
        if !current.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            clauses.append(current)
        }
        return clauses
    }
}

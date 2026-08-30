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
        if !isSettled, CompactView(speakable).characters.count < minimumVolatileLength(for: language) {
            return ([], alreadySpoken)
        }

        let remnants = unspokenRemnants(speakable: speakable, alreadySpoken: alreadySpoken, language: language)
        let pieces: [String]
        if isSettled {
            let joined = remnants
                .map { stripLeadingTerminators($0) }
                .joined()
                .trimmingCharacters(in: .whitespacesAndNewlines)
            pieces = joined.trimmingCharacters(in: terminators.union(.whitespacesAndNewlines)).isEmpty
                ? []
                : [joined]
        } else {
            pieces = remnants
                .flatMap { splitClauses(stripLeadingTerminators($0)) }
                .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                .filter { !$0.trimmingCharacters(in: terminators.union(.whitespacesAndNewlines)).isEmpty }
        }
        let clauses = pieces.map { piece in
            Clause(id: UUID(), utteranceID: utteranceID, text: piece, language: language)
        }
        let nextPrefix = spokenCursor(alreadySpoken: alreadySpoken, speakable: speakable)
        return (clauses, nextPrefix)
    }

    static func shouldCarry(_ alreadySpoken: String, into translated: String, language: AppLanguage) -> Bool {
        let spoken = alreadySpoken.trimmingCharacters(in: .whitespacesAndNewlines)
        let stem = stripIgnorable(spoken)
        guard CompactView(stem).characters.count >= 2 else { return false }
        if translated.hasPrefix(spoken) || translated.hasPrefix(stem) {
            return true
        }
        if alignmentEndIndex(of: stem, in: translated) != nil {
            return true
        }
        return compactSpan(of: stem, in: translated, language: language) != nil
    }

    static func unspokenSuffix(speakable: String, alreadySpoken: String, language: AppLanguage) -> String {
        unspokenRemnants(speakable: speakable, alreadySpoken: alreadySpoken, language: language).joined()
    }

    static func unspokenRemnants(speakable: String, alreadySpoken: String, language: AppLanguage) -> [String] {
        let spoken = alreadySpoken.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !spoken.isEmpty else { return [speakable] }
        if speakable.hasPrefix(spoken) {
            return [String(speakable.dropFirst(spoken.count))]
        }

        let stem = stripIgnorable(spoken)
        guard !stem.isEmpty else { return [speakable] }
        if speakable.hasPrefix(stem) {
            return [String(speakable.dropFirst(stem.count))]
        }
        if let endIndex = alignmentEndIndex(of: stem, in: speakable) {
            return [String(speakable[endIndex...])]
        }
        if let span = compactSpan(of: stem, in: speakable, language: language) {
            return remnantsAroundSpokenSpan(in: speakable, span: span, language: language)
        }
        if let tail = subsequenceTail(speakable: speakable, alreadySpoken: stem, language: language) {
            return tail.isEmpty ? [] : [tail]
        }

        let shared = longestCommonPrefixCount(speakable, stem)
        if shared >= minimumStemLength(for: language) {
            let index = speakable.index(speakable.startIndex, offsetBy: shared)
            return [String(speakable[index...])]
        }

        let speakableStem = stripIgnorable(speakable)
        if stem.hasPrefix(speakableStem) {
            return []
        }
        return [speakable]
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
            terminators.contains($0)
                || CharacterSet.whitespacesAndNewlines.contains($0)
                || quotationMarks.contains($0)
        }
    }

    private static let quotationMarks = CharacterSet(charactersIn: "《》〈〉「」『』“”\"'")

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

    /// Find already-spoken text even if the new translation prepended words, e.g.
    /// spoken "那是3月18日" inside "是的，那是 3月18日，但他们改成了 15日。"
    private static func compactSpan(
        of stem: String,
        in text: String,
        language: AppLanguage
    ) -> Range<String.Index>? {
        let haystack = CompactView(text)
        let needle = CompactView(stem).characters
        if needle.count >= 2, let compactRange = firstOccurrence(needle, in: haystack.characters) {
            return haystack.originalRange(compactRange: compactRange)
        }
        if let aligned = bestAlignedRange(
            needle: needle,
            haystack: haystack,
            minLength: minimumStemLength(for: language)
        ) {
            return aligned
        }
        var truncated = needle
        while truncated.count >= minimumStemLength(for: language) {
            truncated.removeFirst()
            if let compactRange = firstOccurrence(truncated, in: haystack.characters) {
                return haystack.originalRange(compactRange: compactRange)
            }
        }
        return nil
    }

    private static func bestAlignedRange(
        needle: [Character],
        haystack: CompactView,
        minLength: Int
    ) -> Range<String.Index>? {
        guard needle.count >= minLength, !haystack.characters.isEmpty else { return nil }
        var bestOffset = 0
        var bestLength = 0
        for offset in 0..<haystack.characters.count {
            let length = longestCommonPrefixCount(
                needle,
                Array(haystack.characters[offset...])
            )
            if length > bestLength {
                bestLength = length
                bestOffset = offset
            }
        }
        for skip in 0..<needle.count {
            let remaining = Array(needle[skip...])
            guard remaining.count >= minLength else { break }
            let length = longestCommonPrefixCount(remaining, haystack.characters)
            if length > bestLength {
                bestLength = length
                bestOffset = 0
            }
        }
        guard bestLength >= minLength else { return nil }
        return haystack.originalRange(compactRange: bestOffset..<(bestOffset + bestLength))
    }

    /// Already-spoken text is still the same sentence, with words inserted in the middle
    /// (《幸运》 → 《幸运的日子》). Speak only what comes after the spoken characters.
    private static func subsequenceTail(
        speakable: String,
        alreadySpoken: String,
        language: AppLanguage
    ) -> String? {
        let haystack = CompactView(speakable)
        let needle = CompactView(alreadySpoken).characters
        guard needle.count >= minimumStemLength(for: language) else { return nil }
        var needleIndex = 0
        var hayIndex = 0
        while needleIndex < needle.count, hayIndex < haystack.characters.count {
            if haystack.characters[hayIndex] == needle[needleIndex] {
                needleIndex += 1
            }
            hayIndex += 1
        }
        guard needleIndex == needle.count else { return nil }
        if hayIndex >= haystack.origins.count {
            return ""
        }
        return String(speakable[haystack.origins[hayIndex]...])
    }

    private static func remnantsAroundSpokenSpan(
        in speakable: String,
        span: Range<String.Index>,
        language: AppLanguage
    ) -> [String] {
        let leading = String(speakable[..<span.lowerBound])
        let trailing = String(speakable[span.upperBound...])
        var remnants: [String] = []
        if CompactView(leading).characters.count >= minimumStemLength(for: language) {
            remnants.append(leading)
        }
        if !stripIgnorable(trailing).isEmpty {
            remnants.append(trailing)
        }
        return remnants
    }

    private static func firstOccurrence(_ needle: [Character], in haystack: [Character]) -> Range<Int>? {
        guard !needle.isEmpty, haystack.count >= needle.count else { return nil }
        let lastStart = haystack.count - needle.count
        for start in 0...lastStart {
            if haystack[start..<(start + needle.count)].elementsEqual(needle) {
                return start..<(start + needle.count)
            }
        }
        return nil
    }

    private struct CompactView {
        let characters: [Character]
        let origins: [String.Index]
        let source: String

        init(_ text: String) {
            var characters: [Character] = []
            var origins: [String.Index] = []
            var index = text.startIndex
            while index < text.endIndex {
                let character = text[index]
                if !ClauseSplitter.isIgnorable(character) {
                    characters.append(character)
                    origins.append(index)
                }
                index = text.index(after: index)
            }
            self.characters = characters
            self.origins = origins
            self.source = text
        }

        func originalRange(compactRange: Range<Int>) -> Range<String.Index>? {
            guard compactRange.lowerBound >= 0,
                  compactRange.upperBound <= characters.count,
                  compactRange.lowerBound < compactRange.upperBound
            else {
                return nil
            }
            let start = origins[compactRange.lowerBound]
            if compactRange.upperBound < origins.count {
                return start..<origins[compactRange.upperBound]
            }
            return start..<source.endIndex
        }
    }

    private static func minimumVolatileLength(for language: AppLanguage) -> Int {
        language.usesLatinScript ? 18 : 6
    }

    private static func minimumStemLength(for language: AppLanguage) -> Int {
        language.usesLatinScript ? 12 : 4
    }

    private static func longestCommonPrefixCount(_ left: String, _ right: String) -> Int {
        zip(left, right).prefix { $0 == $1 }.count
    }

    private static func longestCommonPrefixCount(_ left: [Character], _ right: [Character]) -> Int {
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

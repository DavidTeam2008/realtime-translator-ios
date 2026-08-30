import Foundation

enum SpokenText {
    static func isContinuation(_ incoming: String, of previous: String, language: AppLanguage) -> Bool {
        let incomingText = normalized(incoming)
        let previousText = normalized(previous)
        guard !incomingText.isEmpty, !previousText.isEmpty else { return false }
        if incomingText == previousText { return true }
        if incomingText.hasPrefix(previousText) || previousText.hasPrefix(incomingText) {
            return true
        }
        if incomingText.contains(previousText), previousText.count >= minimumStemLength(for: language) {
            return true
        }
        let shared = zip(incomingText, previousText).prefix { $0 == $1 }.count
        let shorter = min(incomingText.count, previousText.count)
        guard shorter > 0 else { return false }
        return shared >= minimumStemLength(for: language) && Double(shared) / Double(shorter) >= 0.55
    }

    static func preferredSource(_ current: String, _ incoming: String) -> String {
        incoming.count >= current.count ? incoming : current
    }

    static func preferredTranslation(_ current: String, _ incoming: String) -> String {
        if incoming.isEmpty { return current }
        if current.isEmpty { return incoming }
        if covers(incoming, of: current) { return incoming }
        if covers(current, of: incoming) { return current }
        if isRefinement(incoming, of: current) {
            let incomingText = compact(incoming)
            let currentText = compact(current)
            if currentText.count > incomingText.count, isSubsequence(incomingText, of: currentText) {
                return current
            }
            return incoming
        }
        return incoming.count >= current.count ? incoming : current
    }

    /// Same sentence growing or being lightly revised, e.g. 《幸运》 → 《幸运的日子》.
    static func isRefinement(_ incoming: String, of previous: String) -> Bool {
        let incomingText = compact(incoming)
        let previousText = compact(previous)
        guard !incomingText.isEmpty, !previousText.isEmpty else { return false }
        if incomingText == previousText { return true }
        if incomingText.hasPrefix(previousText) || previousText.hasPrefix(incomingText) {
            return true
        }
        if incomingText.contains(previousText) || previousText.contains(incomingText) {
            return true
        }
        let shorter = min(incomingText.count, previousText.count)
        let longer = max(incomingText.count, previousText.count)
        guard shorter >= 4 else { return false }
        let lcs = longestCommonSubsequenceCount(incomingText, previousText)
        if Double(lcs) / Double(shorter) >= 0.82 {
            return true
        }
        let shared = zip(incomingText, previousText).prefix { $0 == $1 }.count
        guard shared > 0 else { return false }
        let shorterRatio = Double(shared) / Double(shorter)
        let longerRatio = Double(shared) / Double(longer)
        guard shorterRatio >= 0.5 else { return false }
        if longerRatio >= 0.75 {
            return true
        }
        let previousTail = previousText.dropFirst(shared)
        let incomingTail = incomingText.dropFirst(shared)
        // "See you later Jack" vs "See you later Lucy" share a stem but swap a name.
        if previousTail.count >= 3, incomingTail.count >= 3 {
            return false
        }
        return true
    }

    static func covers(_ text: String, of other: String) -> Bool {
        let haystack = compact(text)
        let needle = compact(other)
        guard !needle.isEmpty else { return true }
        return haystack.contains(needle)
    }

    static func isRewrite(_ current: String, incoming: String) -> Bool {
        guard !current.isEmpty, !incoming.isEmpty else { return false }
        return !covers(incoming, of: current) && !covers(current, of: incoming)
    }

    static func isShortRewrite(_ current: String, incoming: String) -> Bool {
        guard isRewrite(current, incoming: incoming) else { return false }
        return compact(incoming).count <= compact(current).count + 6
    }

    static func compact(_ text: String) -> String {
        text.lowercased().filter { $0.isLetter || $0.isNumber }
    }

    static func normalized(_ text: String) -> String {
        compact(text)
    }

    static func containsCompact(_ haystack: String, clause: String) -> Bool {
        let needle = compact(clause)
        guard needle.count >= 2 else { return false }
        return compact(haystack).contains(needle)
    }

    private static func minimumStemLength(for language: AppLanguage) -> Int {
        language.usesLatinScript ? 16 : 6
    }

    static func isSubsequence(_ needle: String, of haystack: String) -> Bool {
        guard !needle.isEmpty else { return true }
        var needleIndex = needle.startIndex
        for character in haystack {
            if character == needle[needleIndex] {
                needleIndex = needle.index(after: needleIndex)
                if needleIndex == needle.endIndex {
                    return true
                }
            }
        }
        return false
    }

    private static func longestCommonSubsequenceCount(_ left: String, _ right: String) -> Int {
        let first = Array(left)
        let second = Array(right)
        guard !first.isEmpty, !second.isEmpty else { return 0 }
        var previous = Array(repeating: 0, count: second.count + 1)
        for index in 1...first.count {
            var current = Array(repeating: 0, count: second.count + 1)
            for other in 1...second.count {
                if first[index - 1] == second[other - 1] {
                    current[other] = previous[other - 1] + 1
                } else {
                    current[other] = max(previous[other], current[other - 1])
                }
            }
            previous = current
        }
        return previous[second.count]
    }
}

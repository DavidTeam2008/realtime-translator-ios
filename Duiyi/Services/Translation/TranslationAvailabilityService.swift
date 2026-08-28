import Foundation
import Translation

struct TranslationAvailabilityService: TranslationAvailabilityChecking {
    func pairStatus(from: AppLanguage, to: AppLanguage) async -> TranslationPairStatus {
        let availability = LanguageAvailability()
        let source = from.localeLanguage
        let target = to.localeLanguage
        let forward = await availability.status(from: source, to: target)
        let reverse = await availability.status(from: target, to: source)
        return Self.combine(forward, reverse)
    }

    private static func combine(
        _ forward: LanguageAvailability.Status,
        _ reverse: LanguageAvailability.Status
    ) -> TranslationPairStatus {
        if forward == .unsupported || reverse == .unsupported {
            return .unsupported
        }
        if forward == .installed && reverse == .installed {
            return .installed
        }
        return .supported
    }
}

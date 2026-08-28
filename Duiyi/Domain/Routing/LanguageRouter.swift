import Foundation

enum LanguageRouter {
    static func targetSide(detected: AppLanguage, userLanguage: AppLanguage) -> SpeakerSide {
        detected == userLanguage ? .peer : .user
    }

    static func targetLanguage(
        detected: AppLanguage,
        userLanguage: AppLanguage,
        peerLanguage: AppLanguage
    ) -> AppLanguage {
        detected == userLanguage ? peerLanguage : userLanguage
    }

    static func speakerSide(detected: AppLanguage, userLanguage: AppLanguage) -> SpeakerSide {
        targetSide(detected: detected, userLanguage: userLanguage).opposite
    }
}

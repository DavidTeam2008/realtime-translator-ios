import Foundation
import Testing
@testable import Duiyi

struct LanguageRouterTests {
    @Test("User language matches detected speech → captions go to the peer pane")
    func userSpeechRoutesToPeer() {
        #expect(LanguageRouter.targetSide(detected: .zhHans, userLanguage: .zhHans) == .peer)
        #expect(LanguageRouter.targetSide(detected: .english, userLanguage: .english) == .peer)
        #expect(LanguageRouter.targetSide(detected: .japanese, userLanguage: .japanese) == .peer)
    }

    @Test("The other language of the pair → captions go to the user pane")
    func peerSpeechRoutesToUser() {
        #expect(LanguageRouter.targetSide(detected: .english, userLanguage: .zhHans) == .user)
        #expect(LanguageRouter.targetSide(detected: .zhHans, userLanguage: .english) == .user)
        #expect(LanguageRouter.targetSide(detected: .korean, userLanguage: .zhHans) == .user)
    }

    @Test("Target language is the other language of the selected pair")
    func targetLanguageIsTheOtherOfThePair() {
        #expect(
            LanguageRouter.targetLanguage(
                detected: .zhHans,
                userLanguage: .zhHans,
                peerLanguage: .japanese
            ) == .japanese
        )
        #expect(
            LanguageRouter.targetLanguage(
                detected: .thai,
                userLanguage: .english,
                peerLanguage: .thai
            ) == .english
        )
        #expect(
            LanguageRouter.targetLanguage(
                detected: .vietnamese,
                userLanguage: .zhHans,
                peerLanguage: .vietnamese
            ) == .zhHans
        )
    }

    @Test("Speaker side is the opposite of the listener")
    func speakerIsOppositeOfListener() {
        #expect(LanguageRouter.speakerSide(detected: .zhHans, userLanguage: .zhHans) == .user)
        #expect(LanguageRouter.speakerSide(detected: .english, userLanguage: .zhHans) == .peer)
    }
}

import Foundation

@MainActor
@Observable
final class PreferencesStore {
    private enum Key {
        static let userLanguage = "duiyi.userLanguage"
        static let peerLanguage = "duiyi.peerLanguage"
        static let fontSize = "duiyi.fontSize"
        static let onboarding = "duiyi.onboardingComplete"
        static let autoStart = "duiyi.autoStartListening"
        static let onboardingStep = "duiyi.onboardingStep"
    }

    private let defaults: UserDefaults

    var userLanguage: AppLanguage {
        didSet { defaults.set(userLanguage.rawValue, forKey: Key.userLanguage) }
    }

    var peerLanguage: AppLanguage {
        didSet { defaults.set(peerLanguage.rawValue, forKey: Key.peerLanguage) }
    }

    var fontSize: CaptionFontSize {
        didSet { defaults.set(fontSize.rawValue, forKey: Key.fontSize) }
    }

    var hasCompletedOnboarding: Bool {
        didSet { defaults.set(hasCompletedOnboarding, forKey: Key.onboarding) }
    }

    var autoStartListening: Bool {
        didSet { defaults.set(autoStartListening, forKey: Key.autoStart) }
    }

    var onboardingStep: Int {
        didSet { defaults.set(onboardingStep, forKey: Key.onboardingStep) }
    }

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        let resolvedUser: AppLanguage
        if let raw = defaults.string(forKey: Key.userLanguage), let language = AppLanguage(rawValue: raw) {
            resolvedUser = language
        } else {
            resolvedUser = .inferredFromSystem()
        }
        userLanguage = resolvedUser
        if let raw = defaults.string(forKey: Key.peerLanguage),
           let language = AppLanguage(rawValue: raw),
           language != resolvedUser {
            peerLanguage = language
        } else {
            peerLanguage = resolvedUser.defaultPeer
        }
        if let raw = defaults.string(forKey: Key.fontSize), let size = CaptionFontSize(rawValue: raw) {
            fontSize = size
        } else {
            fontSize = .larger
        }
        hasCompletedOnboarding = defaults.bool(forKey: Key.onboarding)
        if defaults.object(forKey: Key.autoStart) == nil {
            autoStartListening = true
        } else {
            autoStartListening = defaults.bool(forKey: Key.autoStart)
        }
        onboardingStep = defaults.integer(forKey: Key.onboardingStep)
    }
}

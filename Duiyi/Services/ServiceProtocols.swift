import AVFAudio
import Foundation

struct SendablePCMBuffer: @unchecked Sendable {
    let buffer: AVAudioPCMBuffer
}

protocol SpeechRecognizing: Sendable {
    func start(languages: [AppLanguage], fallbackLanguage: AppLanguage) async throws -> AsyncStream<Utterance>
    func stop() async
}

protocol SpeechModelPreparing: Sendable {
    func isDeviceCapable(for languages: [AppLanguage]) async -> Bool
    func prepare(languages: [AppLanguage], progress: @escaping @Sendable (Double) -> Void) async throws
}

protocol AudioCapturing: Sendable {
    func start() async throws -> AsyncStream<SendablePCMBuffer>
    func stop() async
}

protocol PermissionGranting: Sendable {
    func currentStatus() async -> PermissionStatus
    func requestAccess() async -> PermissionStatus
}

enum PermissionStatus: Equatable, Sendable {
    case unknown
    case granted
    case microphoneDenied
    case speechDenied

    var isGranted: Bool { self == .granted }

    func asDuiyiError() -> DuiyiError? {
        switch self {
        case .granted, .unknown:
            return nil
        case .microphoneDenied:
            return .microphoneDenied
        case .speechDenied:
            return .speechDenied
        }
    }
}

protocol TranslationAvailabilityChecking: Sendable {
    func pairStatus(from: AppLanguage, to: AppLanguage) async -> TranslationPairStatus
}

enum TranslationPairStatus: Equatable, Sendable {
    case installed
    case supported
    case unsupported
}

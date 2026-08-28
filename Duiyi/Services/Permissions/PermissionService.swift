import AVFoundation
import Foundation
import Speech

struct PermissionService: PermissionGranting {
    func currentStatus() async -> PermissionStatus {
        let microphone = AVAudioApplication.shared.recordPermission
        let speech = SFSpeechRecognizer.authorizationStatus()
        return map(microphone: microphone, speech: speech)
    }

    func requestAccess() async -> PermissionStatus {
        _ = await requestMicrophone()
        _ = await requestSpeech()
        return await currentStatus()
    }

    private func map(
        microphone: AVAudioApplication.recordPermission,
        speech: SFSpeechRecognizerAuthorizationStatus
    ) -> PermissionStatus {
        if microphone == .denied {
            return .microphoneDenied
        }
        switch speech {
        case .authorized where microphone == .granted:
            return .granted
        case .denied, .restricted:
            return .speechDenied
        default:
            return .unknown
        }
    }

    private func requestMicrophone() async -> Bool {
        await withCheckedContinuation { continuation in
            AVAudioApplication.requestRecordPermission { granted in
                continuation.resume(returning: granted)
            }
        }
    }

    private func requestSpeech() async -> SFSpeechRecognizerAuthorizationStatus {
        await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { status in
                continuation.resume(returning: status)
            }
        }
    }
}

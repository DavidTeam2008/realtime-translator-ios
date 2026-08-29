import Foundation
import Testing
@testable import Duiyi

struct AudioSessionPolicyTests {
    @Test("Speaker-only output cannot speak without echo")
    func speakerOnlyIsUnsafe() {
        #expect(AudioEchoPolicy.canSpeakWithoutEcho(outputs: [.builtInSpeaker]) == false)
        #expect(AudioEchoPolicy.canSpeakWithoutEcho(outputs: []) == false)
        #expect(AudioEchoPolicy.canSpeakWithoutEcho(outputs: [.other]) == false)
    }

    @Test("Headphones and Bluetooth can speak without echo")
    func headsetRoutesAreSafe() {
        #expect(AudioEchoPolicy.canSpeakWithoutEcho(outputs: [.headphones]))
        #expect(AudioEchoPolicy.canSpeakWithoutEcho(outputs: [.bluetoothA2DP]))
        #expect(AudioEchoPolicy.canSpeakWithoutEcho(outputs: [.bluetoothLE]))
        #expect(AudioEchoPolicy.canSpeakWithoutEcho(outputs: [.bluetoothHFP]))
        #expect(AudioEchoPolicy.canSpeakWithoutEcho(outputs: [.builtInReceiver]))
    }

    @Test("Any echo-safe output is enough even if speaker is also present")
    func mixedRouteIsSafe() {
        #expect(AudioEchoPolicy.canSpeakWithoutEcho(outputs: [.builtInSpeaker, .headphones]))
    }

    @Test("Bluetooth listed only as an input still allows voice-out")
    func bluetoothInputIsSafe() {
        #expect(AudioEchoPolicy.canSpeakWithoutEcho(outputs: [.builtInSpeaker], inputs: [.bluetoothHFP]))
        #expect(AudioEchoPolicy.canSpeakWithoutEcho(outputs: [], inputs: [.bluetoothLE]))
    }

    @Test("Unknown headphone-like ports are treated as safe")
    func externalPortIsSafe() {
        #expect(AudioEchoPolicy.canSpeakWithoutEcho(outputs: [.external]))
        #expect(AudioEchoPolicy.canSpeakWithoutEcho(outputs: [.usbAudio]))
    }
}

import AVFAudio
import Foundation

final class BufferConverter: @unchecked Sendable {
    enum ConverterError: Error {
        case failedToCreateConverter
        case failedToCreateConversionBuffer
        case conversionFailed(NSError?)
    }

    private var converter: AVAudioConverter?

    func convert(_ buffer: AVAudioPCMBuffer, to format: AVAudioFormat) throws -> AVAudioPCMBuffer {
        let inputFormat = buffer.format
        guard inputFormat != format else { return buffer }

        if converter == nil || converter?.outputFormat != format || converter?.inputFormat != inputFormat {
            converter = AVAudioConverter(from: inputFormat, to: format)
            converter?.primeMethod = .none
        }

        guard let converter else {
            throw ConverterError.failedToCreateConverter
        }

        let sampleRateRatio = converter.outputFormat.sampleRate / converter.inputFormat.sampleRate
        let scaledInputFrameLength = Double(buffer.frameLength) * sampleRateRatio
        let frameCapacity = AVAudioFrameCount(scaledInputFrameLength.rounded(.up))

        guard let conversionBuffer = AVAudioPCMBuffer(pcmFormat: converter.outputFormat, frameCapacity: frameCapacity) else {
            throw ConverterError.failedToCreateConversionBuffer
        }

        var nsError: NSError?
        let consumed = ConverterFlag()
        let status = converter.convert(to: conversionBuffer, error: &nsError) { _, inputStatusPointer in
            defer { consumed.value = true }
            inputStatusPointer.pointee = consumed.value ? .noDataNow : .haveData
            return consumed.value ? nil : buffer
        }

        guard status != .error else {
            throw ConverterError.conversionFailed(nsError)
        }
        return conversionBuffer
    }

    static func copy(_ buffer: AVAudioPCMBuffer) -> AVAudioPCMBuffer? {
        guard let copy = AVAudioPCMBuffer(pcmFormat: buffer.format, frameCapacity: buffer.frameLength) else {
            return nil
        }
        copy.frameLength = buffer.frameLength
        let channelCount = Int(buffer.format.channelCount)
        if let src = buffer.floatChannelData, let dst = copy.floatChannelData {
            for channel in 0..<channelCount {
                memcpy(dst[channel], src[channel], Int(buffer.frameLength) * MemoryLayout<Float>.size)
            }
            return copy
        }
        if let src = buffer.int16ChannelData, let dst = copy.int16ChannelData {
            for channel in 0..<channelCount {
                memcpy(dst[channel], src[channel], Int(buffer.frameLength) * MemoryLayout<Int16>.size)
            }
            return copy
        }
        return nil
    }
}

private final class ConverterFlag: @unchecked Sendable {
    var value = false
}

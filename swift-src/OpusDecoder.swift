import Foundation
import COpus

public final class OpusDecoderWrapper {
    private var decoder: OpaquePointer?
    private let sampleRate: Int32
    private let channels: Int32
    private let maxFrameSize: Int32
    private var outBuffer: [Int16]

    public init(sampleRate: Int32 = 48000, channels: Int32 = 1) {
        self.sampleRate = sampleRate
        self.channels = channels
        self.maxFrameSize = sampleRate / 10 // Up to 100ms (4800 samples)
        self.outBuffer = [Int16](repeating: 0, count: Int(maxFrameSize * channels))

        var err: Int32 = 0
        self.decoder = opus_decoder_create(sampleRate, channels, &err)
        if self.decoder == nil || err != 0 {
            let errMsg = String(cString: opus_strerror(err))
            print("❌ OpusDecoder init error: \(errMsg) (\(err))")
        }
    }

    deinit {
        if let dec = decoder {
            opus_decoder_destroy(dec)
        }
    }

    public func decode(data: Data?) -> Data? {
        guard let dec = decoder else { return nil }

        let decodedSamples: Int32
        if let data = data, !data.isEmpty {
            decodedSamples = data.withUnsafeBytes { rawPtr -> Int32 in
                guard let baseAddress = rawPtr.baseAddress?.assumingMemoryBound(to: UInt8.self) else { return 0 }
                return self.outBuffer.withUnsafeMutableBufferPointer { outPtr -> Int32 in
                    guard let outBase = outPtr.baseAddress else { return 0 }
                    return opus_decode(
                        dec,
                        baseAddress,
                        Int32(data.count),
                        outBase,
                        self.maxFrameSize,
                        0
                    )
                }
            }
        } else {
            // Packet loss concealment
            decodedSamples = self.outBuffer.withUnsafeMutableBufferPointer { outPtr -> Int32 in
                guard let outBase = outPtr.baseAddress else { return 0 }
                return opus_decode(dec, nil, 0, outBase, self.maxFrameSize, 1)
            }
        }

        guard decodedSamples > 0 else { return nil }

        let byteCount = Int(decodedSamples * channels) * MemoryLayout<Int16>.size
        return self.outBuffer.withUnsafeBufferPointer { bufPtr -> Data in
            guard let bufBase = bufPtr.baseAddress else { return Data() }
            return Data(bytes: bufBase, count: byteCount)
        }
    }
}

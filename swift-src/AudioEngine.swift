import Foundation
import AudioToolbox
import CoreAudio
import QuartzCore

/// Clean, zero-latency DSP processor for microphone level calibration & clarity
public final class VoiceDSPProcessor {
    // 80Hz Butterworth High-Pass Filter Coefficients (for 48000Hz, Q = 0.707)
    private let hp_b0: Float = 0.99262144
    private let hp_b1: Float = -1.98524288
    private let hp_b2: Float = 0.99262144
    private let hp_a1: Float = -1.98518845
    private let hp_a2: Float = 0.98529731
    private var hp_x1_L: Float = 0.0, hp_x2_L: Float = 0.0, hp_y1_L: Float = 0.0, hp_y2_L: Float = 0.0
    private var hp_x1_R: Float = 0.0, hp_x2_R: Float = 0.0, hp_y1_R: Float = 0.0, hp_y2_R: Float = 0.0

    // 3.2kHz Vocal Presence & Clarity Peaking Filter (+3.0dB, Q = 0.8)
    private let eq_b0: Float = 1.07168925
    private let eq_b1: Float = -1.51271430
    private let eq_b2: Float = 0.58418270
    private let eq_a1: Float = -1.51271430
    private let eq_a2: Float = 0.65587195
    private var eq_x1_L: Float = 0.0, eq_x2_L: Float = 0.0, eq_y1_L: Float = 0.0, eq_y2_L: Float = 0.0
    private var eq_x1_R: Float = 0.0, eq_x2_R: Float = 0.0, eq_y1_R: Float = 0.0, eq_y2_R: Float = 0.0

    // Standard PC Microphone Sensitivity Calibration Factor (+12dB = 4.0x)
    // Mobile mic ADCs capture raw telephony-level signals (~ -26dBFS at desk distance).
    // This baseline calibration brings 100% gain to standard broadcast/meeting level (-8dBFS to -12dBFS).
    private let baselineCalibration: Float = 4.0

    public func reset() {
        hp_x1_L = 0; hp_x2_L = 0; hp_y1_L = 0; hp_y2_L = 0
        hp_x1_R = 0; hp_x2_R = 0; hp_y1_R = 0; hp_y2_R = 0
        eq_x1_L = 0; eq_x2_L = 0; eq_y1_L = 0; eq_y2_L = 0
        eq_x1_R = 0; eq_x2_R = 0; eq_y1_R = 0; eq_y2_R = 0
    }

    public func process(stereoBuffer: UnsafeMutablePointer<Int16>, sampleCount: Int, userGain: Float, isMuted: Bool) -> (peak: Float, rms: Float) {
        if isMuted {
            for i in 0..<sampleCount {
                stereoBuffer[i] = 0
            }
            return (0.0, 0.0)
        }

        let effectiveGain = userGain * baselineCalibration
        var outSumSquares: Float = 0.0
        var maxPeak: Float = 0.0

        for i in stride(from: 0, to: sampleCount, by: 2) {
            var sL = Float(stereoBuffer[i]) / 32768.0
            var sR = Float(stereoBuffer[i + 1]) / 32768.0

            // 1. 80Hz Low-Cut (High-Pass) to remove desk rumble & mud
            let yL1 = hp_b0 * sL + hp_b1 * hp_x1_L + hp_b2 * hp_x2_L - hp_a1 * hp_y1_L - hp_a2 * hp_y2_L
            hp_x2_L = hp_x1_L; hp_x1_L = sL; hp_y2_L = hp_y1_L; hp_y1_L = yL1; sL = yL1

            let yR1 = hp_b0 * sR + hp_b1 * hp_x1_R + hp_b2 * hp_x2_R - hp_a1 * hp_y1_R - hp_a2 * hp_y2_R
            hp_x2_R = hp_x1_R; hp_x1_R = sR; hp_y2_R = hp_y1_R; hp_y1_R = yR1; sR = yR1

            // 2. 3.2kHz Voice Clarity & Consonant Presence
            let yL2 = eq_b0 * sL + eq_b1 * eq_x1_L + eq_b2 * eq_x2_L - eq_a1 * eq_y1_L - eq_a2 * eq_y2_L
            eq_x2_L = eq_x1_L; eq_x1_L = sL; eq_y2_L = eq_y1_L; eq_y1_L = yL2; sL = yL2

            let yR2 = eq_b0 * sR + eq_b1 * eq_x1_R + eq_b2 * eq_x2_R - eq_a1 * eq_y1_R - eq_a2 * eq_y2_R
            eq_x2_R = eq_x1_R; eq_x1_R = sR; eq_y2_R = eq_y1_R; eq_y1_R = yR2; sR = yR2

            // 3. Apply Calibrated Gain
            sL *= effectiveGain
            sR *= effectiveGain

            // 4. Soft-Knee Studio Limiter (prevents harsh digital clipping on loud speech)
            sL = softLimit(sL)
            sR = softLimit(sR)

            let outValL = max(-32768.0, min(32767.0, sL * 32767.0))
            let outValR = max(-32768.0, min(32767.0, sR * 32767.0))
            stereoBuffer[i] = Int16(outValL)
            stereoBuffer[i + 1] = Int16(outValR)

            let mag = max(abs(sL), abs(sR))
            if mag > maxPeak { maxPeak = mag }
            outSumSquares += sL * sL + sR * sR
        }

        let outRMS = sqrt(outSumSquares / Float(max(1, sampleCount)))
        return (maxPeak, outRMS)
    }

    @inline(__always)
    private func softLimit(_ x: Float) -> Float {
        if x > 0.85 {
            let excess = x - 0.85
            return 0.85 + 0.15 * tanh(excess / 0.15)
        } else if x < -0.85 {
            let excess = x + 0.85
            return -0.85 + 0.15 * tanh(excess / 0.15)
        }
        return x
    }
}

public final class AudioEngine: ObservableObject {
    @Published public var vuLevel: Float = 0.0
    @Published public var gain: Float = 1.0 // 0.0 to 2.0 (1.0 = 100% standard calibrated volume)
    @Published public var isMuted: Bool = false

    public let dsp = VoiceDSPProcessor()

    private var audioQueue: AudioQueueRef?
    private var buffers: [AudioQueueBufferRef] = []
    private let bufferCount = 4
    // 20ms at 48000Hz Stereo (2 ch * 2 bytes * 960 frames = 3840 bytes)
    private let bufferSize: UInt32 = 960 * 2 * 2
    private var isRunning = false
    private let lock = NSLock()
    private var pcmQueue: [Data] = []
    private var prebufferCount = 0
    private let targetPrebuffer = 2 // Cushion 2 packets (40ms) to eliminate network jitter stutter
    private var lastVUUpdate: CFTimeInterval = 0

    public var currentDevice: AudioDevice?

    public init() {
        self.currentDevice = AudioDeviceManager.getDefaultDevice()
    }

    deinit {
        stop()
    }

    public func start(device: AudioDevice? = nil) {
        stop()
        dsp.reset()
        prebufferCount = 0

        if let dev = device {
            self.currentDevice = dev
        }

        // Ensure macOS input volume is set to 100% so system apps (e.g. WeChat) don't attenuate the virtual mic
        DispatchQueue.global(qos: .utility).async {
            let script = "set volume input volume 100"
            if let appleScript = NSAppleScript(source: script) {
                var error: NSDictionary?
                appleScript.executeAndReturnError(&error)
            }
        }

        var format = AudioStreamBasicDescription(
            mSampleRate: 48000.0,
            mFormatID: kAudioFormatLinearPCM,
            mFormatFlags: kLinearPCMFormatFlagIsSignedInteger | kLinearPCMFormatFlagIsPacked,
            mBytesPerPacket: 4,
            mFramesPerPacket: 1,
            mBytesPerFrame: 4,
            mChannelsPerFrame: 2, // Stereo for full BlackHole and macOS compatibility
            mBitsPerChannel: 16,
            mReserved: 0
        )

        let callback: AudioQueueOutputCallback = { userData, queue, buffer in
            guard let userData = userData else { return }
            let engine = Unmanaged<AudioEngine>.fromOpaque(userData).takeUnretainedValue()
            engine.handleAudioQueueOutput(queue: queue, buffer: buffer)
        }

        let selfPtr = UnsafeMutableRawPointer(Unmanaged.passUnretained(self).toOpaque())
        let status = AudioQueueNewOutput(&format, callback, selfPtr, nil, nil, 0, &audioQueue)

        guard status == noErr, let queue = audioQueue else {
            return
        }

        if let dev = self.currentDevice, !dev.uid.isEmpty {
            var uidCF = dev.uid as CFString
            _ = withUnsafePointer(to: &uidCF) { ptr in
                AudioQueueSetProperty(queue, kAudioQueueProperty_CurrentDevice, ptr, UInt32(MemoryLayout<CFString>.size))
            }
        }

        buffers.removeAll()
        for _ in 0..<bufferCount {
            var buffer: AudioQueueBufferRef?
            AudioQueueAllocateBuffer(queue, bufferSize, &buffer)
            if let buf = buffer {
                buf.pointee.mAudioDataByteSize = bufferSize
                memset(buf.pointee.mAudioData, 0, Int(bufferSize))
                AudioQueueEnqueueBuffer(queue, buf, 0, nil)
                buffers.append(buf)
            }
        }

        AudioQueueStart(queue, nil)
        isRunning = true
    }

    public func stop() {
        isRunning = false
        if let queue = audioQueue {
            AudioQueueStop(queue, true)
            AudioQueueDispose(queue, true)
            audioQueue = nil
        }
        buffers.removeAll()
        lock.lock()
        pcmQueue.removeAll()
        prebufferCount = 0
        lock.unlock()
        DispatchQueue.main.async {
            self.vuLevel = 0.0
        }
    }

    public func writePCM(monoData: Data) {
        guard isRunning else { return }
        // Convert Mono 16-bit to Stereo 16-bit (L=R)
        let sampleCount = monoData.count / MemoryLayout<Int16>.size
        var stereoData = Data(count: sampleCount * 2 * MemoryLayout<Int16>.size)

        stereoData.withUnsafeMutableBytes { dstRaw in
            guard let dst = dstRaw.baseAddress?.assumingMemoryBound(to: Int16.self) else { return }
            monoData.withUnsafeBytes { srcRaw in
                guard let src = srcRaw.baseAddress?.assumingMemoryBound(to: Int16.self) else { return }
                for i in 0..<sampleCount {
                    let s = src[i]
                    dst[i * 2] = s
                    dst[i * 2 + 1] = s
                }
            }
        }

        lock.lock()
        if pcmQueue.count > 50 {
            pcmQueue.removeFirst(10)
        }
        pcmQueue.append(stereoData)
        prebufferCount += 1
        lock.unlock()
    }

    private func handleAudioQueueOutput(queue: AudioQueueRef, buffer: AudioQueueBufferRef) {
        guard isRunning else {
            buffer.pointee.mAudioDataByteSize = bufferSize
            memset(buffer.pointee.mAudioData, 0, Int(bufferSize))
            AudioQueueEnqueueBuffer(queue, buffer, 0, nil)
            return
        }

        var filledBytes: Int = 0
        let dest = buffer.pointee.mAudioData.assumingMemoryBound(to: UInt8.self)

        lock.lock()
        // Wait for prebuffer on initial start to avoid glitch
        if prebufferCount >= targetPrebuffer || !pcmQueue.isEmpty {
            while filledBytes < Int(bufferSize) && !pcmQueue.isEmpty {
                let chunk = pcmQueue.removeFirst()
                let needed = Int(bufferSize) - filledBytes
                let toCopy = min(chunk.count, needed)
                _ = chunk.withUnsafeBytes { rawPtr in
                    memcpy(dest.advanced(by: filledBytes), rawPtr.baseAddress!, toCopy)
                }
                filledBytes += toCopy
                if toCopy < chunk.count {
                    let remaining = chunk.subdata(in: toCopy..<chunk.count)
                    pcmQueue.insert(remaining, at: 0)
                }
            }
        }
        lock.unlock()

        if filledBytes < Int(bufferSize) {
            memset(dest.advanced(by: filledBytes), 0, Int(bufferSize) - filledBytes)
        }
        buffer.pointee.mAudioDataByteSize = bufferSize

        // Apply VoiceDSPProcessor (Low-Cut, Clarity EQ, Calibrated Gain, Soft Limiter)
        let samples = buffer.pointee.mAudioData.assumingMemoryBound(to: Int16.self)
        let totalSamples = Int(bufferSize) / MemoryLayout<Int16>.size

        let (_, rms) = dsp.process(
            stereoBuffer: samples,
            sampleCount: totalSamples,
            userGain: self.gain,
            isMuted: self.isMuted
        )

        // Convert to dB, then normalize to 0.0 - 1.0 range
        let db = rms > 0 ? 20 * log10(rms) : -100.0
        let normalized = max(0.0, min(1.0, (db + 50.0) / 50.0))

        let now = CACurrentMediaTime()
        if now - lastVUUpdate >= 0.04 {
            lastVUUpdate = now
            DispatchQueue.main.async {
                self.vuLevel = Float(normalized)
            }
        }

        AudioQueueEnqueueBuffer(queue, buffer, 0, nil)
    }
}

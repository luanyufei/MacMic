import Foundation
import CoreAudio
import AudioToolbox

public struct AudioDevice: Identifiable, Hashable {
    public var id: AudioDeviceID
    public var name: String
    public var uid: String

    public init(id: AudioDeviceID, name: String, uid: String) {
        self.id = id
        self.name = name
        self.uid = uid
    }
}

public final class AudioDeviceManager {
    public static func getOutputDevices() -> [AudioDevice] {
        var propertySize: UInt32 = 0
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDevices,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )

        let status = AudioObjectGetPropertyDataSize(
            AudioObjectID(kAudioObjectSystemObject),
            &address,
            0,
            nil,
            &propertySize
        )

        guard status == noErr else { return [] }

        let deviceCount = Int(propertySize) / MemoryLayout<AudioDeviceID>.size
        var deviceIDs = [AudioDeviceID](repeating: 0, count: deviceCount)

        let getStatus = AudioObjectGetPropertyData(
            AudioObjectID(kAudioObjectSystemObject),
            &address,
            0,
            nil,
            &propertySize,
            &deviceIDs
        )

        guard getStatus == noErr else { return [] }

        var outputDevices: [AudioDevice] = []

        for devID in deviceIDs {
            // Check if device has output streams
            var streamAddress = AudioObjectPropertyAddress(
                mSelector: kAudioDevicePropertyStreams,
                mScope: kAudioObjectPropertyScopeOutput,
                mElement: kAudioObjectPropertyElementMain
            )
            var streamSize: UInt32 = 0
            _ = AudioObjectGetPropertyDataSize(devID, &streamAddress, 0, nil, &streamSize)
            if streamSize == 0 {
                continue
            }

            // Query Name
            var nameAddress = AudioObjectPropertyAddress(
                mSelector: kAudioObjectPropertyName,
                mScope: kAudioObjectPropertyScopeGlobal,
                mElement: kAudioObjectPropertyElementMain
            )
            var nameCF: CFString = "" as CFString
            var nameSize = UInt32(MemoryLayout<CFString>.size)
            let nameRes = withUnsafeMutablePointer(to: &nameCF) { ptr in
                AudioObjectGetPropertyData(devID, &nameAddress, 0, nil, &nameSize, ptr)
            }
            let name = (nameRes == noErr) ? (nameCF as String) : "Unknown Device"

            // Query UID
            var uidAddress = AudioObjectPropertyAddress(
                mSelector: kAudioDevicePropertyDeviceUID,
                mScope: kAudioObjectPropertyScopeGlobal,
                mElement: kAudioObjectPropertyElementMain
            )
            var uidCF: CFString = "" as CFString
            var uidSize = UInt32(MemoryLayout<CFString>.size)
            let uidRes = withUnsafeMutablePointer(to: &uidCF) { ptr in
                AudioObjectGetPropertyData(devID, &uidAddress, 0, nil, &uidSize, ptr)
            }
            let uid = (uidRes == noErr) ? (uidCF as String) : ""

            outputDevices.append(AudioDevice(id: devID, name: name, uid: uid))
        }

        return outputDevices
    }

    public static func getDefaultDevice() -> AudioDevice? {
        let devs = getOutputDevices()
        if let wm = devs.first(where: { $0.name.contains("WO Mic") }) {
            return wm
        }
        if let bh = devs.first(where: { $0.name.contains("BlackHole") }) {
            return bh
        }
        return devs.first
    }
}

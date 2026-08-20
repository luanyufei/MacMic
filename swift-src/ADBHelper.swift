import Foundation

public struct ADBDevice: Identifiable {
    public var id: String { serial }
    public let serial: String
    public let state: String
}

public final class ADBHelper {
    public static func findADBPath() -> String? {
        let candidates = [
            "/opt/homebrew/bin/adb",
            "/usr/local/bin/adb",
            "/Users/\(NSUserName())/Library/Android/sdk/platform-tools/adb",
            "/usr/bin/adb"
        ]
        for path in candidates {
            if FileManager.default.isExecutableFile(atPath: path) {
                return path
            }
        }
        return nil
    }

    public static func listDevices() -> [ADBDevice] {
        guard let adb = findADBPath() else { return [] }
        let pipe = Pipe()
        let process = Process()
        process.executableURL = URL(fileURLWithPath: adb)
        process.arguments = ["devices"]
        process.standardOutput = pipe

        do {
            try process.run()
            process.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            guard let output = String(data: data, encoding: .utf8) else { return [] }

            var devices: [ADBDevice] = []
            let lines = output.components(separatedBy: .newlines)
            for line in lines.dropFirst() {
                let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
                guard !trimmed.isEmpty else { continue }
                let parts = trimmed.split(separator: "\t")
                if parts.count >= 2 {
                    devices.append(ADBDevice(serial: String(parts[0]), state: String(parts[1])))
                }
            }
            return devices
        } catch {
            return []
        }
    }

    @discardableResult
    public static func forwardPort(localPort: Int = 8125, remotePort: Int = 8125) -> Bool {
        guard let adb = findADBPath() else { return false }
        let process = Process()
        process.executableURL = URL(fileURLWithPath: adb)
        process.arguments = ["forward", "tcp:\(localPort)", "tcp:\(remotePort)"]
        do {
            try process.run()
            process.waitUntilExit()
            return process.terminationStatus == 0
        } catch {
            return false
        }
    }

    @discardableResult
    public static func removeForward(localPort: Int = 8125) -> Bool {
        guard let adb = findADBPath() else { return false }
        let process = Process()
        process.executableURL = URL(fileURLWithPath: adb)
        process.arguments = ["forward", "--remove", "tcp:\(localPort)"]
        do {
            try process.run()
            process.waitUntilExit()
            return process.terminationStatus == 0
        } catch {
            return false
        }
    }
}

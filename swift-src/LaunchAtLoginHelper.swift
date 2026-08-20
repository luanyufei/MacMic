import Foundation
import ServiceManagement

public final class LaunchAtLoginHelper {
    public static var isEnabled: Bool {
        get {
            if #available(macOS 13.0, *) {
                return SMAppService.mainApp.status == .enabled
            } else {
                return UserDefaults.standard.bool(forKey: "macmic_launch_at_login")
            }
        }
        set {
            UserDefaults.standard.set(newValue, forKey: "macmic_launch_at_login")
            if #available(macOS 13.0, *) {
                do {
                    if newValue {
                        if SMAppService.mainApp.status != .enabled {
                            try SMAppService.mainApp.register()
                        }
                    } else {
                        if SMAppService.mainApp.status == .enabled {
                            try SMAppService.mainApp.unregister()
                        }
                    }
                } catch {
                    print("⚠️ SMAppService error: \(error)")
                }
            } else {
                setupLegacyLaunchAgent(enabled: newValue)
            }
        }
    }

    private static func setupLegacyLaunchAgent(enabled: Bool) {
        let fileManager = FileManager.default
        let launchAgentsDir = fileManager.homeDirectoryForCurrentUser.appendingPathComponent("Library/LaunchAgents")
        let plistURL = launchAgentsDir.appendingPathComponent("com.macmic.app.plist")

        if enabled {
            let bundleURL = Bundle.main.bundleURL
            let executableURL = Bundle.main.executableURL ?? bundleURL.appendingPathComponent("Contents/MacOS/MacMic")
            
            let plistContent: [String: Any] = [
                "Label": "com.macmic.app",
                "ProgramArguments": [executableURL.path],
                "RunAtLoad": true,
                "ProcessType": "Interactive"
            ]
            
            try? fileManager.createDirectory(at: launchAgentsDir, withIntermediateDirectories: true)
            (plistContent as NSDictionary).write(to: plistURL, atomically: true)
        } else {
            try? fileManager.removeItem(at: plistURL)
        }
    }
}

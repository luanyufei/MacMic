import SwiftUI
import AppKit
import Combine

public enum SettingsTab: String, CaseIterable, Identifiable {
    case display = "display"
    case general = "general"
    case about = "about"

    public var id: String { rawValue }

    public func title(using l10n: LocalizationManager) -> String {
        switch self {
        case .display: return l10n.t("tab_display")
        case .general: return l10n.t("tab_general")
        case .about: return l10n.t("tab_about")
        }
    }

    public var icon: String {
        switch self {
        case .display: return "paintpalette.fill"
        case .general: return "gearshape.fill"
        case .about: return "info.circle.fill"
        }
    }
}

public final class SettingsViewModel: ObservableObject {
    @Published public var selectedTab: SettingsTab = .display
    @Published public var launchAtLogin: Bool {
        didSet {
            LaunchAtLoginHelper.isEnabled = launchAtLogin
        }
    }
    @Published public var hideDock: Bool {
        didSet {
            UserDefaults.standard.set(hideDock, forKey: "macmic_hide_dock")
            DispatchQueue.main.async {
                NSApp.setActivationPolicy(self.hideDock ? .accessory : .regular)
            }
        }
    }

    public init() {
        self.launchAtLogin = LaunchAtLoginHelper.isEnabled
        self.hideDock = UserDefaults.standard.bool(forKey: "macmic_hide_dock")
    }
}

public struct SettingsView: View {
    @ObservedObject var l10n = LocalizationManager.shared
    @StateObject private var vm = SettingsViewModel()
    @Environment(\.presentationMode) var presentationMode

    public init() {}

    public var body: some View {
        VStack(spacing: 0) {
            // Header Bar
            HStack {
                Text(l10n.t("settings_title"))
                    .font(.system(size: 14, weight: .bold, design: .rounded))
                Spacer()
                Button(action: {
                    presentationMode.wrappedValue.dismiss()
                }) {
                    Image(systemName: "xmark.circle.fill")
                        .font(.system(size: 17))
                        .foregroundColor(.secondary.opacity(0.8))
                }
                .buttonStyle(.plain)
                .focusable(false)
            }
            .padding(.horizontal, 16)
            .padding(.top, 12)
            .padding(.bottom, 10)

            // Tab Selector
            Picker("", selection: $vm.selectedTab) {
                ForEach(SettingsTab.allCases) { tab in
                    Label(tab.title(using: l10n), systemImage: tab.icon).tag(tab)
                }
            }
            .pickerStyle(.segmented)
            .labelsHidden()
            .padding(.horizontal, 16)
            .padding(.bottom, 12)

            Divider()

            // Content Area
            VStack(spacing: 12) {
                switch vm.selectedTab {
                case .display:
                    displaySection
                case .general:
                    generalSection
                case .about:
                    aboutSection
                }
                Spacer(minLength: 0)
            }
            .padding(16)
        }
        .frame(width: 360, height: 320)
        .background(Color(NSColor.windowBackgroundColor))
        .preferredColorScheme(l10n.currentTheme.colorScheme)
    }

    // MARK: - Display Section
    private var displaySection: some View {
        VStack(spacing: 0) {
            // Language Setting Row
            HStack {
                Label(l10n.t("settings_language"), systemImage: "globe")
                    .font(.system(size: 13, weight: .medium))
                Spacer()
                Picker("", selection: $l10n.currentLanguage) {
                    ForEach(AppLanguage.allCases) { lang in
                        Text(lang.displayName).tag(lang)
                    }
                }
                .labelsHidden()
                .pickerStyle(.menu)
                .frame(width: 140)
            }
            .padding(.vertical, 8)
            .padding(.horizontal, 12)

            Divider()

            // Theme Setting Row
            HStack {
                Label(l10n.t("settings_theme"), systemImage: "circle.lefthalf.filled")
                    .font(.system(size: 13, weight: .medium))
                Spacer()
                Picker("", selection: $l10n.currentTheme) {
                    ForEach(AppTheme.allCases) { theme in
                        Text(theme.displayName(using: l10n)).tag(theme)
                    }
                }
                .labelsHidden()
                .pickerStyle(.segmented)
                .frame(width: 195)
            }
            .padding(.vertical, 8)
            .padding(.horizontal, 12)
        }
        .background(Color(NSColor.controlBackgroundColor).opacity(0.7))
        .cornerRadius(10)
    }

    // MARK: - General Section
    private var generalSection: some View {
        VStack(spacing: 0) {
            // Launch at Login Toggle
            HStack {
                Text(l10n.t("settings_launch_at_login"))
                    .font(.system(size: 13, weight: .medium))
                Spacer()
                Toggle("", isOn: $vm.launchAtLogin)
                    .labelsHidden()
                    .toggleStyle(.switch)
            }
            .padding(.vertical, 8)
            .padding(.horizontal, 12)

            Divider()

            // Hide Dock Icon Toggle
            HStack {
                Text(l10n.t("settings_hide_dock"))
                    .font(.system(size: 13, weight: .medium))
                Spacer()
                Toggle("", isOn: $vm.hideDock)
                    .labelsHidden()
                    .toggleStyle(.switch)
            }
            .padding(.vertical, 8)
            .padding(.horizontal, 12)
        }
        .background(Color(NSColor.controlBackgroundColor).opacity(0.7))
        .cornerRadius(10)
    }

    // MARK: - About Section
    private var aboutSection: some View {
        VStack(spacing: 12) {
            // App Badge
            VStack(spacing: 4) {
                Image(systemName: "mic.fill.badge.plus")
                    .font(.system(size: 32, weight: .bold))
                    .foregroundColor(.accentColor)
                Text("MacMic")
                    .font(.system(size: 16, weight: .bold, design: .rounded))
                Text("Version 1.0.0 (Apple Silicon Native)")
                    .font(.system(size: 10, design: .monospaced))
                    .foregroundColor(.secondary)
            }
            .padding(.top, 2)

            // Info Card
            VStack(spacing: 8) {
                // Project URL
                HStack {
                    Label(l10n.t("about_project_url"), systemImage: "link")
                        .font(.system(size: 12, weight: .medium))
                    Spacer()
                    Button(action: {
                        if let url = URL(string: "https://github.com/luanyufei/MacMic") {
                            NSWorkspace.shared.open(url)
                        }
                    }) {
                        HStack(spacing: 4) {
                            Text("GitHub")
                            Image(systemName: "arrow.up.right.square")
                        }
                        .font(.system(size: 11, weight: .semibold))
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                    .focusable(false)
                }

                Divider()

                // Author
                HStack {
                    Label(l10n.t("about_author"), systemImage: "person.crop.circle")
                        .font(.system(size: 12, weight: .medium))
                    Spacer()
                    Text("FEEFEENOON")
                        .font(.system(size: 12, weight: .bold, design: .rounded))
                        .foregroundColor(.primary)
                }

                Divider()

                // Email
                HStack {
                    Label(l10n.t("about_email"), systemImage: "envelope.fill")
                        .font(.system(size: 12, weight: .medium))
                    Spacer()
                    Button(action: {
                        if let url = URL(string: "mailto:noonyjufee@gmail.com") {
                            NSWorkspace.shared.open(url)
                        }
                    }) {
                        HStack(spacing: 4) {
                            Text("noonyjufee@gmail.com")
                            Image(systemName: "paperplane.fill")
                        }
                        .font(.system(size: 11, weight: .semibold))
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                    .focusable(false)
                }
            }
            .padding(10)
            .background(Color(NSColor.controlBackgroundColor).opacity(0.7))
            .cornerRadius(10)
        }
    }
}

import SwiftUI

struct HistoryIPRowView: View {
    let ip: String
    @ObservedObject var vm: AppViewModel
    @ObservedObject var l10n: LocalizationManager

    var body: some View {
        HStack(spacing: 8) {
            Button(action: {
                vm.host = ip
                vm.showHistoryPopover = false
            }) {
                HStack(spacing: 4) {
                    Image(systemName: "desktopcomputer")
                        .font(.system(size: 10))
                        .foregroundColor(.accentColor)
                    Text(ip)
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundColor(.primary)
                    Spacer()
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            Button(action: {
                vm.removeHistoryIP(ip)
                if vm.ipHistory.isEmpty {
                    vm.showHistoryPopover = false
                }
            }) {
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 12))
                    .foregroundColor(.secondary.opacity(0.7))
            }
            .buttonStyle(.plain)
            .help(l10n.t("delete"))
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 3)
    }
}

public struct ContentView: View {
    @ObservedObject private var vm = AppViewModel.shared
    @ObservedObject private var l10n = LocalizationManager.shared

    public init() {}

    public var body: some View {
        VStack(spacing: 12) {
            // Header Bar (Centered Logo & Trailing Settings Icon)
            ZStack {
                // Centered App Logo & Name
                HStack(spacing: 6) {
                    Image(systemName: "mic.fill.badge.plus")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundColor(.accentColor)
                    Text(l10n.t("app_title"))
                        .font(.system(size: 15, weight: .bold, design: .rounded))
                }

                // Trailing Settings Button
                HStack {
                    Spacer()
                    Button(action: {
                        vm.showSettings = true
                    }) {
                        Image(systemName: "gearshape.fill")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(.secondary)
                            .padding(4)
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .focusable(false)
                    .help(l10n.t("settings"))
                }
            }
            .frame(height: 22)
            .padding(.top, 2)
            .padding(.bottom, 2)

            // Transport Card
            VStack(alignment: .leading, spacing: 8) {
                Label(l10n.t("transport_header"), systemImage: "network")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(.secondary)

                Picker("", selection: $vm.selectedTransport) {
                    ForEach(TransportMode.allCases) { mode in
                        Text(mode.displayName(using: l10n)).tag(mode)
                    }
                }
                .labelsHidden()
                .pickerStyle(.segmented)
                .disabled(vm.isStreaming)

                if vm.selectedTransport != .usb {
                    HStack(spacing: 6) {
                        Text(l10n.t("phone_ip_label"))
                            .font(.system(size: 12, weight: .medium))
                            .foregroundColor(.secondary)

                        HStack(spacing: 4) {
                            TextField(l10n.t("phone_ip_placeholder"), text: $vm.host)
                                .textFieldStyle(.plain)
                                .font(.system(size: 12, design: .monospaced))
                                .disabled(vm.isStreaming)
                                .padding(.leading, 6)
                                .padding(.vertical, 4)

                            if !vm.ipHistory.isEmpty {
                                Button(action: {
                                    vm.showHistoryPopover.toggle()
                                }) {
                                    Image(systemName: "chevron.down")
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundColor(.secondary)
                                        .padding(.horizontal, 6)
                                        .padding(.vertical, 4)
                                        .contentShape(Rectangle())
                                }
                                .buttonStyle(.plain)
                                .disabled(vm.isStreaming)
                                .popover(isPresented: $vm.showHistoryPopover, arrowEdge: .bottom) {
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(l10n.t("history_ips"))
                                            .font(.system(size: 11, weight: .bold))
                                            .foregroundColor(.secondary)
                                            .padding(.horizontal, 8)
                                            .padding(.top, 6)

                                        Divider()

                                        ForEach(vm.ipHistory, id: \.self) { ip in
                                            HistoryIPRowView(ip: ip, vm: vm, l10n: l10n)
                                        }
                                    }
                                    .padding(.bottom, 6)
                                    .frame(minWidth: 190)
                                }
                            }
                        }
                        .background(Color(NSColor.controlBackgroundColor))
                        .cornerRadius(6)
                        .overlay(
                            RoundedRectangle(cornerRadius: 6)
                                .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                        )
                    }
                }
            }
            .padding(10)
            .background(Color(NSColor.controlBackgroundColor).opacity(0.6))
            .cornerRadius(10)

            // Audio Routing Card
            VStack(alignment: .leading, spacing: 8) {
                Label(l10n.t("audio_routing_header"), systemImage: "speaker.wave.2.fill")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(.secondary)

                Picker("", selection: $vm.selectedDevice) {
                    ForEach(vm.availableDevices) { dev in
                        Text(dev.name + (dev.name.contains("BlackHole") ? l10n.t("virtual_mic_tag") : "")).tag(Optional(dev))
                    }
                }
                .labelsHidden()
                .pickerStyle(.menu)

                HStack {
                    Text(l10n.t("gain_label"))
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                    Spacer()
                    Text("\(Int(vm.gainValue))%")
                        .font(.system(size: 11, weight: .bold, design: .monospaced))
                }

                Slider(value: $vm.gainValue, in: 0...200, step: 5)

                Toggle(l10n.t("mute_toggle"), isOn: $vm.isMuted)
                    .font(.system(size: 11))
            }
            .padding(10)
            .background(Color(NSColor.controlBackgroundColor).opacity(0.6))
            .cornerRadius(10)

            // VU Meter Card
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Label(l10n.t("vu_meter_header"), systemImage: "waveform")
                        .font(.system(size: 11, weight: .semibold))
                    Spacer()
                    if vm.isStreaming {
                        Text("\(vm.packetsReceived) pkts")
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundColor(.secondary)
                    }
                }

                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        RoundedRectangle(cornerRadius: 3)
                            .fill(Color.primary.opacity(0.08))
                            .frame(height: 10)

                        RoundedRectangle(cornerRadius: 3)
                            .fill(
                                LinearGradient(
                                    gradient: Gradient(colors: [.blue, .cyan, .green, .yellow]),
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                            .frame(width: max(0, min(geo.size.width, geo.size.width * CGFloat(vm.vuLevel))), height: 10)
                            .animation(.linear(duration: 0.06), value: vm.vuLevel)
                    }
                }
                .frame(height: 10)
            }
            .padding(10)
            .background(Color(NSColor.controlBackgroundColor).opacity(0.6))
            .cornerRadius(10)

            Spacer(minLength: 0)

            // Status Row
            HStack(spacing: 6) {
                Circle()
                    .fill(vm.statusColor)
                    .frame(width: 8, height: 8)
                Text(vm.statusMessage(using: l10n))
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(.secondary)
                    .lineLimit(1)
                Spacer()
            }
            .padding(.horizontal, 4)

            // Main Action Button
            Button(action: { vm.toggleConnect() }) {
                HStack {
                    Spacer()
                    Image(systemName: vm.isStreaming ? "stop.fill" : "play.fill")
                    Text(vm.isStreaming ? l10n.t("btn_disconnect") : l10n.t("btn_connect"))
                        .font(.system(size: 13, weight: .bold, design: .rounded))
                    Spacer()
                }
                .padding(.vertical, 8)
            }
            .buttonStyle(.borderedProminent)
            .tint(vm.isStreaming ? .red : .accentColor)
            .controlSize(.large)
        }
        .padding(.horizontal, 14)
        .padding(.bottom, 14)
        .padding(.top, 8)
        .frame(width: 360, height: 530)
        .preferredColorScheme(l10n.currentTheme.colorScheme)
        .sheet(isPresented: $vm.showSettings) {
            SettingsView()
        }
        .alert(isPresented: $vm.showAlert) {
            Alert(
                title: Text(l10n.t("alert_title")),
                message: Text(vm.alertMessage),
                dismissButton: .default(Text(l10n.t("alert_ok")))
            )
        }
    }
}

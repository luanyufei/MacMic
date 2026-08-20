# AGENTS.md - Developer & AI Maintenance Guide

Welcome to the **MacMic** project repository. This document serves as the primary technical specification, architectural guide, and operational runbook for AI agents and human contributors maintaining and extending this codebase.

---

## 1. Project Overview & Architecture

**MacMic** is an unofficial native macOS audio client for Apple Silicon (macOS 12.0+), designed to be 100% protocol-compatible with the official **WO Mic** mobile client (iOS / Android). It turns a smartphone into an ultra-low-latency wireless or wired microphone for macOS, outputting audio directly into a virtual audio device (such as **BlackHole 2ch**).

### 1.1 Tech Stack
- **Language**: Pure Swift 5.7+ / SwiftUI (Native App), Python 3 (CLI utilities / reference scripts)
- **Audio Decoding**: Statically linked C `libopus` (via Homebrew `opus`)
- **Audio Output Pipeline**: macOS CoreAudio / `AudioQueue`
- **Device Management**: CoreAudio HAL (`AudioObjectGetPropertyData`)
- **Android Port Forwarding**: Local ADB subprocess bridge (`adb forward tcp:8125 tcp:8125`)
- **System Integration**: MenuBar status item (`NSStatusItem`), `SMAppService` (Launch at Login), multi-language i18n (`Localization.swift`)

### 1.2 Repository Structure
```text
├── swift-src/
│   ├── main.swift                 # App entrypoint, NSApplicationDelegate, window styling & hide-on-close
│   ├── ContentView.swift          # Main SwiftUI interface, connection panel, logarithmic dB VU meter
│   ├── ViewModel.swift            # ObservableObject state manager & audio/network event coordinator
│   ├── WOMicClient.swift          # Network protocol handshake (TCP/UDP), audio packet receiver
│   ├── AudioEngine.swift          # CoreAudio AudioQueue playback engine & real-time dB peak calculation
│   ├── OpusDecoder.swift          # C libopus decoding wrapper (48kHz, mono/stereo)
│   ├── AudioDeviceManager.swift   # macOS CoreAudio output device discovery & BlackHole auto-detection
│   ├── ADBHelper.swift            # Android ADB detection and automatic port forwarding
│   ├── MenuBarManager.swift       # Menu bar icon, resident background operation & quick popover
│   ├── SettingsView.swift         # Multi-language selection & Launch at Login settings UI
│   ├── Localization.swift         # 9-language native dictionary & runtime dynamic language switcher
│   ├── LaunchAtLoginHelper.swift  # Apple SMAppService login item manager
│   ├── module.modulemap           # Clang module map for bridging C libopus headers
│   └── test_opus.swift            # Standalone Opus decoder test verification script
├── assets/                        # Screenshots & visual assets for documentation
├── WOMic.iconset/                 # Multi-resolution macOS app icon PNG assets
├── AppIcon.icns                   # Compiled macOS application icon file
├── build_app.sh                   # Native Apple Silicon arm64 compilation and ad-hoc codesigning script
├── README.md                      # English documentation & guide
├── README_ZH.md                   # 简体中文使用说明与技术文档
├── LICENSE                        # MIT License
└── .gitignore                     # Strict exclusion rules (apps, dmgs, logs, caches, reverse-engineering files)
```

---

## 2. Development Guidelines & Important Caveats

When making changes to the codebase, all AI agents and contributors must adhere to the following rules:

1. **Keep Standalone & Lightweight**:
   - The native Swift app must compile as a single standalone `.app` bundle with **zero external dynamic library dependencies at runtime** (Opus is statically linked into the Mach-O binary).
2. **Audio Routing**:
   - The app must default to or recommend **BlackHole 2ch** so that other macOS applications (Zoom, Teams, WeChat, OBS, etc.) can capture the microphone input.
3. **Window Management & Menu Bar**:
   - Closing the main window (`NSWindow`) MUST hide it to the menu bar rather than quitting the app, ensuring audio streaming continues uninterrupted.
4. **Localization (i18n)**:
   - When adding UI labels or alerts, always update all 9 languages in `swift-src/Localization.swift` (`zh_Hans`, `zh_Hant`, `en`, `ja`, `ko`, `es`, `fr`, `ru`, `de`).
5. **Git Hygiene**:
   - Never commit `.app` bundles, `.dmg` files, `.DS_Store`, build logs (`*.log`), or reverse-engineering materials (`android/`, `windows/`).

---

## 3. Release Publication Specifications (Strict Rules)

Every GitHub Release published for this repository **MUST** strictly follow the standards below:

### 3.1 Release Asset Rule
- ⚠️ **ONLY `.dmg` format is allowed.**
- ❌ **Strictly DO NOT upload `.zip`, `.tar.gz`, or bare binary executables.**
- The DMG filename format should follow: `MacMic-v<version>-arm64.dmg` (e.g. `MacMic-v1.0.0-arm64.dmg`).

### 3.2 Release Note Structure & Language Order
- **Language Order**: **English first, then Chinese**. Never interleave English and Chinese lines.
- **Section Order**:
  1. `### 🚀 New Features` / `### 🚀 新特性`
  2. `### 🐛 Bug Fixes` / `### 🐛 问题修复`
  3. `### ⚠️ Known Issues` / `### ⚠️ 已知问题`
  4. `### 📦 Installation & Gatekeeper Troubleshooting` / `### 📦 安装与故障排查`

*(Note: For the initial `v1.0.0` release, the "New Features" and "Bug Fixes" sections can be omitted or replaced with an Initial Release summary, keeping the focus on Known Issues and Installation.)*

### 3.3 Gatekeeper Troubleshooting Standard
Because open-source macOS apps are ad-hoc signed without paid Apple Developer ID notarization, macOS Gatekeeper may show:
> *"MacMic is damaged and can't be opened. You should move it to the Trash."* or *"Apple cannot verify the developer."*

The release notes **MUST** provide clear instructions for resolving this using `xattr -cr /Applications/MacMic.app`.

---

## 4. Release Note Standard Templates

### 4.1 General Release Note Template (For Future Versions)

```markdown
## English

### 🚀 New Features
- Feature item 1
- Feature item 2

### 🐛 Bug Fixes
- Bug fix 1
- Bug fix 2

### ⚠️ Known Issues
- Known issue 1

### 📦 Installation & Gatekeeper Troubleshooting
1. Download the `.dmg` installer below.
2. Open the DMG and drag **MacMic.app** into your **Applications** folder.
3. Open **MacMic** from Applications.
4. **If macOS displays "MacMic is damaged and can't be opened" or "Cannot verify developer"**:
   - Open **Terminal** and run the following command:
     ```bash
     xattr -cr /Applications/MacMic.app
     ```
   - Alternatively, right-click (or Control-click) `MacMic.app` in `/Applications` and select **Open**.

---

## 简体中文

### 🚀 新特性
- 新特性 1
- 新特性 2

### 🐛 问题修复
- 问题修复 1
- 问题修复 2

### ⚠️ 已知问题
- 已知问题 1

### 📦 安装与故障排查
1. 下载下方的 `.dmg` 安装包。
2. 双击打开 DMG，将 **MacMic.app** 拖入右侧的 **Applications (应用程序)** 文件夹。
3. 从“应用程序”启动 **MacMic**。
4. **如果打开时系统提示“已损坏，移到废纸篓”或“无法验证开发者”**：
   - 打开 **终端 (Terminal)**，执行以下命令解除安全隔离拦截：
     ```bash
     xattr -cr /Applications/MacMic.app
     ```
   - 或者在“访达 -> 应用程序”中右键（或按住 Control 键）点击 `MacMic.app`，选择 **打开**。
```

---

### 4.2 Initial Release (v1.0.0) Specific Note

```markdown
## English

### ⚠️ Known Issues
- Audio clarity and sound quality may be slightly muffled or less crisp depending on the mobile device's built-in microphone and network conditions.

### 📦 Installation & Gatekeeper Troubleshooting
1. Download `MacMic-v1.0.0-arm64.dmg` below.
2. Open the DMG and drag **MacMic.app** into your **Applications** folder.
3. Launch **MacMic** from Applications.
4. **If macOS displays "MacMic is damaged and can't be opened" or "Cannot verify developer"**:
   - Open **Terminal** and run the following command:
     ```bash
     xattr -cr /Applications/MacMic.app
     ```
   - Alternatively, right-click (or Control-click) `MacMic.app` in `/Applications` and select **Open**.

---

## 简体中文

### ⚠️ 已知问题
- 当前版本受手机端麦克风硬件采集及网络传输环境影响，音频清晰度可能略有不足，声音听起来可能略显发闷。

### 📦 安装与故障排查
1. 下载下方的 `MacMic-v1.0.0-arm64.dmg` 安装包。
2. 双击打开 DMG 文件，将 **MacMic.app** 拖入右侧的 **Applications (应用程序)** 文件夹。
3. 从“应用程序”启动 **MacMic**。
4. **如果打开时系统提示“已损坏，移到废纸篓”或“无法验证开发者”**：
   - 打开 **终端 (Terminal)**，执行以下命令解除 macOS Gatekeeper 安全隔离拦截：
     ```bash
     xattr -cr /Applications/MacMic.app
     ```
   - 或者在“访达 -> 应用程序”中右键（或按住 Control 键）点击 `MacMic.app`，选择 **打开**。
```

---

## 5. Automated Build & Release Packaging Commands

To build and publish a release via CLI:

```bash
# 1. Build the native application bundle
./build_app.sh

# 2. Package into a clean DMG with Applications symlink
rm -rf dmg_staging MacMic-v1.0.0-arm64.dmg
mkdir -p dmg_staging
cp -R MacMic.app dmg_staging/
ln -s /Applications dmg_staging/Applications
hdiutil create -volname "MacMic" -srcfolder dmg_staging -ov -format UDZO MacMic-v1.0.0-arm64.dmg
rm -rf dmg_staging

# 3. Create GitHub Release with DMG ONLY (never attach zip)
gh release create v1.0.0 MacMic-v1.0.0-arm64.dmg --title "MacMic v1.0.0" --notes-file release_notes.md
```

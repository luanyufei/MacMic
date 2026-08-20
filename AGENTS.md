# AGENTS.md - Developer & AI Maintenance Guide

This document covers the technical architecture, development constraints, and release standards for **MacMic**. Any AI agent or developer working on this repository should follow these instructions.

---

## 1. Project Overview & Architecture

**MacMic** is an unofficial macOS native audio client for Apple Silicon (macOS 12.0+), built to work with the **WO Mic** mobile app protocol (iOS & Android). It receives audio from your phone over Wi-Fi or USB and feeds it into a virtual audio device (like **BlackHole 2ch**), turning your phone into a Mac microphone.

### 1.1 Tech Stack
- **App**: Pure Swift 5.7+ with SwiftUI
- **Audio Decoding**: C `libopus` (statically linked from Homebrew `opus`)
- **Audio Output**: macOS CoreAudio (`AudioQueue`)
- **Device Management**: CoreAudio HAL APIs
- **Android USB**: Bridges to local ADB CLI (`adb forward tcp:8125 tcp:8125`)
- **System Integration**: Menu bar status item (`NSStatusItem`), `SMAppService` for launch-at-login, 9-language i18n (`Localization.swift`)

### 1.2 Codebase Layout
```text
├── swift-src/
│   ├── main.swift                 # Entry point, app delegate, window styling & hide-on-close logic
│   ├── ContentView.swift          # Main UI, connection controls, logarithmic dB VU meter
│   ├── ViewModel.swift            # State management & event coordination
│   ├── WOMicClient.swift          # Protocol handshake (TCP/UDP) & packet parsing
│   ├── AudioEngine.swift          # AudioQueue playback & real-time dB peak metering
│   ├── OpusDecoder.swift          # C libopus wrapper (48kHz, mono/stereo)
│   ├── AudioDeviceManager.swift   # Audio output device enumeration & BlackHole detection
│   ├── ADBHelper.swift            # Android ADB detection & port forwarding
│   ├── MenuBarManager.swift       # Menu bar icon, popover & background state
│   ├── SettingsView.swift         # Language picker & launch-at-login toggle
│   ├── Localization.swift         # 9-language string tables & runtime language switcher
│   ├── LaunchAtLoginHelper.swift  # SMAppService integration
│   ├── module.modulemap           # Clang module map for C libopus headers
│   └── test_opus.swift            # Opus decoder test script
├── assets/                        # Documentation images & UI screenshots
├── WOMic.iconset/                 # App icon PNG assets
├── AppIcon.icns                   # Compiled macOS app icon
├── build_app.sh                   # Build script (Swift compilation + static linking + codesign)
├── README.md                      # English documentation
├── README_ZH.md                   # Chinese documentation
├── LICENSE                        # MIT License
└── .gitignore                     # Exclusion rules
```

---

## 2. Key Development Rules

1. **Zero Runtime Dependencies**:
   - The compiled app must stay a standalone `.app` bundle. `libopus.a` is statically linked into the Mach-O binary. Do not introduce external dynamic libraries or runtime package managers that require user setup.
2. **Audio Output Default**:
   - Always prioritize **BlackHole 2ch** so third-party apps (Zoom, Teams, WeChat, OBS, etc.) can pick up the microphone input.
3. **Window Close Behavior**:
   - Closing the main window must hide it to the menu bar instead of terminating the app, keeping audio streaming alive in the background.
4. **Multi-Language Support (9 Languages)**:
   - Any new user-facing text must be added to all 9 languages in `swift-src/Localization.swift` (`zh_Hans`, `zh_Hant`, `en`, `ja`, `ko`, `es`, `fr`, `ru`, `de`).
5. **Git Cleanliness**:
   - Never commit `.app` bundles, `.dmg` files, `.DS_Store`, build logs, or reverse-engineering dumps (`android/`, `windows/`).

---

## 3. Release Publication Rules

Every GitHub Release must follow these rules without exception:

### 3.1 Assets
- **Only `.dmg` files are allowed.**
- Never upload `.zip`, `.tar.gz`, or raw binaries.
- Naming format: `MacMic-v<version>-arm64.dmg` (e.g., `MacMic-v1.0.0-arm64.dmg`).

### 3.2 Content & Language Order
- **English first, then Chinese.** Do not mix English and Chinese within the same section.
- Section ordering:
  1. `### 🚀 New Features` / `### 🚀 新特性`
  2. `### 🐛 Bug Fixes` / `### 🐛 问题修复`
  3. `### ⚠️ Known Issues` / `### ⚠️ 已知问题`
  4. `### 📦 Installation & Gatekeeper Troubleshooting` / `### 📦 安装与故障排查`

*(For v1.0.0 initial release: omit New Features and Bug Fixes, keep only Known Issues and Installation.)*

### 3.3 Gatekeeper Instructions
Because the binary is ad-hoc signed without a paid Apple Developer ID certificate, macOS may warn that the file is damaged or cannot be verified. Every release note must include the `xattr -cr` command to help users clear the quarantine flag.

---

## 4. Release Note Templates

### 4.1 General Template (Future Releases)

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
1. Download the `.dmg` file below.
2. Open the DMG and drag **MacMic.app** into your **Applications** folder.
3. Open **MacMic** from Applications.
4. **If macOS says the app is damaged or cannot verify the developer**:
   - Open **Terminal** and run:
     ```bash
     xattr -cr /Applications/MacMic.app
     ```
   - Or right-click `MacMic.app` in `/Applications` and select **Open**.

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
2. 双击打开 DMG，把 **MacMic.app** 拖到右边的 **Applications (应用程序)** 文件夹。
3. 从“应用程序”启动 **MacMic**。
4. **如果打开时提示“已损坏，移到废纸篓”或“无法验证开发者”**：
   - 打开**终端**，运行以下命令清除隔离属性：
     ```bash
     xattr -cr /Applications/MacMic.app
     ```
   - 也可以在“访达 -> 应用程序”中右键点击 `MacMic.app`，选择**打开**。
```

---

### 4.2 Initial Release (v1.0.0) Template

```markdown
## English

### ⚠️ Known Issues
- Audio clarity and sound quality may be slightly muffled or less crisp depending on the mobile device's built-in microphone and network conditions.

### 📦 Installation & Gatekeeper Troubleshooting
1. Download `MacMic-v1.0.0-arm64.dmg` below.
2. Open the DMG and drag **MacMic.app** into your **Applications** folder.
3. Open **MacMic** from Applications.
4. **If macOS says the app is damaged or cannot verify the developer**:
   - Open **Terminal** and run:
     ```bash
     xattr -cr /Applications/MacMic.app
     ```
   - Or right-click `MacMic.app` in `/Applications` and select **Open**.

---

## 简体中文

### ⚠️ 已知问题
- 声音可能会有些发闷或不够清晰，主要受手机自带麦克风和网络传输质量影响。

### 📦 安装与故障排查
1. 下载下方的 `MacMic-v1.0.0-arm64.dmg` 安装包。
2. 双击打开 DMG，把 **MacMic.app** 拖到右边的 **Applications (应用程序)** 文件夹。
3. 从“应用程序”启动 **MacMic**。
4. **如果打开时提示“已损坏，移到废纸篓”或“无法验证开发者”**：
   - 打开**终端**，运行以下命令清除隔离属性：
     ```bash
     xattr -cr /Applications/MacMic.app
     ```
   - 也可以在“访达 -> 应用程序”中右键点击 `MacMic.app`，选择**打开**。
```

---

## 5. Build & Packaging Commands

```bash
# 1. Build native app bundle
./build_app.sh

# 2. Package DMG with Applications symlink
rm -rf dmg_staging MacMic-v1.0.0-arm64.dmg
mkdir -p dmg_staging
cp -R MacMic.app dmg_staging/
ln -s /Applications dmg_staging/Applications
hdiutil create -volname "MacMic" -srcfolder dmg_staging -ov -format UDZO MacMic-v1.0.0-arm64.dmg
rm -rf dmg_staging

# 3. Create GitHub Release (DMG only, never attach zip)
gh release create v1.0.0 MacMic-v1.0.0-arm64.dmg --title "MacMic v1.0.0" --notes-file release_notes.md
```

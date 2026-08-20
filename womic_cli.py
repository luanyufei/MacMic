"""
WO Mic CLI Client for macOS (Apple Silicon arm64).
Usage:
    python3 womic_cli.py --wifi 192.168.1.100
    python3 womic_cli.py --usb
    python3 womic_cli.py --list-devices
"""

import argparse
import sys
import time
import signal
from womic_protocol import WOMicClient, ConnectionState
from womic_audio import AudioOutputEngine
from womic_adb import ADBManager


def main():
    parser = argparse.ArgumentParser(description="WO Mic Client for macOS (Apple Silicon)")
    parser.add_argument("--wifi", type=str, metavar="IP", help="Connect via Wi-Fi with phone IP (e.g. 192.168.1.100)")
    parser.add_argument("--usb", action="store_true", help="Connect via USB cable (ADB)")
    parser.add_argument("--wifidirect", type=str, default="192.168.49.1", metavar="IP", nargs="?", help="Connect via Wi-Fi Direct (default 192.168.49.1)")
    parser.add_argument("--device", type=int, default=None, help="Audio output device ID (run --list-devices to see)")
    parser.add_argument("--gain", type=float, default=1.0, help="Volume gain multiplier (1.0 = 100%)")
    parser.add_argument("--list-devices", action="store_true", help="List available audio output devices")

    args = parser.parse_args()

    if args.list_devices:
        print("=== Available Output Audio Devices on macOS ===")
        devs = AudioOutputEngine.get_output_devices()
        for d in devs:
            flag = " [RECOMMENDED VIRTUAL MIC]" if d["is_blackhole"] else ""
            print(f"  ID {d["id"]}: {d["name"]} ({d["channels"]}ch, {d["default_samplerate"]}Hz){flag}")
        return

    host = None
    is_tcp = False

    if args.usb:
        print("🔍 Checking connected Android devices via ADB...")
        devices = ADBManager.list_devices()
        if not devices:
            print("❌ No ADB devices detected! Please ensure USB Debugging is ON and cable is connected.")
            sys.exit(1)
        print(f"✅ Found device: {devices[0]["serial"]}")
        print("🔌 Forwarding port tcp:8125...")
        if not ADBManager.forward_port(8125, 8125):
            print("❌ Failed to forward ADB port!")
            sys.exit(1)
        host = "127.0.0.1"
        is_tcp = True
    elif args.wifi:
        host = args.wifi
        is_tcp = False
    elif args.wifidirect:
        host = args.wifidirect
        is_tcp = False
    else:
        parser.print_help()
        sys.exit(0)

    print("🎧 Initializing CoreAudio Output Engine...")
    audio = AudioOutputEngine(sample_rate=48000, channels=1)
    audio.set_gain(args.gain)
    audio.start(args.device)
    print(f"🔊 Audio routed to: {audio.device_name} (Gain: {int(args.gain * 100)}%)")

    def on_state(state, detail):
        print(f"[{state}] {detail}")

    client = WOMicClient(
        host=host,
        control_port=8125,
        media_port=8125,
        is_tcp_media=is_tcp,
        audio_engine=audio,
        on_state_change=on_state
    )

    def handle_sigint(sig, frame):
        print("\n🛑 Stopping WO Mic client...")
        client.disconnect()
        audio.stop()
        if is_tcp:
            ADBManager.remove_forward(8125)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    print(f"🚀 Connecting to WO Mic server at {host}:8125...")
    success = client.connect()
    if not success:
        print("❌ Connection failed.")
        sys.exit(1)

    print("🎙️ WO Mic is STREAMING! Speak into your phone. Press Ctrl+C to stop.")
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()

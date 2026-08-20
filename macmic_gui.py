"""
MacMic GUI Client for macOS (Apple Silicon arm64 Native).
Modern, elegant interface styled with native macOS aesthetics.
Supports Wi-Fi, USB (ADB), Wi-Fi Direct, dynamic VU level meter, gain slider, and device routing.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import socket

from macmic_protocol import MacMicClient, ConnectionState, DEFAULT_CONTROL_PORT, DEFAULT_MEDIA_PORT
from macmic_audio import AudioOutputEngine
from macmic_adb import ADBManager


class ModernMacMicApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MacMic (Apple Silicon)")
        self.root.geometry("480x640")
        self.root.minsize(440, 580)
        self.root.configure(bg="#1E1E24")

        # Initialize audio engine & client
        self.audio_engine = AudioOutputEngine(sample_rate=48000, channels=1)
        self.client = None
        self.is_connected = False
        self.meter_running = True

        # Styles
        self.setup_styles()

        # Build UI
        self.create_widgets()

        # Start background timers
        self.update_devices()
        self.update_vu_meter()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Configure custom colors
        self.c_bg = "#1E1E24"
        self.c_card = "#2B2B36"
        self.c_card_border = "#3D3D4E"
        self.c_accent = "#0A84FF"
        self.c_accent_hover = "#409CFF"
        self.c_green = "#30D158"
        self.c_red = "#FF453A"
        self.c_text = "#FFFFFF"
        self.c_text_dim = "#A0A0B0"

        style.configure("TFrame", background=self.c_bg)
        style.configure("Card.TFrame", background=self.c_card, relief="flat")
        style.configure("TLabel", background=self.c_bg, foreground=self.c_text, font=("SF Pro Display", 11))
        style.configure("Card.TLabel", background=self.c_card, foreground=self.c_text, font=("SF Pro Display", 11))
        style.configure("Dim.TLabel", background=self.c_card, foreground=self.c_text_dim, font=("SF Pro Text", 10))
        style.configure("Title.TLabel", background=self.c_bg, foreground=self.c_text, font=("SF Pro Display", 18, "bold"))
        style.configure("Status.TLabel", background=self.c_card, foreground=self.c_text_dim, font=("SF Pro Text", 11, "bold"))

        style.configure("TCombobox", fieldbackground="#383848", background="#383848", foreground="#FFFFFF", arrowcolor="#FFFFFF")
        style.map("TCombobox", fieldbackground=[("readonly", "#383848")], foreground=[("readonly", "#FFFFFF")])

        style.configure("TProgressbar", thickness=8, troughcolor="#1A1A22", background=self.c_green)

    def create_widgets(self):
        # Header
        header_frame = tk.Frame(self.root, bg=self.c_bg)
        header_frame.pack(fill="x", padx=20, pady=(18, 10))

        title_lbl = tk.Label(
            header_frame,
            text="🎙️ WO Mic Client",
            font=("SF Pro Display", 20, "bold"),
            bg=self.c_bg,
            fg=self.c_text
        )
        title_lbl.pack(side="left")

        arch_badge = tk.Label(
            header_frame,
            text=" Apple Silicon (arm64) ",
            font=("SF Pro Text", 9, "bold"),
            bg="#0F3860",
            fg="#64D2FF",
            padx=6,
            pady=2
        )
        arch_badge.pack(side="right")

        # 1. Connection Mode Card
        card1 = tk.Frame(self.root, bg=self.c_card, padx=16, pady=14, highlightbackground=self.c_card_border, highlightthickness=1)
        card1.pack(fill="x", padx=20, pady=8)

        card1_title = tk.Label(card1, text="连接传输方式 (Transport)", font=("SF Pro Display", 12, "bold"), bg=self.c_card, fg=self.c_text)
        card1_title.pack(anchor="w", pady=(0, 10))

        self.transport_var = tk.StringVar(value="wifi")
        modes_frame = tk.Frame(card1, bg=self.c_card)
        modes_frame.pack(fill="x", pady=(0, 10))

        rb_wifi = tk.Radiobutton(
            modes_frame, text="Wi-Fi", variable=self.transport_var, value="wifi",
            bg=self.c_card, fg=self.c_text, selectcolor="#383848", activebackground=self.c_card,
            activeforeground=self.c_text, command=self.on_transport_change, font=("SF Pro Text", 11)
        )
        rb_wifi.pack(side="left", padx=(0, 15))

        rb_usb = tk.Radiobutton(
            modes_frame, text="USB (ADB)", variable=self.transport_var, value="usb",
            bg=self.c_card, fg=self.c_text, selectcolor="#383848", activebackground=self.c_card,
            activeforeground=self.c_text, command=self.on_transport_change, font=("SF Pro Text", 11)
        )
        rb_usb.pack(side="left", padx=(0, 15))

        rb_wifidirect = tk.Radiobutton(
            modes_frame, text="Wi-Fi Direct", variable=self.transport_var, value="wifidirect",
            bg=self.c_card, fg=self.c_text, selectcolor="#383848", activebackground=self.c_card,
            activeforeground=self.c_text, command=self.on_transport_change, font=("SF Pro Text", 11)
        )
        rb_wifidirect.pack(side="left")

        # IP Address Entry
        self.ip_frame = tk.Frame(card1, bg=self.c_card)
        self.ip_frame.pack(fill="x", pady=(0, 5))

        self.ip_lbl = tk.Label(self.ip_frame, text="手机 IP 地址:", bg=self.c_card, fg=self.c_text_dim, font=("SF Pro Text", 10))
        self.ip_lbl.pack(side="left", padx=(0, 8))

        self.ip_entry = tk.Entry(self.ip_frame, bg="#383848", fg="#FFFFFF", insertbackground="#FFFFFF", font=("SF Mono", 11), relief="flat", highlightthickness=1, highlightbackground="#484858")
        self.ip_entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 5))

        # 2. Audio Device Card
        card2 = tk.Frame(self.root, bg=self.c_card, padx=16, pady=14, highlightbackground=self.c_card_border, highlightthickness=1)
        card2.pack(fill="x", padx=20, pady=8)

        card2_title = tk.Label(card2, text="音频输出目标 (Audio Routing)", font=("SF Pro Display", 12, "bold"), bg=self.c_card, fg=self.c_text)
        card2_title.pack(anchor="w", pady=(0, 8))

        tip_lbl = tk.Label(card2, text="💡 选 BlackHole 2ch 可作为系统全局虚拟麦克风", bg=self.c_card, fg="#FFD60A", font=("SF Pro Text", 9))
        tip_lbl.pack(anchor="w", pady=(0, 6))

        self.dev_combo = ttk.Combobox(card2, state="readonly", font=("SF Pro Text", 10))
        self.dev_combo.pack(fill="x", pady=(0, 10))
        self.dev_combo.bind("<<ComboboxSelected>>", self.on_device_selected)

        # Volume / Gain Slider & Mute
        vol_frame = tk.Frame(card2, bg=self.c_card)
        vol_frame.pack(fill="x", pady=(0, 5))

        vol_lbl = tk.Label(vol_frame, text="音量增益:", bg=self.c_card, fg=self.c_text_dim, font=("SF Pro Text", 10))
        vol_lbl.pack(side="left", padx=(0, 5))

        self.gain_val_lbl = tk.Label(vol_frame, text="100%", bg=self.c_card, fg=self.c_text, font=("SF Mono", 10, "bold"), width=5)
        self.gain_val_lbl.pack(side="right")

        self.gain_slider = tk.Scale(
            vol_frame, from_=0, to=200, orient="horizontal", bg=self.c_card, fg=self.c_text,
            troughcolor="#1A1A22", highlightthickness=0, showvalue=0, command=self.on_gain_changed
        )
        self.gain_slider.set(100)
        self.gain_slider.pack(side="left", fill="x", expand=True, padx=5)

        self.mute_var = tk.BooleanVar(value=False)
        self.mute_chk = tk.Checkbutton(
            card2, text="一键静音 (Mute)", variable=self.mute_var, bg=self.c_card, fg=self.c_text,
            selectcolor="#383848", activebackground=self.c_card, activeforeground=self.c_text,
            command=self.on_mute_toggled, font=("SF Pro Text", 10)
        )
        self.mute_chk.pack(anchor="w", pady=(4, 0))

        # 3. Audio Monitor & VU Meter Card
        card3 = tk.Frame(self.root, bg=self.c_card, padx=16, pady=12, highlightbackground=self.c_card_border, highlightthickness=1)
        card3.pack(fill="x", padx=20, pady=8)

        card3_title = tk.Label(card3, text="实时音频电平 (VU Meter)", font=("SF Pro Display", 12, "bold"), bg=self.c_card, fg=self.c_text)
        card3_title.pack(anchor="w", pady=(0, 6))

        self.vu_canvas = tk.Canvas(card3, height=14, bg="#181820", highlightthickness=1, highlightbackground="#383848")
        self.vu_canvas.pack(fill="x", pady=4)

        # 4. Status Bar & Action Button
        self.status_card = tk.Frame(self.root, bg="#242430", padx=16, pady=10, highlightbackground=self.c_card_border, highlightthickness=1)
        self.status_card.pack(fill="x", padx=20, pady=(10, 15))

        self.status_dot = tk.Label(self.status_card, text="●", fg=self.c_red, bg="#242430", font=("SF Pro Text", 14))
        self.status_dot.pack(side="left", padx=(0, 8))

        self.status_text = tk.Label(self.status_card, text="未连接 (Disconnected)", fg=self.c_text_dim, bg="#242430", font=("SF Pro Text", 11))
        self.status_text.pack(side="left", fill="x", expand=True, anchor="w")

        # Connect / Disconnect Button
        self.btn_connect = tk.Button(
            self.root, text="连 接 (Connect)", bg=self.c_accent, fg="#FFFFFF", activebackground=self.c_accent_hover,
            activeforeground="#FFFFFF", font=("SF Pro Display", 13, "bold"), relief="flat", cursor="pointinghand",
            command=self.toggle_connection
        )
        self.btn_connect.pack(fill="x", padx=20, pady=(0, 15), ipady=8)

    def on_transport_change(self):
        mode = self.transport_var.get()
        if mode == "wifi":
            self.ip_lbl.config(text="手机 IP 地址:")
            self.ip_entry.config(state="normal")
            if self.ip_entry.get() in ("127.0.0.1", "192.168.49.1"):
                self.ip_entry.delete(0, tk.END)
                self.ip_entry.insert(0, "192.168.1.100")
        elif mode == "usb":
            self.ip_lbl.config(text="USB 模式 (ADB 本地转发):")
            self.ip_entry.delete(0, tk.END)
            self.ip_entry.insert(0, "127.0.0.1")
            self.ip_entry.config(state="disabled")
        elif mode == "wifidirect":
            self.ip_lbl.config(text="Wi-Fi Direct 热点网关:")
            self.ip_entry.config(state="normal")
            self.ip_entry.delete(0, tk.END)
            self.ip_entry.insert(0, "192.168.49.1")

    def update_devices(self):
        devices = AudioOutputEngine.get_output_devices()
        self.devices_map = {f"[{d[id]}] {d[name]}": d[id] for d in devices}
        self.dev_combo["values"] = list(self.devices_map.keys())

        # Select BlackHole or default
        def_dev = AudioOutputEngine.get_default_device()
        if def_dev:
            target_key = f"[{def_dev[id]}] {def_dev[name]}"
            if target_key in self.devices_map:
                self.dev_combo.set(target_key)
                self.audio_engine.device_index = def_dev[id]

    def on_device_selected(self, event=None):
        selected_key = self.dev_combo.get()
        if selected_key in self.devices_map:
            dev_id = self.devices_map[selected_key]
            self.audio_engine.device_index = dev_id
            if self.audio_engine.is_running:
                self.audio_engine.start(dev_id)

    def on_gain_changed(self, val):
        gain_percent = int(val)
        self.gain_val_lbl.config(text=f"{gain_percent}%")
        self.audio_engine.set_gain(gain_percent / 100.0)

    def on_mute_toggled(self):
        self.audio_engine.set_muted(self.mute_var.get())

    def update_vu_meter(self):
        if not self.meter_running:
            return
        
        # Draw VU level
        rms = self.audio_engine.current_rms
        peak = self.audio_engine.current_peak
        
        self.vu_canvas.delete("all")
        width = self.vu_canvas.winfo_width()
        height = self.vu_canvas.winfo_height()
        
        if width > 1:
            level_w = int(width * min(1.0, peak * 2.0))
            if level_w > 0:
                # Color based on level: Green -> Yellow -> Red
                color = self.c_green
                if peak > 0.7:
                    color = self.c_red
                elif peak > 0.4:
                    color = "#FFD60A"
                self.vu_canvas.create_rectangle(0, 0, level_w, height, fill=color, outline="")

        self.root.after(40, self.update_vu_meter)

    def on_state_change(self, state: str, detail: str = ""):
        self.root.after(0, self._handle_state_update, state, detail)

    def _handle_state_update(self, state: str, detail: str):
        if state == ConnectionState.STREAMING:
            self.status_dot.config(fg=self.c_green)
            self.status_text.config(text=f"已连接 - 麦克风工作正常 ({detail})", fg=self.c_green)
            self.btn_connect.config(text="断 开 连 接 (Disconnect)", bg=self.c_red, state="normal")
            self.is_connected = True
        elif state == ConnectionState.CONNECTING:
            self.status_dot.config(fg="#FFD60A")
            self.status_text.config(text=f"正在连接中... {detail}", fg="#FFD60A")
            self.btn_connect.config(text="连接中...", state="disabled")
        elif state == ConnectionState.ERROR:
            self.status_dot.config(fg=self.c_red)
            self.status_text.config(text=f"错误: {detail}", fg=self.c_red)
            self.btn_connect.config(text="连 接 (Connect)", bg=self.c_accent, state="normal")
            self.is_connected = False
        else:
            self.status_dot.config(fg=self.c_red)
            self.status_text.config(text="未连接 (Disconnected)", fg=self.c_text_dim)
            self.btn_connect.config(text="连 接 (Connect)", bg=self.c_accent, state="normal")
            self.is_connected = False

    def toggle_connection(self):
        if self.is_connected:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        mode = self.transport_var.get()
        host = self.ip_entry.get().strip()
        is_tcp = (mode == "usb")

        if mode == "usb":
            # Check ADB devices
            devices = ADBManager.list_devices()
            if not devices:
                messagebox.showerror(
                    "USB 模式错误",
                    "未检测到 USB 连接的 Android 设备！
请确保已开启手机的【USB 调试】并用数据线连接 Mac。"
                )
                return
            # Forward port 8125
            if not ADBManager.forward_port(local_port=8125, remote_port=8125):
                messagebox.showerror("ADB 错误", "ADB 端口转发失败！")
                return
            host = "127.0.0.1"

        if not host:
            messagebox.showwarning("提示", "请输入手机 IP 地址！")
            return

        # Prepare client
        self.client = MacMicClient(
            host=host,
            control_port=DEFAULT_CONTROL_PORT,
            media_port=DEFAULT_MEDIA_PORT,
            is_tcp_media=is_tcp,
            audio_engine=self.audio_engine,
            on_state_change=self.on_connection_state_change
        )
        self.client.connect()

    def disconnect(self):
        if self.client:
            self.client.disconnect()
            self.client = None
        self.audio_engine.stop()
        self.is_connected = False
        self.status_var.set("Disconnected")
        self.btn_connect.config(text="Connect", bg="#0A84FF")
        self.lbl_status_icon.config(text="⚪")

    def on_closing(self):
        self.disconnect()
        self.meter_running = False
        self.root.destroy()


def main():
    root = tk.Tk()
    app = ModernMacMicApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()

"""
WO Mic Audio Output Engine for macOS.
Manages playback to Virtual Mic (BlackHole) or Speakers with volume, mute, and VU meter support.
"""

import sounddevice as sd
import numpy as np
import threading
import queue
import time


class AudioOutputEngine:
    """Audio player that outputs 48000Hz PCM stream to CoreAudio devices."""

    def __init__(self, sample_rate: int = 48000, channels: int = 1, block_size: int = 480):
        self.sample_rate = sample_rate
        self.channels = channels
        self.block_size = block_size  # e.g. 10ms at 48000Hz = 480 samples
        self.stream = None
        self.device_index = None
        self.device_name = ""
        self.is_running = False
        
        # Audio controls
        self.gain = 1.0        # 0.0 to 2.0 (1.0 = 100% standard calibrated volume)
        self.is_muted = False
        self.baseline_calibration = 4.0  # +12dB standard PC mic level calibration
        
        # VU meter levels (0.0 to 1.0)
        self.current_rms = 0.0
        self.current_peak = 0.0
        
        # DSP Filter state (Biquad HPF & Peaking EQ)
        # 80Hz Low-Cut (48000Hz, Q=0.707)
        self._hp_b0 = 0.99262144
        self._hp_b1 = -1.98524288
        self._hp_b2 = 0.99262144
        self._hp_a1 = -1.98518845
        self._hp_a2 = 0.98529731
        self._hp_x1 = 0.0
        self._hp_x2 = 0.0
        self._hp_y1 = 0.0
        self._hp_y2 = 0.0

        # 3.2kHz Peaking EQ (+3.0dB, Q=0.8)
        self._eq_b0 = 1.07168925
        self._eq_b1 = -1.51271430
        self._eq_b2 = 0.58418270
        self._eq_a1 = -1.51271430
        self._eq_a2 = 0.65587195
        self._eq_x1 = 0.0
        self._eq_x2 = 0.0
        self._eq_y1 = 0.0
        self._eq_y2 = 0.0
        
        # Ring buffer / queue for decoded PCM
        self._queue = queue.Queue(maxsize=100)
        self._lock = threading.Lock()

    @staticmethod
    def get_output_devices():
        """Returns a list of available output audio devices on macOS."""
        devices = []
        try:
            dev_list = sd.query_devices()
            for idx, dev in enumerate(dev_list):
                if dev["max_output_channels"] > 0:
                    devices.append({
                        "id": idx,
                        "name": dev["name"],
                        "channels": dev["max_output_channels"],
                        "default_samplerate": int(dev["default_samplerate"]),
                        "is_blackhole": "blackhole" in dev["name"].lower() or "virtual" in dev["name"].lower()
                    })
        except Exception as e:
            print(f"Error querying audio devices: {e}")
        return devices

    @staticmethod
    def get_default_device():
        """Finds BlackHole 2ch if present, otherwise system default output."""
        devices = AudioOutputEngine.get_output_devices()
        # Prefer BlackHole for virtual microphone use
        for dev in devices:
            if "blackhole 2ch" in dev["name"].lower():
                return dev
        for dev in devices:
            if dev["is_blackhole"]:
                return dev
        # Fallback to system default
        try:
            default_out = sd.default.device[1]
            for dev in devices:
                if dev["id"] == default_out:
                    return dev
        except Exception:
            pass
        return devices[0] if devices else None

    def start(self, device_id: int = None):
        """Starts the CoreAudio playback stream."""
        self.stop()
        
        if device_id is None:
            def_dev = self.get_default_device()
            self.device_index = def_dev["id"] if def_dev else None
            self.device_name = def_dev["name"] if def_dev else "Default"
        else:
            self.device_index = device_id
            try:
                info = sd.query_devices(device_id)
                self.device_name = info["name"]
            except Exception:
                self.device_name = f"Device {device_id}"

        # Determine target channels for device
        try:
            dev_info = sd.query_devices(self.device_index)
            max_ch = dev_info["max_output_channels"]
            out_channels = min(2, max_ch) if max_ch >= 2 else 1
        except Exception:
            out_channels = 1

        self._out_channels = out_channels
        self.is_running = True

        def callback(outdata, frames, time_info, status):
            if not self.is_running:
                outdata.fill(0)
                return
            
            try:
                data = self._queue.get_nowait()
            except queue.Empty:
                data = None

            if data is None or len(data) == 0:
                outdata.fill(0)
                self.current_rms = max(0.0, self.current_rms * 0.8)
                self.current_peak = max(0.0, self.current_peak * 0.8)
                return

            # Convert 16-bit PCM bytes to float32 numpy array
            audio_int16 = np.frombuffer(data, dtype=np.int16)
            audio_float = audio_int16.astype(np.float32) / 32768.0

            # Apply mute and gain
            if self.is_muted:
                audio_float.fill(0)
                self.current_rms = 0.0
                self.current_peak = 0.0
            else:
                effective_gain = self.gain * self.baseline_calibration

                # 1. 80Hz Low-Cut (High-Pass) Biquad filter
                for i in range(len(audio_float)):
                    s = audio_float[i]
                    y = (self._hp_b0 * s + self._hp_b1 * self._hp_x1 + self._hp_b2 * self._hp_x2 
                         - self._hp_a1 * self._hp_y1 - self._hp_a2 * self._hp_y2)
                    self._hp_x2, self._hp_x1 = self._hp_x1, s
                    self._hp_y2, self._hp_y1 = self._hp_y1, y
                    audio_float[i] = y

                # 2. 3.2kHz Vocal Presence Peaking filter
                for i in range(len(audio_float)):
                    s = audio_float[i]
                    y = (self._eq_b0 * s + self._eq_b1 * self._eq_x1 + self._eq_b2 * self._eq_x2 
                         - self._eq_a1 * self._eq_y1 - self._eq_a2 * self._eq_y2)
                    self._eq_x2, self._eq_x1 = self._eq_x1, s
                    self._eq_y2, self._eq_y1 = self._eq_y1, y
                    audio_float[i] = y

                # 3. Apply Calibrated Gain
                audio_float *= effective_gain

                # 4. Soft-Knee Studio Limiter (prevents harsh digital clipping)
                high_mask = audio_float > 0.85
                low_mask = audio_float < -0.85
                audio_float[high_mask] = 0.85 + 0.15 * np.tanh((audio_float[high_mask] - 0.85) / 0.15)
                audio_float[low_mask] = -0.85 + 0.15 * np.tanh((audio_float[low_mask] + 0.85) / 0.15)
                np.clip(audio_float, -1.0, 1.0, out=audio_float)
                
                # Calculate VU meter levels
                peak = float(np.max(np.abs(audio_float)))
                rms = float(np.sqrt(np.mean(audio_float ** 2)))
                self.current_peak = peak
                self.current_rms = rms

            # Adjust channels (Mono to Stereo if output device is 2-ch)
            if self._out_channels == 2:
                # Duplicate mono to stereo
                audio_out = np.column_stack((audio_float, audio_float))
            else:
                audio_out = audio_float.reshape(-1, 1)

            # Pad or truncate to match expected buffer frames
            if len(audio_out) < frames:
                pad = np.zeros((frames - len(audio_out), self._out_channels), dtype=np.float32)
                audio_out = np.vstack((audio_out, pad))
            elif len(audio_out) > frames:
                audio_out = audio_out[:frames]

            outdata[:] = audio_out

        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self._out_channels,
            dtype="float32",
            device=self.device_index,
            blocksize=self.block_size,
            latency="low",
            callback=callback
        )
        self.stream.start()

    def write_pcm(self, pcm_bytes: bytes):
        """Pushes raw 16-bit Mono PCM bytes to playback queue."""
        if not self.is_running or not pcm_bytes:
            return
        try:
            if self._queue.full():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass
            self._queue.put_nowait(pcm_bytes)
        except Exception:
            pass

    def set_gain(self, gain: float):
        """Sets volume gain (e.g. 1.0 = 100%, 2.0 = 200%, 5.0 = 500%)."""
        self.gain = max(0.0, min(gain, 5.0))

    def set_muted(self, muted: bool):
        """Mutes or unmutes playback."""
        self.is_muted = muted

    def stop(self):
        """Stops the stream."""
        self.is_running = False
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        # Clear queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self.current_rms = 0.0
        self.current_peak = 0.0

    def __del__(self):
        self.stop()

"""
MacMic Protocol Implementation for macOS.
Compatible with the WO Mic mobile app protocol.
Handles TCP control commands (handshake, codec params, audio capture) and UDP/TCP media streaming.
"""

import socket
import struct
import threading
import time
from typing import Callable, Optional
from macmic_opus import OpusDecoder
from macmic_audio import AudioOutputEngine


# Protocol Constants (Reverse Engineered from WOMicClient protocol)
PROTOCOL_VERSION_V4 = 4
CLIENT_MAJOR = 6
CLIENT_MINOR = 3
CLIENT_PATCH = 0

CMD_CHECK_VERSION = 0x65       # 101: Handshake and version check
CMD_SET_CODEC_PARAM = 0x66     # 102: Configure audio codec & client UDP port
CMD_START_CAPTURE = 0x67       # 103: Request server to start streaming audio
CMD_STOP_CAPTURE = 0x68        # 104: Stop audio capture / disconnect
CMD_HEARTBEAT = 0x69           # 105: Keepalive heartbeat poll (resets 5s timeout on server)

CODEC_OPUS = 0x02              # Opus audio codec ID
SAMPLE_RATE_INDEX_48K = 0x02   # Sample rate index: 0=8kHz, 1=16kHz, 2=48kHz
PROTOCOL_VERSION_V4_BE = 0x0400  # Protocol version 4 in big-endian 2-byte form (for UDP header)

# UDP Media Packet Header: 11 bytes total
# [proto_ver (2 BE)] [data_len (2 BE)] [seq (2 BE)] [timestamp (4 BE)] [flag (1)]
# data_len = opus_payload_size + 7 (seq + ts + flag fields)
UDP_MEDIA_HEADER_SIZE = 11

DEFAULT_CONTROL_PORT = 8125
DEFAULT_MEDIA_PORT = 8125


class ConnectionState:
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    STREAMING = "Streaming (Mic Active)"
    ERROR = "Error"


class MacMicClient:
    """
    MacMic Client implementation for macOS.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        control_port: int = DEFAULT_CONTROL_PORT,
        media_port: int = DEFAULT_MEDIA_PORT,
        is_tcp_media: bool = False,
        audio_engine: Optional[AudioOutputEngine] = None,
        on_state_change: Optional[Callable[[str, str], None]] = None,
    ):
        self.host = host
        self.control_port = control_port
        self.media_port = media_port
        self.is_tcp_media = is_tcp_media  # True for USB (ADB), False for Wi-Fi (UDP)
        
        self.audio_engine = audio_engine or AudioOutputEngine()
        self.decoder = None
        
        self.state = ConnectionState.DISCONNECTED
        self.on_state_change = on_state_change
        
        self._control_sock = None
        self._media_sock = None
        self._is_running = False
        
        self._worker_thread = None
        self._poll_thread = None
        self._last_seq = -1
        self._packets_received = 0
        self._bytes_received = 0
        self._last_packet_time = 0.0

    def _set_state(self, state: str, detail: str = ""):
        self.state = state
        if self.on_state_change:
            try:
                self.on_state_change(state, detail)
            except Exception:
                pass

    def connect(self, timeout: float = 5.0) -> bool:
        """Initiates connection to the WO Mic server."""
        self.disconnect()
        self._is_running = True
        self._packets_received = 0
        self._bytes_received = 0
        self._last_packet_time = time.time()
        self._set_state(ConnectionState.CONNECTING, f"Connecting to {self.host}:{self.control_port}...")

        try:
            # 1. Initialize Opus decoder
            self.decoder = OpusDecoder(sample_rate=48000, channels=1)
            
            # 2. Establish TCP Control socket
            self._control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._control_sock.settimeout(timeout)
            self._control_sock.connect((self.host, self.control_port))
            
            # 3. Handshake: Send Check Version (0x65)
            # Payload: [proto_ver(1), client_major(1), client_minor(1), 0, 0, 0]
            check_ver_payload = bytes([PROTOCOL_VERSION_V4, CLIENT_MAJOR, CLIENT_MINOR, 0, 0, 0])
            self._send_control_cmd(CMD_CHECK_VERSION, check_ver_payload)
            resp_type, resp_status, resp_data = self._read_control_response()
            if resp_type != CMD_CHECK_VERSION or resp_status != 0:
                raise ConnectionError(f"Version negotiation failed: type={resp_type}, status={resp_status}")

            # 4. Set Codec Parameters (0x66)
            # Payload: [codec(1), sampleRateIndex(1), clientMediaPort(4 BE)]
            # The server uses clientMediaPort to know where to send UDP audio data.
            codec_payload = bytes([CODEC_OPUS, SAMPLE_RATE_INDEX_48K]) + struct.pack(">I", self.media_port)
            self._send_control_cmd(CMD_SET_CODEC_PARAM, codec_payload)
            resp_type, resp_status, resp_data = self._read_control_response()
            if resp_type != CMD_SET_CODEC_PARAM or resp_status != 0:
                raise ConnectionError(f"Set codec parameter failed: type={resp_type}, status={resp_status}")

            # 5. Start Audio Capture (0x67)
            self._send_control_cmd(CMD_START_CAPTURE, b"")
            resp_type, resp_status, resp_data = self._read_control_response()
            if resp_type != CMD_START_CAPTURE or resp_status != 0:
                raise ConnectionError(f"Start audio capture failed: type={resp_type}, status={resp_status}")

            # 6. Start Audio Playback Stream
            if not self.audio_engine.is_running:
                self.audio_engine.start()

            # 7. Start Media Receiving Thread
            if self.is_tcp_media:
                # In USB/TCP mode, media is received over TCP
                self._worker_thread = threading.Thread(target=self._media_tcp_loop, daemon=True)
            else:
                # In Wi-Fi mode, media is received over UDP
                self._worker_thread = threading.Thread(target=self._media_udp_loop, daemon=True)
            
            self._worker_thread.start()

            # 8. Start Poll / Keepalive Thread (Sends 0x69 heartbeat every 2s)
            self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._poll_thread.start()

            self._set_state(ConnectionState.STREAMING, f"Mic active ({self.host})")
            return True

        except Exception as e:
            self.disconnect()
            self._set_state(ConnectionState.ERROR, str(e))
            return False

    def _send_control_cmd(self, cmd_type: int, payload: bytes):
        """Sends a structured control command frame."""
        # Header: [cmd_type (1 byte)] [payload_len (4 bytes BE)]
        header = struct.pack(">BI", cmd_type, len(payload))
        if self._control_sock:
            self._control_sock.sendall(header + payload)

    def _read_exact(self, sock: socket.socket, length: int) -> bytes:
        """Reads exactly `length` bytes from a socket."""
        buf = bytearray()
        while len(buf) < length:
            chunk = sock.recv(length - len(buf))
            if not chunk:
                raise ConnectionResetError("Connection closed by remote host")
            buf.extend(chunk)
        return bytes(buf)

    def _read_control_response(self) -> tuple[int, int, bytes]:
        """Reads a structured control response frame: (type, status, data)."""
        # Response header: [type (1 byte)] [length (4 bytes BE)]
        raw_header = self._read_exact(self._control_sock, 5)
        resp_type, length = struct.unpack(">BI", raw_header)
        if length > 0:
            status_byte = self._read_exact(self._control_sock, 1)[0]
            payload = self._read_exact(self._control_sock, length - 1) if length > 1 else b""
        else:
            status_byte = 0
            payload = b""
        return resp_type, status_byte, payload

    def _poll_loop(self):
        """Periodic heartbeat (0x69) to reset the server's 5-second disconnect timer."""
        while self._is_running:
            time.sleep(2.0)
            if not self._is_running:
                break
            try:
                # 1. Send periodic 0x69 heartbeat over TCP (no response expected)
                self._send_control_cmd(CMD_HEARTBEAT, b"")
                
                # 2. Also send periodic UDP ping to keep NAT/firewall open
                if not self.is_tcp_media and self._media_sock:
                    try:
                        self._media_sock.sendto(b"\x00\x04\x00\x00", (self.host, self.media_port))
                    except Exception:
                        pass
            except Exception as e:
                if self._is_running:
                    self.disconnect()
                    self._set_state(ConnectionState.ERROR, f"Connection lost: {e}")
                break

    def _media_udp_loop(self):
        """Receives UDP audio packets in Wi-Fi mode."""
        try:
            self._media_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._media_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Try to bind to local media port
            try:
                self._media_sock.bind(("0.0.0.0", self.media_port))
            except Exception:
                # If port already in use, bind to any available port
                self._media_sock.bind(("0.0.0.0", 0))

            self._media_sock.settimeout(2.0)

            # Send a trigger datagram to server so NAT / firewalls open the port
            self._media_sock.sendto(b"\x00\x04\x00\x00", (self.host, self.media_port))

            while self._is_running:
                try:
                    packet, addr = self._media_sock.recvfrom(2048)
                except socket.timeout:
                    continue
                except Exception:
                    break

                if not packet or len(packet) <= 7:
                    continue

                self._process_media_packet(packet)

        except Exception as e:
            if self._is_running:
                self._set_state(ConnectionState.ERROR, f"UDP Media stream error: {e}")

    def _media_tcp_loop(self):
        """Receives streaming audio packets over TCP in USB / ADB mode."""
        try:
            # Connect to local forwarded media port or control socket
            self._media_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._media_sock.settimeout(5.0)
            self._media_sock.connect((self.host, self.media_port))
            
            while self._is_running:
                # Read 11-byte stream frame header
                # Bytes 0-1: Protocol version (4)
                # Bytes 2-3: Total packet length
                # Bytes 4-5: Sequence number
                # Bytes 6-9: Timestamp
                # Byte 10: Flags
                header = self._read_exact(self._media_sock, 11)
                ver, total_len, seq, timestamp, flags = struct.unpack(">HHHIb", header)
                
                payload_len = total_len - 7
                if payload_len > 0:
                    payload = self._read_exact(self._media_sock, payload_len)
                    self._decode_and_play(payload)
                    
        except Exception as e:
            if self._is_running:
                self._set_state(ConnectionState.ERROR, f"TCP Media stream error: {e}")

    def _process_media_packet(self, packet: bytes):
        """Parses an 11-byte header UDP media packet and decodes Opus frame."""
        # Packet format (reverse-engineered from Android APK):
        # [proto_ver (2 BE)] [data_len (2 BE)] [seq (2 BE)] [timestamp (4 BE)] [flag (1)] [Opus payload]
        # data_len = len(seq + ts + flag + opus_payload) = opus_len + 7
        try:
            if len(packet) < UDP_MEDIA_HEADER_SIZE:
                return

            ver = struct.unpack(">H", packet[:2])[0]
            if ver != PROTOCOL_VERSION_V4_BE:
                return

            data_len = struct.unpack(">H", packet[2:4])[0]
            seq = struct.unpack(">H", packet[4:6])[0]
            timestamp = struct.unpack(">I", packet[6:10])[0]
            flag = packet[10]

            # Opus payload starts at byte 11
            payload = packet[UDP_MEDIA_HEADER_SIZE:]
            
            self._packets_received += 1
            self._bytes_received += len(payload)
            self._last_seq = seq
            
            self._decode_and_play(payload)

        except Exception:
            pass

    def _decode_and_play(self, opus_payload: bytes):
        """Decodes an Opus packet to PCM and passes to AudioOutputEngine."""
        if not opus_payload or not self.decoder:
            return
        try:
            pcm = self.decoder.decode(opus_payload)
            if pcm and self.audio_engine:
                self.audio_engine.write_pcm(pcm)
        except Exception:
            pass

    def disconnect(self):
        """Disconnects and cleans up resources."""
        self._is_running = False
        
        # Close sockets
        if self._control_sock:
            try:
                # Attempt to send Stop command
                try:
                    self._send_control_cmd(CMD_STOP_CAPTURE, b"")
                except Exception:
                    pass
                self._control_sock.shutdown(socket.SHUT_RDWR)
                self._control_sock.close()
            except Exception:
                pass
            self._control_sock = None

        if self._media_sock:
            try:
                self._media_sock.close()
            except Exception:
                pass
            self._media_sock = None

        # Clean up decoder
        if self.decoder:
            try:
                self.decoder.close()
            except Exception:
                pass
            self.decoder = None

        # Stop audio engine
        if self.audio_engine:
            self.audio_engine.stop()

        self._set_state(ConnectionState.DISCONNECTED, "Disconnected")

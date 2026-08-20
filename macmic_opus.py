"""
WO Mic Opus Decoder Wrapper using libopus.dylib via ctypes.
Decodes Opus frames from WO Mic to raw 16-bit PCM audio.
"""

import ctypes
import os
import sys

POSSIBLE_OPUS_PATHS = [
    "/opt/homebrew/opt/opus/lib/libopus.dylib",
    "/opt/homebrew/lib/libopus.dylib",
    "/usr/local/opt/opus/lib/libopus.dylib",
    "/usr/local/lib/libopus.dylib",
    "/opt/local/lib/libopus.dylib",
    "libopus.dylib",
    "libopus.0.dylib",
]

_opus_lib = None

for path in POSSIBLE_OPUS_PATHS:
    try:
        _opus_lib = ctypes.CDLL(path)
        break
    except OSError:
        continue

if _opus_lib is None:
    raise RuntimeError(
        "libopus.dylib not found. Please install opus via Homebrew: brew install opus"
    )

_opus_lib.opus_decoder_create.argtypes = [
    ctypes.c_int32,
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_int),
]
_opus_lib.opus_decoder_create.restype = ctypes.c_void_p

_opus_lib.opus_decode.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.c_int32,
    ctypes.POINTER(ctypes.c_int16),
    ctypes.c_int,
    ctypes.c_int,
]
_opus_lib.opus_decode.restype = ctypes.c_int

_opus_lib.opus_decoder_destroy.argtypes = [ctypes.c_void_p]
_opus_lib.opus_decoder_destroy.restype = None

_opus_lib.opus_strerror.argtypes = [ctypes.c_int]
_opus_lib.opus_strerror.restype = ctypes.c_char_p


class OpusDecoder:
    """Opus decoder instance for WO Mic stream."""

    def __init__(self, sample_rate: int = 48000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.max_frame_size = sample_rate // 10  # up to 100ms per frame
        err = ctypes.c_int(0)
        self._decoder = _opus_lib.opus_decoder_create(sample_rate, channels, ctypes.byref(err))
        if not self._decoder or err.value != 0:
            err_msg = _opus_lib.opus_strerror(err.value).decode("utf-8")
            raise RuntimeError(f"Failed to create Opus decoder: {err_msg} ({err.value})")

        self._out_buf = (ctypes.c_int16 * (self.max_frame_size * self.channels))()

    def decode(self, opus_bytes: bytes, fec: bool = False) -> bytes:
        """Decodes an Opus byte payload to 16-bit signed PCM audio bytes."""
        if opus_bytes:
            data_len = len(opus_bytes)
            c_data = (ctypes.c_uint8 * data_len).from_buffer_copy(opus_bytes)
            data_ptr = ctypes.cast(c_data, ctypes.POINTER(ctypes.c_uint8))
        else:
            data_len = 0
            data_ptr = None

        samples = _opus_lib.opus_decode(
            self._decoder,
            data_ptr,
            data_len,
            self._out_buf,
            self.max_frame_size,
            1 if fec else 0,
        )

        if samples < 0:
            err_msg = _opus_lib.opus_strerror(samples).decode("utf-8")
            raise ValueError(f"Opus decode error: {err_msg} ({samples})")

        total_bytes = samples * self.channels * 2
        return ctypes.string_at(ctypes.addressof(self._out_buf), total_bytes)

    def close(self):
        if self._decoder:
            _opus_lib.opus_decoder_destroy(self._decoder)
            self._decoder = None

    def __del__(self):
        self.close()

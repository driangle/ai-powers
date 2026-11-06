"""WAV and spectrogram PNG files, with numpy and the standard library only."""

from __future__ import annotations

import struct
import wave
import zlib
from pathlib import Path

import numpy as np

from .render import SAMPLE_RATE

LOW_HZ, HIGH_HZ, ROWS = 30.0, 16000.0, 256
FFT, HOP = 2048, SAMPLE_RATE // 100  # 10 ms per column
GUIDES_HZ = (100.0, 1000.0, 10000.0)
COLOURS = np.array([[0, 0, 4], [80, 18, 123], [182, 54, 121], [251, 136, 97], [252, 253, 191]], float)


def write_wav(path: Path, audio: np.ndarray) -> None:
    stereo = audio if audio.shape[0] == 2 else np.repeat(audio[:1], 2, axis=0)
    pcm = (np.clip(stereo.T, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(SAMPLE_RATE)
        out.writeframes(pcm.tobytes())


def write_png(path: Path, rgb: np.ndarray) -> None:
    height, width, _ = rgb.shape
    rows = b"".join(b"\x00" + rgb[y].astype(np.uint8).tobytes() for y in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def colourise(level: np.ndarray) -> np.ndarray:
    """0..1 -> dark purple to pale yellow."""
    position = level * (len(COLOURS) - 1)
    low = np.clip(position.astype(int), 0, len(COLOURS) - 2)
    frac = (position - low)[..., None]
    return COLOURS[low] * (1 - frac) + COLOURS[low + 1] * frac


def row_of(hz: float) -> int:
    return int(round((ROWS - 1) * (1 - np.log(hz / LOW_HZ) / np.log(HIGH_HZ / LOW_HZ))))


def spectrogram(audio: np.ndarray, marks_s: list[float] = ()) -> np.ndarray:
    """Time left to right, 30 Hz to 16 kHz bottom to top on a log scale, 90 dB of range.

    Dim lines at 100 Hz, 1 kHz and 10 kHz; white ticks along the top at marks_s.
    """
    x = np.concatenate([audio.mean(axis=0), np.zeros(FFT)])
    starts = range(0, max(len(x) - FFT, 1), HOP)
    frames = np.stack([x[s : s + FFT] * np.hanning(FFT) for s in starts])
    power = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    bins = np.geomspace(HIGH_HZ, LOW_HZ, ROWS) * FFT / SAMPLE_RATE
    image = np.stack([np.interp(bins, np.arange(power.shape[1]), col) for col in power], axis=1)
    db = 10 * np.log10(image + 1e-20)
    level = np.clip((db - (db.max() - 90)) / 90, 0, 1)
    rgb = colourise(level)
    for hz in GUIDES_HZ:
        rgb[row_of(hz), ::4] = 110
    for mark in marks_s:
        column = int(mark * SAMPLE_RATE / HOP)
        if 0 <= column < rgb.shape[1]:
            rgb[:6, column] = 255
    return rgb

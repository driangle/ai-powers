"""Measurements of rendered audio that stand in for listening.

All take (channels, samples) float arrays at SAMPLE_RATE and return plain
numbers or None, rounded for reading.
"""

from __future__ import annotations

import numpy as np

from .render import SAMPLE_RATE

HOP = SAMPLE_RATE // 200  # 5 ms envelope frames


def mono(audio: np.ndarray) -> np.ndarray:
    return audio.mean(axis=0) if audio.ndim == 2 else audio


def envelope(audio: np.ndarray) -> np.ndarray:
    x = mono(audio)
    frames = len(x) // HOP
    if frames == 0:
        return np.zeros(1)
    return np.sqrt(np.mean(x[: frames * HOP].reshape(frames, HOP) ** 2, axis=1))


def magnitude_spectrum(audio: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = mono(audio)
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    freqs = np.fft.rfftfreq(len(x), 1 / SAMPLE_RATE)
    band = (freqs >= 20) & (freqs <= 16000)
    return freqs[band], spectrum[band]


def centroid_hz(audio: np.ndarray) -> float | None:
    """Magnitude-weighted mean frequency: how bright it sounds."""
    freqs, magnitude = magnitude_spectrum(audio)
    total = magnitude.sum()
    return round(float((freqs * magnitude).sum() / total)) if total > 0 else None


def flatness(audio: np.ndarray) -> float | None:
    """0 for a pure tone, 1 for white noise."""
    _, magnitude = magnitude_spectrum(audio)
    power = magnitude**2
    power = power[power > 0]
    if power.size == 0:
        return None
    return round(float(np.exp(np.mean(np.log(power))) / np.mean(power)), 3)


def pitch_hz(audio: np.ndarray) -> float | None:
    """Fundamental by autocorrelation over 30 Hz-2 kHz, or None when nothing repeats clearly."""
    x = mono(audio) - mono(audio).mean()
    if not np.any(x):
        return None
    corr = np.fft.irfft(np.abs(np.fft.rfft(x, 2 * len(x))) ** 2)[: len(x)]
    corr = corr / (len(x) - np.arange(len(x)))  # unbiased, so long lags aren't penalised
    low, high = SAMPLE_RATE // 2000, SAMPLE_RATE // 30
    if high + 1 >= len(corr):
        return None
    lags = np.arange(low, high)
    peaks = lags[(corr[lags] > corr[lags - 1]) & (corr[lags] >= corr[lags + 1])]
    if peaks.size == 0 or corr[peaks].max() < 0.3 * corr[0]:
        return None
    # Every multiple of the period peaks about as high; the period is the first that does.
    lag = peaks[np.argmax(corr[peaks] >= 0.85 * corr[peaks].max())]
    return round(SAMPLE_RATE / lag, 1)


def width(audio: np.ndarray) -> float | None:
    """Side over mid level: 0 is mono, around 1 is very wide."""
    if audio.ndim != 2 or audio.shape[0] < 2:
        return 0.0
    mid, side = (audio[0] + audio[1]) / 2, (audio[0] - audio[1]) / 2
    mid_rms = np.sqrt(np.mean(mid**2))
    return round(float(np.sqrt(np.mean(side**2)) / mid_rms), 2) if mid_rms > 0 else None


def attack_ms(env: np.ndarray) -> float | None:
    if env.max() <= 0:
        return None
    return float(np.argmax(env >= 0.9 * env.max()) * 5)


def tail_ms(env: np.ndarray, start_frame: int, drop_db: float) -> float | None:
    """From start_frame to the last moment the envelope is within drop_db of its peak.

    None when it is still that loud at the end, i.e. the tail outlasts the window.
    """
    peak = env.max()
    if peak <= 0:
        return 0.0
    loud = np.nonzero(env[start_frame:] >= peak * 10 ** (-drop_db / 20))[0]
    if loud.size == 0:
        return 0.0
    if start_frame + loud[-1] >= len(env) - 1:
        return None
    return float(loud[-1] * 5)


def to_db(value: float) -> float:
    return round(20 * np.log10(value), 1) if value > 0 else -240.0


def peak_db(audio: np.ndarray) -> float:
    return to_db(float(np.max(np.abs(audio)))) if audio.size else -240.0

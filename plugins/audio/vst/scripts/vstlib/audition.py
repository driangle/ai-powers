"""Render a fixed test through a plugin and measure it.

An instrument plays C1, C2, C3 and C4 at velocity 100, then C2 again at
velocity 40. An effect gets four plucks and a noise burst followed by
silence, and separately a single impulse. Every audition uses the same
material, so numbers compare across plugins, presets and settings.
"""

from __future__ import annotations

import time

import numpy as np

from . import features as f
from .probe import LEAD_IN
from .render import SAMPLE_RATE, level_db, render_audio, render_notes

NOTES = [(36, 0.25, 0.8, 100), (48, 1.75, 0.8, 100), (60, 3.25, 0.8, 100), (72, 4.75, 0.8, 100), (48, 6.25, 0.8, 40)]
INSTRUMENT_SECONDS = 8.0
DRY_END_S, EFFECT_SECONDS, IMPULSE_AT_S = 3.0, 7.0, 0.1


def hz(midinote: int) -> float:
    return 440.0 * 2 ** ((midinote - 69) / 12)


def window(audio: np.ndarray, start: float, end: float) -> np.ndarray:
    return audio[:, int(start * SAMPLE_RATE) : int(end * SAMPLE_RATE)]


def measure_note(audio: np.ndarray, note: tuple, next_start: float) -> dict:
    midinote, start, length, velocity = note
    segment = window(audio, start, next_start)
    held = window(audio, start, start + length)
    env = f.envelope(segment)
    return {
        "note": midinote,
        "velocity": velocity,
        "level_db": level_db(held),
        "peak_db": f.peak_db(segment),
        "centroid_hz": f.centroid_hz(held),
        "flatness": f.flatness(held),
        "expected_hz": round(hz(midinote), 1),
        "pitch_hz": f.pitch_hz(window(audio, start + 0.1, start + length)),
        "attack_ms": f.attack_ms(env),
        "release_ms": f.tail_ms(env, int(length * 200), 40),
        "width": f.width(held),
    }


def audition_instrument(plugin, lead_in_s: float | None) -> tuple[np.ndarray, dict]:
    """lead_in_s: wall-clock seconds the scan found this plugin needs before it sounds."""
    if lead_in_s is not None:
        render_notes(plugin, LEAD_IN, 3.0)
        time.sleep(lead_in_s)
        render_notes(plugin, LEAD_IN, 3.0, reset=False)
    audio = render_notes(plugin, NOTES, INSTRUMENT_SECONDS, reset=lead_in_s is None)
    starts = [n[1] for n in NOTES[1:]] + [INSTRUMENT_SECONDS]
    notes = [measure_note(audio, note, nxt) for note, nxt in zip(NOTES, starts)]
    return audio, {"kind": "instrument", "notes": notes, "marks_s": [n[1] for n in NOTES]}


def pluck(midinote: int, seconds: float) -> np.ndarray:
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    tone = sum(np.sin(2 * np.pi * hz(midinote) * k * t) / k for k in range(1, 6))
    return 0.2 * tone * np.exp(-6 * t)


def dry_material() -> np.ndarray:
    dry = np.zeros(int(EFFECT_SECONDS * SAMPLE_RATE))
    for i, midinote in enumerate((48, 52, 55, 60)):
        start = int(i * 0.5 * SAMPLE_RATE)
        dry[start : start + SAMPLE_RATE // 2] += pluck(midinote, 0.5)
    burst = np.random.default_rng(2).standard_normal(SAMPLE_RATE // 5) * 0.15
    start = int(2.5 * SAMPLE_RATE)
    dry[start : start + burst.size] += burst
    return np.stack([dry, dry]).astype(np.float32)


def impulse() -> np.ndarray:
    x = np.zeros((2, int(5 * SAMPLE_RATE)), np.float32)
    x[:, int(IMPULSE_AT_S * SAMPLE_RATE)] = 1.0
    return x


def audition_effect(plugin) -> tuple[np.ndarray, dict, np.ndarray, np.ndarray]:
    dry, ir_in = dry_material(), impulse()
    wet = render_audio(plugin, dry)
    ir = render_audio(plugin, ir_in)
    wet_env, ir_env = f.envelope(wet), f.envelope(ir)
    report = {
        "kind": "effect",
        "gain_db": round(level_db(wet) - level_db(dry), 1),
        "dry_centroid_hz": f.centroid_hz(dry),
        "wet_centroid_hz": f.centroid_hz(wet),
        "dry_width": f.width(dry),
        "wet_width": f.width(wet),
        "tail_after_input_ms": f.tail_ms(wet_env, int(DRY_END_S * 200), 60),
        "impulse_tail_ms": f.tail_ms(ir_env, int(IMPULSE_AT_S * 200), 60),
        "impulse_centroid_hz": f.centroid_hz(ir),
        "impulse_width": f.width(ir),
        "marks_s": [0.0, 0.5, 1.0, 1.5, 2.5],
    }
    return wet, report, dry, ir

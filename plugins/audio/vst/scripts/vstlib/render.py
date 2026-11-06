"""Load a plugin with pedalboard and render audio through it."""

from __future__ import annotations

import numpy as np

SAMPLE_RATE = 48000
# pedalboard's default block is 8192 samples. Some instruments (Arturia's, at
# least) render pure silence at that size and play normally at 512.
BUFFER_SIZE = 512
SILENCE_DB = -90.0


class ShellBundle(Exception):
    """One bundle holding several plugins (Waves' WaveShell). Each needs a plugin_name."""

    def __init__(self, names: list[str]):
        super().__init__(f"bundle holds {len(names)} plugins")
        self.names = names


def plugin_class(fmt: str):
    from pedalboard import AudioUnitPlugin, VST3Plugin

    return VST3Plugin if fmt == "vst3" else AudioUnitPlugin


def open_plugin(fmt: str, path: str, plugin_name: str | None = None):
    cls = plugin_class(fmt)
    if plugin_name is None:
        names = cls.get_plugin_names_for_file(path)
        if len(names) > 1:
            raise ShellBundle(names)
    return cls(path, plugin_name=plugin_name)


def note_events(notes: list[tuple[int, float, float, int]]) -> list[tuple[bytes, float]]:
    """(midinote, start s, length s, velocity) -> timestamped raw MIDI for pedalboard."""
    events = []
    for midinote, start, length, velocity in notes:
        events.append((bytes([0x90, midinote, velocity]), start))
        events.append((bytes([0x80, midinote, 0]), start + length))
    return sorted(events, key=lambda e: e[1])


def render_notes(plugin, notes, duration: float, reset: bool = True) -> np.ndarray:
    return plugin(
        note_events(notes),
        duration=duration,
        sample_rate=SAMPLE_RATE,
        num_channels=2,
        buffer_size=BUFFER_SIZE,
        reset=reset,
    )


def render_audio(plugin, audio: np.ndarray, reset: bool = True) -> np.ndarray:
    """Stereo in; a plugin that only takes mono gets the left channel."""
    try:
        return plugin(audio, SAMPLE_RATE, buffer_size=BUFFER_SIZE, reset=reset)
    except ValueError:
        return plugin(audio[:1], SAMPLE_RATE, buffer_size=BUFFER_SIZE, reset=reset)


def level_db(audio: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64)))) if audio.size else 0.0
    return round(20 * np.log10(rms), 1) if rms > 0 else -240.0


def is_silent(audio: np.ndarray) -> bool:
    return level_db(audio) < SILENCE_DB

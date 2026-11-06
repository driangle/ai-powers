"""Open one plugin, read what it reports, and check that it makes sound.

`probe_plugin` runs inside a throwaway subprocess (see `scan.py`): plugins
crash, hang on licence dialogs, and leak, and none of that may take the scan
down with it.
"""

from __future__ import annotations

import math
import time

import numpy as np

from .render import SAMPLE_RATE, ShellBundle, is_silent, level_db, open_plugin, render_audio, render_notes

TEST_NOTE = [(48, 0.25, 0.75, 100)]
LEAD_IN = [(48, 0.2, 0.5, 100), (55, 1.2, 0.5, 100), (60, 2.2, 0.5, 100)]
LEAD_IN_WAITS_S = (2.0, 4.0, 8.0, 10.0)  # 24 s in all before calling it silent


def finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def current_value(plugin, key: str, param):
    """pedalboard wraps values in its own types; json wants plain ones."""
    value = getattr(plugin, key, None)
    if value is None:
        return None
    if param.type in (bool, float):
        return finite(param.type(value))
    return str(value)


def describe_parameter(plugin, key: str, param) -> dict:
    low, high, step = (finite(v) for v in param.range)
    entry = {
        "name": param.name,
        "key": key,
        "units": param.units or "",
        "min": low,
        "max": high,
        "step": step,
        "value": current_value(plugin, key, param),
        "text": param.string_value,
    }
    values = list(param.valid_values or [])
    if values and len(values) <= 64 and param.type is not float:
        entry["choices"] = values
    return entry


def test_burst() -> np.ndarray:
    """One second of decaying noise at about -12 dB, then a second of silence for any tail."""
    rng = np.random.default_rng(1)
    seconds = np.arange(SAMPLE_RATE) / SAMPLE_RATE
    burst = rng.standard_normal((2, SAMPLE_RATE)) * 0.25 * np.exp(-4 * seconds)
    return np.concatenate([burst, np.zeros((2, SAMPLE_RATE))], axis=1).astype(np.float32)


def wait_for_sound(plugin) -> tuple[float | None, float]:
    """Some instruments load samples on a background thread and stay silent until it finishes.

    An offline render outruns it, so wait in wall-clock time between tries.
    Returns (seconds waited, or None if it never sounded; level of the last try).
    """
    waited = 0.0
    for pause in (0.0, *LEAD_IN_WAITS_S):
        time.sleep(pause)
        waited += pause
        render_notes(plugin, LEAD_IN, 3.0, reset=False)
        out = render_notes(plugin, TEST_NOTE, 2.0, reset=False)
        if not is_silent(out):
            return waited, level_db(out)
    return None, level_db(out)


def sound_check(plugin, instrument: bool) -> dict:
    """{"status": "ok" | "needs-lead-in" | "silent", "level_db": …, "lead_in_s": …}."""
    if not instrument:
        out = render_audio(plugin, test_burst())
        return {"status": "silent" if is_silent(out) else "ok", "level_db": level_db(out)}
    out = render_notes(plugin, TEST_NOTE, 2.0)
    if not is_silent(out):
        return {"status": "ok", "level_db": level_db(out)}
    waited, level = wait_for_sound(plugin)
    if waited is None:
        return {"status": "silent", "level_db": level}
    return {"status": "needs-lead-in", "level_db": level, "lead_in_s": waited}


def probe_plugin(fmt: str, path: str) -> dict:
    try:
        plugin = open_plugin(fmt, path)
    except ShellBundle as shell:
        return {"status": "shell", "sub_plugins": shell.names}
    instrument = bool(plugin.is_instrument)
    return {
        **sound_check(plugin, instrument),
        "name": plugin.name.strip(),
        "vendor": (plugin.manufacturer_name or "").strip(),
        "category": plugin.category or "",
        "version": plugin.version or "",
        "kind": "instrument" if instrument else "effect",
        "parameters": [describe_parameter(plugin, k, p) for k, p in plugin.parameters.items()],
    }

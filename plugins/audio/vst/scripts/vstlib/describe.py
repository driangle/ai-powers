"""Plain words for an audition's numbers. Coarse on purpose: the numbers stay in the report."""

from __future__ import annotations

from math import log2
from statistics import median


def band(value, steps: list[tuple[float, str]], last: str) -> str:
    for limit, word in steps:
        if value < limit:
            return word
    return last


def brightness(hz) -> str:
    return band(hz, [(700, "dark"), (2000, "mellow"), (4500, "bright")], "very bright")


def stereo(width) -> str:
    return band(width, [(0.05, "mono"), (0.4, "some stereo")], "wide stereo")


def pitch_words(notes: list[dict]) -> str:
    """Does the measured pitch move with the played note, at a fixed interval from it?"""
    found = [n for n in notes if n["pitch_hz"]]
    if len(found) < len(notes) // 2:
        return "no clear pitch"
    offsets = [12 * log2(n["pitch_hz"] / n["expected_hz"]) for n in found]
    shift = round(median(offsets))
    # One note may miss: the lowest is often below what the pitch detector can see.
    if sum(abs(o - shift) < 0.6 for o in offsets) < len(found) - 1:
        return "pitch does not follow the note"
    if shift == 0:
        return "follows the note"
    if shift % 12 == 0:
        octaves = abs(shift) // 12
        return f"follows the note, {octaves} octave{'s' if octaves > 1 else ''} {'down' if shift < 0 else 'up'}"
    return f"follows the note, transposed {shift:+d} semitones"


def describe_instrument(report: dict) -> str:
    notes = [n for n in report["notes"] if n["velocity"] == 100]
    sounding = [n for n in notes if n["centroid_hz"]]
    if not sounding:
        return "silent"
    words = [brightness(median(n["centroid_hz"] for n in sounding))]
    attack = median(n["attack_ms"] for n in sounding)
    words.append(band(attack, [(15, "sharp attack"), (80, "quick attack"), (300, "soft attack")], "slow swell"))
    releases = [n["release_ms"] for n in sounding]
    if any(r is None for r in releases):
        words.append("rings past the next note")
    else:
        words.append(band(median(releases), [(150, "short release"), (800, "medium release")], "long release"))
    words.append(band(median(n["flatness"] for n in sounding), [(0.05, "tonal"), (0.2, "tonal with noise")], "noisy"))
    words.append(pitch_words(sounding))
    words.append(stereo(median(n["width"] for n in sounding)))
    soft = report["notes"][-1]
    loud = next(n for n in notes if n["note"] == soft["note"])
    drop = loud["level_db"] - soft["level_db"]
    if any(r is None for r in releases):
        pass  # earlier notes still sound under the soft one, so its level says nothing
    elif abs(drop) < 1:
        words.append("velocity barely changes the level")
    else:
        words.append(f"velocity 40 is {abs(drop):.0f} dB {'quieter' if drop > 0 else 'louder'} than 100")
    return ", ".join(words)


def describe_effect(report: dict) -> str:
    words = [f"{report['gain_db']:+.0f} dB"]
    dry, wet = report["dry_centroid_hz"] or 1, report["wet_centroid_hz"] or 0
    ratio = wet / dry
    words.append(band(ratio, [(0.8, "darker than"), (1.25, "about as bright as")], "brighter than") + " the input")
    tail = report["impulse_tail_ms"]
    if tail is None:
        words.append("tail longer than 5 s")
    else:
        words.append(band(tail, [(50, "no tail"), (400, "short tail")], f"{tail / 1000:.1f} s tail"))
    words.append(stereo(report["wet_width"]))
    return ", ".join(words)


def describe(report: dict) -> str:
    return describe_instrument(report) if report["kind"] == "instrument" else describe_effect(report)

"""`vst audition`: open a catalogued plugin, apply a preset and settings, render, write the results."""

from __future__ import annotations

import json

from .audition import audition_effect, audition_instrument
from .describe import describe
from .media import spectrogram, write_png, write_wav
from .paths import audition_dir, slug, squash
from .render import open_plugin


class BadSetting(Exception):
    pass


def apply_setting(plugin, assignment: str) -> str:
    """"Cutoff=0.3" -> set it by the plugin's name for it or pedalboard's key. Returns the key."""
    name, sep, raw = assignment.partition("=")
    if not sep:
        raise BadSetting(f"'{assignment}' is not name=value")
    key = squash(name)
    match = [k for k, p in plugin.parameters.items() if key in (squash(k), squash(p.name))]
    if not match:
        raise BadSetting(f"no parameter '{name}'; `vst inspect` lists them")
    param = plugin.parameters[match[0]]
    if param.type is bool:
        value = raw.lower() in ("1", "true", "on", "yes")
    elif param.type is float:
        value = float(raw)
    else:
        value = raw
    setattr(plugin, match[0], value)
    return match[0]


def variant_name(preset: str | None, settings: list[str]) -> str:
    parts = [slug(preset.rsplit("/", 1)[-1].rsplit(".", 1)[0])] if preset else []
    parts += [slug(s) for s in settings]
    return "_".join(parts)[:120] or "default"


def run_audition(entry: dict, preset: str | None, settings: list[str]) -> dict:
    plugin = open_plugin(entry["probed_format"], entry["formats"][entry["probed_format"]])
    if preset:
        plugin.load_preset(preset)
    for assignment in settings:
        apply_setting(plugin, assignment)
    out = audition_dir(entry["id"], variant_name(preset, settings))
    if entry["kind"] == "instrument":
        audio, report = audition_instrument(plugin, entry.get("lead_in_s"))
    else:
        audio, report, dry, ir = audition_effect(plugin)
        write_wav(out / "dry.wav", dry)
        write_wav(out / "impulse.wav", ir)
        write_png(out / "impulse.png", spectrogram(ir, [0.1]))
    write_wav(out / "audition.wav", audio)
    write_png(out / "spectrogram.png", spectrogram(audio, report["marks_s"]))
    report.update(plugin=entry["name"], preset=preset, settings=settings, summary=describe(report))
    (out / "report.json").write_text(json.dumps(report, indent=1))
    report["files"] = sorted(str(p) for p in out.iterdir())
    return report

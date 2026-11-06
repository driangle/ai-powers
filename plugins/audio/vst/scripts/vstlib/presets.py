"""Preset files a plugin's vendor installed where macOS hosts look for them.

That is `/Library/Audio/Presets/<Vendor>/<Plugin…>/` and the same under `~`.
Most vendors save in their own format (Serum `.fxp`, u-he `.h2p`, Valhalla
`.vpreset`), which only the plugin's own UI opens; `vst audition --preset`
loads `.vstpreset` alone. Even unloadable, a preset's path ("Bass/BS Growl")
is often the best description of a sound the plugin can make. Plugins that
keep presets in a database (Arturia, Native Instruments) show none here.
"""

from __future__ import annotations

from pathlib import Path

from .paths import PRESET_DIRS, squash

FORMATS = {
    ".vstpreset": "vst3",
    ".aupreset": "au",
    ".fxp": "vst2",
    ".fxb": "vst2 bank",
    ".h2p": "u-he",
    ".vpreset": "valhalla",
    ".nksf": "nks",
}
LOADABLE = {".vstpreset"}
LIMIT = 5000


def preset_folders(plugin_name: str) -> list[Path]:
    """Vendor subfolders named for the plugin: "ValhallaRoom", "Serum Presets"."""
    key = squash(plugin_name)
    folders = []
    for root in PRESET_DIRS:
        for vendor in (p for p in root.iterdir() if p.is_dir()) if root.is_dir() else ():
            folders.extend(p for p in vendor.iterdir() if p.is_dir() and squash(p.name).startswith(key))
    return folders


def find_presets(plugin_name: str) -> list[dict]:
    found = []
    for folder in preset_folders(plugin_name):
        for path in sorted(folder.rglob("*")):
            suffix = path.suffix.lower()
            if suffix in FORMATS:
                found.append({
                    "name": str(path.relative_to(folder).with_suffix("")),
                    "format": FORMATS[suffix],
                    "loadable": suffix in LOADABLE,
                    "path": str(path),
                })
            if len(found) >= LIMIT:
                return found
    return found

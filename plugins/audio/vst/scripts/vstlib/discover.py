"""Find installed plugin bundles without loading them.

A plugin installed as both VST3 and Audio Unit becomes one entry with two
formats. Names are matched loosely (`ValhallaRoomAU64.component` reports
itself as "ValhallaRoom"), so the AU's own name from its Info.plist is used.
"""

from __future__ import annotations

import plistlib
from dataclasses import dataclass, field
from pathlib import Path

from .paths import AU_DIRS, VST3_DIRS, squash


@dataclass
class Bundle:
    name: str
    formats: dict[str, str] = field(default_factory=dict)  # "vst3" | "au" -> bundle path
    stamp: dict[str, float] = field(default_factory=dict)  # bundle path -> modified time


def bundle_mtime(path: Path) -> float:
    plist = path / "Contents" / "Info.plist"
    return (plist if plist.exists() else path).stat().st_mtime


def au_names(path: Path) -> tuple[str, str]:
    """(name, "Vendor Name") an Audio Unit gives itself in its plist ("Vendor: Name"), else the bundle name."""
    try:
        with open(path / "Contents" / "Info.plist", "rb") as handle:
            components = plistlib.load(handle).get("AudioComponents") or []
    except (OSError, plistlib.InvalidFileException):
        components = []
    for component in components:
        full = str(component.get("name", "")).strip()
        if full:
            vendor, _, name = full.rpartition(":")
            return name.strip(), f"{vendor} {name}".strip()
    return path.stem, path.stem


def bundles_in(dirs: list[Path], suffix: str) -> list[Path]:
    found = []
    for folder in dirs:
        if folder.is_dir():
            found.extend(sorted(p for p in folder.iterdir() if p.suffix == suffix))
    return found


def discover() -> list[Bundle]:
    by_key: dict[str, Bundle] = {}

    def add(name: str, fmt: str, path: Path, aliases: tuple[str, ...] = ()) -> None:
        # FabFilter's AU calls itself "Pro-Q 3"; its VST3 bundle is "FabFilter Pro-Q 3".
        key = next((squash(a) for a in aliases if squash(a) in by_key), squash(name))
        bundle = by_key.setdefault(key, Bundle(name=name))
        bundle.formats.setdefault(fmt, str(path))
        bundle.stamp[str(path)] = bundle_mtime(path)

    for path in bundles_in(VST3_DIRS, ".vst3"):
        add(path.stem, "vst3", path)
    for path in bundles_in(AU_DIRS, ".component"):
        name, vendor_name = au_names(path)
        add(name, "au", path, aliases=(name, vendor_name))
    return sorted(by_key.values(), key=lambda b: b.name.lower())

"""Where plugins are installed on macOS, and where the catalog lives."""

from __future__ import annotations

import os
import re
from pathlib import Path

HOME = Path.home()

VST3_DIRS = [Path("/Library/Audio/Plug-Ins/VST3"), HOME / "Library/Audio/Plug-Ins/VST3"]
AU_DIRS = [Path("/Library/Audio/Plug-Ins/Components"), HOME / "Library/Audio/Plug-Ins/Components"]
PRESET_DIRS = [Path("/Library/Audio/Presets"), HOME / "Library/Audio/Presets"]


def data_dir() -> Path:
    """The catalog, per-plugin details, auditions and notes. VST_CATALOG_DIR overrides it."""
    override = os.environ.get("VST_CATALOG_DIR")
    base = Path(override) if override else HOME / "Library/Application Support/vst-catalog"
    base.mkdir(parents=True, exist_ok=True)
    return base


def catalog_file() -> Path:
    return data_dir() / "catalog.json"


def details_file(plugin_id: str) -> Path:
    path = data_dir() / "plugins" / f"{plugin_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def notes_file() -> Path:
    return data_dir() / "notes.md"


def audition_dir(plugin_id: str, variant: str) -> Path:
    path = data_dir() / "auditions" / plugin_id / variant
    path.mkdir(parents=True, exist_ok=True)
    return path


def slug(text: str) -> str:
    """A filesystem- and lookup-friendly id: lower case, runs of other characters as one dash."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def squash(text: str) -> str:
    """Letters and digits only, for matching names written differently ("Mini V3" ~ "minIV3")."""
    return re.sub(r"[^a-z0-9]", "", text.lower())

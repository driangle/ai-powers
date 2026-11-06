"""The catalog on disk, finding a plugin in it by name, and the user's notes."""

from __future__ import annotations

import json
import re

from .paths import catalog_file, details_file, notes_file, squash

NOTES_TEMPLATE = """# Plugin notes

What each plugin sounds like and is good for, in your own words. Agents read
this before choosing a plugin, and it outranks anything they can measure.
One `## <plugin name>` heading per plugin, as `vst list` spells it.

<!-- ## Mini V3
Fat mono bass and leads. The filter is the whole character: CutOff low, Emphasis high. -->
"""


class PluginNotFound(Exception):
    pass


def load_catalog() -> dict:
    path = catalog_file()
    if not path.exists():
        return {"plugins": []}
    return json.loads(path.read_text())


def save_catalog(catalog: dict) -> None:
    catalog["plugins"].sort(key=lambda e: e["name"].lower())
    catalog_file().write_text(json.dumps(catalog, indent=1))


def load_details(plugin_id: str) -> dict:
    path = details_file(plugin_id)
    return json.loads(path.read_text()) if path.exists() else {}


def save_details(plugin_id: str, details: dict) -> None:
    details_file(plugin_id).write_text(json.dumps(details, indent=1))


def find_plugin(catalog: dict, query: str) -> dict:
    """By id, then by exact name ignoring case and punctuation, then by a unique partial match."""
    plugins = catalog["plugins"]
    if not plugins:
        raise PluginNotFound("the catalog is empty; run `vst scan` first")
    key = squash(query)
    for match in (
        [e for e in plugins if e["id"] == query],
        [e for e in plugins if squash(e["name"]) == key],
        [e for e in plugins if key and key in squash(e["name"])],
    ):
        if len(match) == 1:
            return match[0]
        if len(match) > 1:
            names = ", ".join(e["name"] for e in match[:12])
            raise PluginNotFound(f"'{query}' matches several plugins: {names}")
    raise PluginNotFound(f"no plugin matches '{query}'; `vst list` shows them all")


def load_notes() -> dict[str, str]:
    """Plugin name (squashed) -> the text under its `## ` heading in notes.md."""
    path = notes_file()
    if not path.exists():
        path.write_text(NOTES_TEMPLATE)
    text = re.sub(r"<!--.*?-->", "", path.read_text(), flags=re.S)
    notes = {}
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        heading, _, body = block.partition("\n")
        if body.strip():
            notes[squash(heading)] = body.strip()
    return notes

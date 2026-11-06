"""`vst list` and `vst inspect`: read the catalog and print it for a person or an agent."""

from __future__ import annotations

import json
import re

from .catalog import load_details, load_notes
from .paths import squash
from .presets import find_presets

WORKS = {"ok", "needs-lead-in"}


def matches(entry: dict, notes: dict, kind, status, search) -> bool:
    if kind and entry["kind"] != kind:
        return False
    if status == "works" and entry["status"] not in WORKS:
        return False
    if status and status != "works" and entry["status"] != status:
        return False
    if search:
        note = notes.get(squash(entry["name"]), "")
        haystack = " ".join([entry["name"], entry["vendor"], entry["category"], note]).lower()
        return all(word in haystack for word in search.lower().split())
    return True


def table(rows: list[list[str]]) -> str:
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    return "\n".join("  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip() for r in rows)


def list_plugins(catalog: dict, kind=None, status=None, search=None, as_json=False) -> str:
    notes = load_notes()
    chosen = [e for e in catalog["plugins"] if matches(e, notes, kind, status, search)]
    if as_json:
        return json.dumps([dict(e, notes=notes.get(squash(e["name"]))) for e in chosen], indent=1)
    rows = [["NAME", "KIND", "VENDOR", "CATEGORY", "STATUS", "PARAMS", "PRESETS", "NOTES"]]
    for e in chosen:
        has_note = "yes" if squash(e["name"]) in notes else ""
        counts = [str(e["param_count"]), str(e["preset_count"])]
        rows.append([e["name"], e["kind"], e["vendor"], e["category"], e["status"], *counts, has_note])
    return table(rows) + f"\n\n{len(chosen)} of {len(catalog['plugins'])} plugins"


def parameter_line(p: dict) -> str:
    span = f"{p['min']}..{p['max']}" if p["min"] is not None else ""
    line = f"  {p['name']}  [{p['key']}]  {span} {p['units']}  = {p['text']}".rstrip()
    if p.get("choices"):
        shown = ", ".join(str(c) for c in p["choices"][:12])
        line += f"  ({shown}{', …' if len(p['choices']) > 12 else ''})"
    return line


def inspect_plugin(entry: dict, pattern=None, limit=80, as_json=False) -> str:
    params = load_details(entry["id"]).get("parameters", [])
    if pattern:
        rx = re.compile(pattern, re.I)
        params = [p for p in params if rx.search(p["name"]) or rx.search(p["key"])]
    presets = find_presets(entry["name"])
    note = load_notes().get(squash(entry["name"]))
    if as_json:
        return json.dumps(dict(entry, notes=note, presets=presets, parameters=params), indent=1)
    lines = [f"{entry['name']} — {entry['vendor']}, {entry['kind']} ({entry['category']}), version {entry['version']}"]
    lines.append(f"status: {entry['status']}" + (f" — {entry['error']}" if entry.get("error") else ""))
    lines += [f"{fmt}: {path}" for fmt, path in entry["formats"].items()]
    lines += [f"tried {fmt}: {outcome}" for fmt, outcome in entry.get("attempts", {}).items()]
    if entry.get("sub_plugins"):
        lines.append(f"holds {len(entry['sub_plugins'])} plugins, not probed one by one")
    lines.append(f"\nnotes: {note}" if note else "\nnotes: none in notes.md")
    loadable = sum(p["loadable"] for p in presets)
    lines.append(f"\npresets ({len(presets)}, {loadable} loadable by `vst audition --preset`):")
    lines += [f"  {p['name']}  ({p['format']}{', loadable' if p['loadable'] else ''})" for p in presets[:40]]
    if len(presets) > 40:
        lines.append(f"  … {len(presets) - 40} more (--json lists all, with paths)")
    lines.append(f"\nparameters ({len(params)}{' matching' if pattern else ''}): name  [key]  range units  = current")
    lines += [parameter_line(p) for p in params[:limit]]
    if len(params) > limit:
        lines.append(f"  … {len(params) - limit} more: narrow with --filter or raise --limit")
    return "\n".join(lines)

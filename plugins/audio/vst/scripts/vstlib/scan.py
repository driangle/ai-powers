"""Probe installed plugins into the catalog, each in its own subprocess.

Only plugins that are new or whose bundle changed are probed again, unless
forced. A plugin with both formats is tried as VST3 first and as an Audio Unit
if the VST3 fails.
"""

from __future__ import annotations

import json
import signal
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from .arch import bundle_archs, intel_python, needs_rosetta
from .catalog import load_catalog, save_catalog, save_details
from .discover import Bundle, discover
from .paths import slug, squash
from .presets import find_presets

ENTRY_SCRIPT = Path(__file__).resolve().parent.parent / "vst.py"
WORKS = {"ok", "needs-lead-in"}


def tail(text: str, limit: int = 300) -> str:
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return " | ".join(lines[-3:])[-limit:]


def run_probe(fmt: str, path: str, timeout: float) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "probe.json"
        python = intel_python() if needs_rosetta(bundle_archs(path)) else [sys.executable]
        cmd = [*python, str(ENTRY_SCRIPT), "_probe", fmt, path, str(out)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": f"no answer in {timeout:.0f} s (a licence or login dialog?)"}
        if out.exists():
            return json.loads(out.read_text())
        # A signal shows as -N, or as 128+N when the worker ran behind uv (Intel plugins).
        signum = -proc.returncode if proc.returncode < 0 else proc.returncode - 128
        if 0 < signum < 65:
            name = signal.Signals(signum).name if signum in signal.valid_signals() else f"signal {signum}"
            return {"status": "crashed", "error": f"{name}: {tail(proc.stderr)}"}
        return {"status": "error", "error": tail(proc.stderr) or f"exit {proc.returncode}"}


RANK = ["ok", "needs-lead-in", "shell", "silent", "error", "crashed", "timeout"]


def probe_bundle(bundle: Bundle, timeout: float) -> tuple[dict, str]:
    """Try VST3, then AU unless the VST3 worked; keep the better result and every attempt's outcome."""
    attempts: dict[str, dict] = {}
    for fmt in ("vst3", "au"):
        if fmt in bundle.formats:
            attempts[fmt] = run_probe(fmt, bundle.formats[fmt], timeout)
            if attempts[fmt]["status"] in WORKS or attempts[fmt]["status"] == "shell":
                break
    used = min(attempts, key=lambda fmt: RANK.index(attempts[fmt]["status"]))
    result = dict(attempts[used])
    if len(attempts) > 1:
        result["attempts"] = {fmt: a["status"] + (f": {a['error']}" if a.get("error") else "") for fmt, a in attempts.items()}
    return result, used


def make_entry(bundle: Bundle, result: dict, used: str) -> dict:
    name = result.get("name") or bundle.name
    entry = {
        "id": slug(bundle.name),
        "name": name,
        "vendor": result.get("vendor", ""),
        "kind": result.get("kind", "unknown"),
        "category": result.get("category", ""),
        "version": result.get("version", ""),
        "status": result["status"],
        "level_db": result.get("level_db"),
        "param_count": len(result.get("parameters", [])),
        "preset_count": len(find_presets(name)),
        "formats": bundle.formats,
        "probed_format": used,
        "arch": bundle_archs(bundle.formats[used]),
        "stamp": bundle.stamp,
    }
    for extra in ("lead_in_s", "error", "sub_plugins", "attempts"):
        if extra in result:
            entry[extra] = result[extra]
    return entry


def select(bundles: list[Bundle], known: dict, only: str | None, force: bool) -> list[Bundle]:
    if only:
        key = squash(only)
        return [b for b in bundles if key in squash(b.name)]
    return [b for b in bundles if force or known.get(slug(b.name), {}).get("stamp") != b.stamp]


def scan(only: str | None = None, force: bool = False, jobs: int = 4, timeout: float = 90.0) -> dict:
    catalog = load_catalog()
    bundles = discover()
    known = {e["id"]: e for e in catalog["plugins"]}
    if not only:  # uninstalled plugins leave the catalog
        present = {slug(b.name) for b in bundles}
        known = {k: v for k, v in known.items() if k in present}
    todo = select(bundles, known, only, force)
    print(f"{len(bundles)} plugins installed, probing {len(todo)}", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(probe_bundle, b, timeout): b for b in todo}
        for done, future in enumerate(as_completed(futures), 1):
            bundle = futures[future]
            result, used = future.result()
            entry = make_entry(bundle, result, used)
            known[entry["id"]] = entry
            save_details(entry["id"], {"parameters": result.get("parameters", [])})
            catalog["plugins"] = list(known.values())
            save_catalog(catalog)
            print(f"[{done}/{len(todo)}] {entry['name']}: {entry['status']}", file=sys.stderr)
    catalog["plugins"] = list(known.values())
    catalog["scanned_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_catalog(catalog)
    return catalog

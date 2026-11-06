#!/usr/bin/env python3
"""Catalog, inspect and audition the VST3 and Audio Unit plugins on this Mac.

  vst scan [name] [--force] [--jobs N] [--timeout S]
  vst list [--kind instrument|effect] [--status works|ok|silent|…] [--search words] [--json]
  vst inspect <name> [--filter regex] [--limit N] [--json]
  vst audition <name> [--preset file.vstpreset] [--set Param=value …] [--json]
  vst where

Run through the `vst` launcher beside this file, which supplies pedalboard and numpy.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from vstlib.arch import intel_python, needs_rosetta
from vstlib.catalog import PluginNotFound, find_plugin, load_catalog
from vstlib.commands import inspect_plugin, list_plugins
from vstlib.paths import data_dir, notes_file


def probe_worker(fmt: str, path: str, out: str) -> None:
    """Internal: one plugin, in its own process (see vstlib/scan.py)."""
    from vstlib.probe import probe_plugin

    try:
        result = probe_plugin(fmt, path)
    except Exception as error:  # a plugin can fail in any way; report it as data
        result = {"status": "error", "error": f"{type(error).__name__}: {error}"}
    # Serialise first, so a value json can't handle never leaves half a file behind.
    text = json.dumps(result, default=str)
    with open(out, "w") as handle:
        handle.write(text)


def parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="vst", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="probe new or changed plugins into the catalog")
    scan.add_argument("name", nargs="?", help="only plugins whose name contains this (always re-probed)")
    scan.add_argument("--force", action="store_true", help="re-probe every plugin")
    scan.add_argument("--jobs", type=int, default=4)
    scan.add_argument("--timeout", type=float, default=90.0, help="seconds per plugin")
    lister = sub.add_parser("list", help="the catalog as a table")
    lister.add_argument("--kind", choices=["instrument", "effect"])
    lister.add_argument("--status", help="works (ok or needs-lead-in), ok, needs-lead-in, silent, crashed, timeout, error, shell")
    lister.add_argument("--search", help="words that must all appear in name, vendor, category or notes")
    lister.add_argument("--json", action="store_true")
    inspect = sub.add_parser("inspect", help="one plugin's parameters, presets and notes")
    inspect.add_argument("name")
    inspect.add_argument("--filter", help="regex over parameter names")
    inspect.add_argument("--limit", type=int, default=80)
    inspect.add_argument("--json", action="store_true")
    audition = sub.add_parser("audition", help="render the test material and measure it")
    audition.add_argument("name")
    audition.add_argument("--preset", help="a .vstpreset file (VST3 only)")
    audition.add_argument("--set", action="append", default=[], metavar="PARAM=VALUE")
    audition.add_argument("--json", action="store_true")
    sub.add_parser("where", help="where the catalog, auditions and notes live")
    worker = sub.add_parser("_probe")
    worker.add_argument("fmt")
    worker.add_argument("path")
    worker.add_argument("out")
    return parser.parse_args(argv)


def print_audition(report: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, indent=1))
        return
    print(f"{report['plugin']}: {report['summary']}")
    print("files:\n  " + "\n  ".join(report["files"]))


def main(argv: list[str]) -> int:
    args = parse(argv)
    if args.command == "_probe":
        probe_worker(args.fmt, args.path, args.out)
        return 0
    if args.command == "where":
        print(f"data:  {data_dir()}\nnotes: {notes_file()}")
        return 0
    if args.command == "scan":
        from vstlib.scan import scan

        scan(args.name, args.force, args.jobs, args.timeout)
        print(list_plugins(load_catalog()))
        return 0
    catalog = load_catalog()
    if args.command == "list":
        print(list_plugins(catalog, args.kind, args.status, args.search, args.json))
        return 0
    try:
        entry = find_plugin(catalog, args.name)
    except PluginNotFound as error:
        print(error, file=sys.stderr)
        return 1
    if args.command == "inspect":
        print(inspect_plugin(entry, args.filter, args.limit, args.json))
        return 0
    if needs_rosetta(entry.get("arch", [])):  # an Intel-only plugin: audition it from an x86_64 Python
        return subprocess.run([*intel_python(), __file__, *argv]).returncode
    from vstlib.run_audition import run_audition

    print_audition(run_audition(entry, args.preset, args.set), args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

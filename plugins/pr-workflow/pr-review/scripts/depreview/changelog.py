"""Cuts the part of a shipped changelog that covers the upgrade range, newest-first or oldest-first."""

import re
from pathlib import Path
from typing import Optional

_NAMES = re.compile(r"^(changelog|changes|history|news|releases?)(\.(md|markdown|rst|txt))?$", re.IGNORECASE)
_HEADING_START = re.compile(r"^\s*(#|\[|v?\d|version\b|release\b|\*\*|<a )", re.IGNORECASE)
_MAX_LINES = 400


def find(root: Path) -> Optional[Path]:
    matches = sorted(p for p in root.iterdir() if p.is_file() and _NAMES.match(p.name)) if root.exists() else []
    return matches[0] if matches else None


def excerpt(text: str, old: str, new: str) -> Optional[str]:
    lines = text.splitlines()
    start, stop = _heading(lines, new), _heading(lines, old)
    if start is None:
        return None
    if stop is not None and stop < start:
        # Oldest-first: the range runs from the old version's heading to the end of the new version's section.
        start, stop = stop, _next_heading(lines, start)
    if stop is None:
        stop = start + _MAX_LINES
    return "\n".join(lines[start:stop][:_MAX_LINES])


def _heading(lines: list, version: str) -> Optional[int]:
    pattern = re.compile(rf"(?<![\w.]){re.escape(version)}(?![\w.-])")
    for index, line in enumerate(lines):
        if len(line) <= 160 and pattern.search(line) and _is_heading(lines, index):
            return index
    return None


def _next_heading(lines: list, after: int) -> Optional[int]:
    version = re.compile(r"(?<![\w.])v?\d+\.\d+")
    for index in range(after + 1, len(lines)):
        if version.search(lines[index]) and _is_heading(lines, index):
            return index
    return None


def _is_heading(lines: list, index: int) -> bool:
    following = lines[index + 1] if index + 1 < len(lines) else ""
    return bool(_HEADING_START.match(lines[index])) or bool(re.match(r"^\s*(=+|-+|~+)\s*$", following))

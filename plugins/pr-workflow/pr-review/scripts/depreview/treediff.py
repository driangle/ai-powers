"""Diffs two unpacked package trees file by file, sorting files by what they are so the reader starts with what
matters: manifests, then type declarations, then source, then tests and docs. Generated noise is skipped."""

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Optional

MANIFEST, TYPES, SOURCE, TEST, DOCS = "manifest", "types", "source", "test", "docs"
_ORDER = {MANIFEST: 0, TYPES: 1, SOURCE: 2, TEST: 3, DOCS: 4}
_MANIFEST_NAMES = {
    "package.json", "pyproject.toml", "setup.py", "setup.cfg", "METADATA", "PKG-INFO", "Cargo.toml", "go.mod",
    "binding.gyp", "pom.xml",
}
_TEST_PARTS = {"test", "tests", "__tests__", "spec", "specs", "testing", "fixtures", "__mocks__", "testdata"}
_DOC_PARTS = {"docs", "doc", "examples", "example", "benchmark", "benchmarks"}
_DOC_SUFFIXES = {".md", ".markdown", ".rst", ".txt", ".adoc"}
_TEST_NAME = re.compile(r"(\.test\.|\.spec\.|^test_|_test\.(py|go)$)")
_MAX_FILE_BYTES = 1_500_000
# A bundle whose average line is this long is minified, whatever its name.
_MINIFIED_MIN_BYTES = 10_000
_MINIFIED_LINE_LENGTH = 1_000
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


@dataclass
class FileChange:
    path: str
    status: str  # added | removed | modified
    category: str
    added: int = 0
    removed: int = 0
    skipped: Optional[str] = None  # why the content was not diffed
    added_lines: list = field(default_factory=list)  # (line number in the new file, text)


def diff_trees(old: Path, new: Path) -> tuple:
    """Returns (file changes sorted for reading, unified diff text of the diffed files)."""
    old_files, new_files = _files(old), _files(new)
    changes, patches = [], []
    for path in sorted(set(old_files) | set(new_files), key=lambda p: (_ORDER[category(p)], p)):
        before, after = old_files.get(path), new_files.get(path)
        if before is not None and after is not None and before.read_bytes() == after.read_bytes():
            continue
        status = "added" if before is None else "removed" if after is None else "modified"
        change = FileChange(path, status, category(path), skipped=_skip_reason(path, before, after))
        if change.skipped is None:
            patch = _unified(path, _text(before), _text(after))
            _count(change, patch)
            patches.append("".join(patch))
        changes.append(change)
    return changes, "".join(patches)


def category(path: str) -> str:
    posix = PurePosixPath(path)
    parts = {part.lower() for part in posix.parts[:-1]}
    if posix.name in _MANIFEST_NAMES or posix.name.endswith(".gemspec"):
        return MANIFEST
    if posix.name.endswith((".d.ts", ".d.mts", ".d.cts", ".pyi")):
        return TYPES
    if parts & _TEST_PARTS or _TEST_NAME.search(posix.name):
        return TEST
    if parts & _DOC_PARTS or posix.suffix.lower() in _DOC_SUFFIXES or posix.name.upper().startswith(("LICENSE", "README")):
        return DOCS
    return SOURCE


def _files(root: Path) -> dict:
    return {str(p.relative_to(root).as_posix()): p for p in root.rglob("*") if p.is_file()} if root.exists() else {}


def _skip_reason(path: str, *files) -> Optional[str]:
    name = PurePosixPath(path).name
    if name.endswith(".map"):
        return "source map"
    if re.search(r"[.-]min\.(js|css|mjs)$", name):
        return "minified"
    if (name == "RECORD" and ".dist-info" in path) or name.endswith(".tsbuildinfo"):
        return "generated"
    for file in filter(None, files):
        if file.stat().st_size > _MAX_FILE_BYTES:
            return "too large"
        content = file.read_bytes()
        if b"\0" in content[:8000]:
            return "binary"
        if len(content) > _MINIFIED_MIN_BYTES and len(content) / (content.count(b"\n") + 1) > _MINIFIED_LINE_LENGTH:
            return "minified"
    return None


def _text(file: Optional[Path]) -> list:
    return [] if file is None else file.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)


def _unified(path: str, before: list, after: list) -> list:
    lines = list(difflib.unified_diff(before, after, f"a/{path}", f"b/{path}", n=3))
    return [line if line.endswith("\n") else line + "\n" for line in lines]


def _count(change: FileChange, patch: list) -> None:
    new_line = 0
    for line in patch:
        hunk = _HUNK.match(line)
        if hunk:
            new_line = int(hunk.group(1))
        elif line.startswith("+") and not line.startswith("+++"):
            change.added += 1
            change.added_lines.append((new_line, line[1:].rstrip("\n")))
            new_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            change.removed += 1
        elif line.startswith(" "):
            new_line += 1

"""Downloads two releases of one package, unpacks them side by side and writes what changed between them.

An old version of `-` stands for nothing: every file of the new release counts as added, which scans a package new
to the tree for supply-chain signals, or unpacks one release to read it.

Layout of the output directory:
  download/{old,new}/   the archives as published
  old/, new/            the unpacked trees (untrusted data: read them, never run or install them)
  diff.patch            unified diff of every diffed file, manifests first, then types, source, tests, docs
  changelog-excerpt.md  the shipped changelog's section for the range, when there is one
  summary.json          everything below, for tools
"""

import json
import re
from pathlib import Path

from . import changelog, extract, manifest, redflags, registries, treediff

_MAX_FILES_LISTED = 120
EMPTY = "-"


def run(ecosystem: str, name: str, old: str, new: str, out: Path, npm_registry: str) -> dict:
    if new == EMPTY:
        raise SystemExit("depdiff: the new version must be a real version; only the old one can be -")
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"depdiff: {out} is not empty; pick a new directory")
    artifacts, skipped = {}, {}
    for label, version in (("old", old), ("new", new)):
        if version == EMPTY:
            (out / label).mkdir(parents=True, exist_ok=True)
            artifacts[label], skipped[label] = None, []
            continue
        artifact, archive, sha = registries.fetch(ecosystem, name, version, out / "download" / label, npm_registry)
        skipped[label] = extract.extract(archive, out / label, artifact.strip)
        artifacts[label] = {"version": version, "url": artifact.url, "file": str(archive), "sha256": sha,
                            "repository": artifact.repository}
    changes, patch = treediff.diff_trees(out / "old", out / "new")
    (out / "diff.patch").write_text(patch, encoding="utf-8")
    npm_repository = manifest.npm_repository(out / "new") if ecosystem == "npm" else None
    repository = artifacts["new"]["repository"] or registries.repository_url(npm_repository)
    directory = npm_repository.get("directory") if isinstance(npm_repository, dict) else None
    summary = {
        "ecosystem": ecosystem,
        "name": name,
        "from": old,
        "to": new,
        "out": str(out),
        "artifacts": artifacts,
        "repository": repository,
        "compare_hint": None if old == EMPTY else _compare_hint(repository, directory, name, old, new),
        "manifest_changes": manifest.changes(ecosystem, out / "old", out / "new"),
        "totals": _totals(changes),
        "files": [_file_entry(c) for c in changes],
        "supply_chain_signals": redflags.scan(changes),
        "changelog_excerpt": None if old == EMPTY else _write_changelog(out, old, new),
        "unsafe_entries_skipped": skipped,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def to_markdown(summary: dict) -> str:
    totals = summary["totals"]
    lines = [
        f"## {summary['name']} {summary['from']} → {summary['to']} ({summary['ecosystem']})",
        "",
        f"{totals['files']} files changed, +{totals['added']} / -{totals['removed']} lines diffed; "
        f"{totals['skipped']} skipped (maps, minified, binary, oversized)",
        f"Repository: {summary['repository'] or 'unknown'}",
    ]
    if summary["compare_hint"]:
        lines.append(f"Commits and PRs in the range: `{summary['compare_hint']}`")
    lines += [f"Output: {summary['out']} (diff.patch, summary.json, old/, new/)"]
    if summary["manifest_changes"]:
        lines += ["", "### Manifest changes", "", "```json", json.dumps(summary["manifest_changes"], indent=2), "```"]
    lines += ["", "### Files by category", "", "| File | Status | Category | + | - | Note |", "|---|---|---|---|---|---|"]
    for entry in summary["files"][:_MAX_FILES_LISTED]:
        lines.append(f"| `{entry['path']}` | {entry['status']} | {entry['category']} | {entry['added']} | "
                     f"{entry['removed']} | {entry['skipped'] or ''} |")
    if len(summary["files"]) > _MAX_FILES_LISTED:
        lines.append(f"\n… {len(summary['files']) - _MAX_FILES_LISTED} more files in summary.json")
    if summary["supply_chain_signals"]:
        lines += ["", "### Supply-chain signals in added code (read each; most are benign)", ""]
        lines += [f"- {f['signal']}: `{f['path']}`" + (f":{f['line']}" if f["line"] else "") + f" `{f['text']}`"
                  for f in summary["supply_chain_signals"]]
    lines += ["", "### Changelog", ""]
    if summary["from"] == EMPTY:
        lines.append(f"Single release unpacked to {summary['out']}/new; every file counts as added.")
    else:
        lines.append(f"Excerpt for the range: {summary['changelog_excerpt']}" if summary["changelog_excerpt"]
                     else "No changelog section found in the package; use the GitHub releases or the compare range.")
    if any(summary["unsafe_entries_skipped"].values()):
        lines += ["", f"Archive entries not extracted (links, devices, unsafe paths): {summary['unsafe_entries_skipped']}"]
    return "\n".join(lines) + "\n"


def _totals(changes: list) -> dict:
    return {
        "files": len(changes),
        "added": sum(c.added for c in changes),
        "removed": sum(c.removed for c in changes),
        "skipped": sum(1 for c in changes if c.skipped),
        "by_category": {cat: sum(1 for c in changes if c.category == cat)
                        for cat in (treediff.MANIFEST, treediff.TYPES, treediff.SOURCE, treediff.TEST, treediff.DOCS)},
    }


def _file_entry(change) -> dict:
    return {"path": change.path, "status": change.status, "category": change.category,
            "added": change.added, "removed": change.removed, "skipped": change.skipped}


def _write_changelog(out: Path, old: str, new: str):
    found = changelog.find(out / "new")
    text = found and changelog.excerpt(found.read_text(encoding="utf-8", errors="replace"), old, new)
    if not text:
        return None
    path = out / "changelog-excerpt.md"
    path.write_text(text + "\n", encoding="utf-8")
    return str(path)


def _compare_hint(repository, directory, name: str, old: str, new: str):
    match = re.search(r"github\.com[/:]([^/]+)/([^/#?]+)", repository or "")
    if not match:
        return None
    repo = f"{match.group(1)}/{match.group(2).removesuffix('.git')}"
    if directory:
        # A package published from a monorepo rarely has its own release tags; its history is its directory's.
        return f"gh api 'repos/{repo}/commits?path={directory}&per_page=100' (commits to the package's directory)"
    return (f"gh api repos/{repo}/compare/v{old}...v{new} (check the tag names first with "
            f"gh api repos/{repo}/tags; they may be {old}, {name}@{old} or {name}-v{old})")

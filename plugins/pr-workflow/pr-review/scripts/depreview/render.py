"""Markdown and JSON views of a lockfile comparison Report."""

from dataclasses import asdict

from .classify import DEEP, LIST, SKIM, Report

_MAX_VIA = 5
_MAX_IMPORTERS = 3
_MAX_LISTED = 60


def to_json(report: Report) -> dict:
    return {
        "targets": report.targets,
        "target_versions": report.target_versions,
        "limits": asdict(report.limits),
        "counts": {tier: sum(c.tier == tier for c in report.changes) for tier in (DEEP, SKIM, LIST)},
        "overrides": [{"selector": s, "from": o, "to": n} for s, o, n in report.overrides],
        "warnings": report.warnings,
        "changes": [
            {**asdict(c), "bump": asdict(c.bump) if c.bump else None}
            for c in report.changes
        ],
    }


def to_markdown(report: Report) -> str:
    counts = {tier: [c for c in report.changes if c.tier == tier] for tier in (DEEP, SKIM, LIST)}
    lines = [
        f"## Lockfile diff: {len(report.changes)} packages changed "
        f"({len(counts[DEEP])} deep, {len(counts[SKIM])} skim, {len(counts[LIST])} listed)",
        "",
        f"Targets: {', '.join(report.targets) or '(none given)'} · max depth {report.limits.max_depth} · "
        f"cap {report.limits.max_deep} full diffs",
    ]
    if report.target_versions:
        installed = "; ".join(f"{t} {', '.join(v) or '(not installed)'}" for t, v in report.target_versions.items())
        lines.append(f"Head installs: {installed}")
    if report.overrides:
        lines += ["", "### Overrides / resolutions changed", ""]
        lines += [f"- `{s}`: {o or '(none)'} → {n or '(removed)'}" for s, o, n in report.overrides]
    for tier, title in ((DEEP, "Deep review: diff the release"), (SKIM, "Skim: read the release notes")):
        if counts[tier]:
            lines += ["", f"### {title}", "", _TABLE_HEAD, _TABLE_RULE]
            lines += [_row(c) for c in counts[tier]]
            switched = [c for c in counts[tier] if c.consumers]
            if switched:
                lines += ["", "Consumers that switched version:", ""]
                lines += [f"- `{c.name}`: " + "; ".join(c.consumers) for c in switched]
    if counts[LIST]:
        lines += ["", f"### Listed only ({len(counts[LIST])})", ""]
        lines += [f"- {_compact(c)}" for c in counts[LIST][:_MAX_LISTED]]
        if len(counts[LIST]) > _MAX_LISTED:
            lines.append(f"- … {len(counts[LIST]) - _MAX_LISTED} more (see --json)")
    if report.warnings:
        lines += ["", "### Warnings", ""] + [f"- {w}" for w in report.warnings]
    return "\n".join(lines) + "\n"


_TABLE_HEAD = "| Package | From → To | Bump | Depth | Relation | Scope | Used by | Via | Why |"
_TABLE_RULE = "|---|---|---|---|---|---|---|---|---|"


def _row(change) -> str:
    cells = [
        f"`{change.name}`",
        _versions(change),
        _bump(change),
        str(change.depth) if change.depth is not None else "?",
        change.relation,
        change.scope,
        _importers(change.importers),
        _via(change.via),
        "; ".join(change.reasons),
    ]
    return "| " + " | ".join(cells) + " |"


def _compact(change) -> str:
    depth = change.depth if change.depth is not None else "?"
    extra = "; collateral" if change.relation == "unrelated" else ""
    return f"`{change.name}` {_versions(change)} ({_bump(change)}, depth {depth}, {change.scope}{extra})"


def _versions(change) -> str:
    return f"{', '.join(change.old_versions) or '—'} → {', '.join(change.new_versions) or '—'}"


def _bump(change) -> str:
    if change.bump is None:
        return change.kind
    return change.bump.kind + (" ⚠" if change.bump.semver_breaking else "")


def _importers(importers: list) -> str:
    shown = ", ".join(importers[:_MAX_IMPORTERS])
    return shown + (f" +{len(importers) - _MAX_IMPORTERS}" if len(importers) > _MAX_IMPORTERS else "")


def _via(via: list) -> str:
    if len(via) > _MAX_VIA:
        via = via[:2] + ["…"] + via[-(_MAX_VIA - 3):]
    return " › ".join(via)

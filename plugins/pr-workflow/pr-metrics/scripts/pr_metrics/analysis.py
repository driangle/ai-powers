"""Selects the PRs in the window, runs every metric for the whole set and for each group, and
assembles the results document the report is rendered from (see references/results-format.md)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .config import Config
from .metrics import Context, Metric
from .model import PullRequest

OVERALL = ("overall", "all")
NO_PROJECT = "(no project)"


def window_bounds(config: Config, zone: Any) -> Tuple[datetime, datetime]:
    start = datetime.combine(config.since, time.min, tzinfo=zone)
    end = datetime.combine(config.until, time.max, tzinfo=zone)
    return start, end


def select_in_window(
    prs: Sequence[PullRequest], config: Config, start: datetime, end: datetime
) -> Tuple[List[PullRequest], List[Tuple[PullRequest, str]]]:
    """Keeps PRs merged (or created, per `window_by`) in the window, plus PRs still open when
    `include_open` is set. Returns the kept PRs and, for the rest, why they were left out."""
    kept: List[PullRequest] = []
    skipped: List[Tuple[PullRequest, str]] = []
    for pr in prs:
        reason = _exclusion(pr, config, start, end)
        if reason is None:
            kept.append(pr)
        else:
            skipped.append((pr, reason))
    return kept, skipped


def group_prs(prs: Sequence[PullRequest], dimensions: Sequence[str]) -> Dict[Tuple[str, str], List[PullRequest]]:
    """The whole set under ("overall", "all"), then one group per value of each dimension. A PR
    linked to several projects is counted in each of them."""
    groups: Dict[Tuple[str, str], List[PullRequest]] = {OVERALL: list(prs)}
    for dimension in dimensions:
        by_value: Dict[str, List[PullRequest]] = defaultdict(list)
        for pr in prs:
            for value in _values(pr, dimension):
                by_value[value].append(pr)
        for value in sorted(by_value):
            groups[(dimension, value)] = by_value[value]
    return groups


def analyse(
    prs: Sequence[PullRequest], metrics: Sequence[Metric], ctx: Context, extra: Dict[str, Any]
) -> Dict[str, Any]:
    groups = group_prs(prs, ctx.config.group_by)
    results: List[Dict[str, Any]] = []
    per_pr: Dict[str, Dict[str, float]] = defaultdict(dict)
    for metric in metrics:
        by_group = {}
        for (dimension, value), members in groups.items():
            result = metric.compute(members, ctx)
            by_group[f"{dimension}:{value}"] = {
                "summary": result.summary,
                "rows": result.rows,
                "evidence": {key: evidence.to_json() for key, evidence in result.evidence.items()},
            }
            if (dimension, value) == OVERALL:
                for key, number in result.per_pr.items():
                    per_pr[key][metric.id] = number
        results.append({**metric.describe(), "groups": by_group})
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window": {
            "since": ctx.config.since.isoformat(),
            "until": ctx.config.until.isoformat(),
            "by": ctx.config.window_by,
            "include_open": ctx.config.include_open,
        },
        "clock": {
            "mode": ctx.config.clock.mode,
            "unit": ctx.clock.unit_label,
            "timezone": ctx.config.clock.timezone,
            "workdays": list(ctx.config.clock.workdays),
            "hours": f"{ctx.config.clock.start}-{ctx.config.clock.end}",
        },
        "groups": [
            {"id": f"{dimension}:{value}", "dimension": dimension, "value": value, "prs": len(members)}
            for (dimension, value), members in groups.items()
        ],
        "metrics": results,
        "prs": [_pr_record(pr, per_pr.get(pr.key, {})) for pr in prs],
        **extra,
    }


def _exclusion(pr: PullRequest, config: Config, start: datetime, end: datetime) -> Optional[str]:
    if config.authors and pr.author not in config.authors:
        return f"author {pr.author} is not in the configured authors"
    if pr.state == "OPEN":
        if config.include_open and pr.created_at <= end:
            return None
        return "still open"
    if pr.merged_at is None:
        return "closed without merging"
    moment = pr.merged_at if config.window_by == "merged" else pr.created_at
    if not start <= moment <= end:
        return f"{config.window_by} outside the window"
    return None


def _values(pr: PullRequest, dimension: str) -> Tuple[str, ...]:
    if dimension == "project":
        return pr.projects or (NO_PROJECT,)
    if dimension == "repo":
        return (pr.repo,)
    return (pr.author,)


def _pr_record(pr: PullRequest, values: Dict[str, float]) -> Dict[str, Any]:
    return {
        "key": pr.key,
        "url": pr.url,
        "title": pr.title,
        "author": pr.author,
        "repo": pr.repo,
        "state": pr.state,
        "projects": list(pr.projects),
        "tickets": list(pr.tickets),
        "created_at": pr.created_at.isoformat(),
        "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
        "lines_changed": pr.lines_changed,
        "files_changed": pr.changed_files,
        "metrics": values,
    }

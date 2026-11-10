"""Work in progress: how many PRs each author has open at once, sampled at the end of every
working day in the window. Many parallel open PRs usually means PRs are waiting on reviews."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Sequence

from ..model import PullRequest
from ..stats import percentile
from .base import COUNT, NUMBER, Context, Evidence, EvidenceItem, Field, Metric, MetricResult


class WorkInProgress(Metric):
    id = "work_in_progress"
    title = "Open PRs per author"
    description = (
        "PRs open at the same time per author, sampled at the end of each working day on which "
        "the author had at least one PR open."
    )
    headline = "mean_open"
    summary_fields = (
        Field("authors", "Authors", COUNT),
        Field("mean_open", "Typical author's mean open", NUMBER),
        Field("max_open", "Most open at once", COUNT),
        Field("open_now", "Open now", COUNT),
    )
    row_fields = (
        Field("author", "Author", "text"),
        Field("mean_open", "Mean open", NUMBER),
        Field("max_open", "Most at once", COUNT),
        Field("open_now", "Open now", COUNT),
    )

    def compute(self, prs: Sequence[PullRequest], ctx: Context) -> MetricResult:
        samples = _sample_times(ctx)
        by_author: Dict[str, List[PullRequest]] = defaultdict(list)
        for pr in prs:
            by_author[pr.author].append(pr)
        rows = []
        for author, authored in sorted(by_author.items()):
            counts = [sum(1 for pr in authored if _open_at(pr, moment)) for moment in samples]
            active = [count for count in counts if count > 0]
            rows.append(
                {
                    "author": author,
                    "mean_open": sum(active) / len(active) if active else 0.0,
                    "max_open": max(counts) if counts else 0,
                    "open_now": sum(1 for pr in authored if pr.state == "OPEN"),
                }
            )
        rows.sort(key=lambda row: row["mean_open"], reverse=True)
        summary = {
            "authors": len(rows),
            "mean_open": percentile([row["mean_open"] for row in rows], 0.5) if rows else None,
            "max_open": max((row["max_open"] for row in rows), default=None),
            "open_now": sum(row["open_now"] for row in rows),
        }
        open_now = [
            EvidenceItem(pr.key, f"open since {pr.created_at.date().isoformat()}")
            for pr in sorted(prs, key=lambda pr: pr.created_at)
            if pr.state == "OPEN"
        ]
        return MetricResult(summary=summary, rows=rows, evidence={"open_now": Evidence("Open now", open_now)})


def _sample_times(ctx: Context) -> List[datetime]:
    zone = ctx.clock.zone
    day = ctx.window_start.astimezone(zone).date()
    last = ctx.window_end.astimezone(zone).date()
    samples = []
    while day <= last:
        if ctx.clock.is_workday(day):
            samples.append(datetime.combine(day, ctx.clock.end, tzinfo=zone))
        day += timedelta(days=1)
    return samples


def _open_at(pr: PullRequest, moment: datetime) -> bool:
    ended = pr.merged_at or pr.closed_at
    return pr.created_at <= moment and (ended is None or ended > moment)

"""Merged PRs per ISO week across the window, weeks without merges included."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Sequence

from ..model import PullRequest
from ..stats import percentile
from .base import COUNT, NUMBER, Context, Field, Metric, MetricResult


class Throughput(Metric):
    id = "throughput"
    title = "Throughput"
    description = "Merged PRs per week. Read it as a trend; it is not a target for individuals."
    headline = "weekly_median"
    lower_is_better = False
    summary_fields = (
        Field("merged", "Merged PRs", COUNT),
        Field("weeks", "Weeks", COUNT),
        Field("weekly_median", "Median per week", NUMBER),
        Field("weekly_max", "Busiest week", COUNT),
    )
    row_fields = (Field("week", "Week starting", "text"), Field("merged", "Merged", COUNT))

    def compute(self, prs: Sequence[PullRequest], ctx: Context) -> MetricResult:
        counts = Counter(_week_start(pr.merged_at.date()) for pr in prs if pr.merged_at)
        week = _week_start(ctx.window_start.date())
        last = _week_start(ctx.window_end.date())
        rows = []
        while week <= last:
            rows.append({"week": week.isoformat(), "merged": counts.get(week, 0)})
            week += timedelta(weeks=1)
        per_week = [row["merged"] for row in rows]
        summary = {
            "merged": sum(counts.values()),
            "weeks": len(rows),
            "weekly_median": percentile(per_week, 0.5),
            "weekly_max": max(per_week) if per_week else None,
        }
        return MetricResult(summary=summary, rows=rows)


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())

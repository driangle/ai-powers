"""Stacked PRs: PRs based, at any point, on another PR's branch instead of the default branch.

The wait is how long a stacked PR was ready for review while the PR below it was still
unmerged. Reviewers usually hold a stacked PR until its base lands, so this is the time the
bottom of the stack holds the rest up. GitHub retargets a stacked PR once its base merges, and authors
restack PRs after opening them, so the base comes from the PR's whole base history.
"""

from __future__ import annotations

from typing import Dict, Sequence

from ..lifecycle import ready_for_review_at
from ..model import PullRequest
from ..stats import share, summarize
from ..units import format_hours
from .base import COUNT, HOURS, RATIO, Context, Evidence, EvidenceItem, Field, Metric, MetricResult


class StackWait(Metric):
    id = "stack_wait"
    title = "Stacked PR wait"
    description = "Time a stacked PR was ready for review while the PR below it was still unmerged."
    headline = "median"
    per_pr_unit = HOURS
    summary_fields = (
        Field("stacked", "Stacked PRs", COUNT),
        Field("stacked_share", "Share stacked", RATIO),
        Field("n", "Ready before base merged", COUNT),
        Field("median", "Median wait", HOURS),
        Field("p90", "P90 wait", HOURS),
    )

    def compute(self, prs: Sequence[PullRequest], ctx: Context) -> MetricResult:
        by_head = {(pr.repo, pr.head_ref): pr for pr in prs}
        stacked = [pr for pr in prs if pr.stacked_on]
        waits: Dict[str, float] = {}
        for pr in stacked:
            base = by_head.get((pr.repo, pr.stacked_on))
            ready = ready_for_review_at(pr)
            if base and base.merged_at and ready and ready < base.merged_at:
                waits[pr.key] = ctx.clock.hours_between(ready, base.merged_at)
        distribution = summarize(list(waits.values()))
        summary = {
            "stacked": len(stacked),
            "stacked_share": share(len(stacked), len(prs)),
            "n": distribution["n"],
            "median": distribution["median"],
            "p90": distribution["p90"],
        }
        items = [
            EvidenceItem(
                pr.key,
                f"stacked on {pr.stacked_on}"
                + (f" · waited {format_hours(waits[pr.key])}" if pr.key in waits else ""),
            )
            for pr in stacked
        ]
        return MetricResult(summary=summary, per_pr=waits, evidence={"stacked": Evidence("Stacked PRs", items)})

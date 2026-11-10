"""CI failures before merge, from the check rollup of each commit on the PR.

The rollup reflects the latest run of each check, so a failure that passed on a re-run is not
counted: the numbers are a floor, and flaky CI shows up as slow merges more than as failures.
"""

from __future__ import annotations

from typing import Dict, Sequence

from ..model import PullRequest
from ..stats import percentile, share
from .base import COUNT, NUMBER, RATIO, Context, Evidence, EvidenceItem, Field, Metric, MetricResult

FAILED = {"FAILURE", "ERROR"}


class CiFailures(Metric):
    id = "ci_failures"
    title = "CI failures"
    description = "PRs with at least one commit whose checks failed, and how many such commits."
    headline = "share"
    per_pr_unit = COUNT
    summary_fields = (
        Field("n", "PRs with checks", COUNT),
        Field("share", "Had a failing commit", RATIO),
        Field("mean_failing_commits", "Mean failing commits", NUMBER),
        Field("p90_failing_commits", "P90 failing commits", NUMBER),
    )

    def compute(self, prs: Sequence[PullRequest], ctx: Context) -> MetricResult:
        failing: Dict[str, float] = {}
        checked: Dict[str, int] = {}
        for pr in prs:
            states = [commit.ci_state for commit in pr.commits if commit.ci_state]
            if states:
                failing[pr.key] = float(sum(1 for state in states if state in FAILED))
                checked[pr.key] = len(states)
        counts = list(failing.values())
        summary = {
            "n": len(counts),
            "share": share(sum(1 for count in counts if count), len(counts)),
            "mean_failing_commits": sum(counts) / len(counts) if counts else None,
            "p90_failing_commits": percentile(counts, 0.9),
        }
        items = [
            EvidenceItem(key, f"{count:.0f} of {checked[key]} commits with failing checks")
            for key, count in sorted(failing.items(), key=lambda item: item[1], reverse=True)
            if count
        ]
        return MetricResult(summary=summary, per_pr=failing, evidence={"share": Evidence("Had a failing commit", items)})

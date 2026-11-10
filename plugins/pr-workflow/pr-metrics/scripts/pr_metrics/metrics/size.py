"""PR size: the strongest single predictor of how fast and how well a PR gets reviewed."""

from __future__ import annotations

from typing import Sequence

from ..model import PullRequest
from ..sizing import reviewable_lines, test_lines
from ..stats import percentile, share, summarize
from .base import COUNT, LINES, RATIO, Context, Evidence, EvidenceItem, Field, Metric, MetricResult


class PrSize(Metric):
    id = "pr_size"
    title = "PR size"
    description = (
        "Lines added plus deleted, without lock files, snapshots and generated code, split into "
        "test and other code. Large PRs wait longer and get shallower reviews; a large PR that is "
        "mostly tests is less of a problem than one that is mostly code."
    )
    headline = "median"
    per_pr_unit = LINES
    summary_fields = (
        Field("n", "PRs", COUNT),
        Field("median", "Median lines", LINES),
        Field("p90", "P90 lines", LINES),
        Field("median_code_lines", "Median non-test lines", LINES),
        Field("test_share", "Lines in tests", RATIO),
        Field("median_files", "Median files", COUNT),
        Field("large_share", "Large PRs", RATIO),
    )

    def compute(self, prs: Sequence[PullRequest], ctx: Context) -> MetricResult:
        ignore = ctx.config.size_ignore_files
        lines = [reviewable_lines(pr, ignore) for pr in prs]
        tests = [test_lines(pr, ignore, ctx.config.test_files) for pr in prs]
        code = [total - test for total, test in zip(lines, tests)]
        large = sum(1 for value in lines if value > ctx.config.large_pr_lines)
        distribution = summarize(lines)
        summary = {
            "n": distribution["n"],
            "median": distribution["median"],
            "p90": distribution["p90"],
            "median_code_lines": percentile(code, 0.5),
            "test_share": share(sum(tests), sum(lines)),
            "median_files": percentile([pr.changed_files for pr in prs], 0.5),
            "large_share": share(large, len(prs)),
        }
        large_prs = sorted(
            (item for item in zip(prs, lines, tests) if item[1] > ctx.config.large_pr_lines),
            key=lambda item: item[1],
            reverse=True,
        )
        evidence = {
            "large_share": Evidence(
                f"Over {ctx.config.large_pr_lines} lines",
                [
                    EvidenceItem(pr.key, f"{total:,} lines ({test:,} in tests) in {pr.changed_files} files")
                    for pr, total, test in large_prs
                ],
            )
        }
        per_pr = {pr.key: float(value) for pr, value in zip(prs, lines)}
        return MetricResult(summary=summary, per_pr=per_pr, evidence=evidence)

"""Who does the reviewing: load per reviewer and author-to-reviewer pairs.

One or two people doing most reviews is both a bottleneck and a single point of failure;
authors who only ever get one reviewer point to knowledge silos.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, Sequence, Set

from ..model import PullRequest
from ..stats import share
from .base import COUNT, RATIO, Context, Field, Metric, MetricResult


class ReviewerLoad(Metric):
    id = "reviewer_load"
    title = "Reviewer load"
    description = "PRs reviewed per person. A high top-reviewer share means reviews depend on a few people."
    headline = "top_share"
    summary_fields = (
        Field("reviewers", "Reviewers", COUNT),
        Field("reviewed_prs", "Reviewed PRs", COUNT),
        Field("top_share", "Top reviewer's share", RATIO),
        Field("top_two_share", "Top two reviewers' share", RATIO),
    )
    row_fields = (
        Field("reviewer", "Reviewer", "text"),
        Field("prs", "PRs reviewed", COUNT),
        Field("approvals", "Approvals", COUNT),
        Field("changes_requested", "Changes requested", COUNT),
        Field("comments", "Inline comments", COUNT),
        Field("share", "Share of reviewed PRs", RATIO),
    )

    def compute(self, prs: Sequence[PullRequest], ctx: Context) -> MetricResult:
        reviewed_by: Dict[str, Set[str]] = defaultdict(set)
        tallies: Dict[str, Counter] = defaultdict(Counter)
        reviewed_prs = 0
        for pr in prs:
            reviews = ctx.reviewers.human_reviews(pr)
            reviewed_prs += bool(reviews)
            for review in reviews:
                reviewed_by[review.author].add(pr.key)
                tallies[review.author][review.state] += 1
                tallies[review.author]["comments"] += review.comment_count
        rows = sorted(
            (
                {
                    "reviewer": reviewer,
                    "prs": len(keys),
                    "approvals": tallies[reviewer]["APPROVED"],
                    "changes_requested": tallies[reviewer]["CHANGES_REQUESTED"],
                    "comments": tallies[reviewer]["comments"],
                    "share": share(len(keys), reviewed_prs),
                }
                for reviewer, keys in reviewed_by.items()
            ),
            key=lambda row: row["prs"],
            reverse=True,
        )
        top_two: Set[str] = set()
        for row in rows[:2]:
            top_two |= reviewed_by[row["reviewer"]]
        summary = {
            "reviewers": len(rows),
            "reviewed_prs": reviewed_prs,
            "top_share": rows[0]["share"] if rows else None,
            "top_two_share": share(len(top_two), reviewed_prs),
        }
        return MetricResult(summary=summary, rows=rows)


class ReviewPairs(Metric):
    id = "review_pairs"
    title = "Who reviews whom"
    description = "PRs per author and reviewer pair, and authors whose PRs only one person reviews."
    headline = "single_reviewer_authors"
    summary_fields = (
        Field("authors", "Authors", COUNT),
        Field("pairs", "Author-reviewer pairs", COUNT),
        Field("single_reviewer_authors", "Authors with one reviewer", COUNT),
    )
    row_fields = (
        Field("author", "Author", "text"),
        Field("reviewer", "Reviewer", "text"),
        Field("prs", "PRs", COUNT),
        Field("share_of_author", "Share of author's PRs", RATIO),
    )

    def compute(self, prs: Sequence[PullRequest], ctx: Context) -> MetricResult:
        pairs: Counter = Counter()
        authored: Counter = Counter()
        for pr in prs:
            reviewers = {review.author for review in ctx.reviewers.human_reviews(pr)}
            if reviewers:
                authored[pr.author] += 1
            for reviewer in reviewers:
                pairs[(pr.author, reviewer)] += 1
        rows = [
            {"author": author, "reviewer": reviewer, "prs": count, "share_of_author": share(count, authored[author])}
            for (author, reviewer), count in sorted(pairs.items(), key=lambda item: (item[0][0], -item[1]))
        ]
        reviewers_per_author = Counter(author for author, _ in pairs)
        summary = {
            "authors": len(authored),
            "pairs": len(pairs),
            "single_reviewer_authors": sum(1 for count in reviewers_per_author.values() if count == 1),
        }
        return MetricResult(summary=summary, rows=rows)

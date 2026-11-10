"""How much a review changes a PR, and how closely reviewers read it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

from ..model import PullRequest
from ..sizing import reviewable_lines
from ..stats import percentile, share
from .base import COUNT, NUMBER, RATIO, Context, Evidence, EvidenceItem, Field, Metric, MetricResult


class ReviewRounds(Metric):
    id = "review_rounds"
    title = "Review rounds"
    description = (
        "Changes-requested reviews and commits pushed after the first review. High numbers point "
        "to unclear requirements or under-specified PRs. Commit times are author dates, so a "
        "rebase can shift them."
    )
    headline = "changes_requested_share"
    per_pr_unit = COUNT
    summary_fields = (
        Field("n", "Reviewed PRs", COUNT),
        Field("changes_requested_share", "Had changes requested", RATIO),
        Field("mean_changes_requested", "Mean change requests", NUMBER),
        Field("median_commits_after_review", "Median commits after review", NUMBER),
        Field("p90_commits_after_review", "P90 commits after review", NUMBER),
    )

    def compute(self, prs: Sequence[PullRequest], ctx: Context) -> MetricResult:
        change_requests: Dict[str, List[str]] = {}
        commits_after: Dict[str, float] = {}
        for pr in prs:
            reviews = ctx.reviewers.human_reviews(pr)
            if not reviews:
                continue
            first = reviews[0].submitted_at
            change_requests[pr.key] = [r.author for r in reviews if r.state == "CHANGES_REQUESTED"]
            commits_after[pr.key] = float(sum(1 for commit in pr.commits if commit.committed_at > first))
        reviewed = len(change_requests)
        p90 = percentile(list(commits_after.values()), 0.9)
        summary = {
            "n": reviewed,
            "changes_requested_share": share(sum(1 for c in change_requests.values() if c), reviewed),
            "mean_changes_requested": sum(len(c) for c in change_requests.values()) / reviewed if reviewed else None,
            "median_commits_after_review": percentile(list(commits_after.values()), 0.5),
            "p90_commits_after_review": p90,
        }
        evidence = {
            "changes_requested_share": Evidence(
                "Had changes requested",
                [
                    EvidenceItem(key, f"{len(authors)} change request(s) by {', '.join(sorted(set(authors)))}")
                    for key, authors in change_requests.items()
                    if authors
                ],
            ),
            "p90_commits_after_review": Evidence(
                "Commits after the first review at or above the P90",
                [
                    EvidenceItem(key, f"{count:.0f} commits after the first review")
                    for key, count in sorted(commits_after.items(), key=lambda item: item[1], reverse=True)
                    if p90 is not None and count >= p90 and count > 0
                ],
            ),
        }
        return MetricResult(summary=summary, per_pr=commits_after, evidence=evidence)


@dataclass(frozen=True)
class Feedback:
    """Everything reviewers wrote on a PR, by where they wrote it."""

    inline: int  # comments on the diff
    review_notes: int  # reviews with their own text
    conversation: int  # comments in the PR conversation
    approvers: List[str]
    change_requested: bool

    @property
    def total(self) -> int:
        return self.inline + self.review_notes + self.conversation

    def describe(self, lines: int) -> str:
        approved = f"approved by {', '.join(self.approvers)}" if self.approvers else "not approved"
        return (
            f"{lines:,} lines · {approved} · {self.inline} inline, {self.review_notes} review notes, "
            f"{self.conversation} conversation comments"
        )


class ReviewDepth(Metric):
    id = "review_depth"
    title = "Review depth"
    description = (
        "Reviewer feedback per 100 changed lines, counting inline comments, reviews with text and "
        "conversation comments by teammates other than the author (bots excluded), and large PRs "
        "approved with no feedback or change request, which suggests rubber-stamping. Feedback "
        "given outside GitHub, such as in a call or on Slack, is not visible here."
    )
    headline = "median"
    lower_is_better = False
    per_pr_unit = NUMBER
    summary_fields = (
        Field("n", "Reviewed PRs", COUNT),
        Field("median", "Median feedback / 100 lines", NUMBER),
        Field("large", "Large reviewed PRs", COUNT),
        Field("silent_large", "Large PRs approved silently", COUNT),
        Field("silent_large_share", "Share of large PRs", RATIO),
    )

    def compute(self, prs: Sequence[PullRequest], ctx: Context) -> MetricResult:
        density: Dict[str, float] = {}
        large: List[EvidenceItem] = []
        silent: List[EvidenceItem] = []
        for pr in prs:
            reviews = ctx.reviewers.human_reviews(pr)
            if not reviews:
                continue
            feedback = Feedback(
                inline=sum(review.comment_count for review in reviews),
                review_notes=sum(1 for review in reviews if review.has_body),
                conversation=len(ctx.reviewers.human_comments(pr)),
                approvers=sorted({review.author for review in reviews if review.state == "APPROVED"}),
                change_requested=any(review.state == "CHANGES_REQUESTED" for review in reviews),
            )
            lines = reviewable_lines(pr, ctx.config.size_ignore_files)
            density[pr.key] = feedback.total * 100 / max(lines, 1)
            if lines > ctx.config.large_pr_lines:
                item = EvidenceItem(pr.key, feedback.describe(lines))
                large.append(item)
                if feedback.approvers and not feedback.total and not feedback.change_requested:
                    silent.append(item)
        summary = {
            "n": len(density),
            "median": percentile(list(density.values()), 0.5),
            "large": len(large),
            "silent_large": len(silent),
            "silent_large_share": share(len(silent), len(large)),
        }
        evidence = {
            "silent_large": Evidence("Large PRs approved with no feedback", silent),
            "large": Evidence("Large reviewed PRs and the feedback they got", large),
        }
        return MetricResult(summary=summary, per_pr=density, evidence=evidence)

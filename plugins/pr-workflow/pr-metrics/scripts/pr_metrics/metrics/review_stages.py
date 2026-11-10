"""Where a PR's time goes, one stage at a time, plus the end-to-end review cycle.

Milestones come from `lifecycle`; a stage whose end comes before its start (a review left while
the PR was still a draft) counts as zero.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple

from ..lifecycle import ready_for_review_at
from ..model import PullRequest
from .base import Context, DurationMetric

Span = Optional[Tuple[datetime, datetime]]


class ReviewCycleTime(DurationMetric):
    id = "review_cycle_time"
    title = "Review cycle time"
    description = "From ready for review to merged. The headline velocity number."

    def span(self, pr: PullRequest, ctx: Context) -> Span:
        start = ready_for_review_at(pr)
        return (start, pr.merged_at) if start and pr.merged_at else None


class DraftTime(DurationMetric):
    id = "draft_time"
    title = "Time before review"
    description = "From opened to ready for review: time spent as a draft or before asking anyone."
    lower_is_better = None

    def span(self, pr: PullRequest, ctx: Context) -> Span:
        ready = ready_for_review_at(pr)
        return (pr.created_at, ready) if ready else None


class TimeToFirstReview(DurationMetric):
    id = "time_to_first_review"
    title = "Time to first review"
    description = "From ready for review to the first review by a teammate. The stage the team controls best."

    def span(self, pr: PullRequest, ctx: Context) -> Span:
        start = ready_for_review_at(pr)
        review = ctx.reviewers.first_review(pr)
        return (start, review.submitted_at) if start and review else None


class ReviewToApproval(DurationMetric):
    id = "review_to_approval"
    title = "First review to approval"
    description = "From the first review to the first approval. Long times point to many rounds or unclear PRs."

    def span(self, pr: PullRequest, ctx: Context) -> Span:
        review = ctx.reviewers.first_review(pr)
        approval = ctx.reviewers.first_approval(pr)
        return (review.submitted_at, approval.submitted_at) if review and approval else None


class ApprovalToMerge(DurationMetric):
    id = "approval_to_merge"
    title = "Approval to merge"
    description = "From the first approval to the merge: CI, merge queues, stacked PRs and follow-up changes."

    def span(self, pr: PullRequest, ctx: Context) -> Span:
        approval = ctx.reviewers.first_approval(pr)
        return (approval.submitted_at, pr.merged_at) if approval and pr.merged_at else None

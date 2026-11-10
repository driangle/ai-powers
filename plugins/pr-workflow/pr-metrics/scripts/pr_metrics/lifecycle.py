"""Milestones in a PR's life that several metrics share, so each is defined once.

A PR is "ready for review" when:
- it was opened as a draft: the first time it was marked ready for review;
- otherwise: the first review request, or the moment it was opened if nobody was requested
  (reviewers then find it through CODEOWNERS or the team's channel).
"""

from __future__ import annotations

from datetime import datetime
from typing import FrozenSet, List, Optional

from .model import Comment, PullRequest, Review


class ReviewerFilter:
    """Decides which reviews count as a human teammate's review of someone else's PR."""

    def __init__(self, ignored: FrozenSet[str], ignore_bots: bool):
        self.ignored = ignored
        self.ignore_bots = ignore_bots

    def counts(self, author: str, is_bot: bool, pr: PullRequest) -> bool:
        return author != pr.author and author not in self.ignored and not (self.ignore_bots and is_bot)

    def human_reviews(self, pr: PullRequest) -> List[Review]:
        return sorted(
            (r for r in pr.reviews if self.counts(r.author, r.is_bot, pr) and r.state != "PENDING"),
            key=lambda review: review.submitted_at,
        )

    def human_comments(self, pr: PullRequest) -> List[Comment]:
        """Conversation comments by reviewers: teammates other than the author, bots excluded."""
        return [c for c in pr.comments if self.counts(c.author, c.is_bot, pr)]

    def first_review(self, pr: PullRequest) -> Optional[Review]:
        reviews = self.human_reviews(pr)
        return reviews[0] if reviews else None

    def first_approval(self, pr: PullRequest) -> Optional[Review]:
        approvals = [review for review in self.human_reviews(pr) if review.state == "APPROVED"]
        return approvals[0] if approvals else None


def ready_for_review_at(pr: PullRequest) -> Optional[datetime]:
    if pr.created_as_draft:
        return pr.first_ready_for_review_at
    return pr.first_review_requested_at or pr.created_at

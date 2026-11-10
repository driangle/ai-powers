"""The pull request data every metric reads, independent of where it was fetched from."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple


@dataclass(frozen=True)
class Review:
    author: str
    is_bot: bool
    state: str  # APPROVED, CHANGES_REQUESTED, COMMENTED or DISMISSED
    submitted_at: datetime
    comment_count: int  # inline comments on the diff
    has_body: bool = False  # the review's own text, shown in the conversation


@dataclass(frozen=True)
class Comment:
    """A comment in the PR conversation, outside any review."""

    author: str
    is_bot: bool
    created_at: datetime


@dataclass(frozen=True)
class FileChange:
    path: str
    additions: int
    deletions: int

    @property
    def lines(self) -> int:
        return self.additions + self.deletions


@dataclass(frozen=True)
class Commit:
    committed_at: datetime
    ci_state: Optional[str]  # the commit's check rollup: SUCCESS, FAILURE, ERROR, PENDING...


@dataclass(frozen=True)
class PullRequest:
    repo: str  # owner/name
    number: int
    url: str
    title: str
    author: str
    state: str  # OPEN, MERGED or CLOSED
    created_at: datetime
    merged_at: Optional[datetime]
    closed_at: Optional[datetime]
    additions: int
    deletions: int
    changed_files: int
    files: Tuple[FileChange, ...]
    default_branch: str
    base_ref: str
    head_ref: str
    base_ref_history: Tuple[str, ...]  # every base the PR had, oldest first, the current one last
    created_as_draft: bool
    first_review_requested_at: Optional[datetime]
    first_ready_for_review_at: Optional[datetime]
    reviews: Tuple[Review, ...]
    commits: Tuple[Commit, ...]
    comments: Tuple[Comment, ...] = ()
    projects: Tuple[str, ...] = ()
    tickets: Tuple[str, ...] = ()

    @property
    def key(self) -> str:
        return f"{self.repo}#{self.number}"

    @property
    def lines_changed(self) -> int:
        return self.additions + self.deletions

    @property
    def is_merged(self) -> bool:
        return self.merged_at is not None

    @property
    def paths(self) -> Tuple[str, ...]:
        return tuple(file.path for file in self.files)

    @property
    def stacked_on(self) -> Optional[str]:
        """The last non-default branch the PR was based on, if it was ever stacked."""
        stacked = [ref for ref in self.base_ref_history if ref != self.default_branch]
        return stacked[-1] if stacked else None


@dataclass(frozen=True)
class FollowUpCandidate:
    """A merged PR whose title marks it as a fix or a revert, used to spot follow-up work."""

    repo: str
    number: int
    url: str
    title: str
    body: str
    merged_at: datetime
    files: Tuple[str, ...]

    @property
    def key(self) -> str:
        return f"{self.repo}#{self.number}"

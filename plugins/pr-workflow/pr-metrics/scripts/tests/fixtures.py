"""Builders for test PRs: every field has a sensible default so a test states only what it checks."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from pr_metrics.config import ClockConfig, Config
from pr_metrics.lifecycle import ReviewerFilter
from pr_metrics.metrics import Context
from pr_metrics.model import Commit, FileChange, PullRequest, Review


def at(day: int, hour: int = 10, minute: int = 0) -> datetime:
    """A moment in October 2026, in UTC. 2026-10-05 is a Monday."""
    return datetime(2026, 10, day, hour, minute, tzinfo=timezone.utc)


def review(author: str, state: str, when: datetime, comments: int = 0, bot: bool = False) -> Review:
    return Review(author=author, is_bot=bot, state=state, submitted_at=when, comment_count=comments)


def make_pr(number: int = 1, **overrides: Any) -> PullRequest:
    base = PullRequest(
        repo="acme/app",
        number=number,
        url=f"https://github.com/acme/app/pull/{number}",
        title=f"PR {number}",
        author="alice",
        state="MERGED",
        created_at=at(5, 9),
        merged_at=at(5, 15),
        closed_at=at(5, 15),
        additions=100,
        deletions=20,
        changed_files=2,
        files=(FileChange("src/app.ts", 80, 20), FileChange("src/app.test.ts", 20, 0)),
        default_branch="main",
        base_ref="main",
        head_ref=f"alice/branch-{number}",
        base_ref_history=("main",),
        created_as_draft=False,
        first_review_requested_at=at(5, 10),
        first_ready_for_review_at=None,
        reviews=(review("bob", "APPROVED", at(5, 12)),),
        commits=(Commit(at(5, 9), "SUCCESS"),),
    )
    return replace(base, **overrides)


def make_context(**config_overrides: Any) -> Context:
    clock_config = config_overrides.pop("clock", ClockConfig(mode="calendar", timezone="UTC"))
    config = Config(since=at(1).date(), until=at(31).date(), clock=clock_config, **config_overrides)
    return Context(
        config=config,
        clock=config.clock.build(),
        reviewers=ReviewerFilter(frozenset(config.ignore_reviewers), config.ignore_bots),
        window_start=at(1, 0),
        window_end=at(31, 23),
    )

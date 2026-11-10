"""PR size as a reviewer experiences it: changed lines minus files nobody reads line by line
(lock files, snapshots, generated code), as configured in `size_ignore_files`."""

from __future__ import annotations

from fnmatch import fnmatch
from typing import Sequence

from .model import PullRequest


def matches_any(path: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch(path, pattern) for pattern in patterns)


def test_lines(pr: PullRequest, ignore: Sequence[str], tests: Sequence[str]) -> int:
    """Lines in test files among the listed files, so a lower bound for PRs over 100 files."""
    return sum(
        file.lines for file in pr.files if matches_any(file.path, tests) and not matches_any(file.path, ignore)
    )


def reviewable_lines(pr: PullRequest, ignore: Sequence[str]) -> int:
    """GitHub lists at most 100 files per PR, so ignored lines are subtracted from the PR's total
    rather than summing the listed files."""
    ignored = sum(file.lines for file in pr.files if matches_any(file.path, ignore))
    return pr.lines_changed - ignored

"""Quality signals after the merge: fix PRs that touch the same files soon after, and reverts.

Both read the follow-up candidates: merged PRs in the same repositories whose title carries a
fix keyword or "revert" (configured under `follow_up`).
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Dict, List, Sequence

from ..model import FollowUpCandidate, PullRequest
from ..sizing import matches_any
from ..units import format_hours
from ..stats import share
from .base import COUNT, HOURS, RATIO, Context, Evidence, EvidenceItem, Field, Metric, MetricResult

LINK_FIELDS = (
    Field("pr", "PR", "link"),
    Field("follow_up", "Follow-up", "link"),
    Field("follow_up_title", "Follow-up title", "text"),
    Field("hours_after", "Merged after", HOURS),
)


class FollowUpFixes(Metric):
    id = "follow_up_fixes"
    title = "Follow-up fixes"
    description = (
        "Merged PRs followed within the follow-up window by a fix PR touching the same files. "
        "An upper bound on the change failure rate: a fix to a shared file can match several PRs, "
        "so read the matches. Lock files and changelogs are ignored."
    )
    headline = "share"
    needs_follow_ups = True
    summary_fields = (
        Field("n", "Merged PRs", COUNT),
        Field("with_follow_up", "Followed by a fix", COUNT),
        Field("share", "Share", RATIO),
    )
    row_fields = LINK_FIELDS

    def compute(self, prs: Sequence[PullRequest], ctx: Context) -> MetricResult:
        keywords = "|".join(re.escape(word) for word in ctx.config.follow_up.fix_keywords)
        is_fix = re.compile(rf"\b({keywords})\b", re.IGNORECASE)
        fixes = [
            c for c in ctx.follow_up_candidates if is_fix.search(c.title) and not _is_revert(c)
        ]
        window = timedelta(days=ctx.config.follow_up.window_days)
        ignored = ctx.config.follow_up.ignore_files
        rows: List[Dict[str, object]] = []
        items: List[EvidenceItem] = []
        merged = [pr for pr in prs if pr.merged_at]
        for pr in merged:
            files = {path for path in pr.paths if not matches_any(path, ignored)}
            for fix in fixes:
                if (
                    fix.repo == pr.repo
                    and fix.number != pr.number
                    and pr.merged_at < fix.merged_at <= pr.merged_at + window
                    and files.intersection(fix.files)
                ):
                    rows.append(_row(pr, fix, ctx))
                    shared = sorted(files.intersection(fix.files))
                    items.append(EvidenceItem(pr.key, _note(fix, ctx, pr, f"shares {_files(shared)}")))
        flagged = {row["pr"] for row in rows}
        summary = {
            "n": len(merged),
            "with_follow_up": len(flagged),
            "share": share(len(flagged), len(merged)),
        }
        evidence = {"with_follow_up": Evidence("Followed by a fix", items)}
        return MetricResult(summary=summary, rows=rows, evidence=evidence)


class Reverts(Metric):
    id = "reverts"
    title = "Reverts"
    description = "Merged PRs that a later PR reverted, matched by the PR number or title in the revert."
    headline = "reverted"
    needs_follow_ups = True
    summary_fields = (
        Field("n", "Merged PRs", COUNT),
        Field("reverted", "Reverted", COUNT),
        Field("share", "Share", RATIO),
    )
    row_fields = LINK_FIELDS

    def compute(self, prs: Sequence[PullRequest], ctx: Context) -> MetricResult:
        reverts = [c for c in ctx.follow_up_candidates if _is_revert(c)]
        merged = [pr for pr in prs if pr.merged_at]
        rows = [
            _row(pr, revert, ctx)
            for pr in merged
            for revert in reverts
            if revert.repo == pr.repo and _reverts(revert, pr)
        ]
        reverted = len({row["pr"] for row in rows})
        summary = {"n": len(merged), "reverted": reverted, "share": share(reverted, len(merged))}
        items = [
            EvidenceItem(pr.key, _note(revert, ctx, pr, "reverted"))
            for pr in merged
            for revert in reverts
            if revert.repo == pr.repo and _reverts(revert, pr)
        ]
        return MetricResult(summary=summary, rows=rows, evidence={"reverted": Evidence("Reverted", items)})


def _is_revert(candidate: FollowUpCandidate) -> bool:
    return candidate.title.lower().startswith("revert")


def _reverts(revert: FollowUpCandidate, pr: PullRequest) -> bool:
    mentions_number = re.search(rf"#{pr.number}\b", revert.body + " " + revert.title) is not None
    return mentions_number or pr.title in revert.title


def _note(follow_up: FollowUpCandidate, ctx: Context, pr: PullRequest, how: str) -> str:
    after = ctx.clock.hours_between(pr.merged_at, follow_up.merged_at) if pr.merged_at else 0.0
    return f"#{follow_up.number} \"{follow_up.title}\" {how}, merged {format_hours(after)} later"


def _files(paths: List[str]) -> str:
    names = [path.rsplit("/", 1)[-1] for path in paths]
    return ", ".join(names[:3]) + (f" and {len(names) - 3} more" if len(names) > 3 else "")


def _row(pr: PullRequest, follow_up: FollowUpCandidate, ctx: Context) -> Dict[str, object]:
    return {
        "pr": pr.url,
        "follow_up": follow_up.url,
        "follow_up_title": follow_up.title,
        "hours_after": ctx.clock.hours_between(pr.merged_at, follow_up.merged_at) if pr.merged_at else None,
    }

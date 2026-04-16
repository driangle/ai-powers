#!/usr/bin/env python3
"""Fetch open PRs matching filters, bucket them, emit JSON for a reviewer report.

Filters (at least one of teams/authors/repos required):
  --teams      Comma-separated team slugs. A PR matches if ANY of these teams
               is a requested reviewer.
  --authors    Comma-separated GitHub usernames. A PR matches if its author is
               in the list.
  --repos      Comma-separated repo names (org inferred from --org).

teams and authors are OR-combined within each list; across lists they AND —
the skill scopes to "PRs any listed team is reviewing AND authored by any
listed author". Repos scope further on top.

Drafts and bot-authored PRs are always excluded.

Output: JSON on stdout with PRs grouped into 4 mutually-exclusive buckets
(first match wins, in this precedence):
  1. needs_attention   — failing CI, merge conflict, stale (>= --stale-hours since
                        last activity), or old (>= --max-age-days since opened)
  2. ready_to_merge    — approved, CI green (or none), no conflict
  3. in_discussion     — changes requested
  4. awaiting_review   — default bucket for everything else

"stale" and "old" are intentionally separate signals: a PR can be young but
abandoned (stale, not old), or long-running but with recent activity (old, not
stale). Either is worth a reviewer's attention.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone


EXPECTED_GH_MAJOR = 2

PR_VIEW_FIELDS = (
    "number,title,url,author,isDraft,createdAt,updatedAt,additions,deletions,"
    "files,labels,reviewDecision,mergeable,reviews,statusCheckRollup"
)

SEARCH_FIELDS = "url,repository,isDraft,author"

BOT_LOGINS = {"dependabot", "renovate", "renovate-bot", "github-actions"}


def check_gh_version() -> None:
    """Abort early if `gh` is missing or its major version isn't what we built against.

    Flags and JSON fields used here (e.g. `--review-requested`, `statusCheckRollup`)
    can shift between major releases, so we refuse to run on an unknown major.
    """
    try:
        result = subprocess.run(
            ["gh", "--version"], capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        sys.stderr.write("gh CLI not found on PATH. Install from https://cli.github.com/.\n")
        sys.exit(1)

    if result.returncode != 0:
        sys.stderr.write(f"`gh --version` failed (exit {result.returncode}):\n{result.stderr}")
        sys.exit(1)

    match = re.search(r"gh version (\d+)\.(\d+)\.(\d+)", result.stdout)
    if not match:
        sys.stderr.write(f"Could not parse gh version from:\n{result.stdout}")
        sys.exit(1)

    major = int(match.group(1))
    if major != EXPECTED_GH_MAJOR:
        version = ".".join(match.group(i) for i in (1, 2, 3))
        sys.stderr.write(
            f"Unsupported gh major version: got {version}, expected {EXPECTED_GH_MAJOR}.x. "
            f"Update this script after verifying the flags and JSON fields still work.\n"
        )
        sys.exit(1)


def run_gh(args: list[str]) -> list | dict:
    result = subprocess.run(
        ["gh", *args], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        sys.stderr.write(
            f"gh {' '.join(args)} failed (exit {result.returncode}):\n{result.stderr}"
        )
        sys.exit(1)
    out = result.stdout.strip()
    return json.loads(out) if out else []


def search_prs(org: str, team: str | None, author: str | None, repos: list[str] | None) -> list[dict]:
    args = ["search", "prs", "--state", "open", "--limit", "1000", "--json", SEARCH_FIELDS]
    if team:
        args += ["--review-requested", f"{org}/{team}"]
    if author:
        args += ["--author", author]
    if repos:
        for repo in repos:
            args += ["--repo", f"{org}/{repo}"]
    else:
        args += ["--owner", org]
    return run_gh(args)


def fetch_pr_details(url: str) -> dict:
    return run_gh(["pr", "view", url, "--json", PR_VIEW_FIELDS])


def is_bot(author: dict | None, extra_bots: set[str]) -> bool:
    if not author:
        return False
    if author.get("is_bot") or author.get("type") == "Bot":
        return True
    login = (author.get("login") or "").lower()
    if login.endswith("[bot]") or login in BOT_LOGINS:
        return True
    return login in extra_bots


def ci_status(rollup: list | None) -> str:
    """success | failure | pending | none"""
    if not rollup:
        return "none"
    has_failure = False
    has_pending = False
    for check in rollup:
        state = check.get("state") or check.get("conclusion") or check.get("status")
        if state in ("FAILURE", "ERROR", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED"):
            has_failure = True
        elif state in ("PENDING", "QUEUED", "IN_PROGRESS", "WAITING", None, ""):
            has_pending = True
    if has_failure:
        return "failure"
    if has_pending:
        return "pending"
    return "success"


def hours_since(iso_str: str, now: datetime) -> float:
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return (now - dt).total_seconds() / 3600.0


def bucket_for(pr: dict, stale_hours: float, max_age_days: float, now: datetime) -> tuple[str, list[str]]:
    ci = ci_status(pr.get("statusCheckRollup"))
    mergeable = pr.get("mergeable")  # MERGEABLE | CONFLICTING | UNKNOWN
    decision = pr.get("reviewDecision")  # APPROVED | CHANGES_REQUESTED | REVIEW_REQUIRED | ''
    idle_h = hours_since(pr["updatedAt"], now)
    age_h = hours_since(pr["createdAt"], now)

    problems: list[str] = []
    if ci == "failure":
        problems.append("CI failing")
    if mergeable == "CONFLICTING":
        problems.append("merge conflict")
    if idle_h >= stale_hours:
        problems.append(f"stale {_fmt_age(idle_h)}")
    age_triggered = age_h >= max_age_days * 24

    if problems or age_triggered:
        # Age alone can land a PR here; if nothing else fires, surface `old Nd`
        # so the reader sees *why* it was flagged. Otherwise the leading
        # `open Nd` in the rendered line already conveys it.
        if age_triggered and not problems:
            problems.append(f"old {_fmt_age(age_h)}")
        return "needs_attention", problems

    if decision == "APPROVED" and ci in ("success", "none") and mergeable != "CONFLICTING":
        return "ready_to_merge", []

    if decision == "CHANGES_REQUESTED":
        return "in_discussion", ["changes requested"]

    return "awaiting_review", []


def _fmt_age(hours: float) -> str:
    if hours < 24:
        return f"{int(round(hours))}h"
    return f"{int(round(hours / 24))}d"


def approvers_from_reviews(reviews: list | None) -> list[str]:
    if not reviews:
        return []
    seen: dict[str, bool] = {}
    for r in reviews:
        if r.get("state") == "APPROVED":
            login = (r.get("author") or {}).get("login")
            if login:
                seen[login] = True
    return sorted(seen)


def build_entry(pr: dict, repo_full: str, bucket_name: str, reasons: list[str], now: datetime) -> dict:
    return {
        "repo": repo_full,
        "number": pr["number"],
        "title": pr["title"],
        "url": pr["url"],
        "author": (pr.get("author") or {}).get("login"),
        "created_at": pr["createdAt"],
        "updated_at": pr["updatedAt"],
        "age_hours": round(hours_since(pr["createdAt"], now), 1),
        "updated_hours_ago": round(hours_since(pr["updatedAt"], now), 1),
        "additions": pr.get("additions", 0),
        "deletions": pr.get("deletions", 0),
        "files_changed": len(pr.get("files") or []),
        "ci_status": ci_status(pr.get("statusCheckRollup")),
        "mergeable": pr.get("mergeable"),
        "review_decision": pr.get("reviewDecision") or None,
        "approvers": approvers_from_reviews(pr.get("reviews")),
        "labels": [l.get("name") for l in (pr.get("labels") or []) if l.get("name")],
        "bucket": bucket_name,
        "reasons": reasons,
    }


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--org", required=True, help="GitHub organization (e.g. 'acme')")
    p.add_argument("--teams", default=None, help="Comma-separated team slugs (without org prefix). A PR matches if ANY of these teams is a requested reviewer.")
    p.add_argument("--authors", default=None, help="Comma-separated GitHub usernames. A PR matches if its author is in this list.")
    p.add_argument("--repos", default=None, help="Comma-separated repo names to restrict the search to.")
    p.add_argument("--stale-hours", type=float, default=24.0, help="Hours since last update to consider stale (default: 24).")
    p.add_argument("--max-age-days", type=float, default=7.0, help="Days since opened before a PR is flagged as too old (default: 7).")
    p.add_argument(
        "--extra-bots",
        default=None,
        help="Comma-separated additional GitHub logins to treat as bots (case-insensitive). "
        "Use this for machine accounts that GitHub doesn't mark as bots (e.g. org automation users).",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    teams = _split_csv(args.teams)
    authors = _split_csv(args.authors)
    repos = _split_csv(args.repos) or None

    if not (teams or authors or repos):
        sys.stderr.write("Error: provide at least one of --teams, --authors, or --repos.\n")
        return 2

    check_gh_version()

    extra_bots = {b.lower() for b in _split_csv(args.extra_bots)}
    now = datetime.now(timezone.utc)

    # gh search prs has single-valued --review-requested and --author, so
    # we run one query per (team × author) combination and dedupe by URL.
    # None on either axis means "don't apply that filter" for the query.
    team_axis: list[str | None] = list(teams) if teams else [None]
    author_axis: list[str | None] = list(authors) if authors else [None]

    merged: dict[str, dict] = {}
    for team in team_axis:
        for author in author_axis:
            for r in search_prs(args.org, team, author, repos):
                merged[r["url"]] = r
    search_results = list(merged.values())

    buckets: dict[str, list[dict]] = {
        "needs_attention": [],
        "ready_to_merge": [],
        "in_discussion": [],
        "awaiting_review": [],
    }
    skipped_drafts = 0
    skipped_bots = 0

    for result in search_results:
        if result.get("isDraft"):
            skipped_drafts += 1
            continue
        if is_bot(result.get("author"), extra_bots):
            skipped_bots += 1
            continue

        pr = fetch_pr_details(result["url"])
        # Double-check after detail fetch (search index can lag).
        if pr.get("isDraft"):
            skipped_drafts += 1
            continue
        if is_bot(pr.get("author"), extra_bots):
            skipped_bots += 1
            continue

        name, reasons = bucket_for(pr, args.stale_hours, args.max_age_days, now)
        repo_full = (result.get("repository") or {}).get("nameWithOwner", "")
        buckets[name].append(build_entry(pr, repo_full, name, reasons, now))

    # Oldest first within each bucket — those should surface first.
    for name in buckets:
        buckets[name].sort(key=lambda e: e["age_hours"], reverse=True)

    output = {
        "org": args.org,
        "teams": teams,
        "authors": authors,
        "repos": repos,
        "stale_hours": args.stale_hours,
        "max_age_days": args.max_age_days,
        "generated_at": now.isoformat(),
        "total": sum(len(v) for v in buckets.values()),
        "counts": {k: len(v) for k, v in buckets.items()},
        "skipped": {"drafts": skipped_drafts, "bots": skipped_bots},
        "buckets": buckets,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

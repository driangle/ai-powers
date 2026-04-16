#!/usr/bin/env python3
"""Fetch open PRs matching filters, bucket them, emit JSON for a reviewer report.

Filters (all AND-combined, at least one of team/author/repos required):
  --team       Only PRs where this team is a requested reviewer (org/team).
  --author     Only PRs by this author.
  --repos      Comma-separated repo names (org inferred from --org).

Drafts and bot-authored PRs are always excluded.

Output: JSON on stdout with PRs grouped into 4 mutually-exclusive buckets
(first match wins, in this precedence):
  1. needs_attention   — failing CI, merge conflict, or stale (>= --stale-hours)
  2. ready_to_merge    — approved, CI green (or none), no conflict
  3. in_discussion     — changes requested
  4. awaiting_review   — default bucket for everything else
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone


PR_VIEW_FIELDS = (
    "number,title,url,author,isDraft,createdAt,updatedAt,additions,deletions,"
    "files,labels,reviewDecision,mergeable,reviews,statusCheckRollup"
)

SEARCH_FIELDS = "url,repository,isDraft,author"

BOT_LOGINS = {"dependabot", "renovate", "renovate-bot", "github-actions"}


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
        args += ["--team-review-requested", f"{org}/{team}"]
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


def is_bot(author: dict | None) -> bool:
    if not author:
        return False
    if author.get("is_bot") or author.get("type") == "Bot":
        return True
    login = (author.get("login") or "").lower()
    return login.endswith("[bot]") or login in BOT_LOGINS


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


def bucket_for(pr: dict, stale_hours: float, now: datetime) -> tuple[str, list[str]]:
    ci = ci_status(pr.get("statusCheckRollup"))
    mergeable = pr.get("mergeable")  # MERGEABLE | CONFLICTING | UNKNOWN
    decision = pr.get("reviewDecision")  # APPROVED | CHANGES_REQUESTED | REVIEW_REQUIRED | ''
    age_h = hours_since(pr["updatedAt"], now)

    problems: list[str] = []
    if ci == "failure":
        problems.append("CI failing")
    if mergeable == "CONFLICTING":
        problems.append("merge conflict")
    if age_h >= stale_hours:
        problems.append(f"stale ({_fmt_age(age_h)})")

    if problems:
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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--org", required=True, help="GitHub organization (e.g. 'acme')")
    p.add_argument("--team", default=None, help="Team slug (without org prefix). Filters to PRs where this team is a requested reviewer.")
    p.add_argument("--author", default=None, help="GitHub username. Filters to PRs by this author.")
    p.add_argument("--repos", default=None, help="Comma-separated repo names to restrict the search to.")
    p.add_argument("--stale-hours", type=float, default=24.0, help="Hours since last update to consider stale (default: 24).")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not (args.team or args.author or args.repos):
        sys.stderr.write("Error: provide at least one of --team, --author, or --repos.\n")
        return 2

    repos = [r.strip() for r in args.repos.split(",") if r.strip()] if args.repos else None
    now = datetime.now(timezone.utc)

    search_results = search_prs(args.org, args.team, args.author, repos)

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
        if is_bot(result.get("author")):
            skipped_bots += 1
            continue

        pr = fetch_pr_details(result["url"])
        # Double-check after detail fetch (search index can lag).
        if pr.get("isDraft"):
            skipped_drafts += 1
            continue
        if is_bot(pr.get("author")):
            skipped_bots += 1
            continue

        name, reasons = bucket_for(pr, args.stale_hours, now)
        repo_full = (result.get("repository") or {}).get("nameWithOwner", "")
        buckets[name].append(build_entry(pr, repo_full, name, reasons, now))

    # Oldest first within each bucket — those should surface first.
    for name in buckets:
        buckets[name].sort(key=lambda e: e["age_hours"], reverse=True)

    output = {
        "org": args.org,
        "team": args.team,
        "author": args.author,
        "repos": repos,
        "stale_hours": args.stale_hours,
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

"""Fetches pull requests and follow-up candidates from GitHub and turns them into the model.

Raw GraphQL nodes are cached, not parsed models, so a parsing change needs no refetch. Only
merged or closed PRs are cached: they no longer change, while an open PR must be read fresh.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from itertools import groupby
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..model import Comment, Commit, FileChange, FollowUpCandidate, PullRequest, Review
from ..prlist import PrRef
from .client import GitHubClient
from .queries import QUERY_VERSION, SEARCH_PRS, batch_query, pr_alias

BATCH_SIZE = 10


class PrCache:
    def __init__(self, root: Path):
        self.root = root / f"v{QUERY_VERSION}"

    def load(self, ref: PrRef) -> Optional[Dict[str, Any]]:
        path = self._path(ref)
        return json.loads(path.read_text()) if path.exists() else None

    def store(self, ref: PrRef, entry: Dict[str, Any]) -> None:
        if entry["node"]["state"] == "OPEN":
            return
        path = self._path(ref)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entry))

    def _path(self, ref: PrRef) -> Path:
        return self.root / ref.repo.replace("/", "__") / f"{ref.number}.json"


def fetch_pull_requests(
    refs: Sequence[PrRef], client: GitHubClient, cache: PrCache
) -> Tuple[List[PullRequest], List[Tuple[PrRef, str]]]:
    """Returns the PRs it could read and, for the rest, the reason they are missing."""
    entries: Dict[str, Dict[str, Any]] = {}
    to_fetch: List[PrRef] = []
    for ref in refs:
        cached = cache.load(ref)
        if cached is None:
            to_fetch.append(ref)
        else:
            entries[ref.key] = cached

    missing: List[Tuple[PrRef, str]] = []
    by_repo = groupby(sorted(to_fetch, key=lambda ref: ref.repo), key=lambda ref: ref.repo)
    for repo, repo_refs in by_repo:
        repo_list = list(repo_refs)
        for start in range(0, len(repo_list), BATCH_SIZE):
            batch = repo_list[start : start + BATCH_SIZE]
            _progress(f"fetching {repo} PRs {start + 1}-{start + len(batch)} of {len(repo_list)}")
            result = client.graphql(batch_query(repo, (ref.number for ref in batch)))
            repository = result.data.get("repository")
            if not isinstance(repository, dict):
                missing.extend((ref, "repository not found or not accessible") for ref in batch)
                continue
            default_branch = (repository.get("defaultBranchRef") or {}).get("name", "main")
            for ref in batch:
                node = repository.get(pr_alias(ref.number))
                if not isinstance(node, dict):
                    missing.append((ref, "pull request not found"))
                    continue
                entry = {"default_branch": default_branch, "node": node}
                cache.store(ref, entry)
                entries[ref.key] = entry

    prs = [parse_pull_request(entries[ref.key], ref) for ref in refs if ref.key in entries]
    return prs, missing


def fetch_follow_up_candidates(
    repos: Iterable[str], since: date, until: date, keywords: Iterable[str], client: GitHubClient
) -> List[FollowUpCandidate]:
    """Merged PRs in `repos` with any keyword in the title, merged between since and until."""
    found: Dict[str, FollowUpCandidate] = {}
    for repo in sorted(set(repos)):
        for keyword in keywords:
            query = f"repo:{repo} is:pr is:merged merged:{since.isoformat()}..{until.isoformat()} in:title {keyword}"
            _progress(f"searching {repo} for '{keyword}' PRs")
            for node in _search(query, client):
                candidate = _parse_candidate(node)
                if candidate is not None:
                    found[candidate.key] = candidate
    return list(found.values())


def parse_pull_request(entry: Dict[str, Any], ref: PrRef) -> PullRequest:
    node = entry["node"]
    events = sorted(node["timelineItems"]["nodes"], key=lambda event: event["createdAt"])
    draft_events = [e for e in events if e["__typename"] in ("ReadyForReviewEvent", "ConvertToDraftEvent")]
    base_changes = [e for e in events if e["__typename"] == "BaseRefChangedEvent"]
    created_as_draft = (
        draft_events[0]["__typename"] == "ReadyForReviewEvent" if draft_events else bool(node["isDraft"])
    )
    return PullRequest(
        repo=ref.repo,
        number=node["number"],
        url=node["url"],
        title=node["title"],
        author=_login(node.get("author")),
        state=node["state"],
        created_at=_time(node["createdAt"]),
        merged_at=_optional_time(node.get("mergedAt")),
        closed_at=_optional_time(node.get("closedAt")),
        additions=node["additions"],
        deletions=node["deletions"],
        changed_files=node["changedFiles"],
        files=tuple(FileChange(f["path"], f["additions"], f["deletions"]) for f in node["files"]["nodes"]),
        default_branch=entry["default_branch"],
        base_ref=node["baseRefName"],
        head_ref=node["headRefName"],
        base_ref_history=_base_history(base_changes, node["baseRefName"]),
        created_as_draft=created_as_draft,
        first_review_requested_at=_first(events, "ReviewRequestedEvent"),
        first_ready_for_review_at=_first(events, "ReadyForReviewEvent"),
        reviews=tuple(
            Review(
                author=_login(review.get("author")),
                is_bot=_is_bot(review.get("author")),
                state=review["state"],
                submitted_at=_time(review["submittedAt"]),
                comment_count=review["comments"]["totalCount"],
                has_body=bool((review.get("body") or "").strip()),
            )
            for review in node["reviews"]["nodes"]
            if review.get("submittedAt")
        ),
        commits=tuple(
            Commit(
                committed_at=_time(item["commit"]["committedDate"]),
                ci_state=(item["commit"].get("statusCheckRollup") or {}).get("state"),
            )
            for item in node["commits"]["nodes"]
        ),
        comments=tuple(
            Comment(_login(c.get("author")), _is_bot(c.get("author")), _time(c["createdAt"]))
            for c in node["comments"]["nodes"]
        ),
        projects=ref.projects,
        tickets=ref.tickets,
    )


def _search(query: str, client: GitHubClient) -> Iterable[Dict[str, Any]]:
    cursor: Optional[str] = None
    while True:
        result = client.graphql(SEARCH_PRS, {"q": query, "cursor": cursor})
        search = result.data["search"]
        yield from (node for node in search["nodes"] if node)
        if not search["pageInfo"]["hasNextPage"]:
            return
        cursor = search["pageInfo"]["endCursor"]


def _parse_candidate(node: Dict[str, Any]) -> Optional[FollowUpCandidate]:
    if not node.get("mergedAt"):
        return None
    return FollowUpCandidate(
        repo=node["repository"]["nameWithOwner"],
        number=node["number"],
        url=node["url"],
        title=node["title"],
        body=node.get("body") or "",
        merged_at=_time(node["mergedAt"]),
        files=tuple(file["path"] for file in node["files"]["nodes"]),
    )


def _base_history(changes: List[Dict[str, Any]], current: str) -> Tuple[str, ...]:
    """GitHub does not always log the automatic retarget after a base branch merges, so both
    sides of every change are kept."""
    refs = [ref for change in changes for ref in (change["previousRefName"], change["currentRefName"])]
    return tuple(dict.fromkeys(refs + [current]))


def _first(events: List[Dict[str, Any]], typename: str) -> Optional[datetime]:
    matching = [event["createdAt"] for event in events if event["__typename"] == typename]
    return _time(matching[0]) if matching else None


def _login(actor: Optional[Dict[str, Any]]) -> str:
    return actor["login"] if actor else "ghost"


def _is_bot(actor: Optional[Dict[str, Any]]) -> bool:
    return bool(actor) and (actor["__typename"] == "Bot" or actor["login"].endswith("[bot]"))


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _optional_time(value: Optional[str]) -> Optional[datetime]:
    return _time(value) if value else None


def _progress(message: str) -> None:
    print(message, file=sys.stderr)

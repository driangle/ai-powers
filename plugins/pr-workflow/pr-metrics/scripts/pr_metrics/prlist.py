"""The PR list: which pull requests to analyse and the Linear projects and tickets they belong to.

The CSV has the columns `url,projects,tickets`; the list columns separate values with `;`.
It is built from the Linear tickets JSON described in SKILL.md, step 2.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

PR_URL = re.compile(r"https://github\.com/([\w.-]+)/([\w.-]+)/pull/(\d+)")
LIST_SEPARATOR = ";"
COLUMNS = ("url", "projects", "tickets")


@dataclass(frozen=True)
class PrRef:
    repo: str  # owner/name
    number: int
    projects: Tuple[str, ...]
    tickets: Tuple[str, ...]

    @property
    def key(self) -> str:
        return f"{self.repo}#{self.number}"

    @property
    def url(self) -> str:
        return f"https://github.com/{self.repo}/pull/{self.number}"


def parse_pr_url(text: str) -> Tuple[str, int]:
    """Returns (owner/name, number) for any URL inside a PR, comment and file links included."""
    match = PR_URL.search(text)
    if match is None:
        raise ValueError(f"not a GitHub pull request URL: {text}")
    owner, name, number = match.groups()
    return f"{owner}/{name}", int(number)


def read_pr_list(path: Path) -> List[PrRef]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "url" not in reader.fieldnames:
            raise ValueError(f"{path} needs a header row with at least a 'url' column")
        refs = [
            _ref(row["url"], _split(row.get("projects")), _split(row.get("tickets")))
            for row in reader
            if row["url"].strip()
        ]
    return merge_refs(refs)


def write_pr_list(refs: Iterable[PrRef], path: Path) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        for ref in sorted(refs, key=lambda ref: (ref.repo, ref.number)):
            writer.writerow([ref.url, LIST_SEPARATOR.join(ref.projects), LIST_SEPARATOR.join(ref.tickets)])


def refs_from_linear(path: Path) -> List[PrRef]:
    """Reads `[{"ticket", "project", "links": [...]}]` and keeps the links that are PRs."""
    tickets = json.loads(path.read_text())
    if not isinstance(tickets, list):
        raise ValueError(f"{path} must contain a JSON array of tickets")
    refs = []
    for ticket in tickets:
        for link in ticket.get("links", []):
            if PR_URL.search(link):
                refs.append(_ref(link, (ticket["project"],), (ticket["ticket"],)))
    return merge_refs(refs)


def merge_refs(refs: Iterable[PrRef]) -> List[PrRef]:
    """One entry per PR; a PR linked from several tickets keeps every project and ticket."""
    merged: Dict[str, PrRef] = {}
    for ref in refs:
        existing = merged.get(ref.key)
        if existing is None:
            merged[ref.key] = ref
        else:
            merged[ref.key] = PrRef(
                ref.repo,
                ref.number,
                _union(existing.projects, ref.projects),
                _union(existing.tickets, ref.tickets),
            )
    return list(merged.values())


def _ref(url: str, projects: Tuple[str, ...], tickets: Tuple[str, ...]) -> PrRef:
    repo, number = parse_pr_url(url)
    return PrRef(repo, number, projects, tickets)


def _split(value: object) -> Tuple[str, ...]:
    if not isinstance(value, str):
        return ()
    return tuple(part.strip() for part in value.split(LIST_SEPARATOR) if part.strip())


def _union(first: Tuple[str, ...], second: Tuple[str, ...]) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(first + second))

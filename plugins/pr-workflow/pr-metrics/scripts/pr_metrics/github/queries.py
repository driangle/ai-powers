"""GraphQL documents. Bump QUERY_VERSION whenever PR_FIELDS changes so cached PRs are refetched."""

from __future__ import annotations

import re
from typing import Iterable

QUERY_VERSION = 3

PR_FIELDS = """
fragment PrFields on PullRequest {
  number title url state isDraft createdAt mergedAt closedAt
  additions deletions changedFiles baseRefName headRefName
  author { __typename login }
  files(first: 100) { nodes { path additions deletions } }
  reviews(first: 100) {
    nodes { state body submittedAt author { __typename login } comments { totalCount } }
  }
  comments(first: 100) { nodes { createdAt author { __typename login } } }
  commits(first: 100) {
    nodes { commit { committedDate statusCheckRollup { state } } }
  }
  timelineItems(first: 100, itemTypes: [REVIEW_REQUESTED_EVENT, READY_FOR_REVIEW_EVENT,
                                        CONVERT_TO_DRAFT_EVENT, BASE_REF_CHANGED_EVENT]) {
    nodes {
      __typename
      ... on ReviewRequestedEvent { createdAt }
      ... on ReadyForReviewEvent { createdAt }
      ... on ConvertToDraftEvent { createdAt }
      ... on BaseRefChangedEvent { createdAt previousRefName currentRefName }
    }
  }
}
"""

SEARCH_PRS = """
query($q: String!, $cursor: String) {
  search(query: $q, type: ISSUE, first: 50, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest {
        number title body url mergedAt
        repository { nameWithOwner }
        files(first: 100) { nodes { path } }
      }
    }
  }
}
"""

_NAME = re.compile(r"^[\w.-]+$")


def pr_alias(number: int) -> str:
    return f"pr_{number}"


def batch_query(repo: str, numbers: Iterable[int]) -> str:
    """One query fetching several PRs of one repository through aliases."""
    owner, name = repo.split("/", 1)
    if not (_NAME.match(owner) and _NAME.match(name)):
        raise ValueError(f"invalid repository name: {repo}")
    fields = "\n".join(f"    {pr_alias(n)}: pullRequest(number: {int(n)}) {{ ...PrFields }}" for n in numbers)
    return (
        f'query {{\n  repository(owner: "{owner}", name: "{name}") {{\n'
        f"    defaultBranchRef {{ name }}\n{fields}\n  }}\n}}\n{PR_FIELDS}"
    )

"""Runs GraphQL queries through the `gh` CLI, so authentication is whatever `gh auth` has."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class GitHubError(RuntimeError):
    pass


@dataclass(frozen=True)
class GraphQLResult:
    """`errors` lists failures of single fields (a PR that does not exist); those fields are null
    in `data` while the rest of the query still answers."""

    data: Dict[str, Any]
    errors: List[Dict[str, Any]]


class GitHubClient:
    def graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> GraphQLResult:
        body = json.dumps({"query": query, "variables": variables or {}})
        try:
            completed = subprocess.run(
                ["gh", "api", "graphql", "--input", "-"],
                input=body,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as error:
            raise GitHubError("the GitHub CLI `gh` is not installed") from error
        response = _parse(completed.stdout)
        if response is None:
            raise GitHubError(completed.stderr.strip() or "gh returned no output")
        data = response.get("data")
        if not isinstance(data, dict):
            raise GitHubError(json.dumps(response.get("errors", response))[:2000])
        errors = response.get("errors")
        return GraphQLResult(data, errors if isinstance(errors, list) else [])


def _parse(text: str) -> Optional[Dict[str, Any]]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None

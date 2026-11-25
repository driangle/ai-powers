"""Downloads a PR's dependency files at its merge base and its head through `gh`, without checking anything out.

The merge base, not the base branch tip, is the right "before": the base branch may have moved since the PR
branched, and comparing against its tip would attribute other PRs' changes to this one.
"""

import json
import re
import subprocess
from pathlib import Path, PurePosixPath

LOCKFILES = {
    "package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock",
    "poetry.lock", "uv.lock", "Cargo.lock", "go.mod", "go.sum", "Gemfile.lock",
}
MANIFESTS = {
    "package.json", "pnpm-workspace.yaml", ".yarnrc.yml", "pyproject.toml", "Cargo.toml",
    "Gemfile", "requirements.txt", "pom.xml", "build.gradle", "build.gradle.kts",
}
# Read next to each changed lockfile even when the PR leaves them alone: they hold the direct dependencies, or
# the package manager's overrides and release rules.
_COMPANIONS = {
    "yarn.lock": "package.json", "poetry.lock": "pyproject.toml", "package-lock.json": "package.json",
    "pnpm-lock.yaml": "pnpm-workspace.yaml",  # pnpm 10+ keeps overrides and release-age rules here
}
_PR_URL = re.compile(r"github\.com/([^/]+/[^/]+)/pull/(\d+)")


class FetchError(Exception):
    pass


def fetch(pr: str, repo: str, out: Path) -> dict:
    repo, number = _parse_pr(pr, repo)
    _require_empty(out)
    meta = _gh_json(["pr", "view", number, "--repo", repo, "--json", "baseRefOid,headRefOid,files,title"])
    head = meta["headRefOid"]
    merge_base = _gh_json(["api", f"repos/{repo}/compare/{meta['baseRefOid']}...{head}"])["merge_base_commit"]["sha"]
    changed = [f["path"] for f in meta["files"]]
    wanted = sorted({p for p in changed if _is_dependency_file(p)} | _companions(changed))
    fetched = {"repo": repo, "pr": int(number), "title": meta["title"], "merge_base": merge_base, "head": head,
               "changed_files": changed, "files": []}
    for path in wanted:
        entry = {"path": path}
        for side, sha in (("base", merge_base), ("head", head)):
            entry[side] = _download(repo, path, sha, out / side / path)
        fetched["files"].append(entry)
    fetched["other_changed_files"] = [p for p in changed if not _is_dependency_file(p)]
    return fetched


def _parse_pr(pr: str, repo: str):
    match = _PR_URL.search(pr)
    if match:
        return match.group(1), match.group(2)
    if pr.isdigit() and repo:
        return repo, pr
    raise FetchError("give a PR URL, or a PR number with --repo owner/name")


def _require_empty(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise FetchError(f"{out} is not empty")


def _is_dependency_file(path: str) -> bool:
    name = PurePosixPath(path).name
    return name in LOCKFILES or name in MANIFESTS or (name.startswith("requirements") and name.endswith(".txt"))


def _companions(changed: list) -> set:
    found = set()
    for path in changed:
        posix = PurePosixPath(path)
        if posix.name in _COMPANIONS:
            found.add(str(posix.with_name(_COMPANIONS[posix.name])))
    return found


def _download(repo: str, path: str, sha: str, dest: Path):
    result = subprocess.run(
        ["gh", "api", "-H", "Accept: application/vnd.github.raw", f"repos/{repo}/contents/{path}?ref={sha}"],
        capture_output=True,
    )
    if result.returncode != 0:
        return None  # the file does not exist on this side (added or deleted by the PR)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(result.stdout)
    return str(dest)


def _gh_json(args: list) -> dict:
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise FetchError(f"gh {' '.join(args[:3])} failed: {result.stderr.strip()}")
    return json.loads(result.stdout)

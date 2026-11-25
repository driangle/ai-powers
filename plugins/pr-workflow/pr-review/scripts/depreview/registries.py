"""Finds and downloads the published artifact of one package release, straight from the registry's HTTP API.

No package manager runs, so no install script or build step of the downloaded package can execute. The one
exception is npm packages the public registry refuses (private scopes): those fall back to `npm pack
--ignore-scripts`, which uses the user's own registry configuration and still runs no package code.
"""

import hashlib
import json
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import quote

_HEADERS = {"User-Agent": "depdiff (dependency upgrade review)"}
_TIMEOUT = 60
_MAX_BYTES = 300 * 1024 * 1024
FIRST_COMPONENT = "*"  # strip marker: drop whatever single top-level directory the archive has


@dataclass
class Artifact:
    url: Optional[str]  # None when fetched through `npm pack`
    filename: str
    strip: str  # "" none, FIRST_COMPONENT, or a literal path prefix
    repository: Optional[str]


def fetch(ecosystem: str, name: str, version: str, dest_dir: Path, npm_registry: str) -> tuple:
    """Downloads the artifact into dest_dir and returns (Artifact, local path, sha256)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    if ecosystem == "npm":
        try:
            artifact = _npm(name, version, npm_registry)
        except urllib.error.HTTPError as error:
            if error.code not in (401, 403, 404):
                raise
            return _npm_pack(name, version, dest_dir)
    else:
        artifact = _RESOLVERS[ecosystem](name, version)
    path = dest_dir / artifact.filename
    sha = _download(artifact.url, path)
    return artifact, path, sha


def _npm(name: str, version: str, registry: str) -> Artifact:
    meta = _get_json(f"{registry.rstrip('/')}/{quote(name, safe='@')}/{quote(version)}")
    tarball = meta["dist"]["tarball"]
    return Artifact(tarball, tarball.rsplit("/", 1)[-1], FIRST_COMPONENT, repository_url(meta.get("repository")))


def _npm_pack(name: str, version: str, dest_dir: Path) -> tuple:
    result = subprocess.run(
        ["npm", "pack", f"{name}@{version}", "--ignore-scripts", "--json", "--pack-destination", str(dest_dir)],
        capture_output=True, text=True, cwd=dest_dir,
    )
    if result.returncode != 0:
        raise RuntimeError(f"npm pack {name}@{version} failed: {result.stderr.strip()[-500:]}")
    filename = json.loads(result.stdout)[0]["filename"]
    # npm names scoped tarballs `scope-name-1.0.0.tgz` and reports the same name.
    path = dest_dir / filename
    return Artifact(None, filename, FIRST_COMPONENT, None), path, _sha256(path)


def _pypi(name: str, version: str) -> Artifact:
    meta = _get_json(f"https://pypi.org/pypi/{quote(name)}/{quote(version)}/json")
    files = meta["urls"]
    pure_wheel = next((f for f in files if f["filename"].endswith(("-py3-none-any.whl", "-py2.py3-none-any.whl"))), None)
    sdist = next((f for f in files if f["packagetype"] == "sdist"), None)
    chosen = pure_wheel or sdist or (files[0] if files else None)
    if chosen is None:
        raise RuntimeError(f"PyPI has no files for {name} {version}")
    strip = "" if chosen["filename"].endswith(".whl") else FIRST_COMPONENT
    urls = (meta["info"].get("project_urls") or {}).values()
    repository = next((u for u in urls if re.search(r"github\.com|gitlab\.com|bitbucket\.org", u or "")), None)
    return Artifact(chosen["url"], chosen["filename"], strip, repository)


def _crates(name: str, version: str) -> Artifact:
    repository = _get_json(f"https://crates.io/api/v1/crates/{quote(name)}")["crate"].get("repository")
    url = f"https://static.crates.io/crates/{name}/{name}-{version}.crate"
    return Artifact(url, f"{name}-{version}.crate", FIRST_COMPONENT, repository)


def _go(module: str, version: str) -> Artifact:
    escaped = "".join(f"!{c.lower()}" if c.isupper() else c for c in module)
    escaped_version = "".join(f"!{c.lower()}" if c.isupper() else c for c in version)
    url = f"https://proxy.golang.org/{escaped}/@v/{escaped_version}.zip"
    repository = f"https://{'/'.join(module.split('/')[:3])}" if module.startswith("github.com/") else None
    return Artifact(url, f"{module.replace('/', '_')}-{version}.zip", f"{module}@{version}/", repository)


def _rubygems(name: str, version: str) -> Artifact:
    meta = _get_json(f"https://rubygems.org/api/v2/rubygems/{quote(name)}/versions/{quote(version)}.json")
    repository = meta.get("source_code_uri") or meta.get("homepage_uri")
    return Artifact(f"https://rubygems.org/downloads/{name}-{version}.gem", f"{name}-{version}.gem", "", repository)


def _maven(coordinates: str, version: str) -> Artifact:
    group, _, artifact = coordinates.partition(":")
    if not artifact:
        raise RuntimeError("maven packages are named group:artifact")
    url = f"https://repo1.maven.org/maven2/{group.replace('.', '/')}/{artifact}/{version}/{artifact}-{version}-sources.jar"
    return Artifact(url, f"{artifact}-{version}-sources.jar", "", None)


_RESOLVERS = {"pypi": _pypi, "crates": _crates, "go": _go, "rubygems": _rubygems, "maven": _maven}


def repository_url(repository) -> Optional[str]:
    url = repository.get("url") if isinstance(repository, dict) else repository
    if not url:
        return None
    url = re.sub(r"^git\+", "", url)
    url = re.sub(r"^git://", "https://", url)
    url = re.sub(r"^github:", "https://github.com/", url)
    return re.sub(r"\.git$", "", url)


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, headers=_HEADERS), timeout=_TIMEOUT) as response:
        return json.loads(response.read())


def _download(url: str, path: Path) -> str:
    digest, size = hashlib.sha256(), 0
    with urllib.request.urlopen(urllib.request.Request(url, headers=_HEADERS), timeout=_TIMEOUT) as response:
        with path.open("wb") as out:
            while chunk := response.read(1 << 16):
                size += len(chunk)
                if size > _MAX_BYTES:
                    raise RuntimeError(f"{url} is larger than {_MAX_BYTES // (1024 * 1024)} MB")
                digest.update(chunk)
                out.write(chunk)
    return digest.hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

"""Version parsing and bump classification, tolerant of semver, PEP 440 and Go module versions."""

import re
from dataclasses import dataclass
from typing import Optional

_LEADING_RELEASE = re.compile(r"^v?(\d+(?:\.\d+)*)(.*)$")

# How alarming a bump kind is when several version pairs of one package are compared.
_RANK = {"same": 0, "patch": 1, "prerelease": 2, "minor": 3, "unknown": 4, "major": 5, "downgrade": 5}


@dataclass(frozen=True)
class Version:
    release: tuple
    suffix: str

    @property
    def is_prerelease(self) -> bool:
        # A "+..." suffix is build metadata (e.g. Go's +incompatible), not a prerelease.
        return bool(self.suffix) and not self.suffix.startswith("+")


@dataclass(frozen=True)
class Bump:
    kind: str  # same | patch | minor | major | prerelease | downgrade | unknown
    semver_breaking: bool  # breaking by semver rules, including 0.x minors and prereleases

    @property
    def rank(self) -> tuple:
        return (self.semver_breaking, _RANK[self.kind])


def parse(raw: str) -> Optional[Version]:
    match = _LEADING_RELEASE.match(raw.strip())
    if not match:
        return None
    return Version(tuple(int(part) for part in match.group(1).split(".")), match.group(2))


def sort_key(raw: str) -> tuple:
    version = parse(raw)
    if version is None:
        return (1, (), 0, raw)
    return (0, _padded(version.release, 4), 0 if version.is_prerelease else 1, version.suffix)


def classify_bump(old: str, new: str) -> Bump:
    before, after = parse(old), parse(new)
    if before is None or after is None:
        return Bump("unknown", True)
    if sort_key(new) < sort_key(old):
        return Bump("downgrade", True)
    if sort_key(new) == sort_key(old):
        return Bump("same", False)
    was, now = _padded(before.release, 3), _padded(after.release, 3)
    if now[0] != was[0]:
        return Bump("major", True)
    if now[1] != was[1]:
        return Bump("minor", was[0] == 0)
    if now[2] != was[2]:
        return Bump("patch", was[0] == 0 and was[1] == 0)
    if now[3:] != was[3:]:
        return Bump("patch", False)
    return Bump("prerelease", after.is_prerelease)


def worst(bumps: list) -> Optional[Bump]:
    return max(bumps, key=lambda bump: bump.rank, default=None)


def pair_versions(old_versions: list, new_versions: list) -> list:
    """Pairs each new version with the old one it most plausibly replaced: same major first, else the highest."""
    pairs = []
    for new in new_versions:
        parsed = parse(new)
        same_major = [old for old in old_versions if parsed and (p := parse(old)) and p.release[:1] == parsed.release[:1]]
        candidates = same_major or old_versions
        if candidates:
            pairs.append((max(candidates, key=sort_key), new))
    return pairs


def _padded(release: tuple, length: int) -> tuple:
    return release + (0,) * max(0, length - len(release))

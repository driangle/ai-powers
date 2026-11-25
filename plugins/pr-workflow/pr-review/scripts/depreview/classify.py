"""Compares a base and a head LockGraph and sorts every changed package into a review tier.

A package counts as changed when the set of installed versions differs, or when some consumer (an importer or a
package present on both sides) resolves it to a different version, even one that was already installed elsewhere.

Tiers bound the review so a lockfile churn of hundreds of packages does not turn into hundreds of diffs:
  deep  - diff the released code and check it against the app's usage (capped at `max_deep`, targets exempt)
  skim  - read the release notes or changelog for the range only
  list  - report the version change, nothing more
"""

from dataclasses import dataclass, field
from typing import Optional

from . import walk
from .graph import LockGraph
from .versions import Bump, classify_bump, pair_versions, sort_key, worst

DEEP, SKIM, LIST = "deep", "skim", "list"
_MAX_CONSUMERS = 5


@dataclass(frozen=True)
class Limits:
    max_depth: int = 2  # transitive changes deeper than this are listed only, unless they are a target
    max_deep: int = 8  # most packages to diff in full; the rest of the candidates drop to skim
    churn_warning: int = 30  # more changes than this suggests a lockfile re-resolve, not a targeted bump


@dataclass
class Change:
    name: str
    old_versions: list
    new_versions: list
    kind: str  # upgrade | downgrade | added | removed
    bump: Optional[Bump]
    depth: Optional[int]
    via: list
    scope: str  # prod | dev | unreachable
    importers: list
    relation: str  # target | under-target | above-target | unrelated | no-target-given
    consumers: list  # "consumer: old → new" for consumers that switched version
    tier: str = LIST
    reasons: list = field(default_factory=list)


@dataclass
class Report:
    targets: list
    target_versions: dict  # target -> every version the head lockfile still installs, to check against the advisory
    changes: list
    overrides: list  # (selector, old, new)
    warnings: list
    limits: Limits


def compare(base: LockGraph, head: LockGraph, targets: list, limits: Limits) -> Report:
    context = _Context(base, head, targets)
    changes = [context.change_for(name) for name in context.changed_names()]
    for change in changes:
        _assign_tier(change, limits)
    _apply_cap(changes, limits.max_deep)
    warnings = base.warnings + [w for w in head.warnings if w not in base.warnings]
    warnings += [f"target {t!r} is not in the head lockfile" for t in targets if not head.keys_of(t)]
    collateral = [c for c in changes if c.relation in ("unrelated", "above-target") and c.kind != "removed"]
    breaking = [c.name for c in collateral if c.bump and c.bump.semver_breaking]
    if collateral:
        warnings.append(
            f"{len(collateral)} of {len(changes)} changes are not explained by the targets"
            + (f", {len(breaking)} breaking by semver ({', '.join(breaking)})" if breaking else "")
            + ": check whether the update re-resolved open ranges, and whether they belong in this PR"
        )
    if len(changes) > limits.churn_warning:
        warnings.append(
            f"{len(changes)} packages changed: more than a targeted upgrade needs; look for a lockfile re-resolve "
            "and for changes no target explains"
        )
    installed = head.versions_by_name()
    target_versions = {t: sorted(installed.get(t, ()), key=sort_key) for t in targets}
    return Report(targets, target_versions, changes, _override_changes(base, head), warnings, limits)


class _Side:
    """What one lockfile says about where packages sit."""

    def __init__(self, graph: LockGraph, targets: list):
        self.graph = graph
        self.places = walk.locate(graph)
        self.prod = walk.prod_reachable(graph)
        self.users = walk.importers_reaching(graph)
        self.versions = graph.versions_by_name()
        target_keys = [key for target in targets for key in graph.keys_of(target)]
        self.under_target = walk.reachable(graph, target_keys) - set(target_keys)
        self.above_target = walk.ancestors(graph, target_keys)

    def location_of_consumer(self, consumer: str) -> Optional[walk.Location]:
        if consumer.startswith("importer:"):
            importer = consumer.removeprefix("importer:")
            return walk.Location(0, (importer,))
        return self.places.get(consumer)


class _Context:
    def __init__(self, base: LockGraph, head: LockGraph, targets: list):
        self.targets = set(targets)
        self.base, self.head = _Side(base, targets), _Side(head, targets)
        self.switches = _switched_resolutions(base, head)

    def changed_names(self) -> list:
        before, after = self.base.versions, self.head.versions
        names = {n for n in set(before) | set(after) if before.get(n, set()) != after.get(n, set())}
        return sorted(names | set(self.switches))

    def change_for(self, name: str) -> Change:
        before, after = self.base.versions.get(name, set()), self.head.versions.get(name, set())
        switches = self.switches.get(name, [])
        old = set(before - after) | {v for _, olds, _ in switches for v in olds}
        new = set(after - before) | {v for _, _, news in switches for v in news}
        old, new = sorted(old, key=sort_key), sorted(new, key=sort_key)
        bump = worst([classify_bump(o, n) for o, n in pair_versions(old, new)])
        side = self.head if new else self.base
        keys = [k for k in side.graph.keys_of(name) if side.graph.nodes[k][1] in (new or old)]
        located = [side.places[k] for k in keys if k in side.places]
        located += [
            walk.Location(loc.depth + 1, loc.via + (name,))
            for consumer, _, _ in switches
            if (loc := self.head.location_of_consumer(consumer))
        ]
        nearest = min(located, key=lambda loc: loc.depth, default=None)
        return Change(
            name=name,
            old_versions=old,
            new_versions=new,
            kind=_kind(before, after, bump),
            bump=bump,
            depth=nearest.depth if nearest else None,
            via=list(nearest.via) if nearest else [],
            scope=_scope(keys, side.prod, located),
            importers=sorted({imp for k in keys for imp in side.users.get(k, ())}),
            relation=self._relation(name, keys, side),
            consumers=[_describe_switch(c, o, n) for c, o, n in switches[:_MAX_CONSUMERS]]
            + ([f"… {len(switches) - _MAX_CONSUMERS} more"] if len(switches) > _MAX_CONSUMERS else []),
        )

    def _relation(self, name: str, keys: list, side: _Side) -> str:
        if not self.targets:
            return "no-target-given"
        if name in self.targets:
            return "target"
        if any(k in side.under_target for k in keys):
            return "under-target"
        if any(k in side.above_target for k in keys):
            return "above-target"
        return "unrelated"


def _switched_resolutions(base: LockGraph, head: LockGraph) -> dict:
    """name -> [(consumer, old versions, new versions)] for consumers present on both sides."""
    before, after = walk.resolutions(base), walk.resolutions(head)
    switched = {}
    for (consumer, name), old in before.items():
        new = after.get((consumer, name))
        if new is not None and new != old:
            switched.setdefault(name, []).append((consumer, sorted(old - new), sorted(new - old)))
    return {name: sorted(items) for name, items in switched.items()}


def _describe_switch(consumer: str, old: list, new: list) -> str:
    label = consumer.removeprefix("importer:") if consumer.startswith("importer:") else consumer
    return f"{label}: {', '.join(old) or '—'} → {', '.join(new) or '—'}"


def _kind(before: set, after: set, bump: Optional[Bump]) -> str:
    if not before:
        return "added"
    if not after:
        return "removed"
    if bump is None:
        # Versions only went away (deduplicated) or only appeared (a second copy) for a package that stays.
        return "removed" if before > after else "added"
    return "downgrade" if bump.kind == "downgrade" else "upgrade"


def _scope(keys: list, prod: set, located: list) -> str:
    if not located:
        return "unreachable"
    return "prod" if any(k in prod for k in keys) else "dev"


def _assign_tier(change: Change, limits: Limits) -> None:
    within_depth = change.depth is not None and change.depth <= limits.max_depth
    breaking = change.bump is not None and change.bump.semver_breaking
    if change.relation == "target":
        change.tier, change.reasons = DEEP, ["target of the PR"]
    elif change.kind == "removed":
        change.tier = DEEP if change.depth == 1 else LIST
        change.reasons = ["direct dependency removed"] if change.depth == 1 else ["no longer installed"]
    elif change.depth == 1:
        change.tier, change.reasons = DEEP, ["direct dependency of the project"]
    elif within_depth and (breaking or change.kind == "added"):
        change.tier = DEEP
        change.reasons = [f"{_bump_label(change)} within depth {limits.max_depth}"]
    elif within_depth:
        change.tier, change.reasons = SKIM, [f"non-breaking by semver, depth {change.depth}"]
    else:
        change.tier = LIST
        change.reasons = [f"deeper than {limits.max_depth}" if change.depth else "not reachable from the project"]
    if change.relation == "unrelated" and change.kind != "removed":
        change.reasons.append("collateral: no target explains it")
    if change.relation == "above-target":
        change.reasons.append("depends on a target, but its own ranges may be what moved it")


def _apply_cap(changes: list, max_deep: int) -> None:
    candidates = sorted((c for c in changes if c.tier == DEEP), key=_deep_priority)
    budget = max_deep
    for change in candidates:
        if change.relation == "target":
            continue
        if budget > 0:
            budget -= 1
        else:
            change.tier = SKIM
            change.reasons.append(f"over the cap of {max_deep} full diffs")


def _deep_priority(change: Change) -> tuple:
    return (
        change.relation != "target",
        change.depth != 1,
        change.scope != "prod",
        not (change.bump and change.bump.semver_breaking),
        change.depth or 99,
        change.name,
    )


def _bump_label(change: Change) -> str:
    if change.kind == "added":
        return "new package"
    label = f"{change.bump.kind} bump"
    if change.bump.kind in ("minor", "patch"):
        label += " (0.x, breaking by semver)"
    return label


def _override_changes(base: LockGraph, head: LockGraph) -> list:
    selectors = sorted(set(base.overrides) | set(head.overrides))
    return [
        (s, base.overrides.get(s), head.overrides.get(s))
        for s in selectors
        if base.overrides.get(s) != head.overrides.get(s)
    ]

"""Traversals over a LockGraph: depth from the project, reachability, and the target's neighbourhood."""

from collections import deque
from dataclasses import dataclass

from .graph import PROD, LockGraph


@dataclass(frozen=True)
class Location:
    depth: int  # 1 = a direct dependency of some importer
    via: tuple  # importer, then package names down to this node


def locate(graph: LockGraph) -> dict:
    """Shortest path from any importer to every reachable node."""
    found, queue = {}, deque()
    for importer, roots in sorted(graph.importers.items()):
        for key in sorted(roots):
            if key not in found:
                found[key] = Location(1, (importer, graph.nodes[key][0]))
                queue.append(key)
    while queue:
        key = queue.popleft()
        here = found[key]
        for child in sorted(graph.edges.get(key, ())):
            if child not in found:
                found[child] = Location(here.depth + 1, here.via + (graph.nodes[child][0],))
                queue.append(child)
    return found


def reachable(graph: LockGraph, starts) -> set:
    seen, queue = set(starts), deque(starts)
    while queue:
        for child in graph.edges.get(queue.popleft(), ()):
            if child not in seen:
                seen.add(child)
                queue.append(child)
    return seen


def prod_reachable(graph: LockGraph) -> set:
    return reachable(graph, [key for roots in graph.importers.values() for key, scope in roots.items() if scope == PROD])


def importers_reaching(graph: LockGraph) -> dict:
    reached_by = {}
    for importer, roots in graph.importers.items():
        for key in reachable(graph, list(roots)):
            reached_by.setdefault(key, set()).add(importer)
    return reached_by


def resolutions(graph: LockGraph) -> dict:
    """(consumer, dependency name) -> versions it resolves to. A consumer is an importer or a package node.

    Comparing these between base and head catches a consumer switching to a version that already existed in the
    lockfile for someone else, which a plain diff of the installed versions cannot see.
    """
    resolved = {}
    for importer, roots in graph.importers.items():
        for key in roots:
            name, version = graph.nodes[key]
            resolved.setdefault((importer_consumer(importer), name), set()).add(version)
    for parent, children in graph.edges.items():
        for child in children:
            name, version = graph.nodes[child]
            resolved.setdefault((parent, name), set()).add(version)
    return resolved


def importer_consumer(importer: str) -> str:
    return f"importer:{importer}"


def ancestors(graph: LockGraph, keys) -> set:
    parents = {}
    for parent, children in graph.edges.items():
        for child in children:
            parents.setdefault(child, set()).add(parent)
    seen, queue = set(), deque(keys)
    while queue:
        for parent in parents.get(queue.popleft(), ()):
            if parent not in seen:
                seen.add(parent)
                queue.append(parent)
    return seen - set(keys)

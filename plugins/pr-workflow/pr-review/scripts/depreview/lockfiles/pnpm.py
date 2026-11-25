"""pnpm-lock.yaml, lockfileVersion 6.x to 9.x.

Keys look like `/name@1.0.0(peer@2.0.0)` (6.x) or `name@1.0.0(peer@2.0.0)` (9.x). The peer suffix only records how
peers resolved, so nodes are keyed without it: a change in the suffix alone is not a version change.
"""

import yaml

from ..graph import DEV, PROD, LockGraph
from .errors import UnsupportedLockfile

_IMPORTER_SECTIONS = (("dependencies", PROD), ("optionalDependencies", PROD), ("devDependencies", DEV))
_EDGE_SECTIONS = ("dependencies", "optionalDependencies")


def load(text: str, manifests: list) -> LockGraph:
    data = yaml.safe_load(text) or {}
    version = str(data.get("lockfileVersion", ""))
    major = version.split(".")[0]
    if major not in ("6", "7", "8", "9"):
        raise UnsupportedLockfile(f"pnpm lockfileVersion {version!r} is not supported (6.x to 9.x are)")
    graph = LockGraph("npm")
    graph.overrides = {str(k): str(v) for k, v in (data.get("overrides") or {}).items()}
    for importer, body in (data.get("importers") or {".": data}).items():
        for section, scope in _IMPORTER_SECTIONS:
            for name, spec in ((body or {}).get(section) or {}).items():
                resolved = spec.get("version") if isinstance(spec, dict) else spec
                key = _child_key(graph, str(name), str(resolved))
                if key:
                    graph.add_root(str(importer), key, scope)
    resolved_entries = data.get("snapshots") if major == "9" else data.get("packages")
    for raw_key, body in (resolved_entries or {}).items():
        parent = _key_from_id(graph, str(raw_key))
        for section in _EDGE_SECTIONS:
            for name, resolved in ((body or {}).get(section) or {}).items():
                child = _child_key(graph, str(name), str(resolved))
                if child:
                    graph.add_edge(parent, child)
    for raw_key in data.get("packages") or {}:
        _key_from_id(graph, str(raw_key))
    return graph


def _key_from_id(graph: LockGraph, package_id: str) -> str:
    name, _, version = _without_peers(package_id.lstrip("/")).rpartition("@")
    return graph.add_node(name, version)


def _child_key(graph: LockGraph, name: str, resolved: str):
    if resolved.startswith(("link:", "workspace:")):
        return None
    if resolved.startswith("/"):
        return _key_from_id(graph, resolved)
    bare = _without_peers(resolved)
    if bare and not bare[0].isdigit() and "@" in bare[1:]:
        # An alias such as `string-width-cjs: string-width@4.2.3` resolves to another package.
        return _key_from_id(graph, resolved)
    return graph.add_node(name, bare)


def _without_peers(package_id: str) -> str:
    return package_id.split("(", 1)[0]

"""package-lock.json and npm-shrinkwrap.json, lockfileVersion 2 and 3 (the `packages` map).

Paths outside node_modules are the project's own packages (the root and workspaces). A dependency resolves the
way Node does: the nearest `node_modules/<name>` walking up from the requiring package's path.
"""

import json

from ..graph import DEV, PROD, LockGraph
from .errors import UnsupportedLockfile

_IMPORTER_SECTIONS = (
    ("dependencies", PROD),
    ("optionalDependencies", PROD),
    ("peerDependencies", PROD),
    ("devDependencies", DEV),
)
_EDGE_SECTIONS = ("dependencies", "optionalDependencies", "peerDependencies")


def load(text: str, manifests: list) -> LockGraph:
    data = json.loads(text)
    packages = data.get("packages")
    if packages is None or data.get("lockfileVersion", 1) < 2:
        raise UnsupportedLockfile("npm lockfileVersion 1 is not supported; only versions 2 and 3 record `packages`")
    graph = LockGraph("npm")
    keys = {}
    for path, body in packages.items():
        if _is_installed(path) and not body.get("link") and "version" in body:
            keys[path] = graph.add_node(body.get("name") or path.rsplit("node_modules/", 1)[1], body["version"])
    for path, body in packages.items():
        if _is_installed(path):
            continue
        for section, scope in _IMPORTER_SECTIONS:
            for dep in body.get(section) or {}:
                child = keys.get(_locate(packages, path, dep))
                if child:
                    graph.add_root(path or ".", child, scope)
    for path, key in keys.items():
        for section in _EDGE_SECTIONS:
            for dep in packages[path].get(section) or {}:
                child = keys.get(_locate(packages, path, dep))
                if child:
                    graph.add_edge(key, child)
    return graph


def _is_installed(path: str) -> bool:
    return path.startswith("node_modules/") or "/node_modules/" in path


def _locate(packages: dict, path: str, dep: str):
    base = path
    while True:
        candidate = f"{base}/node_modules/{dep}" if base else f"node_modules/{dep}"
        if candidate in packages:
            return candidate
        if not base:
            return None
        cut = base.rfind("/node_modules/")
        base = base[:cut] if cut != -1 else ""

"""Cargo.lock. Entries without a `source` are the workspace's own crates; Cargo.lock does not mark dev-dependencies."""

import tomllib

from ..graph import PROD, LockGraph


def load(text: str, manifests: list) -> LockGraph:
    graph = LockGraph("crates")
    packages = tomllib.loads(text).get("package", [])
    versions = {}
    for package in packages:
        if "source" in package:
            versions.setdefault(package["name"], []).append(package["version"])

    def key_for(dep: str):
        # Entries read `name`, `name version` or `name version (source)`.
        parts = dep.split(" ")
        version = parts[1] if len(parts) > 1 else next(iter(versions.get(parts[0], [])), None)
        return graph.add_node(parts[0], version) if version and parts[0] in versions else None

    for package in packages:
        parent = graph.add_node(package["name"], package["version"]) if "source" in package else None
        for dep in package.get("dependencies", []):
            child = key_for(dep)
            if not child:
                continue
            if parent:
                graph.add_edge(parent, child)
            else:
                graph.add_root(package["name"], child, PROD)
    graph.infer_roots_if_missing("Cargo.lock without workspace crates")
    return graph

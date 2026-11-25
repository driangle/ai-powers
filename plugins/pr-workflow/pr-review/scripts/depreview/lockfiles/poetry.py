"""poetry.lock. It does not record the project's own dependencies; the pyproject.toml texts in `manifests` do."""

import tomllib

from ..graph import LockGraph
from .pyproject import direct_dependencies, normalize


def load(text: str, manifests: list) -> LockGraph:
    graph = LockGraph("pypi")
    keys_by_name = {}
    packages = tomllib.loads(text).get("package", [])
    for package in packages:
        name = normalize(package["name"])
        keys_by_name.setdefault(name, []).append(graph.add_node(name, str(package["version"])))
    for package in packages:
        parent = graph.add_node(normalize(package["name"]), str(package["version"]))
        for dep in package.get("dependencies") or {}:
            for child in keys_by_name.get(normalize(dep), []):
                graph.add_edge(parent, child)
    for index, manifest in enumerate(manifests):
        for name, scope in direct_dependencies(manifest):
            for key in keys_by_name.get(name, []):
                graph.add_root(f"pyproject-{index + 1}", key, scope)
    graph.infer_roots_if_missing("poetry.lock without a pyproject.toml")
    return graph

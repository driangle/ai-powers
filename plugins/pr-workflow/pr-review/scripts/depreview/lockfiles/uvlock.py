"""uv.lock. The project's own packages are the entries whose source is editable, virtual or a workspace member."""

import tomllib

from ..graph import DEV, PROD, LockGraph
from .pyproject import normalize

_PROJECT_SOURCES = ("editable", "virtual", "workspace")


def load(text: str, manifests: list) -> LockGraph:
    graph = LockGraph("pypi")
    packages = tomllib.loads(text).get("package", [])
    versions = {}
    for package in packages:
        if not _is_project(package):
            versions.setdefault(normalize(package["name"]), []).append(str(package["version"]))

    def key_for(dep: dict):
        name = normalize(dep["name"])
        version = dep.get("version") or next(iter(versions.get(name, [])), None)
        return graph.add_node(name, str(version)) if version else None

    for package in packages:
        prod_deps = list(package.get("dependencies", []))
        for extra in package.get("optional-dependencies", {}).values():
            prod_deps += extra
        dev_deps = [dep for group in package.get("dev-dependencies", {}).values() for dep in group]
        if _is_project(package):
            for deps, scope in ((prod_deps, PROD), (dev_deps, DEV)):
                for dep in deps:
                    key = key_for(dep)
                    if key:
                        graph.add_root(package["name"], key, scope)
        else:
            parent = graph.add_node(normalize(package["name"]), str(package["version"]))
            for dep in prod_deps:
                key = key_for(dep)
                if key:
                    graph.add_edge(parent, key)
    graph.infer_roots_if_missing("uv.lock without a project entry")
    return graph


def _is_project(package: dict) -> bool:
    return any(kind in package.get("source", {}) for kind in _PROJECT_SOURCES)

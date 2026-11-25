"""yarn.lock, both the classic v1 format and the YAML format of yarn 2+ (berry).

Classic lockfiles do not record the project's own dependencies, so the root package.json texts passed as
`manifests` supply them; without any, the roots are inferred.
"""

import json

import yaml

from ..graph import DEV, PROD, LockGraph

_EDGE_SECTIONS = ("dependencies", "optionalDependencies")
_MANIFEST_SECTIONS = (("dependencies", PROD), ("optionalDependencies", PROD), ("devDependencies", DEV))


def load(text: str, manifests: list) -> LockGraph:
    if "__metadata:" in text:
        return _load_berry(text)
    return _load_classic(text, manifests)


def descriptor_name(descriptor: str) -> str:
    """`@scope/name@^1.0.0` -> `@scope/name`; the version range starts at the first `@` after the first character."""
    cut = descriptor.find("@", 1)
    return descriptor if cut == -1 else descriptor[:cut]


def _load_classic(text: str, manifests: list) -> LockGraph:
    graph = LockGraph("npm")
    by_descriptor, entries = {}, _parse_classic(text)
    for descriptors, version, _ in entries:
        key = graph.add_node(descriptor_name(descriptors[0]), version)
        for descriptor in descriptors:
            by_descriptor[descriptor] = key
    for descriptors, _, deps in entries:
        parent = by_descriptor[descriptors[0]]
        for name, wanted in deps.items():
            child = by_descriptor.get(f"{name}@{wanted}")
            if child:
                graph.add_edge(parent, child)
    for index, manifest in enumerate(manifests):
        body = json.loads(manifest)
        importer = body.get("name") or f"manifest-{index + 1}"
        for section, scope in _MANIFEST_SECTIONS:
            for name, wanted in (body.get(section) or {}).items():
                key = by_descriptor.get(f"{name}@{wanted}")
                if key:
                    graph.add_root(importer, key, scope)
    graph.infer_roots_if_missing("yarn v1 lockfile without a package.json")
    return graph


def _parse_classic(text: str) -> list:
    entries, current, section = [], None, None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0:
            current = {"descriptors": [_unquote(d) for d in stripped.rstrip(":").split(",")], "version": None, "deps": {}}
            entries.append(current)
            section = None
        elif indent == 2:
            section = stripped[:-1] if stripped.endswith(":") else None
            field, _, value = stripped.partition(" ")
            if _unquote(field) == "version":
                current["version"] = _unquote(value)
        elif section in _EDGE_SECTIONS:
            name, _, wanted = stripped.partition(" ")
            current["deps"][_unquote(name)] = _unquote(wanted)
    return [(e["descriptors"], e["version"], e["deps"]) for e in entries if e["version"]]


def _load_berry(text: str) -> LockGraph:
    graph = LockGraph("npm")
    data = yaml.safe_load(text) or {}
    by_descriptor, workspaces = {}, {}
    for descriptors_text, body in data.items():
        if descriptors_text == "__metadata" or not isinstance(body, dict):
            continue
        descriptors = [d.strip() for d in str(descriptors_text).split(",")]
        if "@workspace:" in str(body.get("resolution", "")):
            workspaces[str(body["resolution"])] = body
            continue
        key = graph.add_node(descriptor_name(descriptors[0]), str(body.get("version")))
        for descriptor in descriptors:
            by_descriptor[descriptor] = key

    def resolve(name, wanted):
        return by_descriptor.get(f"{name}@{wanted}") or by_descriptor.get(f"{name}@npm:{wanted}")

    for descriptors_text, body in data.items():
        if descriptors_text == "__metadata" or not isinstance(body, dict):
            continue
        workspace = str(body.get("resolution", "")) if "@workspace:" in str(body.get("resolution", "")) else None
        parent = None if workspace else by_descriptor[str(descriptors_text).split(",")[0].strip()]
        for section in _EDGE_SECTIONS:
            for name, wanted in (body.get(section) or {}).items():
                child = resolve(str(name), str(wanted))
                if not child:
                    continue
                if workspace:
                    # Berry merges a workspace's dev and prod dependencies, so its scope is unknown; count it as prod.
                    graph.add_root(workspace, child, PROD)
                else:
                    graph.add_edge(parent, child)
    graph.infer_roots_if_missing("yarn berry lockfile without workspace entries")
    return graph


def _unquote(value: str) -> str:
    return value.strip().strip('"')

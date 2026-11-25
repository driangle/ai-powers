"""go.mod. It lists every module in the build but not who requires whom: direct requirements are roots, and
`// indirect` ones get no depth (run `go mod why -m <module>` in a checkout to place them)."""

import re

from ..graph import PROD, LockGraph

_REQUIREMENT = re.compile(r"^(\S+)\s+(v\S+)(\s*//\s*indirect)?")
_REPLACEMENT = re.compile(r"^(\S+)(?:\s+v\S+)?\s+=>\s+(\S+)(?:\s+(v\S+))?")


def load(text: str, manifests: list) -> LockGraph:
    graph = LockGraph("go")
    block = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.endswith("("):
            block = line.split()[0]
            continue
        if line == ")":
            block = None
            continue
        directive = block
        if block is None:
            directive, _, line = line.partition(" ")
        if directive == "require":
            _add_requirement(graph, line.strip())
        elif directive == "replace":
            match = _REPLACEMENT.match(line.strip())
            if match:
                graph.overrides[match.group(1)] = " ".join(filter(None, (match.group(2), match.group(3))))
    graph.warnings.append("go.mod has no dependency graph: indirect modules have no depth or path")
    return graph


def _add_requirement(graph: LockGraph, line: str) -> None:
    match = _REQUIREMENT.match(line)
    if not match:
        return
    key = graph.add_node(match.group(1), match.group(2))
    if not match.group(3):
        graph.add_root("go.mod", key, PROD)

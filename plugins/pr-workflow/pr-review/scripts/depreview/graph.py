"""The resolved dependency graph read from one lockfile, independent of the lockfile format."""

from dataclasses import dataclass, field

PROD, DEV = "prod", "dev"
INFERRED_IMPORTER = "(inferred roots)"


def node_key(name: str, version: str) -> str:
    return f"{name}@{version}"


@dataclass
class LockGraph:
    """Nodes are `name@version`; importers are the project's own packages (workspaces) and their direct deps."""

    ecosystem: str
    nodes: dict = field(default_factory=dict)  # key -> (name, version)
    edges: dict = field(default_factory=dict)  # key -> set of child keys
    importers: dict = field(default_factory=dict)  # importer -> {key: PROD | DEV}
    overrides: dict = field(default_factory=dict)  # selector -> forced version or range
    warnings: list = field(default_factory=list)

    def add_node(self, name: str, version: str) -> str:
        key = node_key(name, version)
        self.nodes.setdefault(key, (name, version))
        self.edges.setdefault(key, set())
        return key

    def add_edge(self, parent: str, child: str) -> None:
        if parent != child:
            self.edges.setdefault(parent, set()).add(child)

    def add_root(self, importer: str, key: str, scope: str) -> None:
        roots = self.importers.setdefault(importer, {})
        # A dependency listed as both prod and dev ships to production.
        if roots.get(key) != PROD:
            roots[key] = scope

    def versions_by_name(self) -> dict:
        versions = {}
        for name, version in self.nodes.values():
            versions.setdefault(name, set()).add(version)
        return versions

    def keys_of(self, name: str) -> list:
        return [key for key, (node_name, _) in self.nodes.items() if node_name == name]

    def infer_roots_if_missing(self, reason: str) -> None:
        """Without importer data, treats packages nobody depends on as the project's direct dependencies."""
        if self.importers:
            return
        depended_on = {child for children in self.edges.values() for child in children}
        for key in self.nodes:
            if key not in depended_on:
                self.add_root(INFERRED_IMPORTER, key, PROD)
        self.warnings.append(
            f"{reason}: direct dependencies were inferred as the packages nothing else depends on, "
            "so depths and prod/dev scope are approximate"
        )

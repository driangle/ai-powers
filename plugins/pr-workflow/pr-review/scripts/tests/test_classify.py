import unittest

from depreview.classify import DEEP, LIST, SKIM, Limits, compare
from depreview.graph import PROD, LockGraph


def graph(edges: dict, roots: dict) -> LockGraph:
    """edges: {"a@1": ["b@1"]}; roots: {"importer": ["a@1"]}."""
    built = LockGraph("npm")
    for parent, children in edges.items():
        built.add_node(*parent.rsplit("@", 1))
        for child in children:
            built.add_edge(parent, built.add_node(*child.rsplit("@", 1)))
    for importer, keys in roots.items():
        for key in keys:
            built.add_root(importer, built.add_node(*key.rsplit("@", 1)), PROD)
    return built


class CompareTest(unittest.TestCase):
    def test_tiers_follow_target_depth_and_semver(self):
        base = graph({"app-lib@1.0.0": ["target@1.0.0"], "target@1.0.0": ["mid@1.0.0"], "mid@1.0.0": ["deep@1.0.0"]},
                     {"svc": ["app-lib@1.0.0"]})
        head = graph({"app-lib@1.0.0": ["target@1.1.0"], "target@1.1.0": ["mid@2.0.0"], "mid@2.0.0": ["deep@2.0.0"]},
                     {"svc": ["app-lib@1.0.0"]})
        report = compare(base, head, ["target"], Limits(max_depth=3))
        tiers = {c.name: (c.tier, c.relation, c.depth) for c in report.changes}
        self.assertEqual(tiers["target"], (DEEP, "target", 2))
        self.assertEqual(tiers["mid"], (DEEP, "under-target", 3))
        self.assertEqual(tiers["deep"], (LIST, "under-target", 4))

    def test_consumer_switching_to_an_already_installed_version_counts(self):
        base = graph({}, {"a": ["client@15.0.0"], "b": ["client@19.0.0"]})
        head = graph({}, {"a": ["client@19.0.0"], "b": ["client@19.0.0"]})
        [change] = compare(base, head, ["other"], Limits()).changes
        self.assertEqual((change.old_versions, change.new_versions, change.bump.kind), (["15.0.0"], ["19.0.0"], "major"))
        self.assertEqual(change.relation, "unrelated")
        self.assertEqual(change.tier, DEEP)
        self.assertEqual(change.consumers, ["a: 15.0.0 → 19.0.0"])

    def test_cap_demotes_lowest_priority_but_never_targets(self):
        base = graph({}, {"svc": [f"p{i}@1.0.0" for i in range(4)] + ["t@1.0.0"]})
        head = graph({}, {"svc": [f"p{i}@2.0.0" for i in range(4)] + ["t@2.0.0"]})
        report = compare(base, head, ["t"], Limits(max_deep=2))
        tiers = {c.name: c.tier for c in report.changes}
        self.assertEqual(tiers["t"], DEEP)
        self.assertEqual(sorted(tiers.values()).count(DEEP), 3)
        self.assertEqual(sorted(tiers.values()).count(SKIM), 2)

    def test_churn_warning(self):
        base = graph({}, {"svc": [f"p{i}@1.0.0" for i in range(5)]})
        head = graph({}, {"svc": [f"p{i}@1.0.1" for i in range(5)]})
        report = compare(base, head, [], Limits(churn_warning=3))
        self.assertTrue(any("re-resolve" in w for w in report.warnings))


if __name__ == "__main__":
    unittest.main()

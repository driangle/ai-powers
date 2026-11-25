import json
import unittest

from depreview.graph import DEV, PROD
from depreview.lockfiles import cargo, gomod, npm, pnpm, poetry, uvlock, yarn
from depreview.walk import locate

PNPM_V9 = """
lockfileVersion: '9.0'
overrides:
  qs: 6.11.0
importers:
  .:
    dependencies:
      express:
        specifier: ^4.0.0
        version: 4.19.2(supports-color@8.1.1)
    devDependencies:
      jest:
        specifier: ^29
        version: 29.7.0
  packages/lib:
    dependencies:
      shared:
        specifier: workspace:*
        version: link:../shared
packages:
  express@4.19.2:
    resolution: {integrity: x}
  qs@6.11.0:
    resolution: {integrity: x}
  jest@29.7.0:
    resolution: {integrity: x}
snapshots:
  express@4.19.2(supports-color@8.1.1):
    dependencies:
      qs: 6.11.0
      string-width-cjs: string-width@4.2.3
  qs@6.11.0: {}
  jest@29.7.0: {}
"""

NPM_V3 = {
    "lockfileVersion": 3,
    "packages": {
        "": {"dependencies": {"a": "^1"}, "devDependencies": {"d": "^1"}},
        "packages/ws": {"dependencies": {"a": "^2"}},
        "node_modules/a": {"version": "1.0.0", "dependencies": {"b": "^1"}},
        "node_modules/b": {"version": "1.1.0"},
        "node_modules/d": {"version": "3.0.0", "dev": True},
        "node_modules/ws": {"link": True, "resolved": "packages/ws"},
        "packages/ws/node_modules/a": {"version": "2.0.0", "dependencies": {"b": "^1"}},
    },
}

YARN_V1 = '''# yarn lockfile v1

"@scope/a@^1.0.0", "@scope/a@^1.1.0":
  version "1.2.0"
  dependencies:
    b "^2.0.0"

b@^2.0.0:
  version "2.3.0"
'''

YARN_BERRY = """
__metadata:
  version: 8

"app@workspace:.":
  version: 0.0.0-use.local
  resolution: "app@workspace:."
  dependencies:
    a: "npm:^1.0.0"

"a@npm:^1.0.0":
  version: 1.4.0
  resolution: "a@npm:1.4.0"
  dependencies:
    b: "npm:^2.0.0"

"b@npm:^2.0.0":
  version: 2.0.1
  resolution: "b@npm:2.0.1"
"""

POETRY = '''
[[package]]
name = "Requests"
version = "2.32.3"
[package.dependencies]
urllib3 = ">=1.21.1,<3"

[[package]]
name = "urllib3"
version = "2.2.1"
'''

PYPROJECT = '''
[tool.poetry.dependencies]
python = "^3.11"
requests = "^2.32"
'''

UV = '''
[[package]]
name = "app"
version = "0.1.0"
source = { editable = "." }
dependencies = [{ name = "httpx" }]
[package.dev-dependencies]
dev = [{ name = "pytest" }]

[[package]]
name = "httpx"
version = "0.27.0"
source = { registry = "https://pypi.org/simple" }
dependencies = [{ name = "anyio" }]

[[package]]
name = "anyio"
version = "4.4.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "pytest"
version = "8.2.0"
source = { registry = "https://pypi.org/simple" }
'''

CARGO = '''
[[package]]
name = "app"
version = "0.1.0"
dependencies = ["serde 1.0.200"]

[[package]]
name = "serde"
version = "1.0.200"
source = "registry+https://github.com/rust-lang/crates.io-index"
dependencies = ["serde_derive"]

[[package]]
name = "serde_derive"
version = "1.0.200"
source = "registry+https://github.com/rust-lang/crates.io-index"
'''

GOMOD = """module example.com/app

go 1.22

require github.com/pkg/errors v0.9.1

require (
\tgolang.org/x/net v0.25.0
\tgolang.org/x/text v0.15.0 // indirect
)

replace golang.org/x/net => golang.org/x/net v0.26.0
"""


class LockfileTest(unittest.TestCase):
    def test_pnpm_strips_peer_suffix_and_follows_aliases(self):
        graph = pnpm.load(PNPM_V9, [])
        self.assertIn("express@4.19.2", graph.nodes)
        self.assertEqual(graph.edges["express@4.19.2"], {"qs@6.11.0", "string-width@4.2.3"})
        self.assertEqual(graph.importers["."], {"express@4.19.2": PROD, "jest@29.7.0": DEV})
        self.assertEqual(graph.overrides, {"qs": "6.11.0"})
        self.assertEqual(locate(graph)["qs@6.11.0"].via, (".", "express", "qs"))

    def test_npm_resolves_nested_copies_per_workspace(self):
        graph = npm.load(json.dumps(NPM_V3), [])
        self.assertEqual(graph.importers["."], {"a@1.0.0": PROD, "d@3.0.0": DEV})
        self.assertEqual(graph.importers["packages/ws"], {"a@2.0.0": PROD})
        self.assertEqual(graph.edges["a@2.0.0"], {"b@1.1.0"})

    def test_yarn_classic_uses_manifest_for_roots(self):
        graph = yarn.load(YARN_V1, [json.dumps({"name": "app", "dependencies": {"@scope/a": "^1.1.0"}})])
        self.assertEqual(graph.importers, {"app": {"@scope/a@1.2.0": PROD}})
        self.assertEqual(graph.edges["@scope/a@1.2.0"], {"b@2.3.0"})

    def test_yarn_classic_infers_roots_without_manifest(self):
        graph = yarn.load(YARN_V1, [])
        self.assertEqual(list(graph.importers.values()), [{"@scope/a@1.2.0": PROD}])
        self.assertTrue(graph.warnings)

    def test_yarn_berry(self):
        graph = yarn.load(YARN_BERRY, [])
        self.assertEqual(graph.importers, {"app@workspace:.": {"a@1.4.0": PROD}})
        self.assertEqual(graph.edges["a@1.4.0"], {"b@2.0.1"})

    def test_poetry_normalizes_names_and_reads_pyproject(self):
        graph = poetry.load(POETRY, [PYPROJECT])
        self.assertEqual(graph.importers, {"pyproject-1": {"requests@2.32.3": PROD}})
        self.assertEqual(graph.edges["requests@2.32.3"], {"urllib3@2.2.1"})

    def test_uv(self):
        graph = uvlock.load(UV, [])
        self.assertEqual(graph.importers["app"], {"httpx@0.27.0": PROD, "pytest@8.2.0": DEV})
        self.assertEqual(graph.edges["httpx@0.27.0"], {"anyio@4.4.0"})

    def test_cargo(self):
        graph = cargo.load(CARGO, [])
        self.assertEqual(graph.importers, {"app": {"serde@1.0.200": PROD}})
        self.assertEqual(graph.edges["serde@1.0.200"], {"serde_derive@1.0.200"})

    def test_gomod(self):
        graph = gomod.load(GOMOD, [])
        self.assertEqual(set(graph.importers["go.mod"]), {"github.com/pkg/errors@v0.9.1", "golang.org/x/net@v0.25.0"})
        self.assertIn("golang.org/x/text@v0.15.0", graph.nodes)
        self.assertEqual(graph.overrides, {"golang.org/x/net": "golang.org/x/net v0.26.0"})


if __name__ == "__main__":
    unittest.main()

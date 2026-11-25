import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from depreview import changelog, redflags, treediff
from depreview.extract import extract
from depreview.registries import FIRST_COMPONENT


def tarball(path: Path, entries: dict, symlink: str = None) -> None:
    with tarfile.open(path, "w:gz") as tar:
        for name, content in entries.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
        if symlink:
            info = tarfile.TarInfo(symlink)
            info.type, info.linkname = tarfile.SYMTYPE, "/etc/passwd"
            tar.addfile(info)


class ExtractTest(unittest.TestCase):
    def test_skips_traversal_and_links_and_strips_top_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "pkg.tgz"
            tarball(archive, {"package/index.js": b"ok", "package/../../escape.js": b"x"}, symlink="package/link")
            skipped = extract(archive, root / "out", FIRST_COMPONENT)
            self.assertEqual((root / "out" / "index.js").read_bytes(), b"ok")
            self.assertFalse((root / "escape.js").exists())
            self.assertFalse((root / "out" / "link").exists())
            self.assertEqual(sorted(skipped), ["package/../../escape.js", "package/link"])


class TreeDiffTest(unittest.TestCase):
    def test_orders_by_category_counts_lines_and_flags_added_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = Path(tmp, "old"), Path(tmp, "new")
            for root, body in ((old, "a\n"), (new, "a\nrequire('child_process').exec(x)\n")):
                (root / "lib").mkdir(parents=True)
                (root / "lib" / "index.js").write_text(body)
                (root / "package.json").write_text('{"version": "%s"}' % root.name)
            (new / "lib" / "index.js.map").write_text("{}")
            changes, patch = treediff.diff_trees(old, new)
            self.assertEqual([c.path for c in changes], ["package.json", "lib/index.js", "lib/index.js.map"])
            index = changes[1]
            self.assertEqual((index.added, index.removed, index.added_lines), (1, 0, [(2, "require('child_process').exec(x)")]))
            self.assertEqual(changes[2].skipped, "source map")
            self.assertIn("+require('child_process')", patch)
            self.assertEqual([h["signal"] for h in redflags.scan(changes)], ["spawns processes"])


class MinifiedTest(unittest.TestCase):
    def test_bundle_with_long_lines_is_skipped_whatever_its_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = Path(tmp, "old"), Path(tmp, "new")
            for root, token in ((old, "a"), (new, "b")):
                root.mkdir()
                (root / "bundle.cjs").write_text("var x=" + token * 20_000 + ";\n")
            [change], _ = treediff.diff_trees(old, new)
            self.assertEqual(change.skipped, "minified")


class ChangelogTest(unittest.TestCase):
    NEWEST_FIRST = "# Changelog\n\n## 2.1.0\n- new\n\n## 2.0.0\n- breaking\n\n## 1.0.0\n- first\n"
    OLDEST_FIRST = "## 1.0.0\n- first\n\n## 2.0.0\n- breaking\n\n## 2.1.0\n- new\n\n## 2.2.0\n- later\n"

    def test_newest_first(self):
        self.assertEqual(changelog.excerpt(self.NEWEST_FIRST, "1.0.0", "2.1.0"), "## 2.1.0\n- new\n\n## 2.0.0\n- breaking\n")

    def test_oldest_first(self):
        excerpt = changelog.excerpt(self.OLDEST_FIRST, "1.0.0", "2.1.0")
        self.assertIn("- breaking", excerpt)
        self.assertNotIn("- later", excerpt)

    def test_missing_version(self):
        self.assertIsNone(changelog.excerpt(self.NEWEST_FIRST, "1.0.0", "9.9.9"))


if __name__ == "__main__":
    unittest.main()

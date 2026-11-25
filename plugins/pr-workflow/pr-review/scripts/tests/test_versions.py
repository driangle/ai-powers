import unittest

from depreview.versions import classify_bump, pair_versions


class ClassifyBumpTest(unittest.TestCase):
    def test_semver_kinds(self):
        self.assertEqual(classify_bump("1.2.3", "2.0.0").kind, "major")
        self.assertEqual(classify_bump("1.2.3", "1.3.0").kind, "minor")
        self.assertEqual(classify_bump("1.2.3", "1.2.4").kind, "patch")
        self.assertEqual(classify_bump("1.2.3", "1.2.2").kind, "downgrade")

    def test_zero_major_minor_is_breaking(self):
        self.assertTrue(classify_bump("0.3.20", "0.4.0").semver_breaking)
        self.assertFalse(classify_bump("0.3.20", "0.3.29").semver_breaking)
        self.assertFalse(classify_bump("1.2.3", "1.9.0").semver_breaking)

    def test_go_and_python_forms(self):
        self.assertEqual(classify_bump("v1.2.3", "v1.2.4+incompatible").kind, "patch")
        self.assertEqual(classify_bump("2.31.0", "2.32.0rc1").kind, "minor")
        self.assertEqual(classify_bump("abc", "1.0.0").kind, "unknown")

    def test_pairs_by_major(self):
        self.assertEqual(pair_versions(["1.0.0", "2.0.0"], ["2.1.0"]), [("2.0.0", "2.1.0")])
        self.assertEqual(pair_versions(["1.0.0"], ["3.0.0"]), [("1.0.0", "3.0.0")])


if __name__ == "__main__":
    unittest.main()

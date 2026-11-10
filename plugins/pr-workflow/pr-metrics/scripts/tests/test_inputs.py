import json
import tempfile
import unittest
from pathlib import Path

from pr_metrics.analysis import select_in_window
from pr_metrics.config import ConfigError, load_config
from pr_metrics.prlist import read_pr_list, refs_from_linear, write_pr_list
from tests.fixtures import at, make_context, make_pr


class PrListTest(unittest.TestCase):
    def test_linear_links_become_one_row_per_pr_with_every_ticket(self):
        tickets = [
            {"ticket": "TEAM-1", "project": "Pilot", "links": [
                "https://github.com/acme/app/pull/7",
                "https://app.notion.com/p/some-doc",
            ]},
            {"ticket": "TEAM-2", "project": "Live", "links": [
                "https://github.com/acme/app/pull/7#issuecomment-1",
            ]},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp, "tickets.json"), Path(tmp, "prs.csv")
            source.write_text(json.dumps(tickets))
            write_pr_list(refs_from_linear(source), target)
            refs = read_pr_list(target)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].projects, ("Pilot", "Live"))
        self.assertEqual(refs[0].tickets, ("TEAM-1", "TEAM-2"))


class ConfigTest(unittest.TestCase):
    def test_unknown_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "config.json")
            path.write_text(json.dumps({"clock": {"mood": "calm"}}))
            with self.assertRaises(ConfigError):
                load_config(path, {})

    def test_overrides_win_over_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "config.json")
            path.write_text(json.dumps({"since": "2026-01-01", "large_pr_lines": 300}))
            config = load_config(path, {"since": "2026-02-01", "until": None})
        self.assertEqual(config.since.isoformat(), "2026-02-01")
        self.assertEqual(config.large_pr_lines, 300)


class WindowTest(unittest.TestCase):
    def test_keeps_merged_in_window_and_open_prs_and_explains_the_rest(self):
        ctx = make_context()
        prs = [
            make_pr(1),
            make_pr(2, state="OPEN", merged_at=None, closed_at=None),
            make_pr(3, state="CLOSED", merged_at=None),
            make_pr(4, merged_at=at(5).replace(month=9)),
        ]
        kept, skipped = select_in_window(prs, ctx.config, ctx.window_start, ctx.window_end)
        self.assertEqual([pr.number for pr in kept], [1, 2])
        self.assertEqual([reason for _, reason in skipped], ["closed without merging", "merged outside the window"])


if __name__ == "__main__":
    unittest.main()

import unittest
from dataclasses import replace

from pr_metrics.metrics.follow_ups import FollowUpFixes, Reverts
from pr_metrics.metrics.review_quality import ReviewDepth
from pr_metrics.metrics.review_stages import ReviewCycleTime, TimeToFirstReview
from pr_metrics.metrics.reviewers import ReviewerLoad
from pr_metrics.metrics.size import PrSize
from pr_metrics.metrics.stacks import StackWait
from pr_metrics.model import Comment, FileChange, FollowUpCandidate
from tests.fixtures import at, make_context, make_pr, review


class ReviewStagesTest(unittest.TestCase):
    def test_cycle_runs_from_review_request_to_merge(self):
        result = ReviewCycleTime().compute([make_pr()], make_context())
        self.assertEqual(result.summary["median"], 5)

    def test_evidence_lists_the_prs_at_or_above_the_p90(self):
        prs = [make_pr(n, merged_at=at(5, 10 + n)) for n in range(1, 11)]
        evidence = ReviewCycleTime().compute(prs, make_context()).evidence["p90"]
        self.assertEqual([item.pr for item in evidence.items], ["acme/app#10"])

    def test_draft_pr_is_ready_when_marked_ready_not_when_review_was_requested(self):
        pr = make_pr(created_as_draft=True, first_review_requested_at=at(5, 9), first_ready_for_review_at=at(5, 11))
        result = ReviewCycleTime().compute([pr], make_context())
        self.assertEqual(result.summary["median"], 4)

    def test_first_review_ignores_bots_the_author_and_ignored_reviewers(self):
        pr = make_pr(
            reviews=(
                review("ci-bot", "COMMENTED", at(5, 10, 5), bot=True),
                review("alice", "COMMENTED", at(5, 10, 10)),
                review("carol", "COMMENTED", at(5, 10, 15)),
                review("bob", "APPROVED", at(5, 13)),
            )
        )
        result = TimeToFirstReview().compute([pr], make_context(ignore_reviewers=("carol",)))
        self.assertEqual(result.summary["median"], 3)

    def test_unreviewed_prs_are_left_out_not_counted_as_zero(self):
        result = TimeToFirstReview().compute([make_pr(reviews=())], make_context())
        self.assertEqual(result.summary["n"], 0)


class SizeTest(unittest.TestCase):
    def test_ignored_files_do_not_count_and_tests_are_split_out(self):
        pr = make_pr(
            additions=1100,
            deletions=0,
            files=(
                FileChange("src/a.ts", 100, 0),
                FileChange("src/a.test.ts", 300, 0),
                FileChange("yarn.lock", 700, 0),
            ),
        )
        summary = PrSize().compute([pr], make_context()).summary
        self.assertEqual(summary["median"], 400)
        self.assertEqual(summary["median_code_lines"], 100)
        self.assertEqual(summary["test_share"], 0.75)


class ReviewDepthTest(unittest.TestCase):
    def large(self, number, **overrides):
        return make_pr(number, additions=900, deletions=0, files=(FileChange("src/app.ts", 900, 0),), **overrides)

    def test_silent_means_no_feedback_from_teammates_anywhere(self):
        prs = [
            self.large(1),
            self.large(2, reviews=(review("bob", "APPROVED", at(5, 12), comments=1),)),
            self.large(3, comments=(Comment("bob", False, at(5, 11)),)),
            self.large(4, comments=(Comment("github-actions", True, at(5, 11)), Comment("alice", False, at(5, 11)))),
        ]
        result = ReviewDepth().compute(prs, make_context())
        self.assertEqual(result.summary["large"], 4)
        self.assertEqual([item.pr for item in result.evidence["silent_large"].items], ["acme/app#1", "acme/app#4"])

    def test_review_text_counts_as_feedback(self):
        pr = self.large(1, reviews=(replace(review("bob", "APPROVED", at(5, 12)), has_body=True),))
        self.assertEqual(ReviewDepth().compute([pr], make_context()).summary["silent_large"], 0)


class StackWaitTest(unittest.TestCase):
    def test_wait_runs_from_ready_until_the_base_pr_merges(self):
        base = make_pr(1, head_ref="alice/base", merged_at=at(6, 10))
        top = make_pr(2, base_ref_history=("alice/base", "main"), first_review_requested_at=at(5, 10))
        summary = StackWait().compute([base, top], make_context()).summary
        self.assertEqual(summary["stacked"], 1)
        self.assertEqual(summary["median"], 24)


class FollowUpTest(unittest.TestCase):
    def candidate(self, number, title, files, merged_at, body=""):
        return FollowUpCandidate("acme/app", number, f"https://github.com/acme/app/pull/{number}", title, body, merged_at, files)

    def test_fix_touching_the_same_file_within_the_window_is_a_follow_up(self):
        ctx = replace(
            make_context(),
            follow_up_candidates=(
                self.candidate(10, "fix: app crash", ("src/app.ts",), at(6)),
                self.candidate(11, "fix: other", ("src/other.ts",), at(6)),
                self.candidate(12, "fix: late", ("src/app.ts",), at(20)),
            ),
        )
        result = FollowUpFixes().compute([make_pr()], ctx)
        self.assertEqual(result.summary["with_follow_up"], 1)
        self.assertEqual([row["follow_up"][-2:] for row in result.rows], ["10"])

    def test_revert_matches_by_pr_number(self):
        ctx = replace(
            make_context(),
            follow_up_candidates=(self.candidate(20, 'Revert "PR 1"', ("src/app.ts",), at(6), "Reverts acme/app#1"),),
        )
        self.assertEqual(Reverts().compute([make_pr()], ctx).summary["reverted"], 1)
        self.assertEqual(FollowUpFixes().compute([make_pr()], ctx).summary["with_follow_up"], 0)


class ReviewerLoadTest(unittest.TestCase):
    def test_shares_count_distinct_prs_per_reviewer(self):
        prs = [
            make_pr(1, reviews=(review("bob", "COMMENTED", at(5, 11)), review("bob", "APPROVED", at(5, 12)))),
            make_pr(2, reviews=(review("carol", "APPROVED", at(5, 12)),)),
        ]
        result = ReviewerLoad().compute(prs, make_context())
        self.assertEqual(result.summary["top_share"], 0.5)
        self.assertEqual(result.summary["top_two_share"], 1.0)
        self.assertEqual(result.rows[0]["prs"], 1)


if __name__ == "__main__":
    unittest.main()

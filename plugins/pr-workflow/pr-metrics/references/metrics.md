# Metrics

Every metric runs for all PRs and for each group in `group_by` (project, repo, author). The ids
are what `metrics` and `exclude_metrics` take.

## Milestones

Defined once in `scripts/pr_metrics/lifecycle.py` and shared by the metrics:

- **Ready for review.** For a PR opened as a draft, the first time it was marked ready. Otherwise
  the first review request, or the moment the PR was opened when nobody was requested.
- **Review.** A submitted review by someone other than the author, a bot, or a login in
  `ignore_reviewers`. Comments-only reviews count.
- **Approval.** The first such review with state `APPROVED`.

Every metric can list the PRs behind its numbers (its evidence), which the report shows as
expandable lists so a number can be checked PR by PR.

Durations use the clock in `clock`: business mode counts only `start` to `end` on `workdays` in
`timezone`, so a PR opened on Friday evening and reviewed on Monday morning waited minutes.

## Definitions

| id | What it measures | Notes |
|---|---|---|
| `review_cycle_time` | Ready for review → merged | The headline velocity number. |
| `draft_time` | Opened → ready for review | Neither good nor bad on its own. |
| `time_to_first_review` | Ready for review → first review | The stage the team controls best. |
| `review_to_approval` | First review → first approval | Zero when the first review is the approval. |
| `approval_to_merge` | First approval → merged | CI, merge conflicts, stacked PRs. |
| `pr_size` | Changed lines without `size_ignore_files`, split into `test_files` and other code | "Large" is over `large_pr_lines`. |
| `throughput` | Merged PRs per week, including empty weeks | A trend, not a target. |
| `work_in_progress` | PRs open at once per author, sampled at the end of each working day | Counts only days with at least one open PR. |
| `stack_wait` | For PRs ever based on another PR's branch: ready for review → base PR merged | Needs the base PR in the list. |
| `review_rounds` | Changes-requested reviews; commits after the first review | Commit dates are author dates; rebases shift them. |
| `review_depth` | Reviewer feedback per 100 lines; large PRs approved with no feedback or change request | Feedback is inline comments, reviews with text and conversation comments by teammates, bots excluded. Feedback outside GitHub is invisible. |
| `follow_up_fixes` | Merged PRs followed within `follow_up.window_days` by a PR whose title has a `fix_keywords` word and that touches a shared file | An upper bound: check the rows. |
| `reverts` | Merged PRs reverted by a later PR whose title starts with "Revert" and names the PR number or title | |
| `ci_failures` | PRs with at least one commit whose check rollup failed | Latest run per check only, so re-run failures are missed. |
| `reviewer_load` | PRs reviewed, approvals, change requests and comments per reviewer | Top reviewer share flags dependence on one person. |
| `review_pairs` | PRs per author-reviewer pair | Authors with one reviewer flag knowledge silos. |

## Adding a metric

1. Create a module in `scripts/pr_metrics/metrics/`, one concept per module.
2. For a duration, subclass `DurationMetric` and implement `span(pr, ctx)`, returning
   `(start, end)` or `None` when the PR has not reached both milestones. Otherwise subclass
   `Metric` and implement `compute(prs, ctx)`, returning a `MetricResult`:
   - `summary`: the values the group table shows, described by `summary_fields`;
   - `rows`: optional detail rows for the whole PR set, described by `row_fields`;
   - `per_pr`: optional value per PR key, saved under each PR in `results.json`;
   - `evidence`: optional PR lists keyed by the summary key they explain, each item with a note
     a reader can check on GitHub. `DurationMetric` lists the PRs at or above its P90.
3. Set `id`, `title`, `description`, `headline` (the summary key that gets the bar in the
   report) and `lower_is_better` (`None` when neither direction is better).
4. Register an instance in `ALL_METRICS` in `metrics/__init__.py`, which also sets its place in
   the report.
5. Add a test in `scripts/tests/test_metrics.py` using the builders in `tests/fixtures.py`.

A metric that needs data the PR query does not fetch adds the fields to `PR_FIELDS` in
`github/queries.py`, bumps `QUERY_VERSION` so cached PRs are refetched, and parses them in
`github/fetch.py`.

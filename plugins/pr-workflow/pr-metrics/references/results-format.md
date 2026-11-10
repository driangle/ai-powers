# results.json

Written by `analyze`, read by `render` and by the agent writing the insights.

```jsonc
{
  "generated_at": "2026-10-14T12:00:00+00:00",
  "window": {"since": "2026-08-15", "until": "2026-10-14", "by": "merged", "include_open": true},
  "clock": {"mode": "business", "unit": "business hours", "timezone": "Europe/Berlin",
            "workdays": [0, 1, 2, 3, 4], "hours": "09:00-18:00"},
  "dataset": {
    "pr_list": "prs.csv", "listed": 146, "fetched": 144, "analysed": 133,
    "missing":  [{"url": "...", "reason": "repository not found or not accessible"}],
    "excluded": [{"url": "...", "reason": "closed without merging"}]
  },
  "groups": [
    {"id": "overall:all", "dimension": "overall", "value": "all", "prs": 133},
    {"id": "project:Project A", "dimension": "project", "value": "Project A", "prs": 15}
  ],
  "metrics": [{
    "id": "time_to_first_review", "title": "...", "description": "...",
    "headline": "median", "lower_is_better": true,
    "summary_fields": [{"key": "median", "label": "Median", "unit": "hours"}],
    "row_fields": [],
    "per_pr_unit": "hours",
    "groups": {"overall:all": {
      "summary": {"n": 126, "median": 1.1},
      "rows": [],
      "evidence": {"p90": {"label": "At or above the P90", "prs": [{"pr": "acme/app#1234", "note": "16.4h"}]}}
    }}
  }],
  "prs": [{
    "key": "acme/app#1234", "url": "...", "title": "...", "author": "...",
    "repo": "acme/app", "state": "MERGED", "projects": ["..."], "tickets": ["TEAM-123"],
    "created_at": "...", "merged_at": "...", "lines_changed": 812, "files_changed": 9,
    "metrics": {"review_cycle_time": 4.2, "time_to_first_review": 0.8, "pr_size": 512}
  }]
}
```

- Units are `hours` (in the clock's unit), `lines`, `count`, `ratio` (0 to 1), `number`, and, in
  rows, `text` and `link`.
- `rows` hold a metric's detail rows (throughput weeks, reviewer tables, follow-up matches) for
  every group; the report shows those of `overall:all`.
- `evidence` maps a summary key to the PRs behind that value, each with a note on why it is
  listed (for example "879 lines · approved by bob · 0 inline, 0 review notes, 0 conversation
  comments"). Insights reference a list by metric id, key and group.
- A summary value is `null` when no PR in the group reached the milestones it needs.
- PRs in `prs` are the analysed ones; `metrics` holds each metric's per-PR value for the whole set.

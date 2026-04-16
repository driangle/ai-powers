---
name: pr-review-report
description: Generate a Slack-friendly triage report of open GitHub PRs for a team, author, or set of repos. Use this skill whenever the user wants a PR review queue summary, a daily/standup PR digest, a reviewer triage list, or asks things like "what PRs does my team owe reviews on", "which of my PRs are waiting on review", "show me the team's open PRs", or "give me a PR status report for org X". The skill buckets each PR into exactly one of Needs attention / Ready to merge / In discussion / Awaiting review so reviewers can focus on what matters most.
allowed-tools: Bash
---

## What this skill does

Pulls open PRs from GitHub via the `gh` CLI and formats them into a Slack-ready triage message grouped into mutually-exclusive priority buckets. A deterministic Python script does all the data gathering; this skill's job is to invoke it and render the JSON into Slack mrkdwn.

## Inputs

Collect these from the user (or infer from the conversation):

- `org` (**required**) — GitHub organization.
- `team` (optional) — team slug, without the `org/` prefix. Filters to PRs where this team is a requested reviewer.
- `author` (optional) — GitHub username. Filters to PRs by this author.
- `repos` (optional) — comma-separated list of repo names (no org prefix). Restricts the search.
- `stale_hours` (optional, default `24`) — hours since last activity before a PR is flagged as stale.

**At least one of `team`, `author`, or `repos` must be provided** — the script errors out otherwise.

If any required input is missing or ambiguous, ask the user before running the script. Don't guess org/team slugs.

## Step 1 — Run the script

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/pr-review-report/scripts/fetch_prs.py" \
  --org <org> \
  [--team <team-slug>] \
  [--author <username>] \
  [--repos repo1,repo2,repo3] \
  [--stale-hours <N>]
```

The script prints a JSON blob on stdout with this shape:

```json
{
  "org": "acme",
  "team": "platform",
  "author": null,
  "repos": ["api", "web"],
  "stale_hours": 24,
  "generated_at": "2026-04-16T...",
  "total": 7,
  "counts": {"needs_attention": 2, "ready_to_merge": 1, "in_discussion": 1, "awaiting_review": 3},
  "skipped": {"drafts": 4, "bots": 5},
  "buckets": {
    "needs_attention": [ { "repo": "acme/api", "number": 123, "title": "...", "url": "...", "author": "...", "age_hours": 72.3, "updated_hours_ago": 48.1, "additions": 120, "deletions": 30, "files_changed": 8, "ci_status": "failure", "mergeable": "MERGEABLE", "review_decision": null, "approvers": [], "labels": ["backend"], "bucket": "needs_attention", "reasons": ["CI failing", "stale (2d)"] } ],
    "ready_to_merge": [...],
    "in_discussion": [...],
    "awaiting_review": [...]
  }
}
```

## Step 2 — Render the Slack report

Format the JSON into Slack mrkdwn following the template below. Print the result inside a fenced code block so the user can copy-paste it directly into Slack.

### Template

```
*PR review report — <team or author or "repos">* · <total> open · _<generated date, human-readable>_

:fire: *Needs attention* (<count>)
• <<url>|<repo>#<number>> — <title> _by @<author>_ · <age> · <reasons joined with ", ">
...

:white_check_mark: *Ready to merge* (<count>)
• <<url>|<repo>#<number>> — <title> _by @<author>_ · approved by @<a>, @<b>
...

:speech_balloon: *In discussion* (<count>)
• <<url>|<repo>#<number>> — <title> _by @<author>_ · <reasons>
...

:eyes: *Awaiting review* (<count>)
• <<url>|<repo>#<number>> — <title> _by @<author>_ · <age> · +<additions>/-<deletions>
...
```

### Rendering rules

- **Omit empty buckets entirely** — don't print a heading for an empty bucket.
- **Header line** — use the most specific label you have. If a team is set, use the team name; if only author, use `@<author>`; if only repos, use `repos: <list>`. Combine when both team and author are given: `team <team> / @<author>`.
- **Age** — use the `age_hours` field (hours since the PR was opened). Format as `<N>h` under 24 hours, otherwise `<N>d`. Round sensibly.
- **Links** — use Slack's `<url|text>` syntax. The link text should be `<repo-short-name>#<number>` (strip the `org/` prefix from `repo` for brevity).
- **Sizes** — only include `+additions/-deletions` in the *Awaiting review* bucket. Elsewhere it's noise.
- **Reasons** — for *Needs attention* and *In discussion*, join the `reasons` array with `, `. For *Ready to merge*, list approvers as `approved by @a, @b`; if approvers is empty, write `approved`.
- **Footer** — if `skipped.drafts` or `skipped.bots` are non-zero, add a final italic line: `_Skipped: <N> drafts, <M> bot PRs_`. Omit when both are zero.
- **No truncation** — print every PR, even if the message is long. The user asked for one large message.
- **Ordering** — preserve the script's ordering within each bucket (oldest PR first).

### Example output

```
*PR review report — platform* · 5 open · _Apr 16, 2026_

:fire: *Needs attention* (2)
• <https://github.com/acme/api/pull/312|api#312> — Refactor auth middleware _by @jess_ · 4d · CI failing, stale (4d)
• <https://github.com/acme/web/pull/188|web#188> — Upgrade React to 19 _by @tom_ · 2d · merge conflict

:white_check_mark: *Ready to merge* (1)
• <https://github.com/acme/api/pull/320|api#320> — Add rate-limit headers _by @sam_ · approved by @jess, @tom

:eyes: *Awaiting review* (2)
• <https://github.com/acme/web/pull/205|web#205> — Fix hydration warning on /dashboard _by @lee_ · 1d · +42/-18
• <https://github.com/acme/api/pull/325|api#325> — Add /health endpoint _by @sam_ · 6h · +80/-3

_Skipped: 3 drafts, 4 bot PRs_
```

## Edge cases

- **No matching PRs** — the script returns `total: 0`. Print a short message: `No open PRs match those filters.` Don't print empty bucket headings.
- **Script fails** — usually a `gh` auth issue or invalid team slug. Surface the error to the user verbatim; don't retry blindly.
- **Very large results** (hundreds of PRs) — still render the full report as specified. If the user asks to summarize, that's a follow-up; the default output is complete.

## Why the deterministic-script approach

All data gathering and bucketing happens in Python so the report is reproducible: same inputs → same buckets. The agent's only job is presentation. This keeps the bucketing logic (precedence rules, bot/draft filtering, stale threshold) in one reviewable place rather than scattered across prompt instructions.

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
- `teams` (optional) — comma-separated team slugs (no `org/` prefix). A PR matches if **any** of these teams is a requested reviewer.
- `authors` (optional) — comma-separated GitHub usernames. A PR matches if its author is **any** of these users.
- `repos` (optional) — comma-separated repo names (no org prefix). Restricts the search to these repos.
- `stale_hours` (optional, default `24`) — hours since last activity before a PR is flagged as stale (idle-age signal).
- `max_age_days` (optional, default `7`) — days since the PR was opened before it's flagged as too old (open-age signal). Independent of activity: catches long-running PRs even if someone commented recently.
- `extra_bots` (optional) — comma-separated GitHub logins to treat as bots. Use this for machine accounts GitHub doesn't flag (e.g. an internal automation user that opens dependency PRs). Matched case-insensitively.

**At least one of `teams`, `authors`, or `repos` must be provided** — the script errors out otherwise.

Filter semantics: within a list values are OR'd (any team OR any author). Across lists they AND (must be reviewed by one of those teams AND authored by one of those authors AND in one of those repos). Repos further restrict the search.

If any required input is missing or ambiguous, ask the user before running the script. Don't guess org/team slugs.

## Step 1 — Run the script

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/pr-review-report/scripts/fetch_prs.py" \
  --org <org> \
  [--teams team1,team2] \
  [--authors user1,user2] \
  [--repos repo1,repo2,repo3] \
  [--stale-hours <N>] \
  [--max-age-days <N>] \
  [--extra-bots login1,login2]
```

The script prints a JSON blob on stdout with this shape:

```json
{
  "org": "acme",
  "teams": ["platform"],
  "authors": [],
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

Every bullet uses the same shape: `open <age>` first (always labeled — so the reader never has to guess what a bare number means), then bucket-specific fields.

```
*PR review report — <team or author or "repos">* · <total> open · _<generated date, human-readable>_

:fire: *Needs attention* (<count>)
• <<url>|<repo>#<number>> — <title> _by @<author>_ · open <age> · <reasons joined with ", ">
...

:white_check_mark: *Ready to merge* (<count>)
• <<url>|<repo>#<number>> — <title> _by @<author>_ · open <age> · approved by @<a>, @<b>
...

:speech_balloon: *In discussion* (<count>)
• <<url>|<repo>#<number>> — <title> _by @<author>_ · open <age> · <reasons>
...

:eyes: *Awaiting review* (<count>)
• <<url>|<repo>#<number>> — <title> _by @<author>_ · open <age> · +<additions>/-<deletions>
...
```

### Rendering rules

- **Omit empty buckets entirely** — don't print a heading for an empty bucket.
- **Header line** — describe the scope from the filters. Single team → `team <name>`; multiple teams → `teams <t1>, <t2>`. Single author → `@<user>`; multiple authors → `@<a>, @<b>`. Combine non-empty pieces with ` / ` (e.g. `teams choco-ai, platform / @ebukaume`). If only repos are set, fall back to `repos: <list>`.
- **Age** — prefix with `open` and format `age_hours` (hours since opened) as `<N>h` under 24 hours, otherwise `<N>d`. Round sensibly.
- **Links** — use Slack's `<url|text>` syntax. The link text should be `<repo-short-name>#<number>` (strip the `org/` prefix from `repo` for brevity).
- **Sizes** — only include `+additions/-deletions` in the *Awaiting review* bucket. Elsewhere it's noise.
- **Reasons** — the script emits already-labeled reasons (`CI failing`, `merge conflict`, `stale <Nd>`, `old <Nd>`, `changes requested`). Join them with `, ` and drop them in verbatim; don't reformat. The leading `open <age>` already covers open-age, so the script only emits `old <Nd>` when age is the *sole* trigger — otherwise it'd be redundant.
- **Approvers** (*Ready to merge*) — `approved by @a, @b`; if the approvers list is empty, write just `approved`.
- **Footer** — if `skipped.drafts` or `skipped.bots` are non-zero, add a final italic line: `_Skipped: <N> drafts, <M> bot PRs_`. Omit when both are zero.
- **No truncation** — print every PR, even if the message is long. The user asked for one large message.
- **Ordering** — preserve the script's ordering within each bucket (oldest PR first).

### Example output

```
*PR review report — team platform* · 5 open · _Apr 16, 2026_

:fire: *Needs attention* (3)
• <https://github.com/acme/api/pull/300|api#300> — Refactor token cache _by @jess_ · open 30d · stale 15d
• <https://github.com/acme/api/pull/312|api#312> — Harden auth middleware _by @jess_ · open 4d · CI failing, stale 4d
• <https://github.com/acme/web/pull/188|web#188> — Long-running React 19 upgrade _by @tom_ · open 12d · old 12d

:white_check_mark: *Ready to merge* (1)
• <https://github.com/acme/api/pull/320|api#320> — Add rate-limit headers _by @sam_ · open 2d · approved by @jess, @tom

:eyes: *Awaiting review* (2)
• <https://github.com/acme/web/pull/205|web#205> — Fix hydration warning on /dashboard _by @lee_ · open 1d · +42/-18
• <https://github.com/acme/api/pull/325|api#325> — Add /health endpoint _by @sam_ · open 6h · +80/-3

_Skipped: 3 drafts, 4 bot PRs_
```

Notice how the three needs-attention PRs each tell a different story at a glance:
- `#300`: old *and* gone quiet ("open 30d · stale 15d")
- `#312`: young, but actively broken ("open 4d · CI failing, stale 4d")
- `#188`: long-running but still being worked on ("open 12d · old 12d") — age was the sole trigger, so the script adds `old 12d` explicitly so the reader sees why it was flagged.

## Edge cases

- **No matching PRs** — the script returns `total: 0`. Print a short message: `No open PRs match those filters.` Don't print empty bucket headings.
- **Script fails** — usually a `gh` auth issue or invalid team slug. Surface the error to the user verbatim; don't retry blindly.
- **Very large results** (hundreds of PRs) — still render the full report as specified. If the user asks to summarize, that's a follow-up; the default output is complete.

## Why the deterministic-script approach

All data gathering and bucketing happens in Python so the report is reproducible: same inputs → same buckets. The agent's only job is presentation. This keeps the bucketing logic (precedence rules, bot/draft filtering, stale threshold) in one reviewable place rather than scattered across prompt instructions.

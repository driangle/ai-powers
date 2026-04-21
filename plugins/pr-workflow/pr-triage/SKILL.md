---
name: pr-triage
description: Generate a Slack-friendly triage report of open GitHub PRs for a team, author, or set of repos — pure-prompt variant of pr-review-report with no helper script. Use this skill whenever the user wants a PR review queue summary, a daily/standup PR digest, a reviewer triage list, or asks things like "what PRs does my team owe reviews on", "which of my PRs are waiting on review", "show me the team's open PRs", or "give me a PR status report for org X". The skill buckets each PR into exactly one of Needs attention / Ready to merge / In discussion / Awaiting review so reviewers can focus on what matters most.
allowed-tools: Bash
---

## What this skill does

Pulls open PRs from GitHub via the `gh` CLI and formats them into a Slack-ready triage message grouped into mutually-exclusive priority buckets. Unlike `pr-review-report`, this variant has **no helper script** — you drive `gh` yourself, apply the bucketing rules below, and render the output. Follow the rules strictly so the report stays reproducible.

## Inputs

Collect these from the user (or infer from the conversation):

- `org` (**required**) — GitHub organization.
- `teams` (optional) — comma-separated team slugs (no `org/` prefix). A PR matches if **any** of these teams is a requested reviewer.
- `authors` (optional) — comma-separated GitHub usernames. A PR matches if its author is **any** of these users.
- `repos` (optional) — comma-separated repo names (no org prefix). Restricts the search to these repos.
- `stale_hours` (optional, default `24`) — hours since last activity before a PR is flagged as stale.
- `max_age_days` (optional, default `7`) — days since the PR was opened before it's flagged as too old. Independent of activity: catches long-running PRs even if someone commented recently.
- `extra_bots` (optional) — comma-separated GitHub logins to treat as bots, matched case-insensitively. Use for machine accounts GitHub doesn't flag itself (e.g. an internal automation user that opens dependency PRs).

**At least one of `teams`, `authors`, or `repos` must be provided.** If all three are empty, stop and ask the user — don't run a repo-wide open-PR query against an entire org.

Filter semantics: within a list, values are OR'd (any team OR any author). Across lists they AND (must be reviewed by one of those teams AND authored by one of those authors AND in one of those repos). Repos further restrict the search.

If any required input is missing or ambiguous, ask the user before running `gh`. Don't guess org/team slugs.

## Step 1 — Verify `gh` is available

Run `gh --version` once. If it's missing or the major version is not `2`, stop and surface the error — the flags and JSON fields below are pinned to `gh` v2. Don't try to proceed on an unknown major.

## Step 2 — Search for candidate PRs

`gh search prs` takes a single `--review-requested` and a single `--author`. When the user supplies multiple teams or authors, run **one query per (team × author) combination** and dedupe results by URL.

Base command:

```bash
gh search prs --state open --limit 1000 --json url,repository,isDraft,author \
  [--review-requested <org>/<team>] \
  [--author <user>] \
  [--repo <org>/<repo> ... | --owner <org>]
```

Rules:

- If `teams` is set, iterate over each team and pass `--review-requested <org>/<team>`. Otherwise omit that flag.
- If `authors` is set, iterate over each author and pass `--author <user>`. Otherwise omit.
- If `repos` is set, pass one `--repo <org>/<name>` per repo. Otherwise pass `--owner <org>` once.
- Merge all query results into a map keyed by `url` to dedupe.

## Step 3 — Skip drafts and bots early

From the merged search results, drop any PR where:

- `isDraft` is `true` → count toward `skipped.drafts`.
- Author is a bot → count toward `skipped.bots`.

A PR counts as bot-authored if **any** of these holds on its author object:

- `author.is_bot` is `true`, or `author.type == "Bot"`.
- `author.login` ends with `[bot]` (case-insensitive).
- `author.login` (lowercased) is in `{dependabot, renovate, renovate-bot, github-actions}`.
- `author.login` (lowercased) is in the user-supplied `extra_bots` set.

## Step 4 — Fetch details per surviving PR

For each remaining PR, run:

```bash
gh pr view <url> --json number,title,url,author,isDraft,createdAt,updatedAt,additions,deletions,files,labels,reviewDecision,mergeable,reviews,statusCheckRollup
```

The search index can lag, so re-check `isDraft` and the bot rules on the detail payload too; if either fires now, move the PR to the corresponding skipped counter and drop it.

Parallelize these detail fetches where reasonable — each PR is independent.

## Step 5 — Compute per-PR signals

For each detailed PR, derive:

- **`age_hours`** — hours between `createdAt` and now (UTC).
- **`idle_hours`** — hours between `updatedAt` and now (UTC).
- **`ci`** — one of `success | failure | pending | none`, derived from `statusCheckRollup`:
  - `none` if the rollup is empty/missing.
  - `failure` if any check's `state`/`conclusion`/`status` is in `{FAILURE, ERROR, TIMED_OUT, CANCELLED, ACTION_REQUIRED}`.
  - else `pending` if any check is in `{PENDING, QUEUED, IN_PROGRESS, WAITING}` or has an empty state.
  - else `success`.
- **`mergeable`** — pass through `MERGEABLE | CONFLICTING | UNKNOWN`.
- **`decision`** — pass through `reviewDecision`: `APPROVED | CHANGES_REQUESTED | REVIEW_REQUIRED | null`.
- **`approvers`** — unique, sorted list of `reviews[].author.login` where `reviews[].state == "APPROVED"`.

## Step 6 — Bucket each PR (first match wins, in this precedence)

1. **`needs_attention`** — any of the following fire:
   - `ci == "failure"` → reason `"CI failing"`.
   - `mergeable == "CONFLICTING"` → reason `"merge conflict"`.
   - `idle_hours >= stale_hours` → reason `"stale <fmt_age(idle_hours)>"`.
   - `age_hours >= max_age_days * 24` → triggers the bucket, but only add an explicit `"old <fmt_age(age_hours)>"` reason **if no other reason fired** (otherwise the leading `open <age>` in the rendered line already conveys it and `old` would be redundant).
2. **`ready_to_merge`** — `decision == "APPROVED"` AND `ci in {success, none}` AND `mergeable != "CONFLICTING"`. No reasons.
3. **`in_discussion`** — `decision == "CHANGES_REQUESTED"`. Reason: `"changes requested"`.
4. **`awaiting_review`** — everything else. No reasons.

Where `fmt_age(hours)` is `<N>h` if `hours < 24`, otherwise `<N>d`, rounding to the nearest integer.

"Stale" and "old" are intentionally separate signals: a PR can be young but abandoned (stale, not old), or long-running but with recent activity (old, not stale). Either is worth a reviewer's attention.

## Step 7 — Order within each bucket

Sort each bucket by `age_hours` descending (oldest PR first). Those should surface at the top of the bucket.

## Step 8 — Render the Slack report

Format the result into Slack mrkdwn following the template below. Print the final report **inside a fenced code block** so the user can copy-paste it directly into Slack.

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
- **Age** — prefix with `open` and format `age_hours` as `<N>h` under 24 hours, otherwise `<N>d`. Round sensibly.
- **Links** — use Slack's `<url|text>` syntax. The link text should be `<repo-short-name>#<number>` (strip the `org/` prefix from the full repo name for brevity).
- **Sizes** — only include `+additions/-deletions` in the *Awaiting review* bucket. Elsewhere it's noise.
- **Reasons** — join the computed reasons with `, ` and drop them in verbatim. The leading `open <age>` already covers open-age, so only emit `old <Nd>` when age is the *sole* trigger.
- **Approvers** (*Ready to merge*) — `approved by @a, @b`; if the approvers list is empty, write just `approved`.
- **Footer** — if `skipped.drafts` or `skipped.bots` are non-zero, add a final italic line: `_Skipped: <N> drafts, <M> bot PRs_`. Omit when both are zero.
- **No truncation** — print every PR, even if the message is long. The user asked for one large message.
- **Ordering** — preserve the bucket ordering from Step 7 (oldest PR first).

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
- `#300`: old *and* gone quiet (`open 30d · stale 15d`)
- `#312`: young, but actively broken (`open 4d · CI failing, stale 4d`)
- `#188`: long-running but still being worked on (`open 12d · old 12d`) — age was the sole trigger, so `old 12d` is added explicitly so the reader sees why it was flagged.

## Edge cases

- **No matching PRs** — every bucket is empty. Print a short message: `No open PRs match those filters.` Don't print empty bucket headings.
- **`gh` fails** — usually an auth issue or an invalid team slug. Surface the error to the user verbatim; don't retry blindly.
- **Very large results** (hundreds of PRs) — still render the full report as specified. If the user asks to summarize, that's a follow-up; the default output is complete.

## Why pure-prompt

This variant keeps the bucketing rules in the SKILL.md itself so the skill ships as a single reviewable file with no runtime dependency on Python. The trade-off vs `pr-review-report`: bucketing is done by the agent, so minor wording differences between runs are possible. If you need strict reproducibility (CI, scheduled digests), prefer `pr-review-report`; if you want a dependency-free skill that just works off `gh`, use this one.

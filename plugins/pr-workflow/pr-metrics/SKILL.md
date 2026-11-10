---
name: pr-metrics
description: >
  Analyse a team's pull requests and produce a PR health report. Collects the PRs
  linked from Linear tickets in the given projects, fetches them from GitHub, and measures review
  speed stage by stage (time before review, time to first review, review to approval, approval to
  merge, full review cycle), PR size, throughput, open PRs per author, stacked PR wait, review
  rounds and depth, follow-up fixes, reverts, CI failures, reviewer load and who reviews whom,
  per project and per repository. Use this whenever the user asks how long PRs take to merge or
  get reviewed, wants PR, review or engineering velocity metrics, cycle time, DORA-style
  numbers, a PR health or review bottleneck report, or wants to understand or improve their
  team's PR process, for Linear projects or for a list of PRs. Requires an authenticated `gh` CLI,
  and the Linear MCP server to start from Linear projects.
allowed-tools: Bash(python3 *), Bash(gh auth status), Bash(gh api *), Read, Write
---

# PR Metrics

Turns "how are our PRs doing?" into numbers and a report. The program does the fetching and the
arithmetic; the agent's job is to choose the right PRs, read the results critically, and write
findings a team can act on.

> `${CLAUDE_SKILL_DIR}` below means the directory holding this `SKILL.md`. Claude Code expands it
> automatically; other agents (Codex included) do not — substitute that directory's absolute path,
> which is shown next to this skill in the session's skill list.

## Prerequisites

- **Linear MCP**, to collect PRs from tickets. Without it, ask the user for a PR list instead
  (step 3 describes the CSV).
- **`gh`**, authenticated with read access to the repositories (`gh auth status`).
- **Python 3.9+**. The program uses only the standard library.

Run it as `python3 "${CLAUDE_SKILL_DIR}/scripts/run.py" <command>`. Its commands are `prlist`,
`analyze`, `render` and `metrics` (lists every metric with its definition).

## Procedure

### 1. Settle the scope

- **Projects.** Find each named project with `list_projects` (`query` = the name, include
  archived). When a name matches several projects (for example "Payments" matching
  "Payments v1" and "Payments v2"), take all of them unless one is an exact match, and tell the user
  which ones you used.
- **Window.** Default to the last 60 days. The window applies to merge dates.
- **Config.** Business hours default to 09:00 to 18:00, Monday to Friday, in Europe/Berlin;
  set `clock.timezone` to the team's time zone when it differs. Otherwise write a config file
  only for what the user asks to change. The options are in
  [`config.example.json`](config.example.json) and [`references/metrics.md`](references/metrics.md).

### 2. Collect the tickets' PR links

For each project, call `list_issues` with `project`, `updatedAt: -P<days>D`, `limit: 250` and
`fields: ["title", "status", "statusType", "completedAt"]`, following the cursor to the end.

Keep the tickets where work happened: status type `started`, or `completed` with `completedAt`
inside the window. Skip backlog, unstarted and canceled tickets; they have no PRs worth counting.

For each kept ticket, call `get_issue` with `fields: ["attachments"]`. Issue these calls in
parallel batches of about 25. After each batch, append to a tickets JSON file in a working
directory:

```json
[{"ticket": "TEAM-123", "project": "Project A",
  "links": ["https://github.com/acme/app/pull/1234", "https://docs.example.com/design"]}]
```

Writing after every batch means a long run can stop without losing work. Put every attachment
URL in `links`; the next step keeps only GitHub PR links.

### 3. Build the PR list

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/run.py" prlist tickets.json -o prs.csv
```

The CSV has the columns `url,projects,tickets`, with `;` between list values. It is the input to
every later run, so save it where the user can find it and tell them the path. A user who already
has PR URLs can write this CSV by hand and skip steps 1 and 2.

### 4. Analyse

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/run.py" analyze prs.csv --since <YYYY-MM-DD> --until <YYYY-MM-DD> \
  [--config config.json] -o results.json
```

It fetches each PR from GitHub, caches merged and closed PRs in `~/.cache/pr-metrics` (open PRs
are always read fresh), runs every metric for all PRs and for each project and repository, and
prints a text digest. The first run of about 150 PRs takes about a minute. The structure of
`results.json` is in [`references/results-format.md`](references/results-format.md).

### 5. Read the results and write the insights

Read the digest, then the parts of `results.json` that explain it: the slowest PRs, the rows
behind follow-up fixes, the reviewer tables. Write `insights.json`:

```json
{
  "headline": "One or two sentences: the state of things and the one thing to change.",
  "findings": [{"title": "Short claim", "detail": "The numbers behind it.", "tone": "good | watch | problem",
                "evidence": {"metric": "review_depth", "key": "silent_large", "group": "overall:all"}}],
  "recommendations": [{"title": "A concrete change", "detail": "Why, and how to tell it worked."}]
}
```

Rules for the insights, because a team will act on them:

- **Every finding cites numbers from `results.json`.** Use medians and P90; mention a mean only
  next to them.
- **Link the PRs behind a finding.** Metrics list the PRs behind their numbers under
  `groups.<group>.evidence.<key>`, each with a note on why the PR is listed. Point the finding's
  `evidence` at the list that backs it (`group` defaults to `overall:all`); the report shows it
  under the finding so readers can check the claim PR by PR. Leave `evidence` out when no list
  backs the claim.
- **Spot-check a problem before calling it one.** For each "problem" finding, open two or three
  PRs from its evidence on GitHub (`gh api repos/<repo>/pulls/<n>/reviews`, `.../pulls/<n>/comments`,
  `.../issues/<n>/comments`) and confirm the note matches. If a check turns up something the
  metric cannot see, such as feedback only from bots, say so in the finding.
- **Small groups.** For any group with fewer than 5 PRs, say how few there are, or leave it out.
- **Check the noisy metrics before using them.** Follow-up fixes is an upper bound: open its rows
  and drop matches that are clearly not fixes to that PR (for example one registry file touched by
  every PR). Review rounds depend on author commit dates, which a rebase rewrites.
- **Teams, not individuals.** Reviewer load and open PRs per author are for spotting bottlenecks
  and single points of failure. Do not rank people or set targets for them.
- **At most 5 findings and 3 recommendations.** Include at least one "good" finding when the
  data supports one.
- **Report missing data.** If `dataset.missing` or `dataset.excluded` holds PRs the user would
  expect to be included (an inaccessible repository, closed PRs), mention it in a finding.

### 6. Render and publish

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/run.py" render results.json --insights insights.json \
  --title "<Team or project> PR Health" -o report.html
```

`report.html` is one self-contained page with light and dark themes that works at phone width.
It is generated, so to change the page, change the renderer, not the HTML.

- **Claude, with an Artifact tool:** publish `report.html` as an Artifact with `icon: "chart"`
  and a one-sentence `description` naming the projects and the window. The page already follows
  the Artifact page contract, so publish it as is. To refresh a report published earlier,
  publish to its URL.
- **Other harnesses:** give the user the path to `report.html` to open in a browser.

### 7. Reply

Send the report (the Artifact link or the file path), the headline, and the top two or three
findings, then say where `prs.csv` and `results.json` are so the next run can reuse them. An
Artifact is private until the user shares it; say so.

## Extending

Metrics are classes registered in `scripts/pr_metrics/metrics/__init__.py`. A "time from A to B"
measure is a `DurationMetric` with one `span()` method; anything else implements `compute()`.
The report renders any registered metric with no changes to the renderer.
[`references/metrics.md`](references/metrics.md) has the definitions and the steps. Run the tests
with `cd "${CLAUDE_SKILL_DIR}/scripts" && python3 -m unittest discover -s tests -t .`.

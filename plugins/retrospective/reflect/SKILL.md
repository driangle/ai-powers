---
name: reflect
description: >-
  End-of-session retrospective. Reads the agent's own session transcript and
  analyses what actually happened: failed tool calls, retry loops, broken or
  flaky tests, work redone, wasted time, user corrections, and long stalls — then
  writes a reflection note, files the durable findings, and proposes fixes so the
  same mistakes cost less next time. Use when the user says "reflect", "retro",
  "post-mortem", "what went wrong", "how did that session go", "what could I have
  done better", or invokes /reflect — typically at the end of a session or right
  after a task lands. Analyse the real transcript, never memory alone.
---

# Reflect

## Why this exists

A session's failures are cheap to notice and expensive to remember. The retry
loop you spent eight minutes in, the test that failed for a reason unrelated to
your change, the file you rewrote three times because you read the convention
late — none of it survives into the next session unless somebody writes it down.

Two rules make this worth running:

- **Analyse the transcript, not your memory of it.** Your recollection is
  optimised to make the session look coherent. The `.jsonl` is not. Every claim
  in the report must be traceable to something in the transcript or in git.
- **Be blunt and specific.** "Could have been more efficient" helps nobody.
  "Read `Canvas.tsx` four times because I never held the relevant part in
  context — should have read it once, fully, at the start" is a lesson.

This is a retrospective, not a grading exercise. Do not pad it with things that
went well beyond a one-line summary, and do not manufacture failures for a
session that genuinely went smoothly — "nothing notable" is a legitimate result.

## The loop

1. **Gather** the hard data from the transcript and git.
2. **Read** the transcript for the things the numbers cannot see.
3. **Diagnose** — turn observations into causes, using the failure taxonomy.
4. **Report** to the user and stop. *Do not write files yet.*
5. **File** the approved findings: a reflection note, tasks, process fixes.

---

## Step 1 — Gather the data

Run the metrics script first. It locates the current session's transcript (via
`vibeview` if installed, otherwise by finding the newest transcript under
`~/.claude/projects/` for this working directory) and prints timing, per-tool
error counts, retry loops, file churn, the slowest tool calls, and the full
steering log:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/reflect/scripts/session_metrics.py"
```

Pass a session id or a `.jsonl` path to reflect on a *different* session
(`… session_metrics.py 877fff1e-…`). To list candidate transcripts:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/reflect/scripts/session_metrics.py" --list
```

Then add the surrounding context:

```bash
git log --oneline -20        # what actually landed
git diff --stat HEAD~5       # scope of the work
git status --short           # what is still uncommitted
```

If `vibeview` is available, `vibeview inspect <id>` adds tokens and cost and
`vibeview related --json <id>` surfaces subagents and sibling sessions — a
subagent that flailed for ten minutes is invisible in the parent transcript's
tool counts.

## Step 2 — Read the transcript

The numbers point at *where* to look; the text says *why*. Read the transcript
around every signal the script flagged. With `vibeview`:

```bash
vibeview show <session-id> | less        # compact conversation
vibeview show --verbose <session-id>     # full tool inputs/outputs
vibeview show --thinking <session-id>    # reasoning, where the wrong turn was decided
```

Without it, read the `.jsonl` directly (the script prints its path) with `jq`
and `grep` — `references/signals.md` gives patterns that work either way.

`references/signals.md` lists what to look for and how to find each one. At
minimum, walk the **steering log** — every user turn after the first is a moment
the agent was heading somewhere the user did not want. Those are the
highest-value findings in the whole exercise.

## Step 3 — Diagnose

Sort each observation into one of these, because the fix differs by kind:

| Kind | Looks like | The fix lives in |
| --- | --- | --- |
| **Wrong approach** | Work later thrown away; a rewrite after a user correction | A rule in `CLAUDE.md` or a principle doc |
| **Missing context** | Same file read 3×; a convention discovered late; an assumption contradicted by an existing doc | Reading the right doc *first*; sometimes a pointer added to `CLAUDE.md` |
| **Tool thrash** | Retry loops, repeated near-identical commands, flag guessing | A note in the relevant skill, or in `CLAUDE.md` |
| **Environment friction** | Broken/flaky tests, teardown timeouts, slow suites, unrelated failures | The project's friction ledger if it has one; otherwise a task once it recurs |
| **Scope drift** | Time spent on work the user never asked for | A rule; usually "ask before widening" |
| **Process skipped** | Convention not followed, task status not flipped, docs not updated, checks not run | The relevant skill or the project's contributing/development guide |
| **Idle / stall** | Long gaps, a hung command, waiting on approval | Usually nothing — note it, don't invent a fix |

For every finding, state the **cost** in concrete terms (minutes, tokens, tool
calls, a redone file) and the **counterfactual**: what would you do differently
if the session started over? A finding without a counterfactual is a complaint.

Be honest about attribution. Distinguish *my mistake* (wrong assumption, skipped
step) from *repo friction* (flaky suite, missing doc) from *ambiguity* (the
request genuinely had two readings). Only the first is a lesson about conduct;
the second is a task; the third is a prompt for the user.

## Step 4 — Report, then stop

Present this and wait. Do **not** write files yet.

```
## Session reflection — <slug>

**Shape:** 2h10m wall clock (~1h20m active), 214 tool calls, 9 errors, 3 commits, 1 task landed.
**Summary:** one or two sentences on what the session was and whether it went well.

### What went wrong

| # | Finding | Kind | Cost | Counterfactual |
|---|---------|------|------|----------------|
| 1 | Rewrote `UserPanel.tsx` after reading the layout convention late | missing context | ~25 min, 3 rewrites | Read `CLAUDE.md` § Layout before the first edit |
| 2 | `db.integration.test.ts` teardown timeout (again) | environment | ~6 min re-running | Already known — 4th occurrence, worth a task |
| 3 | Built a settings toggle the user never asked for | scope drift | ~15 min, reverted | Ask before widening scope |

### What went well
- One line. Keep it short.

### Proposed follow-ups
- [ ] task: fix the integration-test teardown (4th occurrence)
- [ ] CLAUDE.md: nothing — the rule for #1 already exists, I just didn't read it
- [ ] reflection note at <reflections-dir>/2026-09-07-<slug>.md

Which of these should I do?
```

## Step 5 — File what was approved

Each finding has exactly one home. Do not duplicate a finding across two.

**Where the reflection note goes.** Use the project's existing convention if it
has one — look, in order, for an existing `**/reflections/` directory, a
`docs/internal/` tree, or a `docs/` tree. Otherwise create
`.claude/reflections/`. Name the file `YYYY-MM-DD-<short-slug>.md`; two sessions
on one day get two files. Never edit an old note — a later session that reaches
a different conclusion writes its own note and links back. On first use, drop a
short `README.md` in that directory explaining what belongs there (the table
below is the content) so the convention outlives this session.

**A session id is not stable, so never identify a session by id alone.** One
conversation can be re-keyed as it runs and end up as several `.jsonl` files,
each recording its own `sessionId`. Cite the id you actually analysed *and* the
content that pins it down: start time, wall clock, tool-call count.

Note format:

```markdown
# 2026-09-07 — user panel toolbar

Session: `18bf4f4b` · 2h10m wall (~1h20m active) · 214 tool calls, 9 errors · 3 commits

## What this session was
One or two sentences.

## What went wrong

### 1. Rewrote the panel after reading the layout convention late
**Kind:** missing context · **Cost:** ~25 min, 3 rewrites of `UserPanel.tsx`
**What happened:** started editing before reading `CLAUDE.md` § Layout, then
restructured twice once the folder-per-feature rule surfaced.
**Counterfactual:** read the layout section before the first edit.
**Filed:** nothing — the rule already exists and was simply not read.

### 2. …

## What went well
One line.

## Filed
- task: `01m2…` fix the integration-test teardown — 4th occurrence
- rules: none proposed
```

Everything else:

| Finding | Home |
| --- | --- |
| Build/test friction seen while verifying | The project's friction ledger (e.g. a `check-log.md`) if one exists — one appended row per occurrence, never an edit, because the repetition *is* the signal. No ledger: fold it into the note, and file a task once it recurs. |
| Something worth fixing | A task — via the project's task convention (`taskmd:add-task`, an issue tracker, a `TODO`/backlog file). Never fix it inline: that mixes an unrelated change into the session you are reflecting on. The exception is a fix to this skill or to `CLAUDE.md` wording, which is documentation of the lesson itself. |
| A recurring conduct mistake | A rule in `CLAUDE.md` (or the skill that should have prevented it). Propose the exact wording and the exact file, and let the user approve it. Add a rule only for something that has happened **more than once** — a one-off gets a note, not a permanent rule. Rules are expensive; every one is read by every future session. |
| The narrative of what happened and why | The reflection note |

Keep each finding traceable to the transcript or to git. A reflection that
cannot point at evidence is a story, and stories are what the note exists to
replace.

Close by saying what you filed and what you deliberately left alone.

---
name: skill-scout
description: >-
  Scouts the agent's own session transcript for work worth turning into a
  skill: multi-step procedures done by hand, instructions the user had to spell
  out, knowledge that took a long time to discover, and throwaway scripts that
  will be needed again. Checks every candidate against the skills already
  installed, weighs cheaper options first (nothing, a CLAUDE.md line, a hook,
  extending an existing skill), and proposes only the new skills that clear the
  bar, each with a name, trigger description, outline and transcript evidence.
  Use when the user asks "what skills should I create", "is there a skill in
  this", "what could be automated from this session", "scout for skills", or
  invokes /skill-scout, typically at the end of a session. Base it on the real
  transcript, never on memory alone.
---

# Skill Scout

## Why this exists

The best skills come from work that has already been done once by hand. That
work shows the real steps, where it went wrong, and what had to be explained.
Once the session ends, that record is lost unless someone pulls it out.

`reflect` asks *what went wrong*. This skill asks *what will be done again*.
They read the same transcript, but they look for different things.

Three rules:

- **Use the transcript, not your memory of it.** Every candidate must point to
  turns or tool calls you can find in the `.jsonl`.
- **The bar is high.** A skill is loaded into every future session's list of
  options, and each one makes choosing the right skill harder. Propose fewer,
  better ones. "Nothing here is worth a skill" is a valid result, and a common one.
- **Prefer the cheapest fix that works.** Many candidates are really a line in
  `CLAUDE.md`, a hook, or a paragraph added to a skill that already exists.

## The loop

1. **Gather** the transcript and the list of installed skills.
2. **Mine** the transcript for candidates.
3. **Filter** each candidate against existing skills and cheaper options.
4. **Propose** to the user, then stop. *Do not write any files yet.*
5. **Hand off** the approved candidates to `skill-creator`.

---

## Step 1: Gather

Use `reflect`'s metrics script, which is in the same plugin, to find the
transcript. Its report also includes the steering log (every user turn) and the
commands that were repeated:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/reflect/scripts/session_metrics.py"          # current session
python3 "${CLAUDE_PLUGIN_ROOT}/reflect/scripts/session_metrics.py" --list   # other sessions in this project
```

The report prints the transcript path at the top. `references/signals.md` calls
it `$F`.

Then list what is already installed, so you don't propose something that
exists:

- The skills listed in your context for this session, which include plugin
  skills.
- `~/.claude/skills/`, `.claude/skills/` in the project, and any plugin repo the
  user works in (a `plugins/` tree or a `.claude-plugin/marketplace.json`).

Read the `description` of every skill that might overlap. Names alone can
mislead.

## Step 2: Mine

`references/signals.md` lists what to look for and how to grep for it. The main
signals:

| Signal | Looks like | Skill material |
| --- | --- | --- |
| **Hand-run procedure** | 4+ tool calls that together reach one outcome that will come up again (cut a release, set up a service, triage an alert) | The steps, in order, with the checks between them |
| **User-supplied procedure** | The user explains "first X, then Y, and make sure Z", or corrects the order of steps | The user's own wording is the best first draft |
| **Repeated instruction** | The user states the same preference or step in two different turns, or two different sessions | The rule the skill has to enforce |
| **Hard-won knowledge** | Flag guessing, reading docs or `--help`, several attempts before a command worked | The answer, so the next session skips the search |
| **Throwaway script** | A heredoc, a `python3 -c`, or a scratchpad script that parses or reshapes data | A bundled `scripts/` file |
| **Skill that fell short** | A skill ran and then the agent or user worked around it or extended it | An edit to that skill, not a new one |

Whether something recurs is the strongest evidence. If a candidate looks
plausible, run the metrics script with `--list`, or use `vibeview search` if it
is installed, to check whether earlier sessions did the same thing. When the
user tells you something is routine ("I do this every Monday"), that also
counts as recurrence.

## Step 3: Filter

Go through these options in order for each candidate and stop at the first one
that fits:

| Option | When | Output |
| --- | --- | --- |
| **Nothing** | Done once and unlikely to come up again, or the agent already does it well without help | Drop it and say why |
| **CLAUDE.md line** | A single preference or fact, with no procedure attached | The exact wording and the file it goes in |
| **Hook** | "Every time X, do Y" and the harness can run it without judgement (formatting, a check before commit) | Name `update-config` as the route |
| **Extend a skill** | An existing skill covers the area but is missing this case | The skill, the section, and what to add |
| **New skill** | A procedure with several steps that recurs and needs judgement or knowledge that isn't obvious, and no existing skill covers it | A full proposal (Step 4) |

A new skill also has to meet these conditions:

- **You can say when to trigger it in one sentence.** If you can't say when it
  should fire, it won't fire.
- **The scope is right.** It should be one job, not "everything about service X".
  It should also be more than one command, which belongs in `CLAUDE.md`.
- **It can run anywhere it would be installed.** Nothing tied only to this
  session, unless it is meant to be a skill for this one project.

## Step 4: Propose, then stop

Present the proposals and wait. Do **not** write files yet.

```
## Skill scout: <session slug>

**Scanned:** 1 session (plus 4 earlier ones in this project, checked for recurrence), 38 skills installed.
**Result:** 1 new skill, 1 extension, 2 dropped.

### New: `deploy-preview`
**Trigger:** "Deploy a preview environment for the current branch; use when the user says 'preview', 'deploy this branch', or pastes a PR asking for an env."
**What it does:**
1. Check the branch is pushed and CI is green (`gh pr checks`)
2. Run `make preview ENV=<branch-slug>` with the flags that worked (`--no-cache` is needed after a dependency change)
3. Poll `kubectl rollout status` until ready, then post the URL
**Bundled:** `scripts/slugify_branch.sh`, the heredoc used in this session, cleaned up
**Evidence:** turns 12–31 (19 tool calls, 3 failed attempts at the flags); the same sequence in session `a41c…` on 09-22
**Overlaps checked:** `release` (tags and publishing, not previews), no conflict
**Home:** `.claude/skills/` in this project, since the Makefile targets are project-specific

### Extend: `pr-open`
Add: "If the repo has a `CHANGELOG.md`, remind the user to update it." The user asked for this at turn 44.

### Dropped
- One-off data backfill: not going to happen again
- "Use pnpm, not npm": this is one line for `CLAUDE.md`, not a skill. Want me to add it?

Which of these should I build?
```

For each proposal, fill in every field. **Evidence** has to cite real turns or
sessions. If you can't fill it in, the candidate didn't clear the bar.

**Home** is where the skill will live. Choose from:

- `.claude/skills/` in the project, for anything tied to this repo.
- `~/.claude/skills/`, for personal skills that work across projects.
- A plugin repo the user maintains, if they publish skills. Follow that repo's
  rules for registering a skill, for example adding it to `marketplace.json`,
  updating the README, and bumping the version.

## Step 5: Hand off

For each approved new skill, invoke `skill-creator` and pass the proposal as
the starting brief: trigger, steps, evidence, bundled scripts, and home. Also
pass the relevant parts of the transcript, meaning the user's own wording and
the commands that finally worked. Those are why the draft will be better than
one written from scratch.

For approved extensions and `CLAUDE.md` lines, make the edit directly. Each one
is small and the user has already approved the wording.

Finish by listing what you created, what you edited, and what you dropped and
why.

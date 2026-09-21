# Signals to look for in a session transcript

The metrics script counts things. This file says what those counts *mean* and
how to find the ones a count cannot reach. Work top-down: the first three
sections find most of what matters in a typical session.

Throughout, `$F` is the transcript path — the metrics script prints it at the
top of its report. With `vibeview` installed, `$S` is the session id
(`vibeview self | awk '/Session:/{print $2}'`) and
`$F = $(vibeview inspect --json $S | jq -r .file_path)`. Every `grep` below
works on `$F` directly, so none of this requires `vibeview`.

---

## 1. User corrections — the highest-signal thing in the file

Every user turn after the first is a moment the agent was going somewhere the
user did not want. The script prints them all as the *steering log*. For each
one, read what came immediately before it and classify:

- **A redirect** ("no, do X instead") → the agent chose wrong. Why? Was the
  information available in the repo, or genuinely absent from the request?
- **An addition** ("also update the docs") → not a mistake, but ask whether the
  agent should have proposed it. If the request implied it, that is a miss.
- **A repeat** — the user saying the same thing twice is the strongest possible
  signal that the agent was not listening. Never wave this one away.
- **A frustration marker** ("no", "stop", "I already said", "why did you") —
  grep the steering log the script printed, or the raw file:
  `grep -oE '"content":"(no,|stop|I already|why did you)[^"]{0,120}"' "$F"`.

## 2. Failures and retries

The script lists failed tool calls and repeated near-identical commands. The
pattern that matters is not a single error — it is **three variations of the
same command in a row**, which means the agent was guessing instead of reading.

```bash
# Every bash command run, most repeated first
grep -o '"command":"[^"]\{0,120\}"' "$F" | sort | uniq -c | sort -rn | head -20

# Tool results flagged as errors, with surrounding context
grep -o '"is_error":true[^}]\{0,200\}' "$F" | head -30
```

Ask of each cluster: was the answer available in `--help`, in `CLAUDE.md`, or in
a file that was never opened?

## 3. Work that was thrown away

The most expensive failure mode and the hardest to see in counts. Look for:

- **File churn** — the script flags files edited 3+ times. Three edits to one
  file is normal when building it; three *rewrites* after a correction is not.
  Check the diffs: did edit 3 undo edit 1?
- **Reverted or deleted work** — `git log --oneline --diff-filter=D -10`, and
  anything in the transcript where a file was written then removed.
- **Re-reading** — the same `Read` on the same path several times means the
  first read was too narrow:
  `grep -o '"file_path":"[^"]*"' "$F" | sort | uniq -c | sort -rn | head -20`.

## 4. Tests and checks

```bash
grep -oE '(npm|pnpm|yarn|make|npx|cargo|go|pytest|python3?|gradle|mvn)[^"]{0,80}(check|test|lint|build)[^"]{0,40}' "$F" \
  | sort | uniq -c | sort -rn
```

For each run, find its result in the transcript and classify:

| Observed | Kind | Where it goes |
| --- | --- | --- |
| Failed for a reason my change caused | my mistake | fix it (or a task) |
| Failed on an unrelated, pre-existing problem | environment friction | the friction ledger, or a task if it recurs |
| Passed on retry with no change | flaky | the friction ledger, marked flaky |
| Never ran before committing | process skipped | a lesson |

If the project keeps a friction ledger (a `check-log.md` or similar), check it
before writing anything: if the symptom is already there, this occurrence is
*another row* (not an edit), and a repeat count of three or more is the argument
for a task.

## 5. Time

The script reports wall clock, idle gaps, and the slowest tool calls. Interpret,
do not just report:

- **A long idle gap** is usually the user being away or an approval wait. Not a
  finding. Do not pad the report with these.
- **A slow tool call** matters only if it was avoidable — a full test suite when
  a targeted run would have done, a broad search that a known path would have
  answered, a build run three times.
- **Long active stretches with no commit** suggest the work was not sliced.
  Compare `git log` timestamps against the session span.

## 6. Process compliance

Do not guess the rules — read them. `CLAUDE.md`, `CONTRIBUTING.md`, and any
development/contributing guide the repo has are the source of what "compliant"
means here. Then check the session against the rules that are easy to skip, and
report **only** the ones actually skipped. Typical candidates:

- Branch/worktree conventions: did the work happen where it was supposed to?
- Was the task or issue status updated in the same commit as the work?
- Did every check/test failure get recorded where the project expects it?
- Did a user-facing change update the docs the project requires?
- Naming, file-layout, and test-placement conventions the repo states explicitly.

A rule the repo never states is not a compliance finding — at most it is a
proposal for the user.

## 7. Subagents and sibling sessions

A subagent's flailing does not appear in the parent's tool counts. With
`vibeview`: `vibeview related --json $S`. Otherwise, sibling transcripts sit in
the same `~/.claude/projects/<project-slug>/` directory — the script's `--list`
mode shows them with their times and sizes.

Run the metrics script against any subagent transcript that looks long, and
check for the classic waste: a subagent launched for something the agent could
have answered directly, or two subagents that searched for the same thing.

## 8. Token and cost shape

If `vibeview` is installed, `vibeview inspect $S` reports input/output/cache
tokens and cost. Big cache-read numbers are normal and healthy. What is worth
noting is a session whose *output* tokens are large relative to what landed — a
lot of writing for a small diff usually means rewrites (§3) or over-long
reports.

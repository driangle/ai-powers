# Signals of a skill worth writing

In the snippets below, `$F` is the transcript path, which the metrics script
prints at the top of its report. They are plain `grep`s on the `.jsonl` file,
so none of them need `vibeview`.

For every hit, read the transcript around it before deciding. A grep finds
where something might be, but only the text shows whether the work will happen
again.

---

## 1. Procedures the user dictated

The steering log, meaning every user turn the script prints, is the richest
source. Look for:

- **Ordering words**: "first", "then", "after that", "before you", "make sure".
  A user writing out a sequence is writing the skill for you.
- **Corrections to the order of steps**, such as "no, run the migration before
  the seed". The corrected order is the part that isn't obvious.
- **Instructions that recur**, where the same preference appears in two turns.
  Within one session it could be a CLAUDE.md line. Across sessions it is a
  strong signal.

```bash
grep -oE '"content":"[^"]{0,40}(first|then|after that|before you|make sure|always|every time)[^"]{0,160}"' "$F"
```

## 2. Sequences of tool calls

A skill packages a sequence. Pull out the ordered list of tool calls and look
for a run of calls with one goal, especially one that crosses tools (for
example `gh` → `kubectl` → a log query → a Slack post).

```bash
# Ordered tool names, one per line
grep -o '"type":"tool_use","id":"[^"]*","name":"[^"]*"' "$F" | sed 's/.*"name":"//; s/"$//'

# Every bash command, in order
grep -o '"command":"[^"]\{0,160\}"' "$F"
```

Cut out the dead ends. The skill should contain the path that worked, not
every attempt.

## 3. Knowledge that took effort to find

When the agent tried several variants of one command, read `--help`, or
searched the docs, the final answer is worth writing down. The metrics script
lists retry loops and failed tool calls. For each one, record the command that
finally worked and what made it work.

```bash
grep -oE '"command":"[^"]*(--help|-h |man )[^"]{0,80}"' "$F"
grep -o '"is_error":true[^}]\{0,200\}' "$F" | head -30
```

## 4. Ad-hoc scripts

Code written inline to parse, filter, or reshape data is a candidate for a
bundled `scripts/` file. A script is more reliable than having the agent
rewrite the same logic each time.

```bash
grep -oE '"command":"[^"]*(python3? -c|node -e|<<.?EOF|jq )[^"]{0,160}"' "$F"
grep -o '"file_path":"[^"]*scratchpad[^"]*"' "$F" | sort -u
```

## 5. Recurrence across sessions

One occurrence is an anecdote. Two or more is a pattern. Check sibling
sessions for the same commands or phrasing:

```bash
DIR=$(dirname "$F")
grep -l 'make preview' "$DIR"/*.jsonl        # replace with the candidate's key command
```

With `vibeview`, `vibeview search "<phrase>"` searches across projects. That
matters for personal skills that aren't tied to one repo.

## 6. Skills that fell short

Find the skills that were invoked, then read what came right after each one:

```bash
grep -oE '"name":"Skill","input":\{"skill":"[^"]*"' "$F" | sort | uniq -c
```

If the agent worked around a skill's output, re-ran its steps by hand, or the
user corrected it, the fix is an edit to that skill, not a new skill.

---
name: work
description: "Pick up the next task, execute it, verify it, mark it complete, and commit. Use when the user wants to work through tasks one at a time, or says 'do the next task', 'work on the next item', or invokes /work. Optionally accepts a task ID and/or custom instructions."
allowed-tools: Bash, Read, Glob, Grep, Edit, Write, Agent, Skill
---

# work

Execute one task end-to-end: pick it up, do the work, verify, mark complete, and commit.

## Input

Optionally accepts:
- A **task ID or name** to work on a specific task (e.g. `/work 042` or `/work auth-refactor`).
- A **task query** to find a task by description or filters. This can be:
  - **Natural language** — e.g. `/work something related to authentication` or `/work a pending high-priority CLI task`.
  - **A `taskmd` CLI command** — e.g. `/work taskmd search 'auth' --filter status=pending` or `/work taskmd next --scope cli --filter priority=high`.
- **Custom instructions** after the task identifier that should guide the implementation (e.g. `/work 042 use the new API client instead of fetch`).

If no task ID or query is provided, the next available task is selected automatically.

## Steps

1. **Find the task.**
   - If the user provided a task ID or name, use that directly.
   - If the user provided a `taskmd` CLI command (starts with `taskmd`), run it with `--format json` appended (if not already present) and `--limit 1` (if not already present) to get the top result. Extract the task ID from the output.
   - If the user provided a natural-language query (not a task ID and not a `taskmd` command), translate it into an appropriate `taskmd` command:
     - Use `taskmd search "<query>" --format json --limit 1` for keyword/topic queries.
     - Add `--filter` flags for any constraints the user mentioned (e.g. status, priority, scope, tags, effort).
     - Use `taskmd next` instead of `taskmd search` when the user's intent is about priority or "what's next" within a filtered set.
     - Run the constructed command and extract the task ID from the output.
   - If no input was provided, run `taskmd next --limit 1 --format json` to get the highest-priority ready task.
   - If no task is found, tell the user there are no remaining tasks and stop.

2. **Do the task.** Invoke the `/do-task` skill with the task ID from step 1. If the user provided custom instructions, incorporate them into the work — they take priority over default approaches where applicable.

3. **Verify the task.** Once the work is done, invoke the `/verify-task` skill with the same task ID. If verification fails, fix the issues and re-verify until it passes.

4. **Mark the task complete.** Invoke the `/complete-task` skill with the task ID.

5. **Commit your changes.** Invoke the `/commit` skill to commit all changes with a conventional commit message.

## Notes

- Only work on **one task** per invocation. If the user wants to continue, they can invoke `/work` again.
- If a task is blocked by dependencies or cannot be completed, explain why and stop — do not skip to another task.

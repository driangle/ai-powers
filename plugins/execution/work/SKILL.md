---
name: work
description: "Pick up the next task, execute it in its own git worktree, verify it, mark it complete, commit, and merge it back into main. Use when the user wants to work through tasks one at a time, or says 'do the next task', 'work on the next item', or invokes /work. Optionally accepts a task ID and/or custom instructions."
allowed-tools: Bash, Read, Glob, Grep, Edit, Write, Agent, Skill, EnterWorktree, ExitWorktree
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

2. **Enter a worktree for the task.** Isolate the work in its own git worktree, so `main` stays clean and several tasks can run side by side.

   Create one with `EnterWorktree`, naming it after the task id (e.g. `EnterWorktree({ name: "01m266ww9" })`). This puts the session in `.claude/worktrees/<id>` on branch `task/<id>`. Do the rest of the task there.

   Create a worktree when **either** holds:
   - The work is tied to a task id — anything resolved in step 1 qualifies.
   - The work is substantial enough to warrant isolation: multiple files, a refactor, anything that will not land in a single small commit.

   Skip the worktree, and work in the current tree, when:
   - The change is a trivial one-off with no task id (a typo, a one-line fix).
   - The session is already inside a worktree (`EnterWorktree` refuses to nest) — reuse it.
   - The repo is not a git repository.

   Say which worktree you entered before starting the work.

3. **Initialize the worktree.** Only if you created one in step 2. A fresh worktree is a clean checkout: it has the source files but none of the untracked, gitignored state the project needs to build, run, or test. Set it up **before** doing any work, or the first test run will fail for reasons that have nothing to do with the task.

   What to run is project-dependent — determine it, do not guess:
   - Read the project's `CLAUDE.md`, `README.md`, or contributing guide for the documented setup command.
   - Otherwise infer from the lockfile at the repo root: `pnpm-lock.yaml` → `pnpm install`, `package-lock.json` → `npm ci` (or `npm install`), `yarn.lock` → `yarn install`, `bun.lockb` → `bun install`, `uv.lock` → `uv sync`, `poetry.lock` → `poetry install`, `Cargo.lock` → `cargo fetch`, `go.sum` → `go mod download`, `Gemfile.lock` → `bundle install`, `composer.lock` → `composer install`.
   - Monorepos usually need the install at the workspace root, not in a sub-package.

   Also copy over any gitignored files the project needs that git will not bring along — most commonly `.env` / `.env.local`. Copy them from the main worktree (find its path in `git worktree list`) rather than inventing values. Do not copy build output or dependency directories; regenerate those.

   If the project needs a build or codegen step before tests run (e.g. `pnpm build`, `cargo build`, `go generate`, a Prisma/protobuf generate), run it too.

   Say what you ran. If setup fails, stop and report it — do not start the task on a broken worktree.

4. **Do the task.** Invoke the `/do-task` skill with the task ID from step 1. If the user provided custom instructions, incorporate them into the work — they take priority over default approaches where applicable.

5. **Verify the task.** Once the work is done, invoke the `/verify-task` skill with the same task ID. If verification fails, fix the issues and re-verify until it passes.

6. **Reconcile the backlog.** A task rarely finishes exactly as written. Before completing it, ask whether any of this happened:
   - **Postponed** — something in the task's scope you deliberately did not do.
   - **Shifted** — work that belonged to a different task, or that you moved out of this one into another.
   - **Missing** — work you discovered that no task covers.
   - **Follow-up** — the task is done but left something behind: a `TODO`, a skipped test, a temporary shim, a doc that is now stale.

   If none of it happened, skip this step. If any of it did, spawn the `backlog-reconciler` subagent (shipped in the `planning` plugin — if it is not installed, do the reconciliation inline and say so) with the task ID and your full list of loose ends — including the ones you suspect are not worth filing. Do not reconcile inline: the point of the subagent is that it comes to the backlog without the tunnel vision of having just written the code, so it finds the existing task that already covers a loose end instead of filing a near-duplicate.

   Accept its answer. If it hands back `fix now:` items, do them in this working tree before step 7, then re-run verification — a fix after a green gate is an unverified fix. Report its arithmetic line and the ids it touched in your closing message.

7. **Mark the task complete.** Invoke the `/complete-task` skill with the task ID.

8. **Commit your changes.** Invoke the `/commit` skill to commit all changes with a conventional commit message. The reconciler's task edits land in the same commit as the work.

9. **Merge back into `main` and clean up.** Only if you created a worktree in step 2. Skip this entire step if the user asked you not to merge (e.g. "leave it on a branch", "I want to review it first", "open a PR instead") — in that case leave the worktree in place, tell the user its path and branch, and stop.

   Otherwise, from inside the worktree:
   1. Confirm the working tree is clean (`git status --short`). If it is not, stop and report — step 8 should have committed everything.
   2. Rebase onto `main`: `git rebase main`. Resolve conflicts by combining both sides' intent, favoring the task branch when the sides are genuinely incompatible; `git add` each resolved file and `git rebase --continue`. If a conflict cannot be resolved confidently, run `git rebase --abort`, leave the worktree in place, report the problematic files, and stop.
   3. Re-run the project's validation command on the rebased branch — this is the exact commit `main` will point to. If it fails, do not merge: leave the worktree in place, report the failures, and stop.
   4. Fast-forward `main` from the main worktree (do **not** `git checkout main` — `main` is checked out elsewhere and the checkout will fail): find its path in `git worktree list`, then run `git -C <main-path> merge --ff-only task/<id>`. If the fast-forward fails, `main` moved during the rebase — report it and stop.
   5. Call `ExitWorktree({ action: "remove" })` to return to the original directory and delete the now-merged worktree and branch. If it refuses because of leftover changes, do not pass `discard_changes` — report what it listed and let the user decide.
   6. Show `git log --oneline -3` from `main`.

## Notes

- Only work on **one task** per invocation. If the user wants to continue, they can invoke `/work` again.
- If a task is blocked by dependencies or cannot be completed, explain why and stop — do not skip to another task. Exit the worktree with `action: "keep"` if you already created one and made changes in it.
- Do NOT push to a remote, and never create a merge commit — `main` only ever moves forward by fast-forward.
- New worktrees branch from whatever the `worktree.baseRef` setting says — `fresh` (the default) branches from `origin/<default-branch>`, `head` from the current local HEAD. If local `main` is ahead of the remote, the step 9 rebase onto `main` is what reconciles the two; if the repo has no remote, set `worktree.baseRef` to `head`.
- Whenever the run ends without merging — blocked task, failed validation, unresolvable conflict, or the user opting out — leave the worktree on disk and report its path and branch so the work is not stranded.

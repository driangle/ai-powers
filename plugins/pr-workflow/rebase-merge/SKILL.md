---
name: rebase-merge
description: "Rebase the current branch onto a target branch, resolve any conflicts, then fast-forward merge it into the target. Use when the user asks to merge a branch via rebase or invokes /rebase-merge."
allowed-tools: [Bash, Read, Edit]
---

# rebase-merge

Merge the current branch into a target branch using rebase + fast-forward only.

`$ARGUMENTS` is the target branch (e.g. `main`). If it is empty, ask the user for the target branch and stop.

## Steps

1. Run `git status --short`. If the working tree is dirty, inform the user and stop — do not stash or commit for them.
2. Record the current branch as the original branch: `git rev-parse --abbrev-ref HEAD`. If it equals the target branch, inform the user and stop. Whatever happens after this point — success, conflict abort, or fast-forward failure — the skill must end with the original branch checked out.
3. Rebase the current branch onto the target:
   ```
   git rebase <target>
   ```
4. If the rebase stops on conflicts, resolve them:
   - Run `git status` to list conflicted files.
   - Read each conflicted file, resolve the conflict markers by combining both sides' intent (favor the current branch's changes when the sides are genuinely incompatible), then `git add` the file.
   - Continue with `git rebase --continue`. Repeat until the rebase completes.
   - If a conflict cannot be resolved confidently, run `git rebase --abort` (this leaves the original branch checked out) and report which files were problematic.
5. Validate the rebased branch before merging — this is the exact commit the target will point to:
   - Determine the project's conventional validation command, in order of preference: instructions in `CLAUDE.md`, a `check` or `test` target in a `Makefile`, a `check`/`test`/`lint` script in `package.json`, or the language's standard (`cargo test`, `go test ./...`, `pytest`, etc.).
   - Run it. If validation fails, do NOT merge: report the failures and stop, leaving the rebased branch checked out so the user can fix it.
   - If no validation command can be found, tell the user validation was skipped and continue.
6. Fast-forward merge into the target:
   ```
   git checkout <target>
   git merge --ff-only <branch>
   ```
7. If the fast-forward merge fails (target has commits not in the rebased branch), inform the user the target moved and a fast-forward is not possible.
8. On success, run `git log --oneline -3` on the target and show the user the result.
9. Return to the original branch: `git checkout <branch>`. Then verify with `git rev-parse --abbrev-ref HEAD` that the checked-out branch matches the original branch recorded in step 2; if it doesn't, check it out and inform the user.

## Notes

- Do NOT push to a remote. All operations are local.
- Do NOT use `git merge` without `--ff-only`, and never create a merge commit.
- Never force-push or rewrite the target branch.
- Always finish with the original branch checked out, regardless of outcome.

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
2. Record the current branch: `git rev-parse --abbrev-ref HEAD`. If it equals the target branch, inform the user and stop.
3. Rebase the current branch onto the target:
   ```
   git rebase <target>
   ```
4. If the rebase stops on conflicts, resolve them:
   - Run `git status` to list conflicted files.
   - Read each conflicted file, resolve the conflict markers by combining both sides' intent (favor the current branch's changes when the sides are genuinely incompatible), then `git add` the file.
   - Continue with `git rebase --continue`. Repeat until the rebase completes.
   - If a conflict cannot be resolved confidently, run `git rebase --abort` and report which files were problematic.
5. Fast-forward merge into the target:
   ```
   git checkout <target>
   git merge --ff-only <branch>
   ```
6. If the fast-forward merge fails (target has commits not in the rebased branch), abort: run `git checkout <branch>` to return to the original branch and inform the user the target moved and a fast-forward is not possible.
7. On success, run `git log --oneline -3` on the target and show the user the result.

## Notes

- Do NOT push to a remote. All operations are local.
- Do NOT use `git merge` without `--ff-only`, and never create a merge commit.
- Never force-push or rewrite the target branch.

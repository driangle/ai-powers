---
name: sync-worktrees
description: "Synchronize worktrees with main: rebase each worktree branch onto main, fast-forward merge it into main, then fast-forward every worktree branch back up to the final main. Use when the user asks to sync worktrees, merge worktrees into main, or invokes /sync-worktrees."
allowed-tools: [Bash, Read, Edit]
---

# sync-worktrees

Synchronize worktree branches with main and back: each branch is rebased onto main and fast-forward merged into main, then all branches are fast-forwarded to the final main so everything ends up in sync.

`$ARGUMENTS` is a list of worktrees to sync (paths or branch names, space-separated). If empty, sync every worktree listed by `git worktree list` except the one with main checked out.

## Steps

1. Run `git worktree list` to map worktree paths to branches. Identify the worktree where `main` is checked out (call it the main worktree). Resolve `$ARGUMENTS` against this list; if an argument matches no worktree, inform the user and stop.
2. For every worktree involved (including the main worktree), run `git -C <path> status --short`. If any working tree is dirty, list the dirty worktrees, inform the user, and stop — do not stash or commit for them.
3. For each selected worktree, one at a time:
   1. Rebase its branch onto main: `git -C <path> rebase main`.
   2. If the rebase stops on conflicts, resolve them: read each conflicted file, resolve the markers by combining both sides' intent (favor the worktree branch's changes when the sides are genuinely incompatible), `git add` the file, and `git -C <path> rebase --continue` until it completes. If a conflict cannot be resolved confidently, run `git -C <path> rebase --abort`, report which files were problematic, and stop the whole sync.
   3. Fast-forward main to the rebased branch, from the main worktree: `git -C <main-path> merge --ff-only <branch>`. If this fails, stop and inform the user.
4. After all selected branches are merged, sync everything back: for each selected worktree, run `git -C <path> merge --ff-only main` so every branch points at the final main. These are guaranteed fast-forwards; if one fails, report it.
5. Verify: run `git -C <path> rev-parse HEAD` for main and each synced worktree and confirm they all match. Show the user `git log --oneline -5` from main and a summary of which branches were synced.

## Notes

- Do NOT push to a remote. All operations are local.
- Never merge without `--ff-only` into main, and never create a merge commit.
- Never force-push or rewrite main beyond the fast-forward merges above.
- Process worktrees strictly one at a time — each rebase must target the main that includes the previously merged branches.
- Do not change which branch any worktree has checked out.

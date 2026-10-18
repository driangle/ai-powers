---
name: commit
description: "Commit all uncommitted changes with an auto-generated conventional commit message. Use when the user asks to commit, save changes, or invokes /commit."
allowed-tools: [Bash, Skill]
---

# commit

Stage and commit all uncommitted changes using an auto-generated commit message.

## Steps

1. Run `git status --short` to check for uncommitted changes (staged and unstaged). If there are no changes, inform the user there is nothing to commit and stop.
2. Run `git add -A` to stage all changes.
3. Invoke the `/commit-msg` skill to generate a conventional commit message from the staged diff.
4. Create the commit using the generated message:
   ```
   git commit -m "<message>"
   ```
   Append a co-author trailer naming the model you are currently running as (do not hardcode a model name):
   ```
   Co-Authored-By: Claude <model name> <noreply@anthropic.com>
   ```
   If the session supplies its own attribution lines for commits, use those exactly instead.
5. Run `git status` after committing to confirm success.
6. Show the user the commit hash and message.

## Notes

- If `$ARGUMENTS` is non-empty, use it as the commit message directly instead of invoking `/commit-msg`.
- Do NOT push to a remote. Only commit locally.

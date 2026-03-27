---
name: commit-msg
description: "Generate a one-line conventional commit message from staged changes. Use when the user asks for a commit message or invokes /commit-msg."
allowed-tools: Bash
---

# commit-msg

Generate a single-line commit message using the Conventional Commits format.

## Steps

1. Run `git diff --cached HEAD` to get the staged diff.
2. If the diff is empty, output: `No staged changes found. Stage your changes with git add first.` and stop.
3. Analyze the diff and write ONE line in Conventional Commits format (feat, fix, refactor, chore, docs, test, style, perf, ci). Add a scope when clearly scoped to one module, e.g. `fix(auth): ...`.
4. Keep the message under 72 characters. Use imperative mood ("add", "fix", "update"). Be specific but concise.

## Output

Output ONLY the commit message — no quotes, no explanation, no markdown, no trailing newline. Just the raw message text. This is critical because the output will be used directly as: `git commit -m "$(claude -p '/commit-msg')"`.

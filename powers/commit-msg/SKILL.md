---
name: commit-msg
description: "Generate a one-line conventional commit message from staged changes. Use when the user asks for a commit message or invokes /commit-msg."
allowed-tools: Bash
---

# commit-msg

Generate a single-line commit message using the Conventional Commits format.

## Steps

1. Run `git diff --cached HEAD` to get the staged diff against HEAD.
2. If the diff is empty, run `git diff HEAD` to check for unstaged changes. If that is also empty, output: `chore: no changes detected` and stop.
3. Analyze the diff and write ONE line in Conventional Commits format:
   - `feat: ...` for new features
   - `fix: ...` for bug fixes
   - `refactor: ...` for restructuring without behavior change
   - `chore: ...` for maintenance, deps, config
   - `docs: ...` for documentation only
   - `test: ...` for adding or updating tests
   - `style: ...` for formatting, whitespace, semicolons
   - `perf: ...` for performance improvements
   - `ci: ...` for CI/CD changes
   - Add a scope in parentheses when the change is clearly scoped to one module, e.g. `fix(auth): ...`
4. Keep the message under 72 characters. Use imperative mood ("add", "fix", "update", not "added", "fixes", "updated"). Be specific but concise.

## Output

Output ONLY the commit message — no quotes, no explanation, no markdown, no trailing newline. Just the raw message text. This is critical because the output will be used directly as: `git commit -m "$(claude -p '/commit-msg')"`.

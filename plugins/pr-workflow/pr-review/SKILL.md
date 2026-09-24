---
name: pr-review
description: Review a GitHub PR and present findings as author-addressed comments. Use when the user asks to review a PR, gives a PR URL or number, or asks for code review feedback on a pull request. Triggers on phrases like "review this PR", "look at this pull request", "code review", or any GitHub PR link.
allowed-tools: Bash, Read, Glob
---

## Input

Accepts a PR URL (e.g. `https://github.com/org/repo/pull/123`) or a PR number (for the current repo).

## Steps

1. Fetch in parallel:
   - `gh pr view <pr> --json title,body,files,additions,deletions,baseRefName,headRefName`
   - `gh pr diff <pr>`
   - Check if the repo has a CLAUDE.md (factor its conventions into the review)
   - Only if the user explicitly asks: `gh api repos/{owner}/{repo}/pulls/{number}/comments`

2. Read the full diff carefully. For large diffs, read persisted output files fully.

3. Write a clear explanation of the PR:
   - What problem does this PR solve and why?
   - What approach was taken — summarize the key changes across files
   - Call out any notable design decisions or trade-offs

4. Review for: bugs, missing error handling, security issues, performance problems, naming/readability, convention violations, lock file anomalies, unsafe casts/patterns.

5. Classify each finding on two axes:
   - **Severity**: **High**, **Medium**, **Low**, or **Nit**.
   - **Blocker**: whether the PR should not merge until it is fixed (bugs, security issues, data loss, broken contracts, violations of explicit repo rules). A Nit is never a blocker.

6. Assign each finding a stable id: `F1`, `F2`, … numbered in output order. The user refers to findings by these ids later (e.g. "fix F2", "post F1 and F3"), so reuse the same ids when the conversation returns to this review.

## Output

Print the review directly — do NOT post comments to the PR unless the user explicitly asks.

Format: H2 title with PR name, then a **"What this PR does"** section explaining the changes (from step 3), followed by a **"Findings"** section, then a **"Positives"** section noting what was done well.

In **Findings**, open with a one-line tally (e.g. `5 findings, 2 blockers`), then list blockers first, then the rest, each ordered by severity. Every finding starts with its id; only blockers carry an explicit mark, so anything unmarked is non-blocking:

```
**F1 · 🚫 Blocker · High** — `src/auth.ts:42`
Token expiry is compared in seconds against a millisecond timestamp, so every token is treated as expired.
Suggestion: compare against `Date.now() / 1000`.

**F2 · Nit** — `src/auth.ts:57`
`tmp` doesn't say what it holds.
Suggestion: rename to `decodedClaims`.
```

If there are no findings, say so instead of the tally.

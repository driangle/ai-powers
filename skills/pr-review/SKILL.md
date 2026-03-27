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

3. Review for: bugs, missing error handling, security issues, performance problems, naming/readability, convention violations, lock file anomalies, unsafe casts/patterns.

4. Categorize each finding: **High**, **Medium**, **Low**, or **Nit**.

## Output

Print the review directly — do NOT post comments to the PR unless the user explicitly asks.

Format: H2 title with PR name, one-line summary, then issues listed with severity, `file:line` reference, and concrete suggestion. End with a "Positives" section noting what was done well.

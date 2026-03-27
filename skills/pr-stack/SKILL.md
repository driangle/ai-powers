---
name: pr-stack
description: Split a large feature branch into multiple smaller PRs of max 20 files each. Use when the user wants to break up a big branch, split changes into stacked or parallel PRs, asks "how do I split this PR", mentions a branch has too many files, or wants a PR splitting strategy. Also triggers on phrases like "split this into PRs", "break up this branch", "chunk these changes", "PR plan", or "too many files in this PR".
allowed-tools: Bash, Read, Write, Glob
---

# PR Stack — Split a branch into multiple PRs

Analyze a feature branch and produce a plan to split it into multiple PRs, grouped by logical cohesion.

### PR size limits (hard caps)
- **Max 20 files** per PR
- **Max 400 lines changed** per PR

## Step 1: Gather context

Run in parallel:
- `git branch --show-current`
- `git remote show origin | grep 'HEAD branch'` (or use user-specified base)
- `git diff --name-only <base>`
- `git diff --stat <base>`

## Step 2: Group files into PRs

Group changed files into coherent PRs that are reviewable in isolation and respect dependency order. Keep tests with their source files. Put foundational changes (shared types, config) in earlier PRs. If grouping is ambiguous, read a sample of files to check imports and relationships.

If a PR changes an exported type/interface, include all consumer files that would break — never split types from their consumers.

## Step 3: Output the plan

Format:
```
# PR 1: <short descriptive title>
git checkout <source-branch> -- path/to/file1.ts
git checkout <source-branch> -- path/to/file2.ts

# PR 2: <title> (depends on PR 1)
git checkout <source-branch> -- path/to/file3.ts
```

Rules:
- Every changed file appears in exactly one PR
- Note dependencies between PRs
- Include file count and line count per PR
- End with a summary: total files, total lines, number of PRs

## Step 4: Save and execute

1. Save the plan to `~/.prs/<branch-name>.md` (replace `/` with `-`). Create `~/.prs/` if needed.

2. For each PR in order:
   - PR 1: branch from base. PR N: branch from PR N-1's branch.
   - `git checkout <source-branch> -- <files...>` then `git add <files...>` (stage by name, never `git add -A`)
   - Commit with the PR title
   - Run type-check/lint for affected projects. If it fails, restructure the plan to fix the issue before continuing.

3. Branch naming: `<source-branch>-pr-1`, `<source-branch>-pr-2`, etc.

4. After all branches are created, switch back to the source branch and list the PR branches.

5. Ask if the user wants to push and open PRs. For stacked PRs, set PR N's base to PR N-1's branch. Respect `PULL_REQUEST_TEMPLATE.md` if one exists.

## Edge cases

- **< 20 files**: Present the plan anyway but note splitting isn't necessary.
- **Orphan files** (config, .gitignore): Attach to PR 1.
- **Monorepo**: Group by package first, then by concern within each package.

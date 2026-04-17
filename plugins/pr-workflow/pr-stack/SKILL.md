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

# PR 2: <title>
git checkout <source-branch> -- path/to/file3.ts
```

Rules:
- Every changed file appears in exactly one PR
- Include file count and line count per PR
- Dependencies are expressed in the ASCII diagram below (not inline in titles)
- End with a summary: total files, total lines, number of PRs

### Status table

Include a **Status** section in the plan file with a markdown table tracking per-PR state. This table is the source of truth for progress and must be kept up-to-date as PRs move through the workflow.

Columns:
- **PR** — PR number (matches the plan above)
- **Status** — one of: `pending`, `branch created`, `pushed`, `draft opened`, `opened`, `merged`, `failed`
- **URL** — GitHub PR URL, or `—` if not yet opened
- **Branch** — branch name (always filled in up-front from the plan)
- **Commit** — short commit SHA on that branch, or `—`
- **typeCheck** — `✓` (passed), `✗` (failed), or `—` (not yet run)

Initial table (all PRs start as `pending`):
```
## Status

| PR  | Status  | URL | Branch                      | Commit | typeCheck |
| --- | ------- | --- | --------------------------- | ------ | --------- |
| 1   | pending | —   | `<source-branch>-pr-1`      | —      | —         |
| 2   | pending | —   | `<source-branch>-pr-2`      | —      | —         |
```

### ASCII diagram of the PR graph

After the plan, render an ASCII diagram of the DAG. A PR may have zero, one, or multiple parents. Place each PR **once**, under its **primary parent** (the branch it will be cut from). Annotate extra parents with `[also depends on PR X, PR Y]`. If any PR has multiple parents, add a **Dependencies** edge list below the tree; otherwise omit it.

**Stacked** (linear chain):
```
main
  └── PR 1: foundational types (4 files, 120 lines)
        └── PR 2: API layer (8 files, 240 lines)
              └── PR 3: UI wiring (12 files, 310 lines)
```

**Parallel** (independent off the same base):
```
main
  ├── PR 1: config cleanup (3 files, 40 lines)
  ├── PR 2: logging refactor (6 files, 180 lines)
  └── PR 3: docs update (2 files, 30 lines)
```

**Diamond** (multi-parent):
```
main
  └── PR 1: shared types (4 files, 120 lines)
        ├── PR 2: API layer (8 files, 240 lines)
        ├── PR 3: client SDK (6 files, 180 lines)
        └── PR 4: integration wiring (10 files, 300 lines) [also depends on PR 2, PR 3]

Dependencies:
  PR 1 → PR 2
  PR 1 → PR 3
  PR 1 → PR 4
  PR 2 → PR 4
  PR 3 → PR 4
```

## Step 4: Save the plan and confirm

1. Save the plan to `./.prs/<branch-name>.md` (repo-local; replace `/` with `-` in the branch name). Create `./.prs/` if needed. This file is the running state log — update it after every step below.

2. Present the plan to the user and **stop for confirmation before creating any branches**. Show the grouping, the ASCII diagram, and the total counts. Ask explicitly: "Proceed with creating these branches?" Do not run any `git checkout -b`, `git checkout -- <files>`, or `git commit` until the user confirms. If the user asks for adjustments, revise the plan, save, and ask again.

## Step 5: Create branches

Only run after the user confirms Step 4.

1. Process PRs in **topological order** (every PR comes after all its parents). For each PR:
   - **No parents**: branch from the base (e.g. `main`).
   - **One parent**: branch from that parent's branch.
   - **Multiple parents**: branch from the primary parent, then `git merge` each additional parent's branch into it before staging files. If a merge conflicts, stop and surface the conflict — do not auto-resolve.
   - `git checkout <source-branch> -- <files...>` then `git add <files...>` (stage by name, never `git add -A`)
   - Commit with the PR title
   - Run type-check/lint for affected projects. If it fails, restructure the plan to fix the issue before continuing.
   - **Update the Status table in `./.prs/<branch-name>.md`** after each state change for this PR: set Status (`branch created` → `pushed` → `draft opened`/`opened`), fill in Commit (short SHA), typeCheck (`✓`/`✗`), and URL once available. Save after each update — do not batch until the end.

2. Branch naming: `<source-branch>-pr-1`, `<source-branch>-pr-2`, etc. (numbering follows the topological order used above).

3. After all branches are created, switch back to the source branch and list the PR branches.

## Step 6: Confirm before opening PRs

After branches are created, **stop and ask the user to confirm before pushing or opening any PRs**. Summarize what will be pushed (branches + target bases), note that PRs will be opened as **drafts by default**, and ask explicitly: "Push these branches and open PRs as drafts?" Do not run `git push` or `gh pr create` until the user confirms. If the user explicitly asks for ready-for-review PRs, skip the `--draft` flag in Step 7.

## Step 7: Push and open PRs

Only run after the user confirms Step 6.

1. **Never force-push. Never push to the main/master branch.** Set each PR's GitHub base to its **primary parent's branch** (GitHub only supports a single base). For PRs with multiple parents, note the additional dependencies in the PR description so reviewers know the full merge order. Respect `PULL_REQUEST_TEMPLATE.md` if one exists. **Always open PRs as drafts by default** — pass `--draft` to `gh pr create` unless the user explicitly requested non-draft/ready-for-review PRs. As each PR is pushed and opened, update its row in the Status table (Status + URL) and save the file.

2. On failure (merge conflict, type-check failure, push rejected, etc.): set that PR's Status to `failed`, leave a short note in the file explaining what broke, save, and surface the failure to the user before moving on.

## Step 8: Updating an already-open PR

When the user applies further changes to a PR that's already been opened (e.g. review feedback, fixes), **do not commit or push, and do not ask to**. Leave the changes in the working tree — the user will decide when and how to commit and push. Only act on commit/push if the user explicitly requests it.

## Edge cases

- **< 20 files**: Present the plan anyway but note splitting isn't necessary.
- **Orphan files** (config, .gitignore): Attach to PR 1.
- **Monorepo**: Group by package first, then by concern within each package.

---
name: pr-stack
description: Split a large feature branch into multiple smaller PRs of max 20 files each. Use when the user wants to break up a big branch, split changes into stacked or parallel PRs, asks "how do I split this PR", mentions a branch has too many files, or wants a PR splitting strategy. Also triggers on phrases like "split this into PRs", "break up this branch", "chunk these changes", "PR plan", or "too many files in this PR".
---

# PR Stack — Split a branch into multiple PRs

Analyze a feature branch's changed files and produce a concrete plan to split them into multiple PRs, grouped by logical cohesion.

### PR size limits (hard caps)
- **Max 20 files** per PR
- **Max 200–400 lines changed** (total diff) per PR

Both limits must be respected. If a group exceeds either limit, split it further. Use `git diff --stat <base> -- <files...>` to measure diff size when planning.

## Step 1: Gather context

Run these in parallel:

- `git branch --show-current` to get the current (source) branch name
- `git remote show origin | grep 'HEAD branch'` to detect the default branch (main/master)
- `git diff --name-only <base_branch>` to get the full list of changed files
- `git diff --stat <base_branch>` to get per-file line counts (used to enforce the 200–400 line limit per PR)

If the user specified a base branch, use that instead of auto-detecting.

## Step 2: Analyze and group files

Look at the changed file list and group them into coherent PRs. The goal is to produce PRs that:

- **Are reviewable in isolation** — each PR should make sense on its own, not require reading 3 other PRs to understand
- **Respect dependency order** — if PR 2 depends on types defined in PR 1, that should be reflected in the ordering
- **Stay within size limits** — max 20 files and 200–400 lines changed per PR (hard caps)
- **Group by logical concern** — files that belong to the same feature, module, or layer go together

Grouping heuristics (in priority order):

1. **Shared directory** — files in the same directory or subtree are likely related
2. **Import/dependency chains** — types, interfaces, and utilities that other files depend on should land first
3. **Feature boundaries** — a complete vertical slice (types + logic + tests) is better than splitting types into one PR and tests into another
4. **Test proximity** — keep `foo.ts` and `foo.spec.ts` in the same PR

When deciding PR order, put foundational changes first (shared types, config, utilities) and higher-level consumers later.

## Step 3: Read files if grouping is ambiguous

If the file paths alone don't make the grouping obvious — e.g., files from different directories that might be related, or a flat list of files with no clear structure — read a sample of the files to understand their relationships. Look at imports, exported types, and function signatures to figure out what depends on what.

Don't read every file. Read enough to resolve ambiguity.

## Step 4: Output the plan

Use this exact format. The source branch is the current branch. Each PR gets a heading with a short descriptive title, followed by `git checkout` commands that would cherry-pick those files from the source branch:

```
# PR 1: <short descriptive title>
git checkout <source-branch> -- path/to/file1.ts
git checkout <source-branch> -- path/to/file2.ts
git checkout <source-branch> -- path/to/file2.spec.ts

# PR 2: <short descriptive title>
git checkout <source-branch> -- path/to/file3.ts
git checkout <source-branch> -- path/to/file4.ts
```

Rules for the output:

- Every changed file must appear in exactly one PR — no file left behind, no duplicates
- PR titles should be concise but descriptive enough to use as actual PR titles
- Add a blank line between PRs for readability
- If a PR has dependencies on a prior PR, note it briefly: `# PR 3: Auth middleware (depends on PR 1)`
- After each PR's file list, include the file count and total lines changed for that PR (from `git diff --stat`)
- After the plan, include a short summary: total file count, total lines changed, number of PRs, and any notes about dependency ordering
- If any PR exceeds 20 files or 400 lines changed, split it further before presenting the plan

## Step 5: Save the plan

Always save the plan to `~/.prs/<plan_name>.md` so it can be referenced later. Use the source branch name as the plan name (replacing `/` with `-`). For example, if the source branch is `feat/big-refactor`, save to `~/.prs/feat-big-refactor.md`.

Create the `~/.prs/` directory if it doesn't exist. The saved file should contain the full plan output from Step 4, including the summary.

Tell the user where the plan was saved.

## Step 6: Offer to execute the plan

After presenting and saving the plan, ask the user: "Want me to create these branches and check out the files for you?"

If the user says yes:

1. For each PR in the plan, starting from PR 1:
   - **PR 1**: branch off the base branch: `git checkout <base_branch> -b <source-branch>-pr-1`
   - **PR N (N > 1)**: branch off the previous PR branch: `git checkout <source-branch>-pr-<N-1> -b <source-branch>-pr-<N>`
   - Check out all the files listed for that PR from the source branch: `git checkout <source-branch> -- <file1> <file2> ...`
   - Stage **only the specific files**, not `git add -A` (which picks up untracked files from the working tree): `git add <file1> <file2> ...`
   - Commit: `git commit -m "<PR title>"`
   - **Verify the branch before moving on**: Run the relevant compilation/check commands for every project affected by the changed files in this PR. Detect affected projects from the file paths (e.g. in an NX monorepo, identify the NX project(s) that own the changed files and run `typeCheck`/`lint`/`test` targets for them). If verification fails, **stop and fix the issue** — typically by restructuring the plan to move consumer files into the same PR as the changes that break them (see "Type-safe splits" in Handling edge cases). Do NOT proceed to the next PR until the current one passes.
   - Report progress (including verification result) after each branch is created

2. After all branches are created, switch back to the original source branch and list them: `git checkout <source-branch> && git branch --list '<source-branch>-pr-*'`

3. Ask the user if they want to push the branches and open PRs. When opening stacked PRs, set the base branch for PR N to the PR N-1 branch (e.g., `gh pr create --base <source-branch>-pr-1` for PR 2). Before creating PRs, check for a `PULL_REQUEST_TEMPLATE.md` in the repo (typically at `.github/PULL_REQUEST_TEMPLATE.md`). If one exists, read it and use its structure for the PR body — fill in each section from the template with content relevant to the PR's changes. If no template exists, use the default format from the pr-open skill or a sensible default.

Branch naming convention: `<source-branch>-pr-1`, `<source-branch>-pr-2`, etc. If the source branch is `feat/big-refactor`, the split branches would be `feat/big-refactor-pr-1`, `feat/big-refactor-pr-2`, etc.

### Why chaining and explicit staging matter

**Chaining branches**: Stacked PRs are meant to be reviewed and merged in order. PR 2 depends on PR 1's changes. If PR 2 is branched from the base branch (e.g., master) instead of PR 1, it won't have PR 1's files and may not compile or pass tests in isolation. Chaining ensures each PR builds on the previous one and is independently valid.

**Explicit file staging**: `git add -A` stages everything in the working tree that differs from HEAD — including untracked files, build artifacts, and test output that happen to exist locally. This can balloon a commit from 18 intended files to hundreds. Always stage files by name (`git add <file1> <file2> ...`) to commit exactly what the plan specifies.

## Handling edge cases

- **Fewer than 20 files total**: Still output the plan in the same format, but it'll just be one PR. Mention that splitting isn't strictly necessary but present the grouped format anyway.
- **Files that don't clearly belong anywhere**: Group them into the PR where they're most likely consumed. If truly standalone (like a .gitignore or config change), attach them to the first PR.
- **Monorepo with multiple packages**: Group by package first, then by concern within each package.
- **Type-safe splits**: Each PR must independently pass `typeCheck` against the codebase at its base. If a PR changes a type (adds a required field, renames a property, changes a signature), every file on the base branch that consumes that type will break — those consumer files **must** be in the same PR as the type change. Splitting types into one PR and their consumers into another guarantees compile failures. When in doubt, check the import graph: if file A changes an exported interface and files B, C, D import it, all of A/B/C/D belong together. If this creates a group that exceeds the size limits, split the group further along internal boundaries (e.g. separate the type change + its direct consumers from unrelated files that were lumped in). Never exceed the limits — find a finer split instead.

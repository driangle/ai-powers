---
name: pr-review
description: Review a GitHub PR and present findings as author-addressed comments. Use when the user asks to review a PR, gives a PR URL or number, or asks for code review feedback on a pull request. Also re-reviews a PR the user already commented on, checking which comments were addressed. Reviews dependency-upgrade PRs (Dependabot, Renovate, Snyk, security bumps) by diffing the released library code between the two versions, bounding transitive upgrades by depth, and checking the changes against how the app uses the library. Triggers on phrases like "review this PR", "look at this pull request", "code review", "the author addressed my feedback", "look at the PR again", "re-review", "is this dependency bump safe", "will this upgrade break anything", or any GitHub PR link.
allowed-tools: Bash, Read, Glob, Grep, Agent
---

## Input

Accepts a PR URL (e.g. `https://github.com/org/repo/pull/123`) or a PR number (for the current repo), or several of them.

## Mode

Check whether the user has already reviewed this PR: `gh api repos/{owner}/{repo}/pulls/{number}/reviews --jq "[.[] | select(.user.login == \"$(gh api user --jq .login)\")] | length"`.

- **0** — first review: follow the steps below.
- **More than 0** — follow-up review: follow `references/follow-up.md` instead of steps 2–7, then apply step 8 and the Output rules it points to. Do a first review anyway if the user asks for a full or fresh review.

A first review of a **dependency upgrade** follows steps D1–D7 of `references/dependency-upgrade.md` instead of steps 1–5. Then it applies steps 6–8, and the Output rules in that file. A PR is one when its purpose is to move packages to new versions: it comes from Dependabot, Renovate or Snyk, or its title says it updates or bumps a dependency, and its diff is mostly manifests and lockfiles. Hand-written code changes in the same PR also get steps 4–5.

## Workspace

Every review, first or follow-up, reads the code from a standalone worktree checked out at the PR's latest head, so it sees the full files around each hunk and never touches the user's own checkout. One worktree per PR.

1. **Find a clone.** Use the current repo if its `origin` is the PR's repo (`gh repo view --json nameWithOwner`), or a clone the user points to. With neither, clone it: `gh repo clone <owner>/<repo> ~/.worktrees/<repo>/pr-<number> -- --filter=blob:none`. That clone is the workspace, so skip step 3's `worktree add` and check out the head there with `git checkout --detach`.
2. **Fetch the latest.** Get the PR's `headRefOid` and `baseRefName` from `gh pr view <pr> --json headRefOid,baseRefName`, then fetch both from the base repo, which also carries the head of a PR from a fork:
   `git -C <clone> fetch origin <baseRefName> "+refs/pull/<number>/head:refs/remotes/origin/pr/<number>"`
   If `origin/pr/<number>` is not `headRefOid`, the PR moved while fetching: fetch again.
3. **Check out the head.** Reuse the PR's worktree if `git -C <clone> worktree list` already has it, and move it with `git -C <worktree> checkout --detach <headRefOid>`. Otherwise add one outside any repository:
   `git -C <clone> worktree add --detach ~/.worktrees/<repo>/pr-<number> <headRefOid>`
   A detached head never collides with a branch the user has checked out elsewhere.
4. **Work only in the worktree.** Read, grep and run tests or linters there, with `git -C <worktree>` and absolute paths. Never check out, stash, reset or pull in the user's checkout. The PR's diff is `git -C <worktree> diff origin/<baseRefName>...HEAD`.
5. **Keep it** for the rest of the conversation: a re-review or a question about a finding reuses it. Name its path at the end of the output, and remove it with `git -C <clone> worktree remove <worktree>` when the user is done with the PR.

## Steps

1. Fetch in parallel:
   - `gh pr view <pr> --json title,body,files,additions,deletions,baseRefName,headRefName`
   - `gh pr diff <pr>`
   - Read the repo's CLAUDE.md in the worktree, if it has one (factor its conventions into the review)
   - Only if the user explicitly asks: `gh api repos/{owner}/{repo}/pulls/{number}/comments`

2. Read the full diff carefully. For large diffs, read persisted output files fully. Open the changed files in the worktree to read each hunk in context, and follow callers and tests the diff does not show.

3. Write a clear explanation of the PR:
   - What problem does this PR solve and why?
   - What approach was taken — summarize the key changes across files
   - Call out any notable design decisions or trade-offs

4. Question the approach before the lines: does the change fix the cause or patch a symptom, is it at the right layer, and is there a sturdier alternative (watch for heuristics such as regexes or keyword lists over open-ended input like speech, free text or model output)? When several findings share one cause, report the cause as its own finding, above them.

5. Review for: bugs, missing error handling, security issues, performance problems, naming/readability, convention violations, lock file anomalies, unsafe casts/patterns.

6. Classify each finding on two axes:
   - **Severity**: **High**, **Medium**, **Low**, or **Nit**.
   - **Blocker**: whether the PR should not merge until it is fixed (bugs, security issues, data loss, broken contracts, violations of explicit repo rules). A Nit is never a blocker.

7. Assign each finding a stable id: `F1`, `F2`, … numbered in output order. The user refers to findings by these ids later (e.g. "fix F2", "post F1 and F3"), so reuse the same ids when the conversation returns to this review.

8. Decide the verdict. It follows from the blockers, so the two never disagree:
   - **✅ Approve** — no blockers. Non-blocking findings can be addressed in this PR or a follow-up.
   - **❌ Request changes** — one or more blockers.

## Output

Print the review directly — do NOT post comments to the PR unless the user explicitly asks. When they do, follow `references/posting.md`; it applies to a follow-up review's findings too.

Format: H2 title with PR name, then the verdict line, then a **"What this PR does"** section explaining the changes (from step 3), followed by a **"Findings"** section, then a **"Positives"** section noting what was done well.

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

The verdict line sits directly under the title so the decision is the first thing read. It names the blockers behind a Request changes:

```
**Verdict: ❌ Request changes** — blocked by F1, F3
**Verdict: ✅ Approve**
```

# Briefs

Fill the placeholders: `{pr_url}`, `{worktree}` (absolute path), `{head_sha}`, `{base}` (the base branch), `{mode}` (first review, follow-up, or dependency upgrade).

## Reviewer brief

Send the same text to every reviewer.

```
Review the pull request {pr_url} with the pr-review skill (/pr-workflow:pr-review, or /pr-review if that is how it is installed). This is a {mode}.

The PR's head ({head_sha}) is already checked out in a worktree at {worktree}. Use it as the skill's workspace: skip the skill's Workspace steps that find a clone, fetch and check out, and do not move, reset or remove the worktree. Read files there, and run git as `git -C {worktree} ...`. The PR's diff is `git -C {worktree} diff origin/{base}...HEAD`.

You are running unattended: nobody will answer questions. Where you would ask, decide, and state the assumption.

Do not post anything to GitHub, comment, write files or change the worktree. Return your review as your reply, in this shape:

## What this PR does
<the skill's explanation>

## Findings
One block per finding:
- id: F1
- severity: High | Medium | Low | Nit
- blocker: yes | no
- location: path:line (or "none")
- problem: <one or two sentences>
- reasoning: <the mechanism in the code, naming the identifiers involved>
- suggestion: <what to change>
For a follow-up review, also one block per previous comment, with its status (Addressed, Partly addressed, Not addressed, Pushed back) and the reason.
Write "none" if there are no findings.

## Positives
<what was done well>

## Access problems
Each time you could not fetch data you wanted: the tool or command, the error, and what you were trying to learn. Or "none".
```

## Arbiter brief

Start a fresh agent, not one of the reviewers. List the disputed findings as D1, D2, … Give each side of a dispute as a neutral "Position A / Position B", never as a reviewer's name, so the arbiter weighs the arguments and not who made them.

```
You are settling disagreements between independent reviewers of the pull request {pr_url}. Its head ({head_sha}) is checked out at {worktree}: read the code there, and run git as `git -C {worktree} ...`. Do not post, comment, write files or change the worktree.

For each disputed finding below, read the code it points at and decide:
- keep, with a severity (High, Medium, Low or Nit) and whether it blocks the merge (bugs, security issues, data loss, broken contracts, violations of explicit repo rules; a Nit never blocks), or
- drop, because it does not hold.
For a follow-up comment, decide its status instead (Addressed, Partly addressed, Not addressed, Pushed back).

Reply with one line per dispute: `D1: keep · High · blocker — <reason>`, `D2: drop — <reason>`. Then an "Access problems" line, or "Access problems: none".

<D1: the finding, then Position A and Position B with their reasoning>
<D2: …>
```

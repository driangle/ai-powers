---
name: pr-review-panel
description: Review a GitHub PR with a panel of independent reviewers running concurrently, each one a subagent running the pr-review skill, then merge their findings into one review in pr-review's format, with each finding's agreement count, disputed findings settled by a fresh arbiter agent, and a record of disagreements. Use when the user wants a more thorough or more reliable review than a single pass, asks for several reviewers, a second opinion, a panel, ensemble or consensus review, or asks to "review this PR with N agents". For a single ordinary review, use pr-review instead.
allowed-tools: Bash, Read, Glob, Grep, Agent, Skill
---

# PR review panel

Several reviewers review the same PR independently and at the same time; you merge their results. You do not review the PR yourself: you prepare the workspace, brief the reviewers, merge, and settle disputes through an arbiter. The result reads like one pr-review review.

The pr-review skill is `../pr-review/SKILL.md` (invoked as `/pr-workflow:pr-review`, or `/pr-review` where it is installed on its own). Its rules for severity, blockers, ids, verdict and output apply here unless this file says otherwise; they are not repeated.

## Input

A PR URL or number, as pr-review takes. Optionally a panel size: **3 reviewers** by default, at most 5. Several PRs get one panel each, one after the other.

## 1. Prepare

1. Set up the worktree once, as pr-review's **Workspace** section describes, and note its path and the head SHA. The reviewers share it; preparing it here keeps them from racing to create it.
2. Decide the mode once, with pr-review's **Mode** check: first review or follow-up, and whether it is a dependency upgrade. Every reviewer gets the same mode.

## 2. Run the panel

Start every reviewer in **one message**, each with the Agent tool in the background, so they run concurrently. Brief each one with the reviewer brief in `references/briefs.md`. The briefs are identical: never pass one reviewer's output to another, so their reviews stay independent. Wait for all of them.

A reviewer that fails or returns no findings list is out of the panel: note it, and go on with the rest. With fewer than 2 reviewers left, say so and present the single review as it is, without merging.

## 3. Merge

Reviewers are named **R1…Rn** in the order they were started. Work from their findings lists, not their prose.

1. **Group** findings that describe the same problem: the same cause in the code, even if they point at different lines or word it differently. Two different problems on the same line stay apart. A finding about a root cause and the symptoms it explains (pr-review step 4) group together under the cause.
2. **Count** each group's support: how many reviewers raised it (`2/3`).
3. **Settle each group**, and record every decision that is not a plain keep:
   - **Raised by a majority, same severity and blocker status** → keep it.
   - **Raised by a minority** (one reviewer of three, for example) → check it against the code in the worktree. Keep it if it holds. If you doubt it, it is disputed, and your reason for doubting it is the other side.
   - **Same problem, different severity or blocker status** → disputed.
   - **Findings that contradict each other** (one asks for what another objects to) → disputed.
   - In a follow-up review, a previous comment the reviewers give different statuses (Addressed, Partly addressed, Not addressed, Pushed back) → disputed.
4. **Arbitrate** the disputed findings, all of them in one fresh agent, with the arbiter brief in `references/briefs.md`. It sees each finding with every side's reasoning, not which reviewer wrote what. Follow its decisions: keep (with the severity and blocker status it gives), or drop. Never drop a finding yourself without the arbiter.
5. **Write each kept finding once**: the clearest wording among the reviewers, the most concrete location, and a suggestion that combines theirs when they complement each other. Keep the severity the reviewers agreed on, or the arbiter's.
6. **Renumber** the kept findings `F1`, `F2`, … in pr-review's output order. In a follow-up, previous comments keep their pr-review ids.
7. **Verdict** from the kept blockers, as pr-review step 8 decides it.

**What this PR does** is one explanation built from the reviewers' explanations, checked against the diff where they differ. **Positives** is the union of theirs, without repeats.

## 4. Output

Print the review in pr-review's Output format (or its follow-up format), with two additions:

- Every finding's header carries its support after the severity: `**F1 · 🚫 Blocker · High · 3/3** — \`src/auth.ts:42\``. A finding the arbiter kept says so: `· 1/3, arbitrated`.
- A **Panel** section after Positives:
  - the reviewers that ran and any that failed, with the error;
  - **Disagreements**: each disputed finding, what each side said, and the arbiter's decision and reason; or `Disagreements: none`;
  - **Dropped**: each finding left out and why (the arbiter dropped it, or it was folded into another finding);
  - **Access problems**: each time a reviewer or the arbiter could not fetch data it wanted, with the tool or command, the error, and what the user can do to unblock it; or `Access problems: none`.

Name the worktree's path at the end, as pr-review does.

Do not post unless the user asks. When they do, follow pr-review's `references/posting.md` with the merged findings. The support counts and the Panel section are for the user and stay out of what is posted.

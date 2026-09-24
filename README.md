# ai-powers

A collection of Claude Code skills for PR workflows and git automation.

## Install

From inside Claude Code interactive mode:

```
# Add the marketplace
/plugin marketplace add driangle/ai-powers

# Install a plugin
/plugin install <plugin_name>@driangle-ai-powers
```

Available plugins: `pr-workflow`, `codebase-analysis`, `codebase-ops`, `release`, `planning`, `execution`, `retrospective`

## Skills

### pr-workflow

- **commit** - Stage and commit all uncommitted changes with an auto-generated conventional commit message
- **commit-msg** - Generate conventional commit messages from staged changes
- **pr-open** - Open GitHub PRs with auto-generated titles and descriptions
- **pr-description** - Generate concise PR descriptions from diffs
- **pr-review** - Review GitHub PRs and present author-addressed findings, each with an id, blockers clearly marked, an approve or request-changes verdict, and a follow-up mode that checks which of your comments were addressed
- **pr-review-report** - Generate a Slack-friendly triage report of open PRs for a team, author, or set of repos (script-backed, deterministic)
- **pr-triage** - Pure-prompt variant of pr-review-report: same Slack-ready triage output driven by `gh` calls and prompt-embedded bucketing rules, no helper script
- **pr-stack** - Split large feature branches into smaller, stacked PRs
- **rebase-merge** - Rebase the current branch onto a target branch, resolve conflicts, validate with the project's conventional checks, then fast-forward merge (aborts if fast-forward isn't possible); always finishes back on the original branch
- **sync-worktrees** - Synchronize worktrees with main: rebase each worktree branch onto main, validate it with the project's conventional checks, fast-forward merge it into main, then fast-forward all branches back up to the final main; each worktree ends on the branch it started on

### codebase-analysis

- **api-review** - Review a library's public API for clarity, consistency, composability, predictability, edge-case handling, and correctness
- **audit** - Perform a comprehensive codebase audit covering security, privacy, data integrity, architecture, and code quality
- **audit-docs** - Audit documentation coverage: discover CLI commands, APIs, config options, and features, then cross-reference against docs to find gaps and stale content
- **dead-code** - Find dead code: unused exports, orphaned files, unreachable code paths, unused dependencies, and stale artifacts
- **oddities** - Scan a scope of code (directory, module, branch diff) for unconventional, strange, questionable, or opaque things — latent bugs, unexpected complexity, inconsistencies, odd design, and library/API workarounds; produces a prioritized reading list, not a refactor plan
- **refactor-plan** - Produce a ranked refactoring plan for the code you just worked with, each suggestion tagged with priority and effort and sorted most- to least-recommended; grounded in files touched during the session, meant to run right after a task
- **test-audit** - Audit test suites for legitimacy: detect tautologies, over-mocking, trivially-passing assertions, and misleading coverage

### codebase-ops

- **refactor** - Structured refactoring: extract module, split file, inline, rename, simplify, decouple, reorganize
- **migrate** - Perform codebase migrations: upgrade dependencies, swap libraries, adopt new APIs or patterns
- **triage-dependabot** - Triage Dependabot alerts: group by package, find high-payoff upgrades and removal candidates, then plan a fix
- **setup-targets** - Bootstrap a project's checks: standardized build targets (compile, lint, format-check, test, build) per project, enforced lint standards (max 200 lines/file, max 50 lines/function, layered imports), top-level check/check-lite, pre-commit hook running check-lite, and CI running check

### release

- **release** - Create versioned releases with automated version bumps, tagging, release notes, and GitHub release publishing

### planning

- **spec-decompose** - Decompose specs, requirements, or design docs into actionable task files

### execution

- **fix-feedback** - Address bug reports or feature feedback with a test-first workflow: reproduce with a failing test, then fix
- **work** - Pick up the next task, execute it, verify it, reconcile the backlog, mark it complete, and commit; isolates the work in a per-task git worktree (`.claude/worktrees/<id>` on `task/<id>`) when the task has an id or is substantial, initializes it with the project's dependency install and any gitignored config it needs, then rebases, validates, fast-forward merges it into `main` and removes the worktree — unless the user asks not to merge

### retrospective

- **reflect** - End-of-session retrospective driven by the real session transcript, not memory: locates the transcript (via `vibeview` if installed, otherwise from `~/.claude/projects/`), mines it for failed tool calls, retry loops, file churn, slow calls and the steering log of user corrections, classifies each finding by kind with its cost and counterfactual, reports for approval, then files the durable lessons as a dated reflection note plus tasks or `CLAUDE.md` rules

## Agents

### planning

- **backlog-reconciler** - Reconciles the task backlog with what actually happened during a task — postponed, shifted, missing and follow-up work. Spawned by `work` before a task is completed; decides each loose end's disposition on a cheapest-first ladder (already covered → fix now → drop → amend an existing task → file a new one), retires tasks the finished work made obsolete, and reports back the ids it touched with a net-change line. It holds the bar on backlog growth rather than filing everything it is handed.

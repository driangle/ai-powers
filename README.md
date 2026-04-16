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

Available plugins: `pr-workflow`, `codebase-analysis`, `codebase-ops`, `release`, `planning`, `execution`

## Skills

- **api-review** - Review a library's public API for clarity, consistency, composability, predictability, edge-case handling, and correctness
- **audit** - Perform a comprehensive codebase audit covering security, privacy, data integrity, architecture, and code quality
- **audit-docs** - Audit documentation coverage: discover CLI commands, APIs, config options, and features, then cross-reference against docs to find gaps and stale content
- **dead-code** - Find dead code: unused exports, orphaned files, unreachable code paths, unused dependencies, and stale artifacts
- **oddities** - Scan a scope of code (directory, module, branch diff) for unconventional, strange, questionable, or opaque things — latent bugs, unexpected complexity, inconsistencies, odd design, and library/API workarounds; produces a prioritized reading list, not a refactor plan
- **test-audit** - Audit test suites for legitimacy: detect tautologies, over-mocking, trivially-passing assertions, and misleading coverage
- **triage-dependabot** - Triage Dependabot alerts: group by package, find high-payoff upgrades and removal candidates, then plan a fix
- **migrate** - Perform codebase migrations: upgrade dependencies, swap libraries, adopt new APIs or patterns
- **refactor** - Structured refactoring: extract module, split file, inline, rename, simplify, decouple, reorganize
- **fix-feedback** - Address bug reports or feature feedback with a test-first workflow: reproduce with a failing test, then fix
- **commit** - Stage and commit all uncommitted changes with an auto-generated conventional commit message
- **commit-msg** - Generate conventional commit messages from staged changes
- **pr-description** - Generate concise PR descriptions from diffs
- **pr-open** - Open GitHub PRs with auto-generated titles and descriptions
- **pr-review** - Review GitHub PRs and post author-addressed comments
- **pr-review-report** - Generate a Slack-friendly triage report of open PRs for a team, author, or set of repos
- **pr-stack** - Split large feature branches into smaller, stacked PRs
- **setup-targets** - Set up standardized build targets (compile, lint, test, build) per project, top-level check/check-lite, pre-commit hook, and CI workflow
- **release** - Create versioned releases with automated version bumps, tagging, release notes, and GitHub release publishing
- **spec-decompose** - Decompose specs, requirements, or design docs into actionable task files
- **work** - Pick up the next task, execute it, verify it, mark it complete, and commit

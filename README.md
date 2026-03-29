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

Available plugins: `pr-workflow`, `codebase-analysis`, `codebase-ops`, `release`, `planning`

## Skills

- **audit** - Perform a comprehensive codebase audit covering security, privacy, data integrity, architecture, and code quality
- **dead-code** - Find dead code: unused exports, orphaned files, unreachable code paths, unused dependencies, and stale artifacts
- **triage-dependabot** - Triage Dependabot security alerts: prioritize by severity, pick one to fix, and plan the remediation
- **migrate** - Perform codebase migrations: upgrade dependencies, swap libraries, adopt new APIs or patterns
- **refactor** - Structured refactoring: extract module, split file, inline, rename, simplify, decouple, reorganize
- **commit-msg** - Generate conventional commit messages from staged changes
- **pr-description** - Generate concise PR descriptions from diffs
- **pr-open** - Open GitHub PRs with auto-generated titles and descriptions
- **pr-review** - Review GitHub PRs and post author-addressed comments
- **pr-stack** - Split large feature branches into smaller, stacked PRs
- **setup-targets** - Set up standardized build targets (compile, lint, test, build) per project, top-level check/check-lite, pre-commit hook, and CI workflow
- **release** - Create versioned releases with automated version bumps, tagging, release notes, and GitHub release publishing
- **spec-decompose** - Decompose specs, requirements, or design docs into actionable task files

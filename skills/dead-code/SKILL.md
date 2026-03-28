---
name: dead-code
description: "Find dead code in the codebase: unused exports, orphaned files, unreachable code paths, unused dependencies, and stale feature flags. Use when the user wants to clean up unused code or identify candidates for removal."
---

# Dead Code

Find unused and unreachable code across the codebase using search-based heuristics. Works with any language.

## Instructions

Scan the codebase for dead code. If `$ARGUMENTS` specifies a scope (e.g., a directory, a specific check like "unused dependencies"), narrow your analysis to that. Otherwise, run all checks.

### Approach

Since this must work across languages without dedicated static analysis tools, use a **search-based heuristic approach**: identify candidates by name/pattern, then verify by searching for references. This means results are _candidates_ — flag confidence level for each finding.

### Step 1: Understand the codebase

Before launching agents, quickly determine:
- Primary language(s) and framework(s) (check file extensions, package manifests)
- Entry points (main files, index files, route definitions, CLI entry points)
- Package manifests (package.json, Cargo.toml, go.mod, pyproject.toml, requirements.txt, Gemfile, etc.)
- Build/bundler config that might re-export or alias modules

This context is needed to avoid false positives (e.g., entry points won't be imported by anything).

### Step 2: Launch parallel analysis agents

Use the **Agent tool** to launch subagents concurrently.

#### Wave 1 — Launch these 3 agents in parallel:

**Agent 1: Orphaned Files** (subagent_type: Explore, thoroughness: very thorough)
```
Find files in this codebase that are never imported, required, or referenced by any other file.

Approach:
1. List all source files (exclude tests, config files, generated files, and known entry points)
2. For each file, search the rest of the codebase for imports/requires that reference it
   - Match by filename (with and without extension)
   - Match by directory index patterns (e.g., importing a directory resolves to index.*)
   - Account for path aliases if a bundler/tsconfig/etc. defines them
3. Entry points (main files, CLI bins, route handlers, config files, test files) are NOT orphaned even if nothing imports them — exclude them
4. Build artifacts and generated files are not orphaned — exclude them

Report each candidate with:
- File path
- Confidence: high (no references found at all) / medium (only referenced in comments or strings)
- Approximate line count (to help prioritize cleanup)

Sort by confidence desc, then by line count desc.
```

**Agent 2: Unused Exports & Symbols** (subagent_type: Explore, thoroughness: very thorough)
```
Find exported functions, classes, types, constants, and variables that are never used outside their defining file.

Approach:
1. Identify exported symbols by searching for export patterns:
   - JS/TS: `export function`, `export const`, `export class`, `export type`, `export interface`, `export default`, `export { ... }`, `module.exports`
   - Python: symbols in `__all__`, or public functions/classes (no leading `_`) in modules that are imported elsewhere
   - Go: capitalized identifiers (public exports)
   - Rust: `pub fn`, `pub struct`, `pub enum`, `pub type`, `pub const`
   - Other languages: adapt to the language's export conventions
2. For each exported symbol, search the rest of the codebase (excluding the defining file) for references to that symbol name
3. Exclude symbols that are part of a public API or framework contract (e.g., lifecycle hooks, route handlers, serialization methods)
4. Exclude re-exports from barrel/index files — but DO check if the re-exported symbol is ultimately used

Report each candidate with:
- Symbol name, file:line
- Confidence: high (zero references outside file) / medium (only referenced in barrel re-exports that themselves appear unused)
- Symbol type (function, class, type, constant)

Sort by confidence desc, grouping by file.
```

**Agent 3: Unused Dependencies** (subagent_type: Explore, thoroughness: medium)
```
Find dependencies declared in package manifests that are never imported or used in source code.

Approach:
1. Read all package manifests (package.json, Cargo.toml, go.mod, pyproject.toml, requirements.txt, Gemfile, build.gradle, pom.xml, etc.)
2. For each declared dependency:
   - Search source files for imports/requires of that package name
   - Check for usage in config files (bundler plugins, babel plugins, eslint configs, etc.)
   - Check for CLI usage in scripts (package.json scripts, Makefiles, CI configs)
   - Check for peer dependency or transitive usage patterns
3. Distinguish between runtime and dev dependencies — dev deps may only be used in config/build files

Report each candidate with:
- Package name, manifest file
- Confidence: high (no references anywhere) / medium (only in lockfile or transitive)
- Whether it's a runtime or dev dependency

Sort by confidence desc.
```

#### Wave 2 — Launch these 2 agents in parallel:

**Agent 4: Unreachable Code Paths** (subagent_type: Explore, thoroughness: medium)
```
Find code that exists but can never execute.

Look for:
- Code after unconditional return/throw/break/continue/exit statements
- Functions/methods defined but never called (internal, non-exported)
- Commented-out code blocks (large blocks, not single-line explanatory comments)
- Dead branches: conditions that are always true/false based on constants or type narrowing
- Unused local variables and parameters (only flag if clearly unused, not framework-required)
- Switch/match cases that duplicate other cases or handle impossible values
- Try/catch blocks catching exceptions that can't be thrown
- Feature flags or environment checks for values that no longer exist

Be conservative — only flag patterns that are clearly unreachable, not merely unlikely.

Report each candidate with:
- File:line, description
- Confidence: high / medium
- Type of dead code (unreachable statement, dead function, commented-out code, dead branch)

Sort by confidence desc, grouping by file.
```

**Agent 5: Stale Artifacts** (subagent_type: Explore, thoroughness: medium)
```
Find stale configuration, references, and artifacts that point to things that no longer exist.

Look for:
- Config entries (env vars, feature flags, settings) referenced in config but never read in source
- Route definitions pointing to handlers that don't exist
- Stale entries in barrel/index files re-exporting modules that no longer exist
- Scripts in package.json referencing files that don't exist
- CI/CD steps referencing scripts or commands that don't exist
- Dead imports: import statements that import a symbol that is never used in that file
- Stale type definitions or interfaces that nothing implements or references

Report each candidate with:
- Location (file:line), description
- Confidence: high / medium
- Type of staleness

Sort by confidence desc.
```

### Step 3: Compile the report

After all agents complete, compile findings into a single report:

```markdown
# Dead Code Report

## Summary
- Total candidates: N
- High confidence: N | Medium confidence: N
- Estimated removable lines: ~N

## 1. Orphaned Files
[Agent 1 findings]

## 2. Unused Exports
[Agent 2 findings, grouped by file]

## 3. Unused Dependencies
[Agent 3 findings]

## 4. Unreachable Code
[Agent 4 findings, grouped by file]

## 5. Stale Artifacts
[Agent 5 findings]

## Recommended Cleanup Order
[Prioritized list: start with high-confidence, high-impact items — orphaned files and unused dependencies first since they're safest to remove, then unused exports, then unreachable code]
```

### Step 4: Present findings

- Present the compiled report to the user
- Lead with high-confidence findings — these are safest to act on
- Clearly distinguish high vs medium confidence so the user knows what needs manual verification
- Offer to create tasks or directly remove high-confidence dead code if the user wants

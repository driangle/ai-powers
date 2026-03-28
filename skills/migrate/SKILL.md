---
name: migrate
description: "Perform codebase migrations: upgrade dependencies, swap libraries, adopt new APIs or patterns, and modernize legacy code. Use when the user wants to migrate, upgrade, swap a library, adopt a new pattern, or modernize code."
---

# Migrate

Perform systematic codebase migrations — upgrading dependencies, swapping libraries, adopting new APIs, or modernizing patterns.

## Instructions

Perform the migration described in `$ARGUMENTS`. The argument should indicate what to migrate (e.g., "upgrade React from 17 to 18", "swap moment.js with date-fns", "adopt the new config API").

### Step 1: Understand the migration scope

1. **Identify the migration type:**
   - **upgrade** — Bump a dependency to a new major/minor version and update breaking changes
   - **swap** — Replace one library/tool with another that serves the same purpose
   - **adopt** — Move from an old pattern/API to a new one across the codebase
   - **modernize** — Update legacy code to use current language features or idioms

2. **Research the migration:**

   Use the **Agent tool** to launch 2 research agents in parallel:

   **Agent 1: Current usage scan** (subagent_type: Explore, thoroughness: very thorough)
   ```
   Find every usage of [the library/pattern/API being migrated away from] in this codebase.

   Search for:
   - Import/require statements
   - Direct API calls and method usage
   - Type references and interface implementations
   - Configuration entries (build config, lint config, etc.)
   - Usage in tests and test fixtures
   - References in documentation, comments, and scripts
   - Transitive usage through wrapper modules

   For each usage, report: file:line, the specific API/pattern used, and surrounding context.
   Group by file, sort by frequency of usage.
   Report total count of usages and number of files affected.
   ```

   **Agent 2: Migration guide research** (subagent_type: general-purpose)
   ```
   Research the migration from [source] to [target].

   Find:
   - Official migration guide or changelog (search the web)
   - Breaking changes between versions (if an upgrade)
   - API mapping: old API → new API equivalents
   - Known gotchas, edge cases, or compatibility issues
   - Codemods or automated migration tools available
   - Required peer dependency changes

   Summarize as a concise mapping table: old pattern → new pattern.
   Flag any changes that require manual judgment (not a 1:1 swap).
   ```

### Step 2: Create the migration plan

Present the plan to the user:

```markdown
## Migration Plan

**Type:** [upgrade | swap | adopt | modernize]
**From:** [current library/version/pattern]
**To:** [target library/version/pattern]

### Scope
- **Files affected:** N
- **Total usages:** N
- **Automated:** N (1:1 mappings that can be mechanically replaced)
- **Manual review:** N (changes requiring judgment)

### API Mapping
| Old | New | Notes |
|-----|-----|-------|
| ... | ... | ...   |

### Migration steps
1. [Ordered list of steps]

### Risks
- [Breaking changes, behavioral differences, or edge cases]
```

Wait for user confirmation before proceeding.

### Step 3: Execute the migration

Apply changes in a safe order:

1. **Update dependencies first** — bump versions in package manifests, update lockfile
2. **Apply mechanical replacements** — 1:1 API swaps that don't require judgment, working file by file
3. **Handle complex migrations** — changes that require understanding context or choosing between alternatives
4. **Update types** — adjust type imports, interfaces, and generics to match the new API
5. **Update configuration** — build config, lint rules, babel/bundler plugins
6. **Update tests** — adapt test code, update mocks/stubs, fix broken assertions
7. **Clean up** — remove old library imports, delete compatibility shims, remove unused polyfills

#### Guidelines

- **Work file by file** — complete all changes in one file before moving to the next
- **Preserve behavior** — the migration should not change what the code does, only how it does it
- **Don't mix refactoring with migration** — resist the urge to "improve" code while migrating; that makes it harder to verify the migration is correct
- **Flag ambiguous cases** — when the old and new APIs aren't equivalent, flag it for the user rather than guessing
- **Keep the old dependency until done** — don't remove the old library from the manifest until all usages are migrated

### Step 4: Verify

After applying changes:

1. Search for any remaining references to the old library/API/pattern
2. Check that no old imports or require statements remain
3. If a codemod was available, compare its output against manual changes for consistency
4. List all files modified for the user to review
5. Suggest running tests and the build to verify nothing is broken
6. If any usages couldn't be migrated automatically, list them with explanations

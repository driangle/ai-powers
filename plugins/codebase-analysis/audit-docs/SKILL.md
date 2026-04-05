---
name: audit-docs
description: "Audit documentation coverage for a project: discover CLI commands, public APIs, configuration options, and features, then cross-reference against documentation to find gaps, stale content, and missing sections. Use when the user wants to check if docs are up to date, find undocumented features, or verify doc completeness."
---

# Audit Documentation

Discover all documented surfaces of the project (CLI commands, public APIs, configuration, features), then cross-reference against the actual documentation to identify gaps, outdated content, and missing sections.

## Instructions

Arguments in `$ARGUMENTS` are optional flags:

- `--fix` — after reporting gaps, update the documentation files to fill them
- `--scope <area>` — limit the audit to a specific area (e.g., `cli`, `api`, `config`, `features`)
- `--verbose` — include per-item detail in the report
- `--since-last-release` — only check items added since the last git tag

If no arguments are provided, run a full audit and produce a report (no fixes).

### Phase 1: Understand the project

Before auditing, understand what kind of project this is and what documentation surfaces exist.

1. **Read project metadata**: Check `package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, `Makefile`, or similar to understand the project type, name, and structure.
2. **Find documentation**: Look for docs in common locations:
   - `docs/`, `doc/`, `documentation/`
   - `README.md`, `CHANGELOG.md`
   - Doc site sources (e.g., `apps/docs/`, `website/`, `site/`, `docusaurus/`, `.vitepress/`, `mkdocs.yml`)
   - API docs (e.g., `api-docs/`, generated docs)
   - Man pages or help text
3. **Identify documentable surfaces** — determine which of these apply to the project:
   - **CLI commands & flags** (if the project has a CLI)
   - **Public API** (exported functions, classes, types for libraries)
   - **Configuration options** (config files, environment variables)
   - **Web features / UI pages** (if the project has a web interface)
   - **REST/GraphQL/RPC endpoints** (if the project exposes an API)

### Phase 2: Discover actual surfaces

For each documentable surface identified in Phase 1, discover what actually exists in the code.

#### CLI commands (if applicable)

1. Build the project if needed to get a working binary.
2. Run `<binary> --help` and parse available commands.
3. For each command, run `<binary> <command> --help` to capture usage, description, and all flags.
4. Recurse into subcommands.
5. Capture global flags.

#### Public API (if applicable)

1. Find all exported symbols: functions, classes, types, constants.
2. Check for JSDoc/docstrings/doc comments on exports.
3. Note which exports lack documentation.

#### Configuration (if applicable)

1. Find config file schemas, types, or parsing code.
2. Extract all supported config keys, their types, and defaults.
3. Check for environment variable support.

#### Web features / endpoints (if applicable)

1. Find route definitions and page components.
2. Find API endpoint handlers.
3. Compile a list of pages, routes, and endpoints.

### Phase 3: Cross-reference against documentation

For each discovered item, check whether it is documented:

1. **Is it mentioned at all?** Search the documentation for references to each item.
2. **Is the documentation accurate?** Compare documented behavior (flag names, defaults, types, descriptions) against actual code.
3. **Are there examples?** Check if usage examples exist for key features.
4. **Are there orphaned docs?** Look for documentation that references items that no longer exist in the code.

Also check documentation infrastructure:
- **Navigation/sidebar**: Do all listed pages exist? Are there orphan pages not linked from navigation?
- **Internal links**: Are cross-references between doc pages valid?
- **Version references**: Do version numbers in docs match the actual project version?

### Phase 4: Generate report

Produce a structured markdown report:

```
## Documentation Audit Report

### Summary
For each surface area, report:
- Total items: X (documented: Y, missing: Z, stale: W)

### Undocumented Items
For each undocumented item:
- Item name and type
- Where it's defined in code
- Which doc file(s) should cover it

### Stale / Inaccurate Documentation
Items where docs don't match reality:
- What the docs say vs what the code does
- File and location of the stale content

### Documentation Infrastructure Issues
- Broken links or references
- Orphan pages (exist but not linked)
- Missing pages (linked but don't exist)
- Version mismatches

### Top Recommendations
Prioritized list of the most impactful documentation improvements
```

Print the report to stdout.

### Phase 5: Fix gaps (only if `--fix` was passed)

If `$ARGUMENTS` contains `--fix`:

1. For each gap identified in Phase 4, update the relevant documentation file.
2. Follow the existing documentation style and formatting conventions in each file.
3. For new sections, match the structure and tone of surrounding content.
4. After making changes, list all modified files.

If `--fix` was NOT passed, end with: "Run `/audit-docs --fix` to automatically update documentation."

### Error Handling

- If a build step fails, report the error and continue with source-level analysis.
- If a command's `--help` output can't be parsed, note it in the report and continue.
- If a documentation file doesn't exist, note it as a gap.

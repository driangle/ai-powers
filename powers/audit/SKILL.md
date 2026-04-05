---
name: audit
description: "Perform a comprehensive codebase audit covering security, privacy, data integrity, architecture, and code quality. Use when the user wants to audit the codebase, check for security issues, or review code quality."
---

# Audit

Perform a comprehensive codebase audit across 8 dimensions using concurrent subagents for thorough, parallel analysis.

## Instructions

Run a full audit of the codebase. If `$ARGUMENTS` contains a specific dimension (e.g., "security", "privacy", "networking"), focus on that dimension only. Otherwise, run all 8 dimensions.

### Step 1: Launch parallel audit subagents

Use the **Agent tool** to launch subagents concurrently. Group them into two waves to balance thoroughness with context efficiency.

#### Wave 1 — Launch these 4 agents in parallel (single message, 4 Agent tool calls):

**Agent 1: Security & Trust Boundaries** (subagent_type: Explore, thoroughness: very thorough)
```
Audit this codebase for security and trust boundary issues. Report findings with severity levels (critical/high/medium/low/info).

Inspect:
- How user input and external data is handled — parsing, validation, sanitization
- Path traversal risks — can crafted paths escape intended directories?
- Symlink handling — does it follow symlinks that could point outside safe directories?
- Permission and authorization checks
- Injection risks in the rendering/output layer:
  - XSS via unsanitized HTML, markdown, or template rendering
  - Code injection via dynamic evaluation
  - SQL/NoSQL injection in database queries
- Command execution: any use of exec, spawn, eval, Function(), dynamic imports, or child_process
- Dependency risk: check package manifests for unpinned deps, postinstall scripts, suspicious packages
- Any auto-update, remote code fetch, or plugin system without integrity checks

For each finding, report: severity, file:line, description, and recommendation.
```

**Agent 2: Secrets & Privacy Exposure** (subagent_type: Explore, thoroughness: very thorough)
```
Audit this codebase for secrets and privacy exposure risks. Report findings with severity levels.

Inspect:
- Hardcoded secrets, API keys, tokens, or credentials in source code
- Does the application redact or detect secrets in user-facing output?
- Could sensitive data be accidentally indexed, cached, or logged?
- Caches, telemetry, crash logs, or analytics that include raw sensitive content
- Search for all network calls: fetch, axios, http, https, XMLHttpRequest, WebSocket, navigator.sendBeacon
- Check for error reporting or usage analytics that could transmit sensitive data
- Clipboard integrations that could leak secrets to global clipboard history
- Client-side storage (localStorage, sessionStorage, IndexedDB, cookies) persisting sensitive content
- Logging that could capture sensitive data (passwords, tokens, PII)

For each finding, report: severity, file:line, description, and recommendation.
```

**Agent 3: Data Integrity & Correctness** (subagent_type: Explore, thoroughness: very thorough)
```
Audit this codebase for data integrity and correctness issues. Report findings with severity levels.

Inspect:
- Input parsing logic: error handling for malformed or unexpected data
- Partial write / truncated file handling
- Concurrency and race condition risks
- Data ordering: is sorting deterministic? How are timestamps handled?
- Timezone handling in date display and sorting
- Data transformation correctness: are conversions and mappings accurate?
- Schema or format version compatibility and migration strategy
- Edge cases: empty inputs, missing fields, very large payloads, unicode handling

For each finding, report: severity, file:line, description, and recommendation.
```

**Agent 4: Networking Behavior** (subagent_type: Explore, thoroughness: very thorough)
```
Audit this codebase for networking behavior. Report findings with severity levels.

Inspect:
- Search for ALL outbound network requests: fetch, axios, http/https imports, WebSocket,
  XMLHttpRequest, navigator.sendBeacon, Image() src loading, script/link tag injection
- Check for: registry calls, API calls, telemetry endpoints, CDN fonts/scripts
- Check HTML templates for external resource loading (fonts, scripts, stylesheets)
- Is there an offline mode? Proxy support? Config to disable network?
- Check for service workers that might make network calls
- Look at build config for any external resource loading
- TLS validation or certificate pinning considerations
- Rate limiting, retry logic, and timeout handling

For each finding, report: severity, file:line, description, and recommendation.
```

#### Wave 2 — Launch these 4 agents in parallel (single message, 4 Agent tool calls):

**Agent 5: Local Attack Surface** (subagent_type: Explore, thoroughness: medium)
```
Audit this codebase for local attack surface issues. Report findings with severity levels.

Inspect:
- Does processing user-provided files trigger rendering, preview, or execution that could be exploited?
- Malicious input handling (e.g., terminal escape sequences, crafted payloads)
- Browser engine exploit surface if using Electron or webview
- Large input handling: could oversized data cause memory exhaustion / DoS?
- Recursive directory scanning: could deep/circular directories cause CPU spikes?
- File watcher behavior with many files
- Temporary file handling and cleanup

For each finding, report: severity, file:line, description, and recommendation.
```

**Agent 6: Architecture & Maintainability** (subagent_type: Explore, thoroughness: medium)
```
Audit this codebase for architecture and maintainability quality. Report findings with severity levels.

Inspect:
- Is the data model well typed with proper types/interfaces?
- Separation of concerns: are layers properly isolated?
- Schema or input validation layer: does the app validate data shape before using it?
- Error boundaries and error handling strategy
- Configuration and feature flag system
- Code modularity: are files focused on single responsibilities?
- Are there god files or components doing too much?
- Import structure: circular dependencies?
- Consistent patterns and conventions across the codebase

For each finding, report: severity, file:line, description, and recommendation.
```

**Agent 7: Testing & Reproducibility** (subagent_type: Explore, thoroughness: medium)
```
Audit this codebase for testing and reproducibility. Report findings with severity levels.

Inspect:
- Test coverage: are there tests? What kind? (unit, integration, snapshot, e2e)
- Property-based or fuzz tests for parsers?
- Deterministic builds: is the lockfile committed?
- Can the app be built reproducibly?
- Are there CI/CD configurations?
- Test fixtures: do they cover edge cases (empty inputs, large payloads, malformed data)?
- Test isolation: do tests depend on external services or shared state?

For each finding, report: severity, file:line, description, and recommendation.
```

**Agent 8: Developer UX & Failure Modes** (subagent_type: Explore, thoroughness: medium)
```
Audit this codebase for developer UX and failure mode handling. Report findings with severity levels.

Inspect:
- Graceful handling of: corrupted data, missing inputs, unknown types or formats
- Error messages: are they helpful and actionable?
- Warnings when: unexpected state detected, data truncated, version mismatch
- Loading states and error states in the UI (if applicable)
- Verbose/debug mode availability
- Debug logging with proper redaction of sensitive data
- Graceful degradation when data is incomplete or unexpected

For each finding, report: severity, file:line, description, and recommendation.
```

### Step 2: Compile the audit report

After all agents complete, compile their findings into a single structured report:

```markdown
# Codebase Audit Report

## Summary
- Total findings: N
- Critical: N | High: N | Medium: N | Low: N | Info: N

## 1. Security & Trust Boundaries
[Agent 1 findings, sorted by severity]

## 2. Secrets & Privacy Exposure
[Agent 2 findings, sorted by severity]

## 3. Data Integrity & Correctness
[Agent 3 findings, sorted by severity]

## 4. Networking Behavior
[Agent 4 findings, sorted by severity]

## 5. Local Attack Surface
[Agent 5 findings, sorted by severity]

## 6. Architecture & Maintainability
[Agent 6 findings, sorted by severity]

## 7. Testing & Reproducibility
[Agent 7 findings, sorted by severity]

## 8. Developer UX & Failure Modes
[Agent 8 findings, sorted by severity]

## Top Recommendations
[List the 5-10 most impactful recommendations across all dimensions]
```

### Step 3: Present findings

- Present the compiled report to the user
- Highlight any critical or high severity findings first
- If `$ARGUMENTS` requested a specific dimension, only show that section
- Offer to create task files for any findings the user wants to address

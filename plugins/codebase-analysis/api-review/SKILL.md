---
name: api-review
description: "Review a library's public API for clarity, consistency, composability, predictability, edge-case handling, and correctness. Use when the user wants to review an API surface, check API design quality, or evaluate a library's exported interface. Designed for libraries and packages — not services, servers, or full applications."
---

# API Review

Review the public API of a software library across 6 quality dimensions using concurrent subagents, then propose a prioritized set of changes.

This skill is designed for **libraries and packages** — code that exposes an importable API to consumers. It is not intended for reviewing HTTP/REST/gRPC service endpoints, full applications, or complex systems. If the project is a service rather than a library, tell the user this skill is not the right fit.

## Instructions

Review the public API of the library (or the package specified in `$ARGUMENTS`). If `$ARGUMENTS` names a specific dimension (e.g., "naming", "composability"), focus on that dimension only. Otherwise, run all 6 dimensions.

### Step 1: Identify the public API surface

Before launching subagents, identify the public API surface so each agent reviews the same scope:

1. Use Glob and Grep to find the package entry points — look for `exports` in package.json, `index.ts`/`index.js` barrel files, or `mod.rs`/`lib.rs` for Rust, `__init__.py` for Python, etc.
2. Collect the list of exported symbols: functions, classes, types, constants, and interfaces that consumers can import.
3. Note the file paths containing these exports — pass this context to every subagent.

### Step 2: Launch parallel review subagents

Use the **Agent tool** to launch all 6 subagents in a single message (6 parallel Agent tool calls).

Every agent prompt below should be prefixed with the public API surface you identified in Step 1 (entry points, exported symbols, and file paths).

**Agent 1: Clarity & Intuitive Naming** (subagent_type: Explore, thoroughness: very thorough)
```
Review the public API of this project for clarity and intuitive naming.

Inspect:
- Are function/method names self-describing? Could a new user guess what they do?
- Do parameter names clearly convey their purpose and expected values?
- Are type/interface names consistent with domain terminology?
- Are abbreviations avoided or universally understood?
- Do boolean parameters/return values read naturally (e.g., `isEnabled` vs `flag`)?
- Are similar operations named with consistent verb choices (get/fetch/retrieve — pick one)?
- Do names avoid misleading implications (e.g., a function named `delete` that only marks as inactive)?

For each finding, report: the symbol, file:line, what's unclear, and a suggested improvement.
```

**Agent 2: Consistent Data Models** (subagent_type: Explore, thoroughness: very thorough)
```
Review the public API of this project for data model consistency.

Inspect:
- Are the same concepts represented by the same types across the API surface?
- Are there redundant or overlapping types that represent the same entity?
- Is the naming convention for types/interfaces uniform (e.g., always `FooOptions` or always `FooConfig`, not a mix)?
- Do related functions accept and return compatible types (not requiring manual conversion)?
- Are enums/unions used consistently for the same set of values?
- Are optional vs required fields consistent across related types?
- Is there a clear hierarchy: input types, output types, internal types — or is it blurred?

For each finding, report: the types involved, file:line references, what's inconsistent, and a suggested fix.
```

**Agent 3: Composability** (subagent_type: Explore, thoroughness: very thorough)
```
Review the public API of this project for composability.

Inspect:
- Can API functions be easily chained or combined to build higher-level operations?
- Do functions accept and return types that are compatible with each other?
- Are there unnecessary coupling points where one function requires specific output from another?
- Is the API layered — can users access low-level primitives or only high-level wrappers?
- Are configuration objects composable (spread/merge-friendly) or monolithic?
- Are callbacks/hooks provided to allow users to customize behavior without forking?
- Do collection operations follow standard patterns (map/filter/reduce-friendly)?
- Is there a builder, pipeline, or middleware pattern where one would be natural?

For each finding, report: the API boundary, file:line references, what limits composability, and a suggested improvement.
```

**Agent 4: Predictable & Pure Behavior** (subagent_type: Explore, thoroughness: very thorough)
```
Review the public API of this project for predictability and purity.

Inspect:
- Do functions have hidden side effects not implied by their name or signature?
- Are there functions that mutate their arguments instead of returning new values?
- Is state management explicit — or do functions rely on hidden shared/global state?
- Are return types consistent for the same function (not sometimes T, sometimes null, sometimes throwing)?
- Do async functions clearly signal their async nature in naming or types?
- Are error cases communicated through return types (Result/Either/Option) rather than thrown exceptions where feasible?
- Are there functions whose behavior changes based on implicit context (locale, timezone, env vars) without the caller knowing?
- Is ordering of operations significant but undocumented?

For each finding, report: the function/method, file:line, what's unpredictable, and a suggested improvement.
```

**Agent 5: Edge Case Handling** (subagent_type: Explore, thoroughness: very thorough)
```
Review the public API of this project for robustness in edge-case handling.

Inspect:
- How do public functions behave with: null/undefined, empty strings, empty arrays, zero, negative numbers?
- Are boundary conditions handled (max int, very long strings, deeply nested objects)?
- Do functions validate their inputs at the API boundary or silently accept invalid data?
- Are error messages actionable — do they tell the caller what went wrong and how to fix it?
- Is there consistent behavior for missing optional parameters (defaults documented)?
- How does the API handle concurrent calls or re-entrant invocations?
- Are there timeout or cancellation mechanisms for long-running operations?
- Do destructive operations (delete, overwrite) have safeguards or confirmation patterns?

For each finding, report: the function/method, file:line, the edge case, observed behavior, and suggested improvement.
```

**Agent 6: Correctness** (subagent_type: Explore, thoroughness: very thorough)
```
Review the public API of this project for correctness.

Inspect:
- Do public functions fulfill their documented or implied contract?
- Are type signatures accurate — do they match what the function actually accepts and returns at runtime?
- Are generics/type parameters correctly constrained (not overly broad like `any`)?
- Are there logic errors in public methods: off-by-one, wrong comparison, swapped arguments?
- Do computed/derived values stay in sync with their source data?
- Are mathematical or algorithmic operations correct for all input ranges?
- Do string operations handle unicode correctly?
- Are there race conditions in async public methods?

For each finding, report: the function/method, file:line, the correctness issue, and a suggested fix.
```

### Step 3: Compile the review report

After all agents complete, compile findings into a single structured report.

**Categorize every proposed change by importance:**
- **High** — Breaks consumers, causes bugs, or violates the principle of least surprise in a dangerous way
- **Medium** — Creates friction, inconsistency, or confusion but doesn't break things
- **Low** — Polish, naming nitpicks, or nice-to-haves

```markdown
# API Review Report

## Summary
- Total findings: N
- High: N | Medium: N | Low: N

## 1. Clarity & Intuitive Naming
[Agent 1 findings, sorted by importance]

## 2. Consistent Data Models
[Agent 2 findings, sorted by importance]

## 3. Composability
[Agent 3 findings, sorted by importance]

## 4. Predictable & Pure Behavior
[Agent 4 findings, sorted by importance]

## 5. Edge Case Handling
[Agent 5 findings, sorted by importance]

## 6. Correctness
[Agent 6 findings, sorted by importance]

## Proposed Changes
[Deduplicated list of all changes, sorted by importance (high → low), with cross-references to the dimension that surfaced them]
```

### Step 4: Present findings

- If **no findings** are worth changing, say so clearly — do not invent issues
- Present the compiled report to the user
- Highlight high-importance changes first
- If `$ARGUMENTS` requested a specific dimension, only show that section
- Offer to create task files for changes the user wants to address

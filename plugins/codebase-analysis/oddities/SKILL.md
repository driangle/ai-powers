---
name: oddities
description: "Scan a scope of code for unconventional, strange, questionable, undocumented, or opaque things — latent bugs, unexpected complexity, inconsistencies, surprising design choices, and library/API workarounds. Produces a prioritized reading list, not a refactor plan. Use whenever the user wants to 'review' a directory/module/branch, flag 'weird' or 'suspicious' code, find 'red flags', spot 'code smells', or just understand what's odd in a slice of the codebase they're about to touch."
---

# Oddities

Produce a **reading list** of things worth a human's attention in a bounded scope of code — not a comprehensive audit, not a fix plan. The goal is to surface items that a thoughtful senior engineer would circle in a review: latent bugs, suspicious complexity, inconsistencies, odd design choices, and escape hatches around the type system or a library.

The output is optimized for someone who will *read* it and decide what, if anything, to chase down. Prefer fewer, sharper findings over a flood of shallow ones.

## When to use this

Trigger this skill when the user asks to:
- "Review" / "look at" / "skim" / "read through" a directory, module, file set, or a branch's changes
- Find "weird", "suspicious", "sus", "strange", "odd", "questionable" code
- Spot "red flags", "smells", "footguns", "gotchas"
- Get a "reading list" or "second set of eyes" on a slice of code
- Understand what's unusual in code they're about to modify

Do **not** use this skill for:
- Full-codebase security/privacy/architecture audits → use `audit`
- Reviewing an open GitHub PR with URL or number → use `pr-review`
- Reviewing a library's public API surface → use `api-review`
- Looking for unused/dead code → use `dead-code`
- Auditing test-suite legitimacy → use `test-audit`

## Scope resolution

The user will pass a scope via `$ARGUMENTS` or inline. Common shapes:

- **Directory or module**: `"review the foo/ module"` → glob files under that path
- **This directory / current scope**: `"this directory"` → the current working directory, non-recursive unless the directory is small; otherwise ask
- **Branch diff**: `"files changed in this branch"` / `"the diff against main"` → `git diff --name-only <base>...HEAD`, then read each changed file in full (not just the diff — you need surrounding context to judge oddness)
- **Specific files**: explicit list → read each
- **Ambiguous**: ask once. "Review the foo module" when there's no `foo` → ask which path.

If the scope is larger than ~50 files, confirm with the user before reading everything — they may want to narrow it. If the scope is ≤50 files, just read.

**Read every file in scope in full.** Skimming or sampling produces shallow findings. If the scope is too big to read in full, say so and ask the user to narrow it — don't silently cut corners.

## What to look for

Five buckets. A finding can belong to more than one; pick the one that best describes *why it's worth noticing*.

### 1. Bugs and latent bugs
Logic that's wrong, or correct today but fragile. Examples:
- Silent failures (swallowed errors, empty catches, ignored promise rejections)
- Off-by-one, wrong operator, wrong comparison semantics
- Hidden coupling: a change in one place silently breaks another
- Missed edge cases: empty input, null/undefined, unicode, timezone, concurrent callers
- Race conditions, ordering assumptions, non-deterministic sorts
- Resource leaks (unclosed handles, unbounded caches, unremoved listeners)

### 2. Unexpected complexity
Code more elaborate than the problem warrants. Examples:
- Hand-rolled parsers / state machines where a library or simpler approach exists
- Clever tricks (bit manipulation, prototype hacks, metaprogramming) in ordinary paths
- Deep nesting (4+ levels) or long functions (100+ lines) handling a simple concept
- Workarounds whose original cause is gone or unclear

### 3. Inconsistencies
Two places doing the same thing differently, or leftovers from an incomplete change. Examples:
- Duplicate logic with subtle divergence
- Abandoned migrations (old API + new API both in use)
- Dead code paths that *look* live
- Inconsistent naming, error handling, or validation across sibling modules

### 4. Odd design choices
Decisions that work but aren't obvious without context. Examples:
- Magic constants and hardcoded values (URLs, IDs, thresholds) with no comment
- Surprising side effects (mutating inputs, reaching into globals, writing files in getters)
- Unusual control flow (exceptions used for flow, early-returns hiding the main path)
- Non-standard patterns that don't match the rest of the codebase

### 5. Library / API workarounds
Escape hatches around the type system, framework, or a library. Examples:
- `as Type`, `@ts-ignore`, `@ts-expect-error`, `any`, `unknown` casts covering real uncertainty
- `# type: ignore`, `cast()`, `# noqa` in Python
- Reaching into private/internal APIs (underscore-prefixed, `_internal`, `unsafe_`)
- Regex where a typed parser / structured API exists
- Monkey-patching or module mutation
- Reflection-based hacks (`Object.getPrototypeOf`, `eval`, `Function(...)`, dynamic imports to bypass checks)

## How to produce findings

For **each finding**:

- **Location**: exact `path/to/file:line` (or line range for a block).
- **One sentence** describing the oddity. Plain English, no lecturing.
- **Why it matters**: pick one — *real bug*, *footgun*, *smell*, or *worth knowing*. Be honest: if it's just interesting and not actionable, say "worth knowing."
- **Confidence**: if you're unsure whether it's intentional, say so explicitly ("unclear if intentional — might be deliberate for X"). Don't assume malice or incompetence; senior engineers make non-obvious choices for reasons you can't see.

**Don't suggest fixes** unless the fix is trivial and obvious (e.g., "the `==` should be `===`"). This is a reading list, not a refactor plan. If the reader decides to act, they'll ask.

## Calibration — what makes a good finding

**Good** findings surprise a reader who knows the code reasonably well. Examples of tone:
- `src/parser.ts:142 — hand-rolled recursive descent parser for CSV; the project already uses papaparse elsewhere. Footgun: will diverge from the library's quoting behavior.`
- `src/auth/session.ts:88 — silent catch around JWT verification returns null on any error, indistinguishable from "no token". Real bug: a malformed token and an absent token are treated identically.`
- `src/util/retry.ts:34 — magic constant 7 retries, no comment. Worth knowing; unclear if intentional.`

**Bad** findings (avoid these):
- "This function could be shorter" (style, not an oddity)
- "No JSDoc comment" (convention, not an oddity, unless the *rest* of the file is documented)
- "Variable name could be clearer" (unless genuinely misleading)
- Anything derivable from a linter the project already runs

Aim for findings a linter *can't* catch. If it's a one-line rule a tool enforces, skip it.

## Severity grouping

Group findings under three headings, in this order:

1. **Bug** — real or latent correctness issues. These are the ones most likely to bite.
2. **Footgun** — things that are correct today but dangerous under plausible future change, or easy to misuse.
3. **Smell** — style/design oddities worth knowing about but not urgent.

Within each group, order by impact (your judgment), not by file path.

## Output format

Use this structure exactly:

```markdown
# Oddities in <scope>

<N findings across M files. Read every file in scope.>

## Top picks

1. **<one-line summary>** — `path:line` — one sentence on why this is the item most worth a human's attention.
2. **<one-line summary>** — `path:line` — …
3. **<one-line summary>** — `path:line` — …

(2–3 items. These should be the ones you'd personally walk a colleague to.)

## Bug

- `path/to/file.ts:142` — <one-sentence description>. Why: <real bug / latent bug>. <optional "unclear if intentional" note>
- …

## Footgun

- `path/to/file.ts:88` — <one-sentence description>. Why: <footgun explanation>.
- …

## Smell

- `path/to/file.ts:34` — <one-sentence description>. Why: <what's odd>.
- …
```

If a bucket is empty, omit the heading entirely — don't write "None."

## Process

1. **Resolve scope.** Determine the exact file list. If ambiguous or large, confirm with the user.
2. **Read everything in scope, in full.** Don't sample. If impossible, narrow the scope first.
3. **While reading, keep a running notes list.** Capture candidates as you go — don't wait until the end.
4. **After reading, cull.** Drop shallow findings (linter-catchable, style-only, no real insight). Thirty thoughtful findings beat fifty shallow ones. If you end up with five truly good findings, five is the answer.
5. **Group by severity, pick top picks, format.** Write the report using the template above.
6. **Present and stop.** Don't offer to fix. If the user wants to act on something, they'll say so.

## A note on parallelism

For large scopes, you *may* delegate reading to `Agent` with `subagent_type: Explore` — one agent per coherent sub-module, each returning its candidate findings. Then you cull and merge. Only do this when the scope genuinely exceeds what a single pass can hold; for most requests, reading directly is faster and produces better findings because you see cross-file patterns.

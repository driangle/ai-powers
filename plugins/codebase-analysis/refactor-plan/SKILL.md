---
name: refactor-plan
description: "Produce a prioritized refactoring plan for the code you just worked with — each suggestion tagged with priority and effort, sorted most- to least-recommended. It recommends and ranks; it does not perform the changes. Use right after finishing a task in a codebase, when the user asks 'what should I refactor', 'what would you clean up here', 'give me a refactor plan', 'what are the follow-up improvements', or wants recommendations grounded in the files already touched during the session. Complements 'oddities' (a reading list) by producing an actionable, ranked plan."
---

# Refactor Plan

Produce a **ranked refactoring plan** for the code you already saw while working on a task — grounded in files you actually read and edited this session, not a fresh scan of the whole repo. Each suggestion carries a **priority** and an **effort** estimate, and the list is sorted from most- to least-recommended so the reader can start at the top and stop whenever they run out of appetite.

This runs *after* the real work is done. The value is that you already understand this code — how it's structured, where it hurt to change, what you had to work around. Capture that hard-won context as concrete, prioritized suggestions before it evaporates.

## When to use this

Trigger this skill when the user, typically just after an agent finished a task, asks to:
- "What should I refactor / clean up here?"
- "Give me a refactor plan" / "refactoring suggestions" / "follow-up improvements"
- "What would you improve about this code?" (grounded in what was just touched)
- "Where's the tech debt in what we just changed?"

Do **not** use this skill for:
- A prioritized *reading list* of odd/suspicious code → use `oddities`
- Actually performing a refactor (extract, split, rename, simplify) → use `codebase-ops:refactor`
- Full-codebase security/privacy/architecture audits → use `audit`
- Finding unused/dead code → use `dead-code`
- Reviewing an open GitHub PR → use `pr-review`

## Scope: what code the plan covers

Default scope is **the code you engaged with during this session** — files you read, edited, or created while completing the task, plus their immediate collaborators (things they import or that import them, when you saw those too).

- **Prefer what you already have in context.** Don't re-scan the repo. The whole point is to convert the understanding you *already built* into recommendations. Re-read a specific file only to confirm a line number or a detail you're unsure about.
- If the session touched very little (one trivial edit), say so — a two-line change rarely warrants a plan. Offer to widen scope instead of manufacturing filler.
- If the user names an explicit scope ("plan refactors for the auth module"), honor it: read those files in full first, then produce the plan.
- If nothing was touched yet this session and no scope is given, ask what to focus on rather than scanning blindly.

## What to look for

Ground every suggestion in something you *observed while working*. The strongest suggestions come from friction you actually hit. Categories:

### 1. Structure and organization
- A file that's grown to mix multiple responsibilities (split by concept)
- Cohesive logic that wants to be its own module
- A "utils" grab-bag that should be grouped by feature
- Deep nesting or long functions handling a simple concept

### 2. Duplication and divergence
- The same logic in two places that you had to change in both (or forgot to)
- Copy-pasted blocks with subtle differences
- Parallel abstractions (old + new API both live) that should converge

### 3. Coupling and boundaries
- A change that rippled across five files because a boundary leaks
- Hidden dependencies / implicit contracts you had to reverse-engineer
- Modules reaching into each other's internals

### 4. Clarity and naming
- Names that misled you while working (not merely "could be shorter")
- Magic constants / hardcoded values you had to decode
- Control flow that hid the main path

### 5. Contracts and safety
- Missing validation at a boundary that made the change risky
- Type escape hatches (`any`, `as`, `@ts-ignore`, `# type: ignore`) covering real uncertainty you noticed
- Missing tests around a critical path you just modified

### 6. Simplification
- An abstraction that earns less than it costs (inline it)
- "Just in case" code with no current caller
- A hand-rolled thing where the codebase already has a library for it

Skip anything a linter the project already runs would catch. Skip pure style. Every item must be something a thoughtful engineer would agree is worth doing, not a preference.

## Priority and effort

Tag **every** suggestion with both:

**Priority** — how much it matters:
- **P1 (high)** — actively causing bugs, blocking change, or a boundary that will keep costing you. Do soon.
- **P2 (medium)** — clear improvement to maintainability; worth doing when nearby.
- **P3 (low)** — nice to have; do it opportunistically.

**Effort** — rough cost to do it well, *including* updating call sites and tests:
- **S** — localized; under ~30 min. One file, few call sites.
- **M** — a module-sized change; touches several files or needs test updates.
- **L** — spans many files, risky, or needs a migration/deprecation path.

## Ranking

Sort the whole list from **most- to least-recommended**. Ranking is *not* just priority — it's your judgment of overall payoff, which trades priority against effort:

- A **P1 / S** (high value, cheap) ranks at the very top — do it first.
- A **P2 / S** often outranks a **P1 / L**: a cheap solid win beats an expensive maybe.
- A **P3 / L** sinks to the bottom.

When two items are close, prefer the one that unblocks or de-risks future work. Use your own judgment and make the reasoning visible in the one-liner.

## Calibration — what makes a good suggestion

The failure mode of a refactoring plan is generic advice that could be pasted into any codebase: "add more tests," "break up large functions," "improve naming." These are worthless because they carry no information the reader didn't already have. Every suggestion you make should be something only *someone who just worked in this code* could have written — anchored to a real location and a real observation.

**Good** — grounded in friction you actually hit, with a specific location and payoff:
- `payments/refund.ts:88-140 — refund logic is duplicated here and in webhook/handler.ts:200; I changed both today and nearly missed the second. Extract one refundOrder() helper. **P1 · M** — kills the whole "forgot the other copy" class of bug.`
- `auth/session.ts:44 — the change I made had to thread userId through four functions because Session doesn't carry it. Add it to the Session type. **P2 · S** — every future auth change gets simpler.`
- `report/build.ts:210-340 — this 130-line function now does fetch + transform + render after today's edit; the render half is self-contained. Split out renderReport(). **P2 · M** — makes the next render change testable in isolation.`

**Bad** — ungrounded, unanchored, or pure style (avoid these):
- "Consider adding unit tests." — no location, applies to any project, ignores what you actually touched.
- "Break large functions into smaller ones." — a principle, not a suggestion. Which function? Why now?
- "Improve variable naming." — style, unless a specific name genuinely misled you while working — then name it and its line.
- Anything a linter the project already runs would flag.

If you can't tie a suggestion to a `path:line` and a thing you observed, it isn't grounded enough — drop it. A plan of three suggestions the reader couldn't have written themselves beats a plan of ten they could.

## Output format

Use this structure exactly:

```markdown
# Refactor plan — <scope, e.g. "the payments module you just changed">

<1–2 sentences: what code this covers and why these came up. Note it's grounded in this session's work.>

## Recommended, in order

### 1. <short imperative title> — `P1` · effort `S`
`path/to/file.ts:120-180` — What to change and why, in 1–3 sentences. Anchor it in something you saw: "this file now mixes X and Y after today's change." State the payoff.

### 2. <short imperative title> — `P2` · effort `M`
`path/to/other.ts:44` — …

### 3. <short imperative title> — `P1` · effort `L`
…

<Continue, most- to least-recommended. Aim for the 3–8 items that genuinely earn their place. Fewer sharp suggestions beat a long shallow list.>

## Skipped / not worth it (optional)
- <thing a reader might expect to see> — why you deliberately left it out.
```

Notes on the format:
- Number the items — the number *is* the recommendation rank.
- Every item shows `P{1,2,3}` and `effort {S,M,L}` in the heading.
- Always include a real `path:line` anchor. If you can't point to a location, the suggestion isn't grounded enough — drop it.
- The optional "Skipped" section builds trust: it shows you considered the obvious candidates and had reasons. Use it when you consciously rejected something a reader would ask about.

## Process

1. **Take inventory of what you touched.** List the files you read/edited/created this session and the friction points you hit. This is your raw material — don't re-scan the repo.
2. **Draft candidates from that friction.** Each candidate ties to a concrete observation and a `path:line`.
3. **Cull.** Drop linter-catchable items, pure style, and anything you can't anchor. A short strong list wins.
4. **Tag priority and effort** on each survivor.
5. **Rank** most- to least-recommended, trading priority against effort. Make the reasoning visible.
6. **Write the plan** using the template. Add a "Skipped" section if you rejected obvious candidates.
7. **Present and stop.** Don't start refactoring. If the user wants to act, they'll pick items — then hand off to `codebase-ops:refactor`.

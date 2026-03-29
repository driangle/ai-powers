---
name: spec-decompose
description: "Decompose a spec, requirements document, or technical design doc into actionable task files. Use when the user provides a spec file and wants it broken down into tasks, work items, or a project plan. Also trigger when the user says things like 'break this down', 'create tasks from this spec', 'plan out this project', 'turn this into tasks', or 'decompose this into work items' — even if they don't say 'spec' explicitly."
allowed-tools: [Read, Bash, Skill, Agent, Glob, Grep, Edit, Write]
---

# spec-decompose

Decompose a specification document into well-structured, independent task files using the taskmd system.

## When to use

The user provides a path to a spec file — this could be:
- High-level product requirements
- A technical design document (TDD)
- An RFC or proposal
- A PRD or feature brief
- Any document describing work that needs to be planned and executed

## Process

### 1. Read and understand the spec

Read the spec file the user provides. Understand the full scope: what's being built, the key components, technical decisions, constraints, and dependencies between parts.

If the spec references other files (e.g., existing code, schemas, APIs), read those too so you can make informed decisions about task boundaries.

### 2. Ask clarifying questions

Before decomposing, confirm a few things with the user:

- **Task granularity**: "Should each task be roughly one PR's worth of work (~1-20 files changed), or do you want smaller, more granular tasks?" If they want smaller tasks, you'll use `/split-task` after initial decomposition.
- **Phasing**: "Does this work have natural phases (e.g., foundation/infrastructure first, then features, then polish)? Or is it all one phase?"
- **Scope**: If the spec is ambiguous or very large, confirm which parts to decompose.

Keep this brief — don't over-interview. If the spec is clear, a single question about granularity may suffice.

### 3. Plan the decomposition

Before creating any tasks, outline your decomposition plan. Think about:

- **Independence**: Each task should be completable and reviewable on its own. Avoid tasks that can only be merged together.
- **Logical grouping**: Group related work (e.g., "set up the database schema" is one task, not one task per table).
- **Dependency ordering**: Identify which tasks must come before others. Foundation/infrastructure tasks come first.
- **PR-sized chunks**: Each task should correspond to roughly one PR — meaningful enough to review, small enough to land cleanly (target: 1-20 files changed).
- **Clear boundaries**: Each task should have an obvious "done" state.

### 4. Create tasks using /add-task

For each task in your plan, invoke the `/add-task` skill (from taskmd) with appropriate metadata.

Use these fields thoughtfully:

- **title**: Clear, action-oriented (e.g., "Implement user authentication API endpoints")
- **priority**: Based on dependency order and business value
  - `critical` — Blocks most other work; foundational
  - `high` — Important for the core feature set
  - `medium` — Needed but not blocking
  - `low` — Nice-to-have, polish, or deferred
- **effort**: Estimate relative size
  - `small` — A few hours, <5 files
  - `medium` — A day or two, 5-15 files
  - `large` — Multiple days, 10-20+ files
- **tags**: Use consistent, descriptive tags derived from the spec's domain (e.g., `backend`, `frontend`, `database`, `auth`, `api`, `testing`, `infrastructure`, `docs`)
- **depends-on**: Reference task IDs for prerequisite tasks. Only add true blockers — not soft preferences.
- **type**: `feature`, `improvement`, `chore`, or `docs` as appropriate
- **group**: Domain classification if the project has clear domains (e.g., `api`, `web`, `cli`)

For the task body, write:
- **Objective**: 2-3 sentences explaining what this task accomplishes and why
- **Tasks**: Specific, actionable checklist items (the actual implementation steps)
- **Acceptance Criteria**: Concrete, verifiable conditions for "done" — things a reviewer could check

### 5. Optionally split large tasks

If the user requested smaller tasks, or if any task ended up with effort `large` and has clearly separable sub-concerns, use `/split-task` on those tasks to break them down further.

### 6. Present the result

After creating all tasks, give the user a summary:

- Total number of tasks created
- A brief dependency graph or ordered list showing the recommended execution sequence
- Any tasks you flagged as large that could be split further
- Any ambiguities or decisions you made that the user should validate

## Guidelines

- Prefer fewer, well-scoped tasks over many tiny ones. A task called "Add the `name` field to the user model" is too small; "Set up user model and database schema" is about right.
- Every task should deliver tangible, reviewable progress. Avoid tasks that are pure setup with no visible outcome.
- If the spec describes work across multiple systems (e.g., backend + frontend + infra), organize tasks so each one stays within a single system where possible. Cross-cutting tasks are harder to review.
- Use phase tags (e.g., `phase:1-foundation`, `phase:2-core`, `phase:3-polish`) if the work has natural phases.
- Don't invent requirements beyond what the spec describes. If something is ambiguous, note it in the task's objective rather than guessing.

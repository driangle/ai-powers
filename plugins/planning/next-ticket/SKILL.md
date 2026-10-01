---
name: next-ticket
description: "List the user's open Linear tickets and recommend the one to work on next, optionally scoped to a project, epic or topic. Use whenever the user asks what to pick up next, which ticket to start, what they should work on in some project or topic, or wants a list of their assigned or open Linear tickets, even when they don't say 'Linear' (e.g. 'what's on my plate', 'suggest a ticket in the payments topic', 'what can I start today'). Reads each candidate's description as well as its relations, because a ticket whose blockers are all done can still be deferred or waiting on a decision. Requires the Linear MCP server."
---

# next-ticket

Recommend one Linear ticket to work on next, with the reasons and the reasons against the others.

## Why the descriptions matter

Blocking relations say whether a ticket *can* start. They don't say whether it *should*. Teams record the rest in the description or title: "deferred post-launch", "open question, needs a team decision", `[BLOCKED]` on an external party, "must agree on X with ticket Y first". A ticket whose blockers are all done but that was explicitly deferred is a bad pick, and only the description shows it. So readiness here has two parts, and both have to hold.

## Prerequisite

The Linear MCP server, connected and authenticated. If no Linear issue tools are available, stop and say so.

## Steps

### 1. List the open tickets

Call `list_issues` with `assignee: "me"`, `limit: 250`, and the fields `id, title, priority, status, statusType, project, url, updatedAt`. Drop `completed` and `canceled` status types.

If the user only asked for a list, report it and stop:

- Group by status in the order In Review, In Progress, Todo/Backlog, since what's closest to done is what usually needs attention first.
- One table per group: ticket (linked), title, priority, project.
- After the tables, a couple of bullets: how the tickets split across projects, any In Progress ticket with no update for weeks, and any title marked `[BLOCKED]`.

### 2. Narrow to the scope

If the user named a project, epic or topic, keep the tickets whose project matches, or whose title or parent clearly belongs to it. Say which tickets you kept if the match was fuzzy. With no scope, use every open ticket.

### 3. Check relations

Call `get_issue` with `includeRelations: true` for every candidate, all in parallel. A ticket is **relation-ready** when each `blockedBy` ticket is done. Take a blocker's status from the step 1 list when it's there. Otherwise, look it up, because blockers owned by other people won't be in your list.

### 4. Read the descriptions

For each relation-ready candidate, read the description and title, and move the ticket down the list if any of these hold:

- A recorded decision to defer it, postpone it, or drop it from the current scope.
- An open question or a decision it needs before work can start.
- `[BLOCKED]`, `[CONDITIONAL]` or similar in the title, or a dependency on an outside party that isn't a Linear relation.
- A stated interaction with another open ticket that has to be settled first, such as a shared threshold or a shared design choice.

Keep the reason in a few words, since step 6 reports it.

### 5. Rank

Among the tickets still workable, order by:

1. Priority.
2. How much it gates: whether a launch, rollout or the parent ticket waits on it, and whether another ticket's deferral was only accepted because this one would cover the risk (alerts, monitoring, a fallback).
3. Size, preferring the smaller ticket when the first two are equal.

### 6. Report

Name one ticket and keep the reply short:

- **The pick**, linked, with three or four bullets of why. Start each bullet with a bold phrase (for example **Nothing blocks it.**, **It's the launch gate.**).
- **What it involves**: the ticket's tasks in two to four short lines, with the estimate if it has one.
- **Why not the others**: one line per remaining candidate in scope, with the reason from step 3 or 4.
- **Check first**: one thing to confirm before starting, if there is one. A common case is a step in the ticket's plan that belongs to a ticket you don't own, whose status you should check.

If the user wants a full dependency graph, critical path, or parallel tracks across an epic, that's a graph question. Use a dependency-graph skill if one is installed.

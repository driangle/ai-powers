# Source: Linear

Tickets in Linear, read through the Linear MCP server. If no Linear issue tools are
available, stop and say so.

## Listing

Translate the user's description into `list_issues` arguments, such as team, project,
cycle, label, assignee, or status. Fetch `id, title, priority, status, statusType,
project, labels, assignee, url, updatedAt`. Drop the `completed` and `canceled` status
types. If the user gave a Linear view URL or a list of ids, use exactly those.

Default with no description: the user's own open tickets (`assignee: "me"`), unstarted
ones only. Never pick up a ticket assigned to someone else unless the user includes it.

## Reading one ticket

Call `get_issue` with `includeRelations: true`. Read the whole description, not just the
title. Dependencies are the `blockedBy` relations, and a ticket with open sub-issues is
blocked by them too. Look up blockers that are not in your list, since they may belong to
other people.

Titles and descriptions carry blocks that relations do not, such as `[BLOCKED]`, "deferred",
"needs a decision", or a dependency on an outside team. Treat those as autonomy exclusions.

Tickets rarely name files, so the area is weaker than for task files. Use the paths the
description names if there are any. Otherwise use the project, labels, and parent ticket,
and treat two tickets with the same parent or the same project and label as overlapping.

## In flight

Tickets in a `started` status type, whoever owns them, plus `git worktree list`.

## Default per-task prompt

`/work` only knows taskmd, so write the prompt out:

> Work Linear ticket `<ID>`: read it with the Linear MCP (`get_issue`), move it to In
> Progress, implement it in its own worktree, run the project's validation, then open a PR
> that names `<ID>`. Report the PR URL. Do not merge it.

Start sessions with `use_worktree: true`, since this prompt does not make its own worktree.

## Landed

Tracker workflows land through PRs, not direct commits. Agree in step 0 which one counts:

- **PR opened** (the default): the session's PR exists, names the ticket, and its CI is
  not failing.
- **PR merged**: the PR is merged, and the ticket has moved to a `completed` status.

Check it with `gh pr list --search <ID>` or `gh pr view`. A session's report alone is
not enough.

## Detecting changes

Record each running ticket's `updatedAt` in the ledger. When you refill, or when the user
says tickets changed, fetch the running tickets again and compare. If one changed, diff
the description against what the session was started with, and message that session.

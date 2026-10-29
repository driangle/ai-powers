# Source: Jira

Issues in Jira, read through the Atlassian MCP server (JQL search, get issue) or the
`acli` CLI. If neither is available, stop and say so.

## Listing

If the user gave JQL, run it **as given**. Otherwise translate their description into JQL,
show it in one line, and run that. Fetch key, summary, status, status category, priority,
components, labels, assignee, parent, and updated. Drop the `Done` status category.

Default with no description:
`assignee = currentUser() AND statusCategory = "To Do" ORDER BY priority DESC, created ASC`.
Never pick up an issue assigned to someone else unless the user includes it.

## Reading one issue

Fetch the full issue with its issue links and sub-tasks. Read the whole description.
Dependencies are `is blocked by` links (and `depends on` where the project uses it), plus
any open sub-tasks. Look up linked issues that are not in your list.

As with any tracker, the description can carry blocks that links do not ("waiting on
legal", "needs design sign-off"). Treat those as autonomy exclusions.

The area comes from paths named in the description, then from components, labels, and
the epic or parent. Two issues in the same component and epic overlap unless their
descriptions name separate files.

## In flight

Issues in the `In Progress` status category, whoever owns them, plus `git worktree list`.

## Default per-task prompt

`/work` only knows taskmd, so write the prompt out:

> Work Jira issue `<KEY>`: read it with the Atlassian MCP, transition it to In Progress,
> implement it in its own worktree, run the project's validation, then open a PR whose
> title starts with `<KEY>`. Report the PR URL. Do not merge it.

Start sessions with `use_worktree: true`, since this prompt does not make its own worktree.

## Landed

Same as Linear. Agree in step 0 whether **PR opened** (the default) or **PR merged**
counts, and check the PR with `gh` yourself.

## Detecting changes

Record each running issue's `updated` timestamp in the ledger. Fetch them again when
refilling or when told issues changed. If one changed, diff the description and message
only that session.

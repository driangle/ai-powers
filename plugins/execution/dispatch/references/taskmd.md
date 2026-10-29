# Source: taskmd

Task files in the repo, managed with the `taskmd` CLI.

## Listing

Run the user's command **as given**, adding only `--format json` if it is missing. Do not
rewrite its filters, sort, or limit. Any of these are valid:

- `taskmd list --status pending --sort created_at --limit 20 --reverse`
- `taskmd next --limit 10`, optionally with `--scope`, `--filter` flags
- `taskmd search "<query>" --filter status=pending`

Default with no command: `taskmd next --format json --limit 20`.

`taskmd next` already drops blocked tasks and ranks by its own recommendation. Keep that
order, and still check dependencies yourself, since it does not know which tasks you have
running.

## Reading one task

Read the whole task file (`taskmd get <id>` gives its path). Dependencies are the
frontmatter `dependencies` list; look up each one's status with `taskmd get <id>`.
Paths in the body give the area. Tags help too.

## In flight

Tasks with status `in-progress`, plus `git worktree list` entries named after a task id.

## Default per-task prompt

`/work <id>`. It makes its own worktree, so start sessions with `use_worktree: false`.

## Landed

The task's commit is on the target branch (`git log <target> --oneline | grep <id>`), and
the task file on that branch says `status: completed`.

## Detecting changes

Task files live in git. Record the target branch's HEAD in the ledger, then run
`git diff <old>..HEAD -- <task files>` for the running tasks.

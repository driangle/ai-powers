---
name: dispatch
description: "Work through a backlog in parallel by delegating each task to its own session (e.g. `/work <id>`), while staying the coordinator: pick only tasks that need no human input and are not blocked, never run two that touch the same area, cap how many run at once by the machine's load, keep a ledger of what landed, refill slots as sessions finish, and stop at an agreed exit condition. Use when the user asks to delegate, dispatch, fan out or parallelize pending tasks across sessions, 'keep N tasks going', 'work through the backlog in the background', or invokes /dispatch."
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, ToolSearch, SendMessage, mcp__ccd_session__start_session, mcp__ccd_session_mgmt__list_sessions, mcp__ccd_session_mgmt__get_session
---

# dispatch

Act as the coordinator for a batch of tasks. Each task runs in its own session; this
session never does task work itself. Its job is choosing what runs, when, and next to what,
then checking what actually landed.

## Input

Any of these, all optional:

- **The task set**, as a command or a description. Examples: `taskmd list --status pending
  --sort created_at --limit 20 --reverse`, "the screencast tasks", or an explicit list of ids.
  Default: the project's pending tasks.
- **The per-task prompt**: what each session is started with. Default: `/work <id>`.
- **Concurrency**, e.g. "at most 2 at a time". Default: decided from the machine in step 3.
- **The exit condition**, e.g. "stop after 20 complete", "until the list is done", "until 6pm".

## Step 0: Settle the exit condition first

Without one, a dispatcher never stops: sessions file follow-up tasks, and those are always
the most attractive ones to start next. If the user gave none, propose one before starting
anything and get a yes. The usual default is "every task in the starting set has landed or
been skipped, and nothing outside that set is started". State the choice in a line.

Count only work that **landed** (merged or committed to the target branch, task marked
complete). A session that reported finishing is not counted until you have checked.

## Step 1: Gather candidates

Run the task-set command. For each candidate, read the **whole task file**, not just the
title, and record:

- **Status and dependencies.** A task is blocked if any dependency is not completed. Look up
  each dependency's status yourself; a dependency on a task that is running right now is still
  a block.
- **Area.** This means the files, directories, modules and docs the task names or will
  obviously touch, plus its tags. Grep the body for paths. This is what conflict checks use.
- **Autonomy.** Can a session finish this with no one at the keyboard? Exclude a task that:
  - is marked manual, or is a decision the user owns ("decide where X is hosted", "pick a
    vendor", a privacy or policy call);
  - needs the user's accounts, credentials, API keys, payments, or an external service sign-up;
  - needs physical hardware or a person's senses: a real device, mic, camera, MIDI gear, or
    "listen to it" / "check it looks right" with no automated proxy;
  - needs an environment this machine cannot provide, e.g. a GPU-less Linux box, a cloud
    container, or another OS;
  - depends on one of the above.

  A keyword scan (manual, decide, account, credential, device, hardware, listen, approve) finds
  candidates for exclusion. Then read each hit, because most are false positives. A
  task saying the agent should "decide the API shape and record it" is still autonomous.

- **Size and priority**, for ordering.

Also check what is **already in flight**. That means tasks marked in progress, existing worktrees
(`git worktree list`), and running sessions (`list_sessions`). Their areas are occupied
even though you did not start them. If the user asks you to leave something alone, do.

## Step 2: Keep a ledger

Write a ledger file in the scratchpad directory (or another path outside the repo) and
update it on every event. Long dispatches get their context summarized, and the ledger
is what survives. Keep in it:

- the exit condition and the rules the user added along the way;
- **Landed**: numbered, with each task's commit;
- **Running**: task id, session id, and area;
- **Skipped**: task id and the reason;
- **Waiting on**: tasks held back by a conflict with a running one, and which one;
- **Next candidates**, in order.

## Step 3: Decide how many to run

Each session eventually runs the project's full validation, and when several overlap that
dominates the machine. Too many at once and the checks time out under load, sessions retry,
and everything takes longer than running fewer.

- Read the core count and the current load (`sysctl -n hw.ncpu` or `nproc`, then `uptime`).
  Check what else is busy with `ps -Ao pcpu,comm -r | head`, such as other projects' sessions,
  simulators or builds.
- Default cap: **3** concurrent sessions on a typical laptop, or fewer if the project's full
  check is heavy. Do not go above the user's number.
- **Back off when loaded.** If the load average is well above the core count, fill only one
  slot, or none. If sessions report tests timing out "under load", hold the next slot open
  until load drops. Sessions blaming the load is the signal you are running too many.

## Step 4: Choose a non-conflicting batch

Pick from the eligible candidates, by priority then age, until the cap is reached. A candidate
is **not** startable if its area overlaps a running session's area, or another task you are
choosing in this round. Overlap means the same files, the same subsystem (e.g. "the
screencast recorder", "the sequencer"), or the same docs page. Two tasks that edit
different functions in one small module still conflict.

Clusters of related tasks (ten tasks on the same tool) run one at a time. Spread the batch
across areas instead of draining one cluster.

A follow-up a session files while it works usually depends on it and shares its area. Treat
it as next in line for that area once its parent lands.

## Step 5: Start sessions

Start one session per task with the platform's session tool. In the Claude desktop app that
is `mcp__ccd_session__start_session`; load it with `ToolSearch` if it is deferred. Use:

- `initiation: "user_asked"`, since the user asked for the delegation;
- `prompt`: the per-task prompt, e.g. `/work 01m639pma`, and nothing else;
- `background`: one or two sentences covering:
  - that this is part of a batch dispatch;
  - which tasks run alongside it and their areas, so it does not wander into them;
  - related work that just landed, with commit ids, that it should build on;
  - "the target branch moves while you work, so rebase onto it before landing";
- `use_worktree: false` when the per-task prompt makes its own worktree (as `/work` does), so
  you do not get a worktree inside a worktree; otherwise `true`;
- a short `name` and a title such as `<id> · <3-5 word summary>`.

Before each start, write one bold line naming the task and why it is safe to run now
(unblocked, autonomous, area free). Then end the turn. Do not wait, poll, or predict
results. The platform wakes you when a session finishes a turn.

If no session tool exists, tell the user. Dispatching needs real separate sessions, and
background subagents in this conversation are not a substitute for long-running tasks that
each validate and land.

## Step 6: Handle each session event

A session finishing a turn is a **report, not proof**. Most turns end with "waiting on the
check". For each note:

1. **Read what it says.** If it is still validating, there is nothing to do; say so in one line.
2. **When it says it landed, verify it.** Check that the target branch's log shows its commit
   and that the task is marked completed. Only then add it to Landed in the ledger.
3. **Note what it filed.** Follow-up task ids go into Next candidates, and a note about a
   flaky check goes into your load judgement.
4. **Refill.** Re-check load. If slots are free, re-run steps 1, 3 and 4 against the current
   state: tasks that just landed may unblock others, and a freed area may let a waiting task
   start. Start the next batch (step 5).
5. **Report briefly**: what landed (commit and one-line effect), what is still running, what
   you started and why, and the count against the exit condition ("14 of 20").

Never merge a session's branch yourself, push, or archive sessions unasked. Each session
lands its own work.

## Step 7: When the source of truth changes under the sessions

The user may pull, or other sessions may land and edit task files. When told "I pulled, tasks
may have changed", or when you notice it:

- Diff the task files of the **running** tasks between the last commit you knew and now
  (`git diff <old>..HEAD -- <task files>`).
- If one changed, message **only** that session (`SendMessage` with its session id). Say
  which commit changed it, summarize the new requirements in a few bullets, and tell it to
  re-read the file. Do not message sessions whose tasks did not change.
- Check whether the branch was rewritten (`git merge-base --is-ancestor <old> HEAD`). If it
  was, tell the affected session to rebase onto the current target. Tell the user too, since
  every rewrite restarts each landing session's validation.
- Changes to tasks nobody is running need no message. Note them in the ledger if they affect
  eligibility.

## Step 8: Stop

Stop starting sessions once **landed + running = the exit target**. Starting more would
overshoot, because every running task is expected to land. Keep handling events until the
running ones finish, then give a final report:

- what landed, with commits and a one-line effect each;
- what was skipped, and why;
- follow-ups filed during the run;
- anything a session could not verify (e.g. "covered by a unit test; no real end-to-end run").

If a running task fails or gets stuck, it does not count. Start one replacement if the user's
condition is a count. Otherwise report it.

## Notes

- New rules from the user mid-run (e.g. "only autonomous tasks", "stop at 20", "leave X alone")
  apply from that point on. Re-check the running sessions against them and write them to the
  ledger.
- Scope does not grow on its own. Tasks filed during the run join the pool only if the exit
  condition is a count or the user says so.
- The coordinator stays cheap: no task work, no full validations, no large file reads beyond
  what eligibility needs.

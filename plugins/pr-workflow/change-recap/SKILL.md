---
name: change-recap
description: Recap what changed in an area of the code over a timeframe — new features, improvements, fixes and under-the-hood work — from the pull requests merged on GitHub in that window, grouped by initiative and project where the issue tracker records them and credited to who built and reviewed each change, written so developers and managers can both read it, as an HTML page that can be published as a Claude Artifact. Typically run on Fridays for the week's recap. Use whenever someone asks what changed, shipped, got merged or happened in a repo, service, folder, product area or team this week, last week, this sprint or since a date, asks for a weekly or Friday recap, a "what's new" or a changelog-style summary of recent work, even if they don't say "recap".
allowed-tools: Read Write Bash(gh repo view *) Bash(gh pr list *) Bash(gh pr view *) Bash(gh search prs *) Bash(gh api users/*) Bash(jq *)
---

# Change Recap

Summarise what changed in a scope of the codebase during a timeframe, from the pull requests merged
in that window. The reader is anyone in the organisation — a developer catching up, an engineering
manager writing a weekly update, a product manager checking what landed — so every item leads with
what changed for the people who use the system, not with how the code changed.

The examples below use a fictional organisation, `acme`, with repositories `api` and `web`, a
Payments team whose tickets start with `PAY-`, and people such as Ana López and Raj Patel. They are
placeholders only; step 1 works out the real ones.

## Prerequisites

The GitHub CLI, authenticated with access to the organisation being recapped:

```bash
brew install gh && gh auth login
gh auth status
```

If an issue-tracker connector (Linear, Jira or similar) is available in the session, it is used to
read the tickets behind pull requests: their projects, initiatives and owners. Without one the
recap still works, from the pull requests alone.

## 1. Settle the context, the scope and the timeframe

The skill knows nothing about the company it runs in. Work out what it needs from the context first,
and ask the user only for what is still missing or ambiguous — in one message, not one question at a
time:

| What | Where to look, in order |
|---|---|
| **GitHub organisation** — `<org>` in every command below | The user's request; the repository in the current directory (`gh repo view --json owner --jq .owner.login`); repository URLs in the conversation; the instruction files the session loaded (`CLAUDE.md`, `AGENTS.md`) |
| **Repositories, apps and services** in scope, and what they are called in product language | The user's request; the instruction files and READMEs of the current workspace; a manifest of repositories if the workspace has one; the repositories that come up in step 2 searches |
| **Team** and its **ticket prefix** | The user's request; ticket keys in the titles and branches of the pull requests found; the teams the issue-tracker connector lists |
| **Issue tracker** | Which tracker connector the session has; the shape of the ticket keys and links in pull request bodies |
| **Product names** — the apps, surfaces and customer types used in the item headlines | The instruction files, READMEs and pull request bodies; never the placeholders in this file |

State what you derived in the scope line below, so a wrong guess gets corrected before the work
starts.

**Scope** is one of:

- **Repositories** — `api`, `web`.
- **Paths inside a repository** — `api/src/billing`. Only pull requests touching files under those
  paths count.
- **A team or ticket prefix** — "the Payments team", `PAY-`. Pull requests count when the team's
  ticket key appears in the title, branch name or body, wherever in the code they landed. A team
  name with no prefix is resolved as in the table above.
- **A product area or topic** — "checkout", "notifications", "search". Keywords match pull requests
  unreliably — they miss work whose title doesn't use the words and catch unrelated work that does —
  so use them only to find where the area lives, then turn it into one of the scopes above:
  1. Run the topic search in step 2 with two or three keywords.
  2. From the hits, note the repositories, and the folders their changed files share (fetch
     `files` with `gh pr view`). Note any ticket prefix that recurs.
  3. Show the user the repositories, paths and prefixes you found and confirm before collecting.
     Then collect by repository and path, adding pull requests that carry the area's ticket prefix.
- **Everything** — every repository in the organisation.

If the user names no scope and the context doesn't suggest one — such as the team or repository the
user works on, from the instruction files or the current directory — ask for it. Don't default to the
whole organisation: it is rarely what a recap reader wants and it is slow.

**Timeframe** defaults to the last 7 days, ending today. Running it every Friday then leaves no gap
and no overlap. Accept "this week" (Monday to today), "last week", "this sprint" (ask for the start
date if it isn't given), "since <date>" and explicit ranges. Work in absolute `YYYY-MM-DD` dates.
GitHub compares merge dates in UTC, so a pull request merged late in the evening in some time zones
can fall on the next day's date.

Before collecting anything, state the resolved organisation, scope and dates in one line, so the
user can correct them early: "Recapping `acme/api` under `src/billing`, merged 2030-03-01 to
2030-03-07."

## 2. Collect the merged pull requests

For a repository, with or without a path filter:

```bash
gh pr list --repo <org>/<repo> --state merged \
  --search "merged:<START>..<END>" --limit 300 \
  --json number,title,body,author,mergedAt,url,labels,headRefName,files
```

For a path scope, keep only pull requests where some entry in `files` starts with one of the paths.
GitHub returns at most 100 files per pull request, so a very large pull request can touch the path
without showing it; when one has exactly 100 files and looks related, check it with `gh pr view`.

For a ticket prefix, keep pull requests whose title, `headRefName` or body contains the prefix.

For a topic or the whole organisation:

```bash
gh search prs --owner <org> --merged-at "<START>..<END>" --limit 1000 \
  --json repository,number,title,body,author,url,labels "<keyword>"
```

Drop the keyword for the whole organisation. Search results carry no `files` and no `mergedAt`;
fetch them with `gh pr view <number> --repo <org>/<repo> --json files,mergedAt` only where you
need them.

A busy repository returns hundreds of pull requests with full bodies, too much to read raw. Filter
before reading, with `--jq` on the `gh` call or by piping to `jq`, keeping only the pull requests in
scope and only the fields you need. For example, for a path scope:

```bash
gh pr list ... --json number,title,url,author,headRefName,files \
  --jq '.[] | select(any(.files[]; .path | startswith("src/billing/")))
        | {number, title, url, author: .author.login, branch: .headRefName}'
```

Then fetch bodies only for the pull requests that remain.

If a call returns exactly `--limit` results, the window was truncated: split it in halves and
collect each, rather than recapping a partial list.

Only merged pull requests count. Merged is not the same as deployed — say "merged" in the recap,
never "released" or "live", unless the pull request itself says it has shipped.

## 3. Set the noise aside

Leave these out of the recap body, and count them in the closing line instead:

- Bot pull requests — `dependabot`, `renovate`, `github-actions` and any author ending in `[bot]` —
  except security fixes, which get one line under **Under the hood**.
- Routine dependency and version bumps, lockfile-only changes, and generated translation syncs. A
  bump made to fix a real bug is not noise: it goes under **Fixes**, described by the bug it fixes.
- A revert together with the pull request it reverts, when both landed in the window — they cancel
  out. A revert of something older stays in, as a fix or a rollback. A pull request that re-lands
  work reverted before the window is new work: recap it, and mention that it is a second attempt.

## 4. Understand each change

The title and body are usually enough. When they aren't — a title like "fix" or "PAY-123", an empty
body — look further, in this order, and stop as soon as the change is clear:

1. The ticket key in the title or branch name (`PAY-123`), read through the issue-tracker connector
   if one is available.
2. The changed files: their paths usually say which feature or service moved.
3. The diff, as a last resort, for the few that are still unclear. Don't read every diff.

Note when a change sits behind a feature flag or is only enabled for some customers — the reader
needs to know it isn't visible to everyone yet.

Note when a change is only half merged: a pull request whose body names a companion pull request
that is still open, so the change has no effect until the other one lands. Link the open one in the
item and say what is still waiting.

### Find the project and initiative

Readers follow work by initiative and project ("how is self-serve onboarding going?"), so find out
which one each change belongs to, wherever that is recorded:

1. **The issue tracker.** Collect the ticket keys from every pull request's title, branch and body.
   Look each ticket up once and note its project; look each project up once and note the initiative
   above it — an initiative in Linear, an epic or parent issue in Jira. A ticket with no project
   inherits its parent ticket's.
2. **The pull request itself**, when there is no ticket: a label naming a project, or a body that
   says which project or epic the work is part of.

Only use a project that is recorded somewhere. Don't invent one from keywords or from a guess about
what changes have in common: those go to "Other changes" in step 5. Without a tracker connector,
rely on the pull requests alone and say in the recap that the grouping is partial.

### Find who did it

Readers want to know who to thank and who to ask, so credit every item to the people behind it.
For each pull request kept in the recap, fetch its commit authors and reviews:

```bash
gh pr view <number> --repo <org>/<repo> --json author,commits,reviews \
  --jq '{author: {login: .author.login, name: .author.name},
         commitAuthors: [.commits[].authors[] | {login, name, email}] | unique,
         approvers: [.reviews[] | select(.state == "APPROVED") | .author.login] | unique}'
```

Identify people by GitHub login, not by name: the same person's commit name often differs from
their profile name ("Ana Lopez" in commits, "Ana María López" on the profile). A commit author with
no login is matched to a known person by email, and kept by name only if nothing matches.

- **Built by** — the pull request's author, plus any other commit author or `Co-authored-by`
  person. For an item spanning several pull requests, the union of them.
- **Reviewed by** — the people who approved the pull requests.
- **Owner** — the assignee of the ticket, when it is someone not already credited; and the
  project's lead, shown once on the project, not on each item.

Show people by their GitHub profile name, falling back to the login; look up a login's name once
with `gh api users/<login> --jq .name` when you only have the login, as for approvers.

Leave out bots and AI agents: Claude (login `claude`, email `noreply@anthropic.com`), Copilot,
Cursor, Devin and any account ending in `[bot]`. A pull request whose only human contributor is the
person who merged an agent's work credits that person.

Attribution is credit, not a scorecard: don't count or rank pull requests per person anywhere in
the recap.

## 5. Group and classify

One item per change a reader would recognise, not per pull request. A feature that took a backend
pull request, a frontend one and a follow-up fix is one item with three links.

Group the items by initiative, then by project within it. A project with no initiative stands on
its own. Order initiatives and projects by how much they changed in the window, most first. Items
with no known project go to **Other changes** at the end.

Give every item a category, shown as a badge next to it within its project, and used as
sub-sections inside **Other changes**:

- **New features** — something users or other teams could not do before.
- **Improvements** — existing behaviour made faster, clearer, more reliable or easier to use.
- **Fixes** — something that was broken and now isn't.
- **Under the hood** — refactors, infrastructure, tests, tooling, monitoring, security dependency
  updates. Real work that users don't see; keep these short.

Within each project and each section, put new features first, then improvements, fixes and under
the hood, and within those the changes with the widest effect first.

## 6. Write the recap

Draft the recap as Markdown first; it is the content of the page in step 7.

```markdown
# Change recap: <scope> · <start> – <end>

<Two or three sentences: the headline of the period — the one or two changes that matter most, and
anything a reader must act on, such as a half-merged change or a fix that still needs deploying.>

## <Initiative>

### <Project>
<One sentence: where the project stands after this period, when the changes say so.> Lead: <name>.

- `New feature` **<What changed, in plain words>.** <Who it affects and how, in one or two
  sentences.> ([web#1204](<url>), [api#3310](<url>))
  By <names> · reviewed by <names>
- `Fix` **...**

### <Another project in the same initiative>
- ...

## <Project with no initiative>
- ...

## Other changes

### New features
- **...**

### Improvements
### Fixes
### Under the hood

## Who did what
- **<Name>** — <the headlines of the items they built, linking to them>; reviewed <headlines>.

<N> pull requests from <M> people across <repositories>. Left out: <counts of bot, dependency,
translation and cancelled-out revert pull requests>.
```

`N` and `M` count only the pull requests linked in the recap; the left-out ones are counted
separately after them. List the people in **Who did what** alphabetically.

How to write the items:

- Lead with the effect, in the words a customer or a support agent would use: "Customers now see
  when an item is out of stock", not "Handle null inventory values in ProductCard".
- Name the product surface — the mobile app, the admin dashboard, the checkout flow, the public API.
- Keep internal names, class names and ticket keys out of the bold headline; the links carry them.
- Leave out empty sections rather than writing "none".
- Link every item to its pull requests as `<repo>#<number>`.

If nothing was merged in scope, say so plainly in the chat and show the scope and dates you used, so
the user can check whether the scope was wrong. Skip the page in that case.

## 7. Build the HTML page

Always turn the recap into one self-contained HTML page. Write it to
`change-recap-<scope-slug>-<start>-to-<end>.html` in the folder the user names, or the current
working directory if they name none.

Build it so it can be published as an Artifact unchanged: in Claude Code, load the `artifact-design`
skill first and follow its page contract (title, theme tokens with dark mode, allowed script
sources, phone-width layout). Keep all the content of the recap and design it for scanning, not as a
transcript of the Markdown:

- A header with the scope, the dates and the generation date.
- A summary strip: pull requests recapped, people, repositories, projects touched, and the count
  per category.
- The headline paragraph, with anything to act on — half-merged changes, fixes that still need
  deploying, work behind a feature flag — as a callout right under it.
- One section per initiative, and one block per project inside it, in the order of step 5, with
  the project's name linked to the tracker when it came from there. Each item is a card with its
  category badge, bold headline, the explanation, small badges for "behind a flag" or "half
  merged", its pull requests as links labelled `<repo>#<number>`, and a footer with who built and
  reviewed it.
- **Other changes**, split by category.
- **Who did what** last: one row per person, listing the items they built and reviewed as links to
  the cards.
- Filters by category, by person, and by repository when the recap spans more than one.
- The closing line with the left-out counts, and the exact scope used (organisation, repositories,
  paths, ticket prefixes, keywords) in a collapsed section at the bottom, so a reader can rerun it.

Open the page for the user if the harness can show a local HTML file.

## 8. Reply and offer to publish

In the chat, give the path to the page, the headline paragraph and the action items — not the whole
recap again.

Then offer to publish the page as a Claude Artifact, so it gets a private link the user can share
with their team. Publish only when the user says yes; the page stays private until they share it.
On a rerun for the same scope, offer to update the existing Artifact rather than create a new one.
The Artifact tool is Claude Code only; in other harnesses, give the file path and stop there.

If the user wants the recap posted anywhere else, such as a chat channel, show them the final text
first and post it only once they confirm.

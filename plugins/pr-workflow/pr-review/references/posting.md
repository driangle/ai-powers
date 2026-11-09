# Posting the review

Post only when the user asks, and only the findings they name ("post F1 and F3"). "Post the review" with no ids means the **High** and **Medium** findings; Low and Nit findings stay in the printed review unless named.

The findings go on the PR as one **pending** (unsubmitted) review, so the user reads it on GitHub and submits it themselves. Submit, approve or request changes only when the user asks for that too.

Everything posted is read by the PR's author, so write it to them: what is wrong and what to change. Anything meant for the user stays in the conversation, such as the verdict, a recommendation to approve or merge, or the finding ids. The review's state (approved, changes requested) already tells the author the decision.

## The payload

Write the review as a JSON file. Use the path the user or the caller gives; otherwise a new file in the session's scratchpad or temporary directory. It holds:

- `comments`: one per posted finding that has a file and line, with `path`, `line`, `side` and `body`. `line` is the line in the PR's version of the file, with `side: "RIGHT"`; for a finding on a removed line, use the old line number and `side: "LEFT"`.
- `body`: one line counting the findings posted (such as `2 High, 1 Medium; see the comments`), then a short paragraph for each posted finding that has no file and line. When no finding is posted, one line telling the author so, such as `No changes needed from my side.`

Leave out `event`: without it the review stays pending.

## A comment's body

Each comment's `body` takes this Markdown shape, leaving out a section that has nothing to say:

```
**<Severity>** — <the problem in one sentence>

**Why:** <the mechanism in the code, naming the identifiers involved>

**Example:** <a concrete scenario; use a numbered list when it has steps>

**Suggested fix:** <what to change>

**Test:** <the spec case that would lock it in>
```

For a blocker, the first line starts `**<Severity> · 🚫 Blocker** —` instead. Keep each section to one to three sentences, put identifiers in backticks, and use a numbered list instead of a long sentence for any sequence of events.

## Posting it

```bash
gh api repos/{owner}/{repo}/pulls/{number}/reviews -X POST --input <file>
```

GitHub allows one pending review per user on a PR. If one is already there, say so and ask whether to delete it (`gh api repos/{owner}/{repo}/pulls/{number}/reviews/{id} -X DELETE`) or leave the new findings unposted. When GitHub rejects a comment's line (HTTP 422, a line outside the diff), move that finding into `body` and post again.

The response holds the review's `id` and `html_url`: report both, and which findings were posted.

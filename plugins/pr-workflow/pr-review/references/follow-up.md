# Follow-up review

A follow-up review checks whether the author addressed the comments the user already posted, and reviews only what changed since. State comes from GitHub, not the conversation, so it works in a fresh session.

## Fetch the previous review

1. The user's login: `gh api user --jq .login`
2. The user's review threads and reviews in one query:

   ```bash
   gh api graphql -F owner={owner} -F repo={repo} -F number={number} -f query='
   query($owner: String!, $repo: String!, $number: Int!) {
     repository(owner: $owner, name: $repo) {
       pullRequest(number: $number) {
         headRefOid
         reviews(last: 50) { nodes { author { login } state body submittedAt commit { oid } } }
         reviewThreads(first: 100) {
           nodes {
             isResolved isOutdated path line
             comments(first: 50) { nodes { author { login } body createdAt } }
           }
         }
       }
     }
   }'
   ```

   Keep threads whose first comment is by the user, and the user's reviews that have a non-empty body (top-level comments that aren't tied to a line).

3. The last reviewed commit is the `commit.oid` of the user's most recent review. Fetch what changed since:
   `gh api repos/{owner}/{repo}/compare/{last_oid}...{headRefOid}` (use `.files[].patch`).
   If the compare fails or the base is unrelated (a force-push or rebase), fall back to the full `gh pr diff` and say so in the output.
   If `last_oid` equals `headRefOid`, there are no new commits: say so, still assess replies on the previous comments, and skip the new-changes review.

## Assess each previous comment

Read the comment, the author's replies, and the current code at that location. Give each one a status:

- **Addressed** — the code now resolves the concern.
- **Partly addressed** — some of it was fixed; say what is left.
- **Not addressed** — no relevant change.
- **Pushed back** — the author replied instead of changing the code. Quote the gist of the reply and say whether the argument holds.

A resolved or outdated thread is a hint, not proof; check the code. Re-judge each comment's severity and blocker status from its content, using the same rules as a first review.

## Review the new changes

Review only the changes since the last reviewed commit, using the same checks as a first review. Skip issues that a previous comment already covers.

## Ids

Previous comments and new findings share one id space: previous comments get `F1`…`Fn` in thread order, and new findings continue from `Fn+1`. If this conversation already assigned ids to those comments, keep them.

## Output

H2 title with the PR name and "(follow-up)", then the verdict line, then:

- **What changed since last review** — a few lines on the new commits.
- **Previous comments** — a tally (e.g. `4 comments: 3 addressed, 1 not addressed`), then open items first:

  ```
  **F2 · 🚫 Blocker · High · Not addressed** — `src/auth.ts:42`
  Expiry is still compared in seconds against milliseconds.

  **F1 · Addressed** — `src/auth.ts:57`
  ```

  Addressed items get one line; open items keep their blocker mark and severity.
- **New findings** — same format as a first review, or "No new findings".

The verdict counts every open blocker, old or new: `**Verdict: ❌ Request changes** — blocked by F2, F6`.

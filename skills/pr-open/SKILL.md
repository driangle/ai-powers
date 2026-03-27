---
name: pr-open
description: Open a GitHub PR for the current branch. Generates a title and description from the diff, and respects the repo's PULL_REQUEST_TEMPLATE if one exists.
---

1. Determine the base branch (most likely `master` or `main`). Run the following in parallel:
   - `git diff <base> --name-only` and `git diff <base>` to understand changes
   - `git log <base>..HEAD --oneline` to see commit history on this branch
   - `git status -u` to check for uncommitted changes
   - Check for a PR template: look for `.github/PULL_REQUEST_TEMPLATE.md` or `.github/PULL_REQUEST_TEMPLATE/` directory in the repo root

2. If there are uncommitted changes, ask the user whether to commit them first or proceed without them.

3. Check if the branch needs to be pushed to the remote. If so, ask the user to push their changes first and stop. Do NOT push on their behalf.

4. Review all changes (all commits since base, not just the latest) and draft:
   - A short PR title (under 70 characters)
   - A concise description summarizing what changed and why

5. Build the PR body:
   - **If a PR template exists:** Read it. Fill in the description/summary section with the generated content. Preserve all other sections, HTML comments, and placeholders from the template exactly as they are.
   - **If no PR template exists:** Use a simple body with a `## Summary` section containing the description.

6. Create the PR using `gh pr create`. Use a HEREDOC for the body:
   ```
   gh pr create --title "the pr title" --body "$(cat <<'EOF'
   <body content here>
   EOF
   )"
   ```

7. Output the PR URL when done.

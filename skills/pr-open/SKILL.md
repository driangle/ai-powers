---
name: pr-open
description: Open a GitHub PR for the current branch. Generates a title and description from the diff, and respects the repo's PULL_REQUEST_TEMPLATE if one exists.
allowed-tools: Bash, Read, Glob
---

1. Detect the base branch via `git remote show origin | grep 'HEAD branch'`. Run in parallel:
   - `git diff <base> --name-only` and `git diff <base>` to understand changes
   - `git log <base>..HEAD --oneline` to see commit history
   - `git status` to check for uncommitted changes
   - `git log @{u}..HEAD --oneline 2>/dev/null` to check if the branch needs pushing
   - Check for `.github/PULL_REQUEST_TEMPLATE.md` or `.github/PULL_REQUEST_TEMPLATE/` directory

2. If there are uncommitted changes, ask the user whether to commit them first or proceed without them.

3. If the branch needs pushing, push it with `git push -u origin HEAD`.

4. Review all changes (all commits since base) and draft:
   - A short PR title (under 70 characters)
   - A concise description summarizing what changed and why

5. Build the PR body:
   - **If a PR template exists:** Fill in the description/summary section. Preserve all other sections and placeholders from the template.
   - **If no template:** Use a simple body with a `## Summary` section.

6. Create the PR using `gh pr create` with a HEREDOC for the body:
   ```
   gh pr create --title "the pr title" --body "$(cat <<'EOF'
   <body content here>
   EOF
   )"
   ```

7. Output the PR URL when done.

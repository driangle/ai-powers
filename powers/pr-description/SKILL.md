---
name: pr-description
description: Generate a concise PR description based on the changed files and their content. Focus on summarizing the key changes and their impact, rather than providing a detailed line-by-line explanation.
allowed-tools: Bash
---

1. Detect the base branch via `git remote show origin | grep 'HEAD branch'`. Run `git diff <base> --name-only` and `git diff <base>` to understand what changed.

2. Review the changes and write a concise PR description summarizing:
   - What was changed
   - Why it was changed
   - Any important implementation details

3. Wrap code identifiers (function names, class names, filenames, etc.) in backticks.

4. Use Markdown formatting. The output will be shown in a terminal, so ensure it can be copied directly into a GitHub PR description.

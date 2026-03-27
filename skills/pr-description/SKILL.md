---
name: pr-description
description: Generate a concise PR description based on the changed files and their content. Focus on summarizing the key changes and their impact, rather than providing a detailed line-by-line explanation.
---

1. Run \`git diff --name-only\` against the base branch (most likely \`master\`) to identify what has changed.

2. Review the changes and write a concise PR description summarizing:
   - What was changed
   - Why it was changed
   - Any important implementation details

3. When referencing discrete code identifiers such as function names, class names, variable names, filenames, or similar, always wrap them in backticks like this, and escape them twice: \\`identifier_name\\`.

4. The output will be shown in a terminal, so ensure it is properly formatted and fully escaped so it can be copied and pasted directly into a GitHub PR description without requiring edits.

5. Use Markdown formatting. Double escape backticks (\\`), pound signs (\\#), and any other special characters where necessary to avoid rendering issues.
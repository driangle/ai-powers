---
name: pr-description
description: Generate a concise PR description based on the changed files and their content. Focus on summarizing the key changes and their impact, rather than providing a detailed line-by-line explanation.
allowed-tools: Bash
---

1. Detect the base branch via `git remote show origin | grep 'HEAD branch'`. Run in parallel:
   - `git diff <base> --name-only` and `git diff <base>` to understand changes
   - `git log <base>..HEAD --oneline` to see commit history

2. Review all changes (all commits since base) and write a PR description following this exact markdown format:

```markdown
## Summary

<1-3 bullet points summarizing what changed and why>

## Changes

<Grouped list of specific changes. Group by area/concern when there are many changes. Use sub-bullets for details.>
```

### Formatting rules

- Wrap code identifiers (function names, class names, filenames, variable names) in backticks.
- Use bullet points (`-`), not numbered lists.
- Keep bullet points concise — one line each when possible.
- Do NOT use bold, italic, or other inline formatting beyond backticks.
- Output raw markdown directly — do not wrap it in a code fence.

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

<Flat list of 4–7 bullets describing behavior/outcome, not files. One line each.>
```

### Formatting rules

- Wrap code identifiers (function names, class names, filenames, variable names) in backticks.
- Use bullet points (`-`), not numbered lists.
- Keep bullet points concise — one line each when possible.
- Cap Summary at 3 bullets and Changes at ~7 bullets. If you need more, you're narrating instead of summarizing.
- Describe outcomes, not files. Don't list every added file, resolver, mapper, or test case — group them ("Add resolvers X and Y", "Add integration tests covering …").
- Avoid sub-bullets. Use them only when a bullet genuinely has 2+ distinct sub-concerns that a reviewer must see separately.
- Omit mechanical housekeeping (lockfile updates, worklogs, task specs, trivial imports) unless reviewer-relevant. Fold changesets/dep bumps into one line.
- Do NOT use bold, italic, or other inline formatting beyond backticks.
- Wrap the entire output inside a fenced code block (triple backticks with `markdown` language tag) so the terminal displays raw markdown that can be copied directly into a GitHub PR description.

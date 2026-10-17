---
name: disk-cleanup
description: "Free disk space on macOS by clearing regenerable developer and app caches (build caches, Docker, package managers, Xcode, stale node_modules), after a survey and the user's pick. Use when the user asks to clean up, free, or reclaim disk space, says the disk is full, or invokes /disk-cleanup."
allowed-tools: Bash, AskUserQuestion
---

# Disk Cleanup

Survey the disk, show the user what can be reclaimed, and clear only what they choose. Only target things that regenerate on their own or with a reinstall. **Never delete personal files** (Movies, Music, Pictures, Documents, Desktop, Downloads, project sources). Report them as large but leave the decision to the user.

## Step 1: Measure

This skill targets macOS. Record the starting free space. The user's data lives on the Data volume:

```bash
df -h /System/Volumes/Data
```

Then find where the space goes. Run these in parallel, because `du` over a large home folder can take minutes:

```bash
du -sh ~/* ~/.[!.]* 2>/dev/null | sort -rh | head -25
du -sh ~/Library/* ~/Library/Caches/* ~/Library/Developer/* ~/Library/Containers/* 2>/dev/null | sort -rh | head -30
```

## Step 2: Size each reclaimable category

Find the user's project roots (`<root>` below). Pick the large folders from Step 1 that contain git repos (`find ~ -maxdepth 3 -name .git -type d -prune`), and ask the user if it's unclear. Size each category below and skip any tool that isn't installed (`command -v <tool>`).

| Category | How to size it | How to clear it |
|---|---|---|
| Monorepo build caches | `find <root> -type d \( -name .turbo -o -name .nx -o -name .next \) -prune -not -path '*/node_modules/*'` then `du -sk` | `rm -rf` each dir |
| Docker | `docker system df` (Build Cache + reclaimable Images) | `docker system prune -a -f` (never `--volumes`: those hold data) |
| npm cache | `du -sh "$(npm config get cache)"` | `npm cache clean --force` |
| pnpm store | `du -sh "$(pnpm store path)"` | `pnpm store prune` |
| Yarn cache | `du -sh "$(yarn cache dir)"` | `yarn cache clean` |
| pip / uv caches | `du -sh "$(pip cache dir)"`, `du -sh "$(uv cache dir)"` | `pip cache purge`, `uv cache clean` |
| Homebrew | `brew cleanup -n \| tail -1` | `brew cleanup` |
| Xcode | `du -sh ~/Library/Developer/Xcode/DerivedData`, any `DerivedData` inside projects, `xcrun simctl list devices unavailable` | `rm -rf` DerivedData, `xcrun simctl delete unavailable` |
| Old iOS DeviceSupport | `ls ~/Library/Developer/Xcode/iOS\ DeviceSupport` | `rm -rf` versions older than the newest major |
| App caches | `du -sh ~/Library/Caches` | delete its entries, **excluding** names matching `anthropic` or `claude` (a running Claude app uses them) |
| Stale `node_modules` | `node_modules` whose project has no file outside `node_modules`/`.git` modified in 90 days (see below) | `rm -rf` each listed dir |
| Rust `target`, Python `venv` | `find <root> -type d \( -name target -o -name venv -o -name .venv \) -prune` | only in stale projects, same 90-day rule |
| Claude Code worktrees | the app's `get_storage_usage` tool, if available | the app's `clean_up_worktrees` tool (it shows its own approval card) |

To find stale `node_modules`, write the list to a file first and delete from that file. That way the deletion matches exactly what was sized:

```bash
find <root> -type d -name node_modules -prune 2>/dev/null | grep -v '/node_modules/.*/node_modules' | while IFS= read -r d; do
  p=$(dirname "$d")
  [ -z "$(find "$p" -maxdepth 3 -not -path '*/node_modules*' -not -path '*/.git/*' -type f -mtime -90 -print -quit 2>/dev/null)" ] && echo "$d"
done > "$TMPDIR/stale_node_modules.txt"
```

## Step 3: Let the user choose

Present the categories with their sizes in one or two multi-select `AskUserQuestion` prompts, with up to 4 options per question and the biggest first. Each option's description says exactly what goes and its side effect. For example, "next build will be slower", "re-run `npm install` when you return to the project" or "Playwright browsers need reinstalling". Skip categories under ~500 MB.

Delete nothing that the user didn't select.

## Step 4: Clear

Run the selected cleanups. Run independent ones in parallel and use long timeouts. Don't stop when one fails: `rm` on a protected cache entry fails harmlessly, so carry on and note it.

## Step 5: Report

Measure the free space again with the same `df` command as Step 1. Report:

- free space before → after, and the total reclaimed
- a short table of what was cleared and roughly how much each freed
- the side effects the user should expect
- the largest remaining personal folders (untouched) as candidates the user may want to archive to an external drive or cloud storage themselves

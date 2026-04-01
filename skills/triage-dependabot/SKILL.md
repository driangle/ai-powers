---
name: triage-dependabot
description: "Triage Dependabot security alerts: group by package, find high-payoff upgrades and removal candidates, then plan a fix for the one the user chooses."
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion, EnterPlanMode
---

# Dependabot Triage

Find, prioritize, and plan fixes for GitHub Dependabot security vulnerabilities in the current repository. Focus on the upgrades that pay off the most — and look for dependencies that can be removed entirely.

## Instructions

### Step 1: Fetch open Dependabot alerts

Run:

```
gh api repos/{owner}/{repo}/dependabot/alerts --jq '
  [.[] | select(.state == "open")] |
  sort_by(
    if .security_vulnerability.severity == "critical" then 0
    elif .security_vulnerability.severity == "high" then 1
    elif .security_vulnerability.severity == "medium" then 2
    elif .security_vulnerability.severity == "low" then 3
    else 4 end
  )'
```

Derive `{owner}/{repo}` from `gh repo view --json nameWithOwner -q .nameWithOwner`.

If the command fails (e.g., Dependabot alerts are not enabled, or insufficient permissions), tell the user what went wrong and how to fix it.

If there are no open alerts, inform the user and stop.

### Step 2: Group alerts by package and rank

Group all open alerts by their dependency package name. For each package, determine:

- **Alert count** — how many open alerts this single upgrade would resolve
- **Highest severity** — the worst severity among its alerts
- **Versions behind** — how far the current version is from the latest patched version (e.g., 3 major versions behind)

Rank packages by **total payoff**: a package with 4 medium alerts that all resolve with one upgrade is often more valuable than a package with 1 high alert. Use this ranking (alert count x severity weight) to pick the top 3 packages to present.

Display a summary table:

```
## Top Dependabot Upgrade Targets

| # | Package | Alerts | Highest severity | Current → Patched | Versions behind | Resolves |
|---|---------|--------|------------------|--------------------|-----------------|----------|
| 1 | express | 4      | HIGH             | 4.17.1 → 4.19.2   | 2 minor         | GHSA-a, GHSA-b, GHSA-c, GHSA-d |
| 2 | lodash  | 2      | CRITICAL         | 4.17.10 → 4.17.21 | 11 patch        | GHSA-e, GHSA-f |
| 3 | axios   | 1      | HIGH             | 0.21.0 → 1.6.0    | 1 major         | GHSA-g |
```

Include a one-line summary of the most severe vulnerability per package.

Then ask the user: **"Which package would you like to tackle? (1, 2, or 3)"**

### Step 3: Deep-dive the chosen package

Once the user picks one, fetch the full alert details for all alerts associated with that package:

```
gh api repos/{owner}/{repo}/dependabot/alerts/{alert_number}
```

Gather:
- Full description and CVE/GHSA details for each alert
- The vulnerable dependency and its version constraints
- The patched version (if available)
- Which manifest files (package.json, Gemfile, requirements.txt, etc.) reference the dependency
- Whether it is a direct or transitive dependency

Then read the relevant manifest/lock files and **search the codebase for actual usage** of the dependency (imports, requires, function calls). Determine:

1. **How heavily is it used?** — a handful of call sites, or deeply integrated?
2. **Can it be removed?** — if the dependency is only used for something simple (e.g., a single utility function), it may be cheaper to replace it with a small in-project implementation than to keep maintaining the dependency.
3. **Is it still needed at all?** — dead imports or unused dependencies should just be removed.

### Step 4: Enter Plan mode with a fix proposal

Enter Plan mode and propose a fix. Start with the highest-leverage option:

1. **Remove the dependency** (if feasible) — explain what it's used for, show the replacement code or confirm it's unused, and note that this eliminates all current and future alerts for this package.
2. **Upgrade the dependency** (if removal isn't practical):
   - **What to change** — which files need updating (manifests, lock files, application code)
   - **Upgrade path** — the target version and how many alerts this single upgrade resolves
   - **Breaking change assessment** — check the changelog/release notes (via web search if needed) for breaking changes between the current and patched version
   - **Migration steps** — if there are breaking changes, outline the code changes needed
   - **Verification** — commands to run (install, build, test) to confirm the fix works

Wait for the user to approve the plan before making any changes.

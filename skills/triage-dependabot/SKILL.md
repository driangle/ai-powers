---
name: triage-dependabot
description: "Triage Dependabot security alerts: list open vulnerabilities sorted by severity, propose the top 3 to fix, then plan a fix for the one the user chooses."
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion, EnterPlanMode
---

# Dependabot Triage

Find, prioritize, and plan fixes for GitHub Dependabot security vulnerabilities in the current repository.

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

### Step 2: Present the top 3 vulnerabilities

From the sorted list, pick the top 3 alerts (highest severity first). For each, display a summary table:

```
## Top Dependabot Vulnerabilities

| # | Severity | Package | Vulnerable range | Patched version | GHSA |
|---|----------|---------|------------------|-----------------|------|
| 1 | CRITICAL | lodash  | < 4.17.21        | 4.17.21         | GHSA-xxxx-... |
| 2 | HIGH     | axios   | < 1.6.0          | 1.6.0           | GHSA-yyyy-... |
| 3 | MEDIUM   | express | < 4.18.2         | 4.18.2          | GHSA-zzzz-... |
```

Include a one-line summary of each vulnerability's description.

Then ask the user: **"Which vulnerability would you like to fix? (1, 2, or 3)"**

### Step 3: Deep-dive the chosen vulnerability

Once the user picks one, fetch the full alert details:

```
gh api repos/{owner}/{repo}/dependabot/alerts/{alert_number}
```

Gather:
- Full description and CVE/GHSA details
- The vulnerable dependency and its version constraints
- The patched version (if available)
- Which manifest files (package.json, Gemfile, requirements.txt, etc.) reference the dependency
- Whether it is a direct or transitive dependency

Then read the relevant manifest/lock files to understand how the dependency is used.

### Step 4: Enter Plan mode with a fix proposal

Enter Plan mode and propose a fix. The plan should cover:

1. **What to change** — which files need updating (manifests, lock files, application code)
2. **Upgrade path** — the target version and whether it includes breaking changes
3. **Breaking change assessment** — check the changelog/release notes (via web search if needed) for breaking changes between the current and patched version
4. **Migration steps** — if there are breaking changes, outline the code changes needed
5. **Verification** — commands to run (install, build, test) to confirm the fix works

Wait for the user to approve the plan before making any changes.

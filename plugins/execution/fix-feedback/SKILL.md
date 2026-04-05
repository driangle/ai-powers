---
name: fix-feedback
description: "Address feedback about a bug or feature issue using a test-first workflow: reproduce with a failing test, then fix. Use when the user provides feedback, a bug report, or a user-reported issue and wants it verified and fixed."
allowed-tools: Bash, Read, Glob, Grep, Edit, Write, Agent
---

# Fix Feedback

Address user feedback about a bug or feature issue using a test-first approach: first prove the problem exists with a failing test at the appropriate level, then fix it.

## Input

Requires feedback in `$ARGUMENTS` — a bug report, user complaint, or description of unexpected behavior. Examples:

- `/fix-feedback "clicking save twice creates duplicate entries"`
- `/fix-feedback "the CSV export drops rows with unicode characters"`
- `/fix-feedback "timeout option is ignored when retry is enabled"`

## Steps

### Step 1: Understand the feedback

Read `$ARGUMENTS` and identify:
- **What** the reported behavior is
- **Where** in the codebase it likely originates
- **What** the expected behavior should be

Use Glob and Grep to locate the relevant code. Read the files to understand the current implementation.

### Step 2: Find the existing test setup

Locate the project's test framework and existing tests for the affected code:
- Find test files near the relevant source files (e.g., `*.test.ts`, `*_test.go`, `test_*.py`, `*_spec.rb`)
- Identify the test runner, assertion style, and patterns used in the project
- Note how fixtures, mocks, and setup/teardown are handled

Match whatever conventions the project already uses.

### Step 3: Write a failing test

Write a test that **reproduces the reported issue** at the appropriate level (unit, integration, or end-to-end — whichever best captures the problem):
- The test should encode the **expected** (correct) behavior described in the feedback
- It must **fail** against the current code — proving the bug exists
- Keep the test focused: one test, one assertion, targeting the specific issue
- Name the test descriptively so the feedback is obvious from the test name
- Choose the test level based on where the bug lives — a logic error in a pure function warrants a unit test; a broken interaction between components warrants an integration test

### Step 4: Run the test — confirm it fails

Run the new test in isolation. It **must fail**.

- If it **passes**: the feedback may not be reproducible with the current code, or your test doesn't capture the issue correctly. Investigate further — re-read the feedback, check your assumptions, and adjust the test. Do not proceed until you have a genuinely failing test or have confirmed the issue is not reproducible.
- If it **fails**: proceed to the fix.

### Step 5: Fix the issue

Make the minimal change needed to address the feedback:
- Fix the root cause, not just the symptom
- Avoid unrelated changes — keep the diff focused
- Preserve existing behavior for cases not described in the feedback

### Step 6: Run the test — confirm it passes

Run the new test again. It **must pass** now.

If it still fails, revisit your fix and iterate until the test goes green.

### Step 7: Run the full test suite

Run the project's full test suite (or the relevant subset) to check for regressions.

- If other tests break, fix them — your change should not degrade existing behavior
- If the suite was already broken before your change, note which failures are pre-existing

### Step 8: Report

Summarize what you did:
- **Feedback**: one-line restatement of the issue
- **Root cause**: what was wrong and why
- **Test added**: file path and test name
- **Fix**: what you changed
- **Regressions**: none, or list any pre-existing failures

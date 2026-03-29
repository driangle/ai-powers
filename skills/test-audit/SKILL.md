---
name: test-audit
description: "Review the project's test suite for legitimacy: detect tautologies, trivially-passing assertions, mocked-away logic, and other patterns that give false confidence in test coverage. Use when the user wants to verify their tests are meaningful."
---

# Test Audit

Review the project's test suite to ensure tests are legitimate and actually verify meaningful behavior, not just creating an illusion of coverage.

## Instructions

Audit the tests in this project for quality and legitimacy. If `$ARGUMENTS` specifies a path or pattern, scope the audit to those tests only. Otherwise, audit all test files.

### Step 1: Discover test files

Use Glob to find all test files (e.g., `**/*.test.*`, `**/*.spec.*`, `**/test_*.py`, `**/*_test.go`, `**/tests/**`). Identify the test framework(s) in use.

### Step 2: Launch parallel audit agents

Use the **Agent tool** to launch subagents concurrently. Each agent should read test files and report findings with severity levels (critical/high/medium/low).

#### Launch these 4 agents in parallel (single message, 4 Agent tool calls):

**Agent 1: Tautologies & Trivially-Passing Tests** (subagent_type: Explore, thoroughness: very thorough)
```
Audit the test files in this project for tautological and trivially-passing tests. Report findings with severity levels (critical/high/medium/low).

Look for:
- Assertions that compare a value to itself (expect(x).toBe(x), assert x == x)
- Assertions that are always true regardless of code behavior (expect(true).toBe(true), assert 1 == 1)
- Tests that assert on hardcoded values unrelated to the code under test
- Tests that only check that a function "doesn't throw" without verifying its output or effects
- Empty test bodies or tests with no assertions at all
- Assertions on mock return values that were set up in the same test (circular: mock returns X, assert result is X)
- Tests where the expected value is copy-pasted from the implementation rather than independently derived
- Tests that only verify types or shapes but never actual computed values
- `expect(result).toBeDefined()` or `assert result is not None` as the sole assertion for complex operations
- Snapshot tests where the snapshot was accepted without review and tests trivially complex markup

For each finding, report: severity, file:line, the assertion or test in question, why it's a tautology, and what should be tested instead.
```

**Agent 2: Over-Mocking & Stubbed-Away Logic** (subagent_type: Explore, thoroughness: very thorough)
```
Audit the test files in this project for over-mocking and tests that stub away the very logic they claim to test. Report findings with severity levels.

Look for:
- Tests that mock/stub the function or module under test itself (testing the mock, not the code)
- Tests where every dependency is mocked so deeply that no real code path executes
- Mock setups that hardcode return values matching expected assertions (self-fulfilling prophecy)
- Tests that mock database/API calls AND never test the real query/request construction
- Tests that mock time/randomness but never verify behavior across different values
- Spy-only tests that verify a function was called but never check what it did with the result
- Tests where the mock setup is longer than the actual test logic (smell for testing mocks, not code)
- Integration or E2E tests that mock core infrastructure, defeating their purpose

For each finding, report: severity, file:line, description, and what the test should actually verify.
```

**Agent 3: Incomplete & Misleading Coverage** (subagent_type: Explore, thoroughness: very thorough)
```
Audit the test files in this project for incomplete and misleading test coverage. Report findings with severity levels.

Look for:
- Tests that only cover the happy path and ignore error/edge cases
- Tests for trivial getters/setters while complex business logic is untested
- Test names that describe behavior the test doesn't actually verify
- Tests that call the function but don't assert on the meaningful parts of its result
- Tests that verify logging or console output instead of actual behavior
- Async tests missing await (may pass before assertions run)
- Tests with conditional logic (if/else) that may skip assertions on some runs
- Try/catch in tests that swallow errors and pass silently
- Tests that use `any` or overly loose matchers that would pass for wrong results
- Tests for deleted or renamed functionality that no longer exercise real code paths

For each finding, report: severity, file:line, description, and what's missing.
```

**Agent 4: Test Design & Structural Issues** (subagent_type: Explore, thoroughness: medium)
```
Audit the test files in this project for structural issues that undermine test reliability. Report findings with severity levels.

Look for:
- Tests that depend on execution order or shared mutable state between tests
- Tests that depend on external services, network, or filesystem without proper isolation
- Flaky patterns: time-dependent assertions, race conditions, non-deterministic ordering
- beforeAll/setUp that does too much, hiding test dependencies
- Tests that pass when run alone but fail (or vice versa) in suite context
- Disabled/skipped tests (xit, xdescribe, @skip, .skip) that may hide regressions
- Duplicated test logic across files that should be shared fixtures
- Tests without meaningful names (test1, test2, "it works", "should work")

For each finding, report: severity, file:line, description, and recommendation.
```

### Step 3: Compile the audit report

After all agents complete, compile findings into a structured report:

```markdown
# Test Audit Report

## Summary
- Test files scanned: N
- Total findings: N
- Critical: N | High: N | Medium: N | Low: N

## Verdict
[One-paragraph overall assessment: are the tests providing genuine confidence, or is coverage largely illusory?]

## 1. Tautologies & Trivially-Passing Tests
[Agent 1 findings, sorted by severity]

## 2. Over-Mocking & Stubbed-Away Logic
[Agent 2 findings, sorted by severity]

## 3. Incomplete & Misleading Coverage
[Agent 3 findings, sorted by severity]

## 4. Test Design & Structural Issues
[Agent 4 findings, sorted by severity]

## Top Recommendations
[5-10 highest-impact actions to improve test legitimacy, ordered by value]
```

### Step 4: Present findings

- Present the compiled report to the user
- Highlight critical and high severity findings first
- For each critical finding, include a concrete example of what a real test should look like
- Offer to fix the worst offenders or create task files for remediation

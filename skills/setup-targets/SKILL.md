---
name: setup-targets
description: "Set up standardized build targets (compile, lint, test, build) for every project in a monorepo, top-level check/check-lite targets, and a pre-commit hook for check-lite. Use when the user wants to add Makefile targets, set up CI-ready build commands, or standardize project build structure."
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent
---

# Setup Targets

Set up standardized build targets for every project in the repo plus top-level aggregation targets and a pre-commit hook.

## Instructions

Analyze the repository and set up build targets as described below. Use `$ARGUMENTS` for any user-specified customization (e.g., which projects to include, build tool preferences, or target overrides).

### Step 1: Discover projects

Identify every project in the repository:

1. **Find project roots** — look for `package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`, `build.gradle`, `pom.xml`, `*.csproj`, or similar build manifests
2. **Determine each project's language and toolchain** — this informs which commands to use for each target
3. **Check for existing Makefiles** — note any existing targets to avoid clobbering

Present a summary to the user:

```markdown
## Discovered Projects

| Project | Path | Language | Toolchain | Has Makefile |
|---------|------|----------|-----------|--------------|
| ... | ... | ... | ... | ... |
```

Wait for user confirmation before proceeding.

### Step 2: Define per-project targets

Each project MUST have these Makefile targets:

- **`compile`** — Type-check or compile the project (no output artifacts required)
- **`lint`** — Run the project's linter(s)
- **`test`** — Run the project's test suite
- **`build`** — Produce deployable/publishable artifacts (only if applicable — skip for libraries with no build step)

Use the appropriate commands for each project's toolchain. Common mappings:

| Toolchain | compile | lint | test | build |
|-----------|---------|------|------|-------|
| TypeScript (tsc + eslint) | `tsc --noEmit` | `eslint .` | `jest` or `vitest` | `tsc` or bundler |
| Rust (cargo) | `cargo check` | `cargo clippy -- -D warnings` | `cargo test` | `cargo build --release` |
| Go | `go build ./...` | `golangci-lint run` | `go test ./...` | `go build -o bin/` |
| Python (ruff/pytest) | `python -m py_compile` or `mypy .` | `ruff check .` | `pytest` | — |
| Java (gradle) | `./gradlew compileJava` | `./gradlew checkstyleMain` | `./gradlew test` | `./gradlew build` |
| Java (maven) | `mvn compile` | `mvn checkstyle:check` | `mvn test` | `mvn package` |

Adapt these based on what's actually configured in each project (check existing scripts in `package.json`, `Cargo.toml`, etc.). Prefer the project's existing commands over generic defaults.

For each project, create or update a `Makefile` with:

```makefile
.PHONY: compile lint test build

compile:
	<command>

lint:
	<command>

test:
	<command>

# Only include if the project produces build artifacts
build:
	<command>
```

### Step 3: Create top-level targets

Create or update the **root Makefile** with two aggregation targets:

**`make check`** — Runs ALL targets (compile, lint, test, build) across every project:

```makefile
.PHONY: check check-lite

# Full check: compile + lint + test + build for all projects
check:
	@echo "Running full check across all projects..."
	$(MAKE) -C path/to/project1 compile
	$(MAKE) -C path/to/project1 lint
	$(MAKE) -C path/to/project1 test
	$(MAKE) -C path/to/project1 build
	# ... repeat for each project
	@echo "All checks passed."
```

**`make check-lite`** — Runs only the fast targets (compile, lint) across every project:

```makefile
# Lite check: compile + lint only (used by pre-commit hook)
check-lite:
	@echo "Running lite check across all projects..."
	$(MAKE) -C path/to/project1 compile
	$(MAKE) -C path/to/project1 lint
	# ... repeat for each project
	@echo "Lite checks passed."
```

Guidelines:
- Fail fast — if any target fails, the whole check should fail
- Print clear output so it's obvious which project/target failed
- If the repo uses a task runner (e.g., `nx`, `turbo`, `lerna`), use it for orchestration instead of raw `$(MAKE) -C` calls
- Include a comment at the top of the root Makefile listing all projects and their available targets

### Step 4: Set up the pre-commit hook

Install `make check-lite` as a git pre-commit hook:

1. **Create `.githooks/pre-commit`** (or update it if it exists):

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "Running pre-commit checks (make check-lite)..."
make check-lite

if [ $? -ne 0 ]; then
  echo "Pre-commit checks failed. Fix the issues above and try again."
  exit 1
fi
```

2. **Make it executable**: `chmod +x .githooks/pre-commit`

3. **Configure git to use the hooks directory**:
   - If a `.githooks` directory already exists, use it
   - Otherwise, create `.githooks/` and run `git config core.hooksPath .githooks`
   - If the project uses `husky` or `lefthook`, integrate with those instead of raw git hooks

### Step 5: Update CI release workflow

If the repository has a release or CI workflow (e.g., `.github/workflows/release.yml`, `.github/workflows/ci.yml`), update it to run the same checks as `make check` but as **separate parallel jobs** for visibility and parallelism.

1. **Find existing workflows** — check `.github/workflows/` for release or CI workflow files
2. **Create or update the workflow** to include parallel jobs for each project/target combination

The CI jobs should mirror `make check` exactly — same scope, broken out into individual jobs:

```yaml
jobs:
  # One job per project per target, all running in parallel
  project1-compile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make -C path/to/project1 compile

  project1-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make -C path/to/project1 lint

  project1-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make -C path/to/project1 test

  project1-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make -C path/to/project1 build

  # ... repeat for each project
```

Guidelines:
- Each job should be independent so they run in parallel
- Include appropriate setup steps (language toolchain installation, dependency caching, etc.)
- Add a final `check-all` job that `needs:` all other jobs — this serves as the single required status check for branch protection
- If no CI workflow exists, create `.github/workflows/ci.yml` triggered on `push` and `pull_request` to the main branch
- Match existing workflow conventions (runner OS, caching strategy, etc.) if workflows already exist

### Step 6: Verify

1. Run `make check-lite` from the repo root to confirm it works
2. Run `make check` from the repo root to confirm all targets work
3. Verify the pre-commit hook is installed: `git config core.hooksPath`
4. If CI was updated, validate the workflow syntax: `actionlint .github/workflows/ci.yml` (if available) or manually review the YAML

Present a summary of everything that was set up:

```markdown
## Setup Complete

### Per-project targets
| Project | compile | lint | test | build |
|---------|---------|------|------|-------|
| ... | <cmd> | <cmd> | <cmd> | <cmd> |

### Top-level targets
- `make check` — runs compile, lint, test, build for all projects
- `make check-lite` — runs compile, lint for all projects

### Pre-commit hook
- Installed at `.githooks/pre-commit`
- Runs `make check-lite` before every commit
- Skip with `git commit --no-verify` (use sparingly)

### CI workflow
- Each project/target runs as a separate parallel job
- Final `check-all` job gates on all individual jobs
```

---
name: setup-targets
description: "Bootstrap a project's checks to standard conventions: per-project build targets (compile, lint, format-check, test, build), enforced lint standards (max 200 lines per file, max 50 lines per function, layered import rules), top-level check/check-lite targets, a pre-commit hook for check-lite, and CI running check. Use when the user wants to add Makefile targets, set up CI-ready build commands, standardize project checks or lint rules, or bootstrap a new/existing repo to their check conventions."
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent
---

# Setup Targets

Set up standardized build targets and lint standards for every project in the repo, plus top-level aggregation targets, a pre-commit hook, and CI.

The conventions this skill enforces:

- Every project has `compile`, `lint`, `format-check`, `test` (and `build` where applicable) targets
- Every project's linter enforces: **max 200 lines per file**, **max 50 lines per function**, and **layered import rules**
- Root `make check-lite` = compile + lint + format-check for all projects → runs in the pre-commit hook
- Root `make check` = check-lite + tests (+ build) for all projects → runs in CI

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
- **`format-check`** — Verify formatting without modifying files (pair with a `format` target that fixes)
- **`test`** — Run the project's test suite
- **`build`** — Produce deployable/publishable artifacts (only if applicable — skip for libraries with no build step)

Use the appropriate commands for each project's toolchain. Common mappings:

| Toolchain | compile | lint | format-check | test | build |
|-----------|---------|------|--------------|------|-------|
| TypeScript (tsc + eslint) | `tsc --noEmit` | `eslint .` | `prettier --check .` | `jest` or `vitest` | `tsc` or bundler |
| Rust (cargo) | `cargo check` | `cargo clippy -- -D warnings` | `cargo fmt --check` | `cargo test` | `cargo build --release` |
| Go | `go build ./...` | `golangci-lint run` | `test -z "$$(gofmt -l .)"` | `go test ./...` | `go build -o bin/` |
| Python (ruff/pytest) | `python -m py_compile` or `mypy .` | `ruff check .` | `ruff format --check .` | `pytest` | — |
| Java (gradle) | `./gradlew compileJava` | `./gradlew checkstyleMain` | `./gradlew spotlessCheck` | `./gradlew test` | `./gradlew build` |
| Java (maven) | `mvn compile` | `mvn checkstyle:check` | `mvn spotless:check` | `mvn test` | `mvn package` |

Adapt these based on what's actually configured in each project (check existing scripts in `package.json`, `Cargo.toml`, etc.). Prefer the project's existing commands over generic defaults. If a project has no formatter configured, set one up using the toolchain's standard choice (prettier/biome, cargo fmt, gofmt, ruff format, spotless).

For each project, create or update a `Makefile` with:

```makefile
.PHONY: compile lint format-check test build

compile:
	<command>

lint:
	<command>

format-check:
	<command>

test:
	<command>

# Only include if the project produces build artifacts
build:
	<command>
```

### Step 3: Enforce lint standards

Every app/package must enforce, at minimum, these three lint rules. They exist to keep files scannable, functions focused, and architecture boundaries explicit — configure them as **errors**, not warnings, so they actually gate commits and CI.

1. **Max 200 lines per file**
2. **Max 50 lines per function**
3. **Layered import rules** — lower layers must not import from higher layers

Configure them with the project's existing linter where possible. Common mappings:

| Toolchain | max lines/file | max lines/function | layered imports |
|-----------|----------------|--------------------|-----------------|
| ESLint | `max-lines: ["error", {"max": 200, "skipBlankLines": true, "skipComments": true}]` | `max-lines-per-function: ["error", {"max": 50, "skipBlankLines": true, "skipComments": true}]` | `import/no-restricted-paths` (zones) or `eslint-plugin-boundaries` |
| Python | Pylint `max-module-lines=200`, or fallback script | Ruff `PLR0915` (statement count) or `flake8-functions` `CFQ001` | `import-linter` layers contract |
| Go (golangci-lint) | fallback script | `funlen` with `lines: 50` | `depguard` rules |
| Rust (clippy) | fallback script | `clippy::too_many_lines` + `too-many-lines-threshold = 50` in `clippy.toml` | module visibility (`pub(crate)`) + `cargo-deny`/workspace deps between crates |
| Java (checkstyle) | `FileLength` with `max=200` | `MethodLength` with `max=50` | ArchUnit test or `ImportControl` |

**Fallback script** — when the toolchain has no native rule (e.g., file length in Go/Rust), add a small check to the project's `lint` target instead of skipping the rule:

```makefile
lint:
	<linter command>
	@awk 'END { if (NR > 200) { print FILENAME ": " NR " lines (max 200)"; exit 1 } }' $$(git ls-files '*.go') || exit 1
```

(Adapt per toolchain — the point is that every rule is enforced somehow, not that this exact snippet is used.)

**Defining the layers**: import rules need a layer model. Infer one from the existing directory structure (e.g., `ui`/`routes` → `services`/`domain` → `db`/`infra` → `shared`/`utils`, where each layer may only import from layers below it, and packages in a monorepo may only depend on packages beneath them). Present the proposed layer graph to the user for confirmation before wiring it into lint config — this is an architectural decision, not a mechanical one.

**Existing violations**: enabling these rules on an established codebase will likely produce violations. Don't silently weaken the rules and don't auto-refactor. Run the linter, report the violation count per project, and ask the user whether to (a) fix violations now, (b) grandfather existing files via per-file overrides/baseline while enforcing for new code, or (c) raise the thresholds. Default recommendation: (b).

### Step 4: Create top-level targets

Create or update the **root Makefile** with two aggregation targets:

**`make check-lite`** — Runs the fast targets (compile, lint, format-check) across every project:

```makefile
.PHONY: check check-lite

# Lite check: compile + lint + format-check (used by pre-commit hook)
check-lite:
	@echo "Running lite check across all projects..."
	$(MAKE) -C path/to/project1 compile
	$(MAKE) -C path/to/project1 lint
	$(MAKE) -C path/to/project1 format-check
	# ... repeat for each project
	@echo "Lite checks passed."
```

**`make check`** — Runs check-lite plus tests (and build where applicable) across every project:

```makefile
# Full check: everything in check-lite + test + build (used by CI)
check: check-lite
	@echo "Running tests and builds across all projects..."
	$(MAKE) -C path/to/project1 test
	$(MAKE) -C path/to/project1 build
	# ... repeat for each project
	@echo "All checks passed."
```

Guidelines:
- Fail fast — if any target fails, the whole check should fail
- Print clear output so it's obvious which project/target failed
- If the repo uses a task runner (e.g., `nx`, `turbo`, `lerna`), use it for orchestration instead of raw `$(MAKE) -C` calls
- Include a comment at the top of the root Makefile listing all projects and their available targets

### Step 5: Set up the pre-commit hook

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

### Step 6: Update CI release workflow

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

  project1-format-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make -C path/to/project1 format-check

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

### Step 7: Verify

1. Run `make check-lite` from the repo root to confirm it works
2. Run `make check` from the repo root to confirm all targets work
3. Sanity-check a lint rule actually fires: temporarily add a >50-line function (or >200-line file) to one project, confirm `lint` fails, then revert
4. Verify the pre-commit hook is installed: `git config core.hooksPath`
5. If CI was updated, validate the workflow syntax: `actionlint .github/workflows/ci.yml` (if available) or manually review the YAML

Present a summary of everything that was set up:

```markdown
## Setup Complete

### Per-project targets
| Project | compile | lint | format-check | test | build |
|---------|---------|------|--------------|------|-------|
| ... | <cmd> | <cmd> | <cmd> | <cmd> | <cmd> |

### Lint standards
| Project | max 200 lines/file | max 50 lines/function | layered imports |
|---------|--------------------|-----------------------|-----------------|
| ... | <rule or script> | <rule or script> | <rule + layer graph> |

### Top-level targets
- `make check-lite` — compile, lint, format-check for all projects
- `make check` — check-lite + test + build for all projects

### Pre-commit hook
- Installed at `.githooks/pre-commit`
- Runs `make check-lite` before every commit
- Skip with `git commit --no-verify` (use sparingly)

### CI workflow
- Runs the full `check` scope: each project/target as a separate parallel job
- Final `check-all` job gates on all individual jobs
```

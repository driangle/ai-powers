---
name: refactor
description: "Perform structured refactoring operations: extract module, split file, inline abstraction, rename symbol across codebase, simplify complex code, or reduce coupling. Use when the user wants to refactor code, extract a module, split a large file, or reorganize code structure."
---

# Refactor

Perform structured refactoring operations guided by user intent. Supports common refactoring patterns across any language.

## Instructions

Perform the refactoring described in `$ARGUMENTS`. If no specific operation is given, analyze the target code and suggest the most impactful refactoring.

### Step 1: Understand the target

Before making any changes, gather context:

1. **Read the target code** — the file, module, or symbol the user wants to refactor
2. **Identify the refactoring type** from `$ARGUMENTS` (or infer it):
   - **extract** — Pull code out into a new module/file/function/class
   - **split** — Break a large file into multiple focused files
   - **inline** — Remove an unnecessary abstraction by inlining its contents
   - **rename** — Rename a symbol across the entire codebase
   - **simplify** — Reduce complexity (flatten nesting, remove dead branches, simplify control flow)
   - **decouple** — Reduce coupling between modules (extract interfaces, inject dependencies)
   - **reorganize** — Move files/modules to a better location in the project structure
3. **Map the blast radius** — find all files that import, reference, or depend on the target code

### Step 2: Plan the refactoring

Present a brief plan to the user before executing:

```markdown
## Refactoring Plan

**Type:** [extract | split | inline | rename | simplify | decouple | reorganize]
**Target:** [file or symbol being refactored]

### Changes
- [ ] [Description of each change, in order]

### Files affected
- [List every file that will be modified]

### Risks
- [Any behavioral changes, import path changes, or public API impacts]
```

Wait for user confirmation before proceeding. If the refactoring is trivial (single-file, no public API change), proceed directly.

### Step 3: Execute the refactoring

Apply changes methodically:

1. **Make structural changes first** — create new files, move code
2. **Update all references** — imports, re-exports, barrel files, config entries
3. **Clean up the source** — remove extracted code from the original location, remove unused imports
4. **Preserve behavior** — do not change logic, types, or public interfaces unless explicitly asked

#### Guidelines per refactoring type

**Extract:**
- Give the new module a clear, descriptive name
- Define a minimal public interface — only export what the original callers need
- Move related types, constants, and helpers together with the extracted code
- Update barrel/index files if the project uses them

**Split:**
- Identify natural seams — group by feature, responsibility, or domain concept
- Each resulting file should have one clear responsibility
- Create an index/barrel file if the original was imported by many consumers
- Aim for files that are scannable in a minute or two

**Inline:**
- Verify the abstraction is used in only a few places (or adds no value despite wide use)
- Replace each call site with the inlined implementation
- Remove the now-empty module and clean up imports
- Simplify the inlined code in context if it was over-generalized

**Rename:**
- Use the Agent tool (subagent_type: Explore) to find ALL references across the codebase — source code, tests, config, docs, comments, strings
- Apply the rename in all locations
- Check for string-based references (e.g., dynamic imports, reflection, serialization keys) that grep might miss — flag these to the user

**Simplify:**
- Flatten deeply nested conditionals (early returns, guard clauses)
- Replace complex logic with clearer alternatives
- Remove unnecessary abstractions or indirection
- Reduce function length by extracting well-named helpers only if they represent distinct concepts

**Decouple:**
- Identify the coupling (direct imports, shared mutable state, circular dependencies)
- Introduce interfaces or dependency injection where appropriate
- Avoid over-engineering — only add abstraction if it reduces coupling meaningfully

**Reorganize:**
- Move files to their new locations
- Update ALL import paths across the codebase
- Update any path references in config files, build scripts, or documentation

### Step 4: Verify

After applying changes:

1. Search for broken references — any remaining imports of old paths or old symbol names
2. Check for circular dependencies introduced by the refactoring
3. List all files modified for the user to review
4. If tests exist, suggest running them to verify behavior is preserved

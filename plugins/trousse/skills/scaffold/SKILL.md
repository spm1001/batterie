---
name: scaffold
description: Orchestrates new repo creation — required before setting up any batterie Python package. 5-step workflow (interview, plan, init script, CLAUDE.md fill-in, conformance validation) ensures every repo starts with hatchling, src layout, bon, and working tests. Handles greenfield, adopt, and extract modes. Triggers on 'create a repo', 'new project', 'scaffold', 'init repo', 'set up a new package', 'make this a proper repo'. (user)
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion]
---

# Scaffold

Creates well-formed batterie-de-savoir Python repos from a checklist derived from building 10+ repos. Every new repo starts at the same baseline — git, hatchling, src layout, tests, CLAUDE.md, bon, GitHub remote.

**Iron Law: Structure is deterministic. Meaning is not.** The init script creates the skeleton; you fill in the CLAUDE.md content that makes the repo navigable.

## When to Use

- Creating a new Python package from scratch
- Promoting scratch/noodling code into a proper repo
- Extracting a module from an existing repo into its own package
- `/close` suggests this when detecting code in a non-repo directory

## Boundaries

- Python repos only (TypeScript is a future extension)
- Does not create plugin structure (`.claude-plugin/`, `skills/`) — that's a different concern
- Does not handle monorepo setups

## Workflow

### Step 1: Interview

Determine the mode and gather inputs.

**Ask the user:**
1. What's the project name? (kebab-case, becomes the repo name)
2. One-line description?
3. What's the bon prefix? (3-4 lowercase letters)

**Detect the mode:**
- **Greenfield** — target directory is empty or doesn't exist
- **Adopt** — target directory has code but no `.git/`
- **Extract** — user mentions pulling code from another repo

For **adopt**, list existing files and confirm they'll be preserved (moved into `src/<pkg>/`).
For **extract**, identify the source module and confirm what's moving.

### Step 2: Plan

Show the user what will be created:

```
Scaffold plan for <name>:
  Mode: greenfield / adopt / extract
  Package: src/<pkg>/
  Bon prefix: <prefix>
  GitHub: spm1001/<name> (public)

  Files to create:
    pyproject.toml          — hatchling, src layout, pytest config
    src/<pkg>/__init__.py   — importlib.metadata version
    .gitignore              — Python standard
    tests/__init__.py       — empty
    tests/conftest.py       — stub
    CLAUDE.md               — [TODO] sections for you to fill
    .bon/                   — work tracker
    .bon/understanding.md   — seed

  [adopt only] Existing files to relocate:
    <list>
```

Confirm with user before proceeding.

### Step 3: Execute

**Greenfield:**
```bash
uv run --script ${CLAUDE_SKILL_DIR}/scripts/init_repo.py \
  --name <name> --prefix <prefix> --description "<desc>"
```

**Adopt:**
1. Move existing code into `src/<pkg>/` (preserve structure)
2. Run `init_repo.py` with `--dir` pointing to the working directory
   - The script will warn about non-empty directory — that's expected
3. Manually adjust if the script created files that conflict with existing ones

**Extract:**
1. Create target directory
2. Copy source module into `src/<pkg>/`
3. Run `init_repo.py`
4. Update source repo to remove extracted code and add dependency

### Step 4: Fill CLAUDE.md

The init script leaves `[TODO]` markers. Replace each one with project-specific content:

**Module Map** — list every module under `src/<pkg>/` with a one-line role description. Use a table:
```markdown
| Module | Role |
|--------|------|
| `parsing` | JSONL loading, entry type classification |
| `content` | System tag stripping, assistant content extraction |
```

**Key Conventions** — document the things a future Claude needs to know:
- What dependencies are allowed (stdlib only? specific packages?)
- What patterns to follow (re-exports from `__init__.py`?)
- What NOT to "fix" (deliberate quirks)
- Quick commands beyond the standard ones

For adopt/extract mode, also note the origin of the code and any context about why it was extracted.

### Step 5: Validate

```bash
uv run --script ${CLAUDE_SKILL_DIR}/scripts/validate_repo.py
```

Review the report. Fix any FAIL items. Re-run until all checks pass.

If `validate_repo.py` doesn't exist yet, manually verify:
- [ ] Git repo on `main` branch (not detached HEAD)
- [ ] `.gitignore` present with Python patterns
- [ ] `pyproject.toml`: hatchling backend, src layout, `[dependency-groups]` dev, pytest config
- [ ] `src/<pkg>/__init__.py` with `__version__` via `importlib.metadata`
- [ ] `tests/` with `conftest.py`
- [ ] `CLAUDE.md` present, no remaining `[TODO]` markers
- [ ] `.bon/` initialized with correct prefix
- [ ] GitHub remote configured and pushed

## The Checklist

Derived from cross-repo survey of 10 batterie repos (April 2026) and every mistake made building deglacer:

| Item | Why |
|------|-----|
| `git init -b main` | Never detached HEAD |
| `.gitignore` | Python bytecode, build artifacts, venv |
| `pyproject.toml` with hatchling | Single version source, src layout |
| `[dependency-groups] dev` | Separate dev deps from runtime |
| `[tool.pytest.ini_options]` | `pythonpath = ["src"]` avoids import errors |
| `src/<pkg>/__init__.py` | `importlib.metadata` version — no hardcoded version |
| `tests/__init__.py` + `conftest.py` | Test infrastructure ready from day one |
| `CLAUDE.md` | Orientation, quick commands, module map, conventions |
| `bon init --prefix` | Work tracker from the start |
| `.bon/understanding.md` | Knowledge accumulation seed |
| `gh repo create` | HTTPS remote, ready to push |

## Common Mistakes

| Mistake | What Happens | Better |
|---------|-------------|--------|
| Hardcoded version in pyproject.toml | Dual-maintenance drift | `importlib.metadata` pattern |
| Missing `pythonpath = ["src"]` in pytest config | Import errors in tests | Always include it |
| No `.gitignore` | `__pycache__` committed | Create before first commit |
| `setuptools` instead of `hatchling` | Inconsistent with suite | Hatchling everywhere |
| Flat layout instead of `src/` | Import confusion in tests | Always `src/<pkg>/` |
| Skipping bon init | No work tracker | Init with prefix immediately |
| CLAUDE.md with just the name | Useless orientation | Fill in module map and conventions |

## Integration

- **Bon:** Every scaffolded repo gets bon initialized. Actions filed here continue in the new repo.
- **Skill-forge:** If the new repo will have skills, use skill-forge after scaffold completes.
- **/close:** Can suggest scaffold when detecting code in a non-repo directory (bds-tipuji).

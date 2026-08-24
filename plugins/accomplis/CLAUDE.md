# CLAUDE.md

Instructions for Claude when working in this repository.

## What This Is

accomplis is a Python CLI for Todoist with GTD coaching. Two parts:
- **CLI** (`accomplis/`) — MCP-free Todoist API access, installed via `uv tool install` from the source repo (`~/repos/spm1001/accomplis`, else `git+https`)
- **Skill** (`SKILL.md` + `references/`) — GTD semantics and coaching

## Versioning & releasing (suite-managed)

accomplis ships as part of the **Batterie de Savoir** suite, which carries **one suite-wide version**. So:

- **Do NOT hand-bump `.claude-plugin/plugin.json` to release.** This repo's own `plugin.json` version is **local-dev-only** — the assembler stamps every published plugin to the suite version, overwriting it.
- **Release via `/batterie:publish`** from this working tree — it bumps the suite version centrally and ships the change (a 2-repo push: this repo + the central suite bump). Never hand-run the assemble.
- **A `CLAUDE.md` / `instructions.md` / `skills/` / `hooks/` edit here is vendored content** — it must ride a suite bump (a publish) to actually ship, or the assembler quarantines the plugin. `docs/` / `.bon/` edits are free.
- **`accomplis --version` is separate** — it reads *the suite release that last changed this CLI* (publish.py lazy-stamps only the repo it publishes), so a CLI number **below** the current suite number is expected, not drift.

Full picture: `spm1001/batterie-de-savoir` → `CLAUDE.md` "Versioning convention" + `.bon/understanding.md`.

## Evals

`evals/coaching/` measures the coaching skill against blank-slate Claudes — smevals harness, fixture-shim Todoist, bare-vs-skill configs across models; its README carries design, first-campaign results and caveats. Like `docs/`, `evals/` is **not vendored**: edits ship without a suite bump. Run artefacts (`runs*/`) are gitignored and machine-local.

## Quick Commands

```bash
accomplis doctor          # Check setup + deps + auth + network
accomplis auth --status   # Check auth
accomplis projects        # List projects
accomplis version         # Show version
```

## Code Conventions

- Python 3.11+ (`requires-python` in pyproject.toml is the enforcement point)
- Keep dependencies minimal (see pyproject.toml)
- Error messages go to stderr, data to stdout
- JSON output for machine consumption
- Exit 0 on success, 1 on failure

## Package Structure

```
src/accomplis/
├── cli.py          # Main CLI entry point (accomplis command)
├── common.py       # Shared utilities (API client, pagination, resolution)
├── auth.py         # Token-based authentication
├── token_store.py  # Portable secrets management (env, keychain, file)
├── flatten.py      # Subtask flattening tool (accomplis-flatten command)
└── _invlog.py      # Vendored estate invocation-log shim — every run of either
                    # console script appends one caller-stamped JSONL line to
                    # ~/.local/share/accomplis[-flatten]/invocations.jsonl.
                    # Canonical copy + conformance test: spm1001/harness-ergonomics.
                    # Never edit here; re-vendor from canonical. auth --token is
                    # REDACTED before logging — keep it that way (erg-tebapi).
```

Entry points defined in `pyproject.toml`:
- `accomplis` → `accomplis.cli:main`
- `accomplis-flatten` → `accomplis.flatten:main`

Install: `uv tool install ~/repos/spm1001/accomplis` (else `uv tool install 'accomplis @ git+https://github.com/spm1001/accomplis'`)
Reinstall after changes: `uv tool install --force --reinstall --no-cache ~/repos/spm1001/accomplis`

## Working with Bon

This repo uses `bon` for work tracking:

```bash
bon list              # See all work
bon list --ready      # Find available work
bon show <id>         # View item details
```

## README skill table is generated

The Skills table in README.md (between `GENERATED:SKILLS` markers) is rendered from
`skills/*/SKILL.md` frontmatter — never hand-edit it. After adding, removing or renaming
a skill: `uv run --script ../batterie-de-savoir/scripts/render-skills.py .` from the repo
root. CI re-checks it on every push (fetching the canonical script from batterie-de-savoir
raw main), so a stale table fails the build. If a table one-liner reads badly, fix the
SKILL.md description (skill-forge), not the table.

**Notes rooms:** `~/notes/practices/GTD/` (the canon) and `~/notes/practices/self-management/` (Sameer's applied system) — the method this tool executes. (bon-jezahi, 2026-08-16)

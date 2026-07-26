# CLAUDE.md

Instructions for Claude when working in this repository.

## What This Is

todoist-gtd is a Python CLI for Todoist with GTD coaching. Two parts:
- **CLI** (`todoist_gtd/`) — MCP-free Todoist API access, installed via `uv tool install` from the source repo (`~/repos/spm1001/todoist-gtd`, else `git+https`)
- **Skill** (`SKILL.md` + `references/`) — GTD semantics and coaching

## Versioning & releasing (suite-managed)

todoist-gtd ships as part of the **Batterie de Savoir** suite, which carries **one suite-wide version**. So:

- **Do NOT hand-bump `.claude-plugin/plugin.json` to release.** This repo's own `plugin.json` version is **local-dev-only** — the assembler stamps every published plugin to the suite version, overwriting it.
- **Release via `/batterie:publish`** from this working tree — it bumps the suite version centrally and ships the change (a 2-repo push: this repo + the central suite bump). Never hand-run the assemble.
- **A `CLAUDE.md` / `instructions.md` / `skills/` / `hooks/` edit here is vendored content** — it must ride a suite bump (a publish) to actually ship, or the assembler quarantines the plugin. `docs/` / `.bon/` edits are free.
- **`todoist --version` is separate** — it reads *the suite release that last changed this CLI* (publish.py lazy-stamps only the repo it publishes), so a CLI number **below** the current suite number is expected, not drift.

Full picture: `spm1001/batterie-de-savoir` → `CLAUDE.md` "Versioning convention" + `.bon/understanding.md`.

## Quick Commands

```bash
todoist doctor          # Check setup
todoist auth --status   # Check auth
todoist projects        # List projects
todoist version         # Show version
todoist doctor          # Check setup + deps + auth + network
```

## Code Conventions

- Python 3.9+, no type stubs required
- Keep dependencies minimal (see pyproject.toml)
- Error messages go to stderr, data to stdout
- JSON output for machine consumption
- Exit 0 on success, 1 on failure

## Package Structure

```
src/todoist_gtd/
├── cli.py          # Main CLI entry point (todoist command)
├── common.py       # Shared utilities (API client, pagination, resolution)
├── auth.py         # Token-based authentication
├── token_store.py  # Portable secrets management (env, keychain, file)
└── flatten.py      # Subtask flattening tool (todoist-flatten command)
```

Entry points defined in `pyproject.toml`:
- `todoist` → `todoist_gtd.cli:main`
- `todoist-flatten` → `todoist_gtd.flatten:main`

Install: `uv tool install ~/repos/spm1001/todoist-gtd` (else `uv tool install 'todoist-gtd @ git+https://github.com/spm1001/todoist-gtd'`)
Reinstall after changes: `uv tool install --force --reinstall --no-cache ~/repos/spm1001/todoist-gtd`

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

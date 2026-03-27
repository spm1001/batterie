# CLAUDE.md

Instructions for Claude when working in this repository.

## What This Is

todoist-gtd is a Python CLI for Todoist with GTD coaching. Two parts:
- **CLI** (`todoist_gtd/`) — MCP-free Todoist API access, installed via `uv tool install`
- **Skill** (`SKILL.md` + `references/`) — GTD semantics and coaching

## Quick Commands

```bash
todoist doctor          # Check setup
todoist auth --status   # Check auth
todoist projects        # List projects
todoist version         # Show version
./scripts/verify.sh    # Run acceptance tests
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
├── auth.py         # OAuth authentication flow
├── token_store.py  # Portable secrets management (env, keychain, file)
└── flatten.py      # Subtask flattening tool (todoist-flatten command)
```

Entry points defined in `pyproject.toml`:
- `todoist` → `todoist_gtd.cli:main`
- `todoist-flatten` → `todoist_gtd.flatten:main`

Install: `uv tool install ~/Repos/todoist-gtd`
Reinstall after changes: `uv tool install --force ~/Repos/todoist-gtd`

## Working with Bon

This repo uses `bon` for work tracking:

```bash
bon list              # See all work
bon list --ready      # Find available work
bon show <id>         # View item details
```

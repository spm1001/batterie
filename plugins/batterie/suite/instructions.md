# Batterie de Savoir — Instruction Shard

Auto-loaded via `~/.claude/rules/batterie.md`.

## The Kitchen

All tools follow a professional kitchen metaphor. Suite: **Batterie de Savoir**.

| Tool | Name | Role |
|------|------|------|
| Work tracker | **Bon** | The ticket |
| Skills & lifecycle | **Trousse** | The knife roll |
| Google OAuth tokens | **Jeton** | The token |
| Content fetcher (MCP) | **Mise** | Mise-en-place |
| Browser automation | **Passe** | The pass |
| BigQuery analysis | **Consommé** | Clarification |
| Multi-session orchestrator | **Aboyeur** | The caller |
| Inter-session messaging | **Sonner** | The bell |
| Mobile interface | **Guéridon** | The side table |
| Natural-language BigQuery UI | **Plongeur** | The dishwasher |
| Survey data transformation | **Mandoline** | The slicer |

Sonner's mechanics (it rings a repo, not a session; the deaf provider-billed
session; the silently dropped repeat) live in its own shard, `rules/sonner.md`, once
sonner is installed.

*Sonnette (the old conductor-mesh plugin) was delisted from the suite 2026-08-24;
sonner supersedes it. Guidance still naming `send_message` or `mesh_peers` is stale.*

## Filesystem Zones

| Zone | Path |
|------|------|
| **Repos** | `~/repos/<owner>/<repo>` — the layout `/open REPO` and `bon move --to` resolve bare names against (`~/repos/*/NAME`). Git-controlled; never inside a cloud-synced folder. |
| **Work documents** | Google Drive, reached through mise — no local mount assumed. |

Everything else about a machine's layout — sync folders, a notes repo, whether `~/.claude` is itself a git repo — differs by machine and belongs in that machine's own guidance, not in this shard, which loads for every teammate.

## Overrides

| Your Default | What I Need |
|-------------|-------------|
| `uv tool install <tool>` from PyPI or git | batterie CLIs install from the wheel their plugin ships (`<plugin dir>/wheels/`) — the SessionStart hooks and `/batterie:update` do it for you; the source repos are private |
| Individual skill permissions | `Skill(*)` in settings.json covers all skills |

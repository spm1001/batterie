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
| Collaborative editing (MCP) | **Tafelmusik** | Table music |

## Filesystem Zones

| Zone | Path |
|------|------|
| **Repos** | `~/repos/` — git-controlled, never cloud-synced. Owner-bucketed: batterie tools in `~/repos/spm1001/`. |
| **Config** | `~/.claude/` — git: `spm1001/.claude` |
| **Work** | Google Drive (web) — no local mount |
| **Capture** | `~/iCloud/Work Inbox/` — iOS quick capture |
| **Taildrive** | `~/Taildrive/` — each server shares here |

## Overrides

| Your Default | What I Need |
|-------------|-------------|
| `uv tool install <tool>` | `uv tool install ~/repos/spm1001/<tool>` for batterie CLI tools |
| Individual skill permissions | `Skill(*)` in settings.json covers all skills |

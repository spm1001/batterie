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
| Inter-session messaging (MCP) | **Sonnette** | The bell |
| Mobile interface | **Guéridon** | The side table |
| Natural-language BigQuery UI | **Plongeur** | The dishwasher |
| Survey data transformation | **Mandoline** | The slicer |

Sonnette rings both ways only in sessions launched with the channels flag
(`--dangerously-load-development-channels`). Otherwise you are **send-only**:
`send_message` and `mesh_peers` work, but inbound messages never arrive — don't
wait on a reply you can't hear.

## Filesystem Zones

| Zone | Path |
|------|------|
| **Repos** | `~/repos/` — git-controlled, never cloud-synced. Owner-bucketed: batterie tools in `~/repos/spm1001/`. |
| **Config** | `~/.claude/` — git: `spm1001/.claude` |
| **Work** | Google Drive (web) — no local mount |
| **Capture** | `~/iCloud/Work Inbox/` — iOS quick capture |
| **Sharing** | `~/scratch/` — Syncthing (Mac ↔ tube); `~/notes` is git-canonical via notes-sync. Taildrive retired 2026-07-07. |

## Overrides

| Your Default | What I Need |
|-------------|-------------|
| `uv tool install <tool>` | `uv tool install ~/repos/spm1001/<tool>` for batterie CLI tools |
| Individual skill permissions | `Skill(*)` in settings.json covers all skills |
| Hand-run the bump→commit→push→assemble→update dance to ship a shard | `/batterie:publish` — one verb does the whole dance (run from the source repo's working tree) |

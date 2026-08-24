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

Sonner addresses a **repo**, not a session id — `sonner <repo> "message"` reaches
a live session there, or spawns one and then delivers, so it still lands as a peer
message rather than as the user speaking. No launch flag is needed. Two things it
cannot do for you: a provider-billed session registers with no inbox socket and is
reachable by nothing, and Claude Code silently drops a byte-identical repeat while
telling the sender it succeeded. So confirm receipt before relying on anything you
sent, and load `Skill(peer-messaging)` first — it carries the rest.

*Sonnette (the old conductor-mesh plugin) was delisted from the suite 2026-08-24;
sonner supersedes it. Guidance still naming `send_message` or `mesh_peers` is stale.*

## Filesystem Zones

| Zone | Path |
|------|------|
| **Repos** | `~/repos/` — git-controlled, never cloud-synced. Owner-bucketed: batterie tools in `~/repos/spm1001/`. |
| **Config** | `~/.claude/` — git: `spm1001/.claude` |
| **Work** | Google Drive (web) — no local mount |
| **Sharing** | `~/scratch/` — Syncthing (Mac ↔ tube); `~/notes` is git-canonical via notes-sync. Taildrive retired 2026-07-07. |

## Overrides

| Your Default | What I Need |
|-------------|-------------|
| `uv tool install <tool>` | `uv tool install ~/repos/spm1001/<tool>` for batterie CLI tools |
| Individual skill permissions | `Skill(*)` in settings.json covers all skills |
| Hand-run the bump→commit→push→assemble→update dance to ship a shard | `/batterie:publish` — one verb does the whole dance (run from the source repo's working tree) |

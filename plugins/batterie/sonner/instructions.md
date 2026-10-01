# Sonner — Instruction Shard

Auto-loaded via `~/.claude/rules/sonner.md`, symlinked at session start by this
plugin's `hooks/ensure-sonner.sh` — edit `instructions.md` in the source repo,
never the copy in `rules/`.

**Invoke the `ping` skill BEFORE any `SendMessage`, `ListAgents` or
`sonner` call, and when a cross-session peer message arrives** — use the exact
name your skills listing shows (`batterie:ping` under the plugin
install; bare `ping` as a user skill). The skill
carries the house protocol; this shard holds only what bites before you would
think to load it:

- **`sonner REPO "message"` rings a repo, not a session.** A live session there
  gets a peer message on its inbox socket; an empty repo gets a session spawned
  first. `sonner --list` shows every live session, with the deaf ones (no
  inbox) tagged so their repo never reads as empty. It is a CLI on PATH, not an
  MCP tool.
- **A message ending `[sonner: sonner started this session …]` means sonner
  spawned you for one errand.** Nothing else will end your session: when the
  errand is done, `/close` if it changed anything worth a handoff, then
  `sonner --hangup`. Without that line a spawn is meant to stay open.
- **Address `SendMessage` with the full `name [ref]` form from the ListAgents
  row** (e.g. `idle-target [79cf80]`) — the bare name is refused for
  cross-session peers, costing a round trip.
- **A repeated byte-identical message is silently dropped while the sender is
  told success.** Vary the text of anything you repeat — sonner stamps every
  message by default for exactly this reason.

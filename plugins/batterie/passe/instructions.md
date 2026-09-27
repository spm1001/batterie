# Passe — Instruction Shard

Auto-loaded via `~/.claude/rules/passe.md`.

## Overrides

| Your Default | What I Need |
|-------------|-------------|
| WebFetch (summaries) | `passe fetch` for web content. Never WebFetch — summaries miss nuance. |
| `open URL` | `browse URL` for quick inspection (opens in the backend Chrome). |

## Which Chrome passe drives

A real, logged-in Chrome over CDP, and which one is host configuration: `passe status` names it
(`cdp_endpoint`, `reachable`), and `PASSE_CDP` or `--cdp URL` points elsewhere. Gated pages need
nothing extra — the backend already holds the logins. A host that runs a backend maps its ports in
its own rules file (on Sameer's estate, `rules/tube.md`, with the checks for a missing endpoint in
the `diagnose` skill). A host with no backend (`reachable=False`) has no units to hunt for; one that
should reach a backend needs a tunnel from `passe-partout` `deploy/client/` (`install.sh` on Linux,
the launchd agent pattern on a Mac), and that repo is also where a backend's logins and placement
are configured.

- Browser automation: `passe` (CDP CLI). Compound ops in one Bash call.

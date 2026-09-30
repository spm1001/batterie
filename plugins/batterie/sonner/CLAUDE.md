# Sonner

Ring a repo, and a Claude answers — repo-addressed messaging for Claude Code sessions.

`SendMessage` addresses a *session*; sonner addresses a *repo*, which is usually what you mean. A live session in the repo gets the message on its inbox socket; an empty repo gets a session spawned under tmux first, so the message still lands as a **peer message** rather than a user prompt. Born 2026-08-09 from the native cross-session-messaging review (`aboyeur/docs/native-xsm-review-2026-08-08.md` — the measurements behind every design choice here).

## Quick Commands

```bash
uv run --group dev pytest          # run tests
uv tool install .                  # put `sonner` on PATH
sonner --list                      # every live session and its repo — deaf ones tagged [deaf: no inbox]
sonner REPO "message"              # ring (spawns if nobody's home; refuses if only a deaf session is home)
sonner REPO "message" --force-spawn  # deaf-occupied repo: plant a socketed sibling anyway, audibly
sonner --name NAME "message"       # ring one session by registry name
sonner --wake REPO [--work]        # ensure a session exists (--work: claudev, MIT work billing on Vertex)
sonner REPO "message" --work       # empty repo: spawn on work billing, deliver over the inbox as usual
sonner --host HOST REPO "message"   # the same, run on HOST over ssh through a login shell (also --wake, --list)
sonner --trust [REPO]               # pre-trust REPO (default: every git repo under ~/repos/*/*) in every seat's config
```

## Module Map

| Module | Role |
|--------|------|
| `cli` | The whole tool: discovery (sockets + registries), wire-format delivery, tmux spawn, argparse `main()` |
| `_invlog` | Vendored estate invocation-log shim — every run appends one caller-stamped JSONL line to `~/.local/share/sonner/invocations.jsonl` (message bodies included, argv-raw by schema design). main() returns ints, so its codes bridge into the shim via the `_ReturnCode` SystemExit subclass — don't unwind that, or returned failures log as ok. Never edit here; re-vendor from canonical (spm1001/harness-ergonomics) |

One module for the tool itself is a deliberate choice — this is a doorbell, not a framework. Split only when a second consumer of discovery actually exists. (`_invlog` is vendored instrumentation, not a second module in that sense.)

## Key Conventions

- **Stdlib only.** No dependencies, ever — sonner must run anywhere `uv` exists, including a Mac over non-interactive ssh.
- **Sockets are the roster; registry records are enrichment.** Every session binds `<pid>.sock` in a shared socket dir; records live under *each config dir's* `sessions/` (`~/.claude`, `~/.claude-commis`, any `~/.claude-*`), so reading one registry silently hides sessions homed in another. Discovery unions sockets across known layouts (`$XDG_RUNTIME_DIR/cc-socks`, `/run/user/<uid>/cc-socks` even when that env var is unset, `/tmp/cc-socks` on macOS, `/tmp/cc-socks-<uid>`) with every record's own `messagingSocketPath`. Don't "simplify" this to a single source — each half catches sessions the other misses (learned the hard way, 2026-08-09).
- **Env vars are hints; the uid is ground truth.** Homes are swept by both `$HOME` and the passwd database — they differ exactly when a harness overrode HOME, which is how the receptionnaire mail session saw an empty machine, spawned a duplicate, and timed out (son-sotize, 2026-08-09). Never key discovery solely on the caller's environment.
- **Every message is timestamped by default.** Claude Code silently drops byte-identical repeat messages *while reporting success to the sender*. `--no-stamp` exists for genuine one-offs; do not make it the default.
- **Spawn-then-deliver, never prompt-injection — no exceptions left.** Passing the message as the spawned session's prompt would make it read as the user speaking. Delivering over the socket after the session binds keeps peer framing and the harness's peer guardrails. The one sanctioned exception (Sameer's verdict, 2026-08-09) was the deaf `--work` spawn: claudefv had no socket, so the message went to a drop file and the prompt carried only the pointer. It was retired 2026-09-30 (son-zecece) when a measurement showed a `claudev` session (Opus 5.5 on Vertex, the house model) binds an inbox and answers a ring: `--work` now launches claudev and delivers over the socket, and a work spawn that comes up deaf anyway fails at once, naming it, rather than falling back to a prompt.
- **Cold-spawn needs a trusted cwd — and a spawn that can never come up says so at once (son-dimohu, 2026-09-30).** Trust is per exact path (`~/.claude.json` `projects[path].hasTrustDialogAccepted`; a trusted `~` or `~/repos` does not cover a repo never opened). The inbox socket binds ~0.35s into startup, ~0.17s *before* the trust dialog draws, so readiness alone once printed `woke`, exit 0, over a session parked at "No, exit". `_await_session` now watches the screen after readiness until the welcome banner (`Claude Code v`) shows: dialog seen → exit 3 `held:` (a ring has already delivered — the message waits, so don't ring twice); the window left open for a human to answer via `tmux attach -t claude`. `sonner --trust [REPO]` pre-trusts (Sameer's call, 2026-09-30: his own repos, every seat's `.claude.json`); it is deliberately not automatic on spawn, since the dialog is the one gate against a freshly cloned repo's hooks. The same loop catches a pane that died (exit status + last screen lines, dead window closed — `_tmux_spawn` opens on a placeholder and sets `remain-on-exit` before `respawn-pane` runs argv, because a command-not-found pane is gone before any later tmux call lands) and a window that vanished. `spawn()` resolves `claude` on sonner's own PATH first, since tmux hands the window the *caller's* PATH and a bare `ssh HOST sonner` has none of `~/.local/bin`.
- **Testing against tmux: `$TMUX` outranks `TMUX_TMPDIR`.** A `tmux kill-server` with `TMUX_TMPDIR` exported but `$TMUX` still set killed tube's default server and five live sessions (2026-09-30). Shell state does not carry between harness Bash calls, so an `unset TMUX` in the previous call is gone. Any private-server tmux command goes as `env -u TMUX tmux -S <private socket> …`, in one command.
- **One tmux session, one window per repo — a spawn is a window, never a session.** `HOME_SESSION` (default `claude`, matching dotfiles' `claude-start`) is the single session everything joins; the window is named for the repo, which is also how `claude-start <repo>` finds and reuses it. This supersedes son-fomuno's `rung-<repo>` session-per-spawn, shipped the night before (Sameer, 2026-08-10) — a sequence, not a reversal: `rung-` fixed sonner's children masquerading as sonner, and this fixes them scattering. Why it matters: a tmux status bar lists only the windows of the session you are attached to, so a session-per-spawn estate hides most of itself. Two mechanics hold it up — `-t '=claude'` forces an exact session match (bare `claude` prefix-matches, and a session named `claude-anything` would swallow every spawn), and `-n <repo>` both labels the tab and disables `automatic-rename`, without which tmux overwrites the name with the running command and every tab reads "claude".
- **A tmux coordinate is only durable as `@window` / `%pane`.** Registry records store `tmux` as `<session>:@win.%pane`; the session-name half is a registration-time snapshot that rots on any rename or window move, and a stale target resolves to nothing while `tmux` still exits `0` — silent, not loud. Strip to the id (measured 2026-08-10, after merging the estate into one session made both events routine).
- **Deaf sessions exist: a live session with no inbox — and the reader, not the wire, is where they went missing.** Some sessions write a full registry record with the `messagingSocketPath` field absent — reachable by nothing, but present and busy (measured 2026-08-09: 5 of 8 live sessions on tube, then all provider-billed). Billing route is not the cause: a `claudev` session on Vertex binds an inbox (2026-09-30), and the traps.md sonner row's 2026-08-31 measurement put it on config dir, so the tag no longer says "provider-gated". The socket roster structurally cannot show them, so `registered_alive()` sweeps the records on a three-state discriminator: field ABSENT + pid alive = live but deaf; field present + socket gone = a dead session's leavings; `procStart` (CC writes the kernel start-time ticks of its own pid) not matching the live process = a reused pid, also leavings. `--list` merges the deaf in tagged `[deaf: no inbox]`; a ring or `--wake` into a repo held only by deaf sessions is refused with the reason, and `--force-spawn` is the single explicit way to plant a sibling there (son-nukuzi). The alternative — no escape hatch, "reach it via tmux" only — lost because a human who *wants* a listener beside a busy work session had no honest route and would spawn one by hand with less visibility; the flag keeps the sibling audible.
- **`from` in the envelope is display/reply-routing only** — receivers verify identity via `SO_PEERCRED` on the connecting process. Don't build anything that trusts the `from` string.
- **The companion skill (`skills/ping/`) carries the house habits** — addressing forms, wake-or-file test, machine-register replies. **This directory is now the only copy that matters** (shipped 2026-08-24, suite 1.73.0): the plugin vendors it, and the old `~/.claude/skills/ping/` user copy was retired on tube the same day. A machine whose `~/.claude` clone is behind may still show a duplicate picker entry until it pulls — benign, and it clears itself.

## Plugin packaging (batterie)

sonner ships as a batterie plugin: `.claude-plugin/plugin.json` (SessionStart hook only), `hooks/ensure-sonner.sh` (symlinks `instructions.md` → `~/.claude/rules/sonner.md`, installs the CLI if missing), `instructions.md` (the thin always-on shard), `skills/ping/`. Three things to hold:

- **The assembler's skill-plugin copy-list ships no Python** — no `pyproject.toml`, no `src/`. The hook therefore installs from the wheel the assembler builds into the vendored plugin (`wheels/sonner-*.whl`, bds-timule, 2026-09-23), from `$PLUGIN_ROOT` in a source checkout, and from `git+https://github.com/spm1001/sonner` only as a maintainer fallback — the repo is private, so that path needs GitHub credentials. Dependencies resolve from PyPI, so any new one must be on PyPI.
- **The vendored plugin.json version is the SUITE version** — the assembler stamps it. This repo's own `0.1.0` is local-dev-only; release via `/ship`, never a hand-bump.
- **A shard/skill/hook edit here is vendored content** — it ships only on a suite bump, and takes effect in sessions only after restart (guidance is session-cached).

## Wire format (captured, not documented upstream)

One newline-terminated JSON line to the socket:

```json
{"msgV":1,"msg_id":"<uuid>","type":"user",
 "message":{"role":"user","content":"<cross-session-message from=\"...\" from-name=\"...\" from-mode=\"prompting\">\nBODY\n</cross-session-message>"},
 "priority":"next","from":"<reply address>"}
```

Captured from a real `SendMessage` on CC 2.1.226 (2026-08-08). Upstream may version it — `msgV` is the canary, and a delivery that stops working after a CC upgrade should check this first.

Work is tracked on a bon board in `.bon/` — read `.bon/README.md` before reading or changing anything there.

# Cowork Cloud Environment Reference

_Cloud (remote) Cowork. For Desktop Cowork, see the sibling [`cowork-environment.md`](cowork-environment.md) — the Detection section below tells the three surfaces apart._

Captured 2026-08-03 from a live cloud Cowork session on Claude Code 2.1.42 (session, env-runner and container identifiers redacted for publication — their shapes: session `cse_01…`, env-runner `staging-…`, container `container_01…--remote_cowork--…`). Every claim below was probed, not assumed.

## Detection

**`CLAUDE_CODE_IS_COWORK` is UNSET in cloud Cowork.** A check for it fails open to the not-Cowork branch, so cloud sessions get treated as plain Claude Code CLI — the worst branch, because it assumes CLIs, hooks and local repos that are all absent. Branch three ways instead:

```bash
if [ "${CLAUDE_CODE_ENTRYPOINT:-}" = "remote_cowork" ]; then
  : # Cowork cloud — this file
elif [ "${CLAUDE_CODE_IS_COWORK:-}" = "1" ]; then
  : # Cowork desktop — see cowork-desktop.md
else
  : # Claude Code CLI
fi
```

Corroborating: `CLAUDE_CODE_REMOTE=true`, `CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE=cloud_default`, and `test -d /mnt/user-data` as a filesystem tell.

## OS and Runtime

- **Kernel:** Linux 6.18.5 **x86_64** — purpose-built (`builder@sandboxing`), `ipv6.disable=1`
- **Distro:** Ubuntu 24.04.4 LTS
- **Python:** 3.11.15 · **Node:** 22.22.2 · **npm:** 10.9.7 · **Go:** 1.24.7 · **Java:** 21 · bun, rustc, ruby, perl, gcc, make, `uv`
- **You are `root`** — `CapEff=000001fffeffffff`, `Seccomp=0`, `NoNewPrivs=0`, `sudo` works, `mount(2)` works, Docker 29.4.3 installed and running. No `bwrap`.
- **2 CPUs · 7.8 GiB RAM · no swap · 252 G ext4 with ~30 G free.** `df` is honest here.
- `HOME=/root` but **cwd is `/home/claude`**, which has its own `.claude/`, `.ssh/`, `.npm-global/`. Two homes that disagree — use absolute paths.

**This is a Firecracker microVM.** `PID 1` is `/process_api --firecracker-init --block-local-connections --listen-vsock-port 2024`, control plane over vsock, one `eth0` routed to `192.0.2.1` (TEST-NET-1). `/opt/*` are read-only squashfs images.

## Package Installation

```bash
pip install duckdb          # just works — no --break-system-packages needed
npm install docx            # lands in /home/claude/.npm-global
```

No `EXTERNALLY-MANAGED` marker. pip writes to `/usr/local/lib/python3.11/dist-packages`. **Installs persist across bash calls and across a VM recycle**, but not across sessions.

## Filesystem

| Path | What | Writable | Persistent |
|------|------|----------|-----------|
| `/home/claude` | cwd. Scratch, invisible to the user | Yes | Session only |
| `/tmp` | Scratch; also harness logs and MCP config | Yes | Session only |
| `/mnt/user-data/working` | The only user-facing directory | Yes | Session only |
| `/root/.claude/skills/` | Account-synced skills | Yes | Session only |
| `/root/.claude/plugins/synced/` | Account-synced plugins | Yes | Session only |
| `/root/.ccr/` | Egress proxy CA bundle, Java truststore, README | Read | Session only |

**Deletes work everywhere.** No FUSE unlink wall, no `mv` direction problem — it is one ext4 filesystem. There is **no mount of the user's machine at all**: no `~/Documents`, no `$HOME/mnt/`, no `CLAUDE.md`, no device bridge. If you need one of their files, they attach it.

## What Doesn't Work

| Feature | CLI | Cowork cloud | Notes |
|---------|-----|--------------|-------|
| Plugin hooks (`SessionStart`, `ensure-*.sh`) | Yes | **No** | Registered in `plugin.json` on disk, never fire. Proven: batterie's hook symlinks `instructions.md` into `~/.claude/rules/`; that directory does not exist. |
| `CLAUDE_PLUGIN_ROOT` | Yes | **No** | Unset — so every `${CLAUDE_PLUGIN_ROOT}/hooks/...` command would resolve to a nonexistent absolute path even if hooks did fire. |
| Plugin CLIs (`bon`, `mise`, `passe`, `trousse`, …) | Yes | **No** | **This is the consequence of the two rows above** — the `ensure-*.sh` bootstraps that install them never run. `PATH` still lists one `.../synced/<name>/bin` per plugin; none of those directories exist. |
| Plugin MCP servers | Yes | **No** | `CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS=1`, except `documents`. `mcp-local.json` is ignored. |
| Plugin `CLAUDE.md` | Yes | **No** | On disk but not loaded — 159 KB across ten plugins against a 27.6 KB `--append-system-prompt`. You get every trigger, no operating manual. Read them off disk before serious work. |
| User `CLAUDE.md` | Yes | **No** | Nothing anywhere: not `/root`, `/root/.claude`, `/home/claude`, `/mnt/user-data`. Personalisation arrives **only** via the system prompt's `<user>` and `user_preferences` blocks. |
| Browser automation over HTTPS | Yes | **No** | See Chromium below. |
| `git push` / private repos | Yes | **No** | See GitHub below. |
| Persistent processes across a VM recycle | Yes | **No** | See VM lifecycle below. |
| Artefact gallery / `create_artifact` | — | **No** | `CLAUDE_CODE_DISABLE_ARTIFACT=1`. Nothing in-conversation outlives the session. |
| `mcp__remote-devices__*`, `mcp__cowork__*` | — | **No** | Not in the MCP config. The system prompt documents them anyway. |
| Launcher hooks | — | **Yes** | `SessionStart → session-start-git-identity.sh`, `Stop → stop-hook-git-check.sh` do fire (`hooks_init_ms: 119`). Anthropic's, not yours. |

## VM lifecycle — the thing that will surprise you

Background processes survive across bash calls: a `nohup`'d loop was still ticking 243 seconds and four tool calls later. But **the VM itself can be replaced mid-session**. In the captured session it was destroyed and a fresh one claimed ~18 minutes in, after the user stepped away:

- `/proc/stat`'s `btime` showed a boot 18 minutes after `CCR_SPAWN_TIMESTAMP_MS`.
- `/tmp/env-manager.log` recorded a second launch with `session_mode: "resume"`, `--resume=https://api.anthropic.com/v1/code/sessions/<id>`, `resume_hydrate_fetch_ms: 741`, `warm_spare_claimed: true`.

The conversation lives server-side and is rehydrated into a pre-warmed spare. Files and installed packages survive; **processes, listeners and the `$HTTPS_PROXY` port do not**. Never put workflow state in a process. When something that worked ten minutes ago fails, check `cut -d' ' -f1 /proc/uptime` first — a small number means you are in a different machine.

`strings /opt/env-runner/environment-manager` puts `MANAGED_AGENTS` in a capability enum beside `SESSION_THREADS`, `CALLABLE_AGENTS`, `AGENT_MEMORY_MOUNT`, `SESSION_VAULT`, `ENVIRONMENTS_SELF_HOSTED` — one runner serves Cowork cloud and Managed Agents both. It also carries snapshot-GC symbols, so eviction aggressiveness is tuned and this behaviour will drift.

## Network

All HTTPS goes through a local CONNECT proxy at `$HTTPS_PROXY`, with the CA bundle at `/root/.ccr/ca-bundle.crt`. **Read `/root/.ccr/README.md` before debugging any TLS failure** — it enumerates every failure class. Diagnostic: `curl -sS "$HTTPS_PROXY/__agentproxy/status"`.

- **The proxy port is randomised per VM boot.** It changed from `41145` to `40159` across the recycle. Never hardcode it.
- **The proxy is not the only way out.** With it unset, `curl` still reached :80 and :443. Enforcement is at the gateway; there are no `iptables` rules inside the VM at all.
- **The gateway is name-based.** `http://example.com` works, the same site by raw IP times out. DNS to `8.8.8.8` works, `1.1.1.1:53` does not.
- **Not everything is MITM'd** — example.com presented its genuine Cloudflare issuer.
- **403/407 is an org egress-policy denial.** Report it; do not route around it. Same for a `WebFetch` refusal.
- Dead: gRPC/HTTP2-only, WebSocket upgrades, client-mTLS, cert-pinned clients, non-443 HTTPS, raw TCP, bare IPs.

**Chromium does HTTP but not HTTPS, and it is not fixable from inside.** `file://` renders and screenshots fine; a local self-signed HTTPS server works, so its TLS stack is healthy; `http://example.com` loads; `https://example.com` gives `ERR_CONNECTION_RESET` under every combination of `--ssl-version-max=tls1.2`, `--disable-features=EncryptedClientHello,PostQuantumKyber,UseMLKEM`, `--ignore-certificate-errors`, `--proxy-server=…` and `--no-sandbox`. `curl` to the same host and port at the same moment returns 200. The gateway discriminates by client, outside the VM. **So: no CDP scraping, no screenshots of live sites. Chromium is a local renderer only** — and as that, HTML → PDF/PNG works perfectly.

**GitHub is a decoy.** `GET api.github.com/user` returns 200 and identifies as the account owner's own login. Everything else 403s, **including public repos**, and `git clone https://x-access-token:$GITHUB_TOKEN@...` fails auth. A successful public clone works anonymously; the token contributes nothing. The tell is `X-Accepted-Github-Permissions: allows_permissionless_access=true` with `X-Oauth-Scopes` empty. Those 403s are the gateway.

## Getting output out

1. **`SendUserFile`** — the workhorse. `.md`, `.html`, `.svg`, `.mermaid`, `.pdf`, `.png` render inline; `.docx`, `.xlsx`, `.pptx`, `.csv`, `.json` attach as download cards. The `display` parameter (`"render"` / `"attach"`) overrides by-type defaults.
2. **`mcp__visualize__show_widget`** — renders an SVG or HTML fragment inline, the only channel producing no file. Its `read_me` is mandatory before first use and **overflows the tool-result budget** (71,564 chars, 774 lines, spilled to `.../tool-results/`); the load-bearing sections are Rules, CSS Variables, Color palette and SVG setup. Constraints are strict: `viewBox="0 0 380 H"` with the 380 load-bearing, a `t`/`ts`/`th` class on every `<text>`, colours only from the nine `c-{ramp}` classes, sentence case, no emoji or gradients, CDN allowlist of six origins.
3. **A hosted MCP the account owns** — the only durable channel. A hosted connector can write the user's private repos because **its credential lives on its server, not in this sandbox**. Prefer it for anything a future session must read.

**Document toolchains all work**: `soffice --headless --convert-to pdf` on `.pptx` and `.docx` (LibreOffice does not hang here), `pandoc` md→docx, `markitdown` for reading Office files back, Chromium for HTML→PDF/PNG. So the full visual-QA loop is available. One gap: the `docx` skill mandates **docx-js**, not preinstalled — `npm install docx` fixes it in seconds; `python-docx` 1.2 is already there.

**Absent and likely to bite:** `sqlite3` CLI (python module fine), `ss`, `netstat`, `ip`, `aws`, `gcloud`, `gsutil`, `gh`, `deno`, `magick` (use `convert`). `rclone` is at `/opt/rclone`, not on `PATH`.

## MCP and subagents

Every MCP server is an HTTP shim to one relay: `https://api.anthropic.com/v2/ccr-sessions/<session-id>/mcp`. Only account-level connectors appear; the set varies per user. Deferred tools need `ToolSearch` with `query="select:<name>"` before they are callable. `MCP_TOOL_TIMEOUT=60000`.

Subagents share the container — same root, hostname, session ID, `/tmp`, and they see your background processes. They start with only their built-in tools, so brief a bash- or MCP-heavy delegate to `ToolSearch` for its own schemas. `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`.

Many built-in Claude Code skills are force-disabled via `CCR_SKILL_OVERRIDES` — `review`, `commit`, `debug`, `loop`, `remember`, `dashboard`, `investigate`, `bughunt` and ~30 more.

## Two gifts

- **Timezone.** `date` is UTC and `$TZ` is empty, but a Todoist connector's `user-info` returns both `timezone` and `currentLocalTime`. That is a reliable oracle where the Desktop reference says none exists.
- **Your own transcript** is on disk at `/root/.claude/projects/-home-claude/<uuid>.jsonl` (record types `user`, `assistant`, `attachment`, `last-prompt`, `mode`, `queue-operation`), so session introspection works even without the `deglacer` CLI. And `~/.claude.json` carries 445 `tengu_*` feature flags — the switch positions governing the session.

## Footguns worth memorising

1. **`pkill -f <pattern>` kills your own shell.** Each call is wrapped as `bash -c '... && eval '\''<your command>'\'''`, so your pattern matches your own wrapper. Exit 144, no output. Use `pgrep -af` then `kill <pid>`.
2. **`cd` is undone.** cwd is reseeded from `/tmp/claude-*-cwd` after each call; env vars and aliases do not persist at all. Absolute paths.
3. **Bash gets 120 s by default, 600 s maximum** — not the 45 s of Desktop Cowork.
4. **`--allow-dangerously-skip-permissions` is on.** Nothing prompts before it runs. Reasoning effort arrives per-invocation as `--effort high`.
5. **Clean `/mnt/user-data/working`.** It is the user's view; a stray probe file there is confusing in a way one in `/tmp` is not.

## Plugin author checklist (cloud-specific)

- [ ] Branch on `CLAUDE_CODE_ENTRYPOINT=remote_cowork`, never on `CLAUDE_CODE_IS_COWORK` alone
- [ ] Assume **no** hooks fire and **no** CLI is installed — a skill must work prompt-only or say plainly that it cannot
- [ ] Never depend on `CLAUDE_PLUGIN_ROOT`
- [ ] Never depend on the plugin's own `CLAUDE.md` being in context — read it off disk if the skill needs it
- [ ] Check for an account-level connector reaching the same service before declaring a capability missing
- [ ] Python 3.11 here vs 3.10 on Desktop — don't pin to 3.10 limitations
- [ ] Frontmatter rules from `cowork-desktop.md` still apply: flat, quoted `description`, comma-separated `allowed-tools`, no `requires:`, no "claude" in the name

## One conflict in your own tooling

`skill-forge/scripts/lint_skill.py` emits `[description_user_tag] Missing (user) tag for user-defined skills`, while `cowork-environment.md` lists a `(user)` suffix in the description as something that **breaks Cowork** and silently drops the skill. Both cannot be satisfied. The `(user)` marker appears in the rendered skill list at runtime, which suggests the platform adds it rather than the author, so the Cowork rule is the one to obey and the lint check is the one to soften.

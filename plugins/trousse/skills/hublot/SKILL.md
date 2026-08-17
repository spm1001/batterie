---
name: hublot
description: >
  Orchestrates a real interactive Claude Code session under tmux using a
  start/wait/read/stop cycle — answers its dialogs, polls its screen for
  patterns, tears it down cleanly. Required first when testing TUI-only
  behaviour (inbound mesh channel tags, trust dialogs, statusline,
  session-start hooks): `claude -p` is a different product surface that
  cannot exhibit them, so this prevents the headless green that proves
  nothing. Triggers on 'test this interactively', 'drive a real session',
  'tmux-driven test', 'answer the dialog for it'. For blank-slate isolation,
  use ardoise. (user)
---

# Hublot

The oven porthole: watch the real thing cooking, in its real environment, without opening the door and changing what you are measuring.

A Claude can drive a genuine interactive Claude Code session — press its buttons, read its screen, and observe how it reacts to the outside world — instead of settling for a headless approximation that structurally cannot show the behaviour under test.

## The principle worth internalising

**`claude -p` is a different product surface, not a cheaper layer of the same one.** Whole classes of behaviour exist only in the interactive TUI:

| Only in interactive | Why headless can't show it |
|---|---|
| Inbound mesh `<channel>` tags | CC drops them at the surfacing layer in `-p`; the wire delivers, the context never sees it |
| Trust / permission / channels dialogs | No TTY, no prompt |
| Statusline, glyphs, live indicators | Nothing renders |
| Session-start rituals and their hooks | Different entrypoint, different lifecycle |

CC names the distinction itself: `CLAUDE_CODE_ENTRYPOINT` is `sdk-cli` for `-p` and `cli` for interactive. Testing an interactive-only behaviour headless and reporting a result is the unearned green in its most convincing costume — the check ran, it passed, and it never touched the thing at risk.

## When to Use

- **Mesh receive-path work** — does a session *actually* surface a peer's message as a tag? Only an interactive session can answer.
- **Dialog flows** — folder trust, the channels warning, permission prompts. Reaching them at all needs a TTY.
- **Statusline and glyph work** — verifying what a human would see.
- **Launch-wrapper verification** — does `claudem` / `-m` produce the session shape it promises?
- **Anything whose evidence is "what appeared on screen"** rather than "what a tool returned".

## Boundaries

- **Not for headless work.** If `-p` can genuinely exhibit the behaviour, use `-p` — it is faster and needs no teardown.
- **Not for isolation testing.** A blank-slate session (no CLAUDE.md, no skills, no plugins) is `ardoise`. The two compose: `hublot` can drive an interactive `ardoise` session, which is the only way to test a fresh user's onboarding flow unattended.
- **Not a substitute for a unit test.** Drive the TUI to confirm the seam; assert the logic offline.
- **Linux-first.** Built on tmux and `capture-pane`.

## Workflow

Resolve the script the way sibling skills do:

```bash
SCRIPT="${CLAUDE_PLUGIN_ROOT}/scripts/hublot.sh"
[ -x "$SCRIPT" ] || SCRIPT=$(find ~/.claude/plugins/cache -path "*/trousse/*/scripts/hublot.sh" 2>/dev/null | sort -rV | head -1)
```

### 1. Choose a cwd that is already trusted

A new folder raises CC's folder-trust dialog, and answering it writes a durable entry into the user's `~/.claude.json` — a config change as a side effect of a test. Check first:

```bash
python3 -c "
import json; d=json.load(open('$HOME/.claude.json'))
print([k for k,v in d.get('projects',{}).items() if v.get('hasTrustDialogAccepted')])"
```

**Success:** you have a trusted directory that is *not* the repo under test if that repo has its own MCP config (a project `.mcp.json` server plus a plugin server means two servers and a muddied result).

### 2. Start, scrubbing whatever the test must not inherit

```bash
$SCRIPT start probe --cwd ~/repos/spm1001/some-trusted-repo \
    --unset CLAUDE_CODE_USE_VERTEX --unset ANTHROPIC_MODEL -- claudem
```

`--unset` scrubs *inside* the session's shell. Billing env is the usual case: a Vertex-billed parent makes every child Vertex, and some behaviour (channels) is unavailable there.

**Success:** `start` reports the tmux session name.

### 3. Wait for a pattern, never sleep and hope

```bash
$SCRIPT wait probe 'I am using this for local development' 60
$SCRIPT enter probe          # accept the dialog
$SCRIPT wait probe 'Channels .experimental.' 60
```

`wait` polls and exits non-zero on timeout, printing the pane so you can see *where* it stalled. A fixed `sleep` is both flaky and slow.

**Success:** each `wait` returns `matched:`.

### 4. Exercise and observe

Do the thing from outside — send a mesh message, touch a file, trigger a hook — then read the screen:

```bash
$SCRIPT read probe -n 20        # visible pane
$SCRIPT read probe --all        # include scrollback
```

**Success:** the pane shows the behaviour, *and* you have a positive control (something that should appear, appearing) so an absence is a finding rather than a dead instrument.

### 5. Stop cleanly

```bash
$SCRIPT stop probe
```

Clears the composer (`C-u`), then sends `/exit` before killing tmux. The clear matters because ghost/suggestion text can be sitting in the composer after an action-capable turn, and `/exit` appended to it would submit the lot as a prompt nobody wrote. The clean exit matters for mesh work: it deregisters, while a kill leaves a roster ghost for the 60–120s expiry window that will confuse the next test.

## Driving TUI menus (/config, /hooks)

The `key` verb sends named tmux keys — `Down`, `Up`, `Escape`, `PPage`, `NPage`, `Tab`, `Enter`, `C-c` — one argument per press, repeats allowed. Menus need `key`; prose needs `keys` (which sends literally, so text that happens to be a key name is typed, not pressed).

```bash
$SCRIPT keys probe "/hooks"          # open the menu (keys types, settles ~1s, submits)
$SCRIPT key  probe Down Down Enter   # walk to an event and open it
$SCRIPT read probe -n 30             # read the matcher list
$SCRIPT key  probe Escape            # back out without changing anything
```

- **`/hooks` answers settings-scope questions no file read can:** each matcher line carries its source — `[User]`, `[Local]`, `[Plugin]` — so "which file contributed this hook?" reads straight off the screen.
- **`/config`:** type-to-filter works at the search box, and `/` re-opens search from the list.
- **Prefer `Escape` to back out** when the goal is observation — it leaves settings uncommitted.

## Common Mistakes

| Mistake | Symptom | Better |
|---|---|---|
| `env -u FOO claudem` | `env: 'claudem': No such file or directory` | `env` execs a binary; a shell function is not one. Use `--unset`, which scrubs inside the shell. |
| `bash -lc 'claudem'` | `claudem: command not found` | bashrc returns early when non-interactive, so wrapper functions are never defined. `start` uses a genuine interactive shell for exactly this reason. |
| Launching in an untrusted cwd | An unexpected trust dialog, then a new entry in the user's config | Pick an already-trusted folder (step 1). |
| `sleep 30; capture-pane` | Flaky and slow at the same time | `wait` with a pattern. |
| Reading the pane once and concluding | An absence that is really a timing artefact | Include a positive control; assert the thing that *should* appear does. |
| Killing the session outright | Roster ghosts, dirty state, missed teardown hooks | `stop` (it sends `/exit` first). |
| Testing in a repo with its own `.mcp.json` | Two MCP servers, one agent id, confusing results | Drive from a neutral trusted folder. |
| Blind `enter` after an action-capable turn | Ghost/suggestion text in the composer submits as a prompt nobody wrote | `read` the pane first; `key NAME C-u` clears anything sitting there. `stop` does this automatically before `/exit`. |

## Quick Reference

```bash
$SCRIPT start NAME [--cwd DIR] [--unset VAR]... -- CMD...   # launch under tmux
$SCRIPT wait  NAME REGEX [TIMEOUT_S]                        # block until it appears
$SCRIPT keys  NAME "text" [--no-enter]                      # type + submit (settles ~1s before Enter)
$SCRIPT key   NAME KEY [KEY...]                             # named keys: Down Escape PPage Tab ...
$SCRIPT enter NAME                                          # bare Enter (confirm a dialog)
$SCRIPT read  NAME [-n LINES] [--all]                       # what is on screen
$SCRIPT stop  NAME [--no-exit]                              # clear composer, /exit, then kill
$SCRIPT list                                                # live hublot sessions
```

Pane size: `HUBLOT_COLS` / `HUBLOT_ROWS` (default 200×50).

## Integration

- **ardoise** — isolates *what a session knows*; hublot drives *what a session does*. Compose them to test a fresh user's onboarding, dialogs included, without a human.
- **sonnette / mesh work** — the receive path is interactive-only, so hublot is the only honest way to verify it. Read `/tmp/conductor-bridge/{agentId}/capability` alongside the pane for the session's own send-only/bidirectional verdict.
- **bon** — when a test produces a finding, file it; when it produces a technique, extend this skill.

## Dependencies

`tmux`. Everything else is the session under test.

---
name: ardoise
allowed-tools: [Bash, Read, Write]
description: >
  Run Claude on a blank slate — full context isolation via env scrub
  (env -i + temporary HOME + /tmp CWD) with zero context leakage.
  Two modes: interactive TUI (default) for manual testing like plugin installs,
  or print mode (-p) for automated probes and evals. INVOKE BEFORE spawning a
  Claude that MUST be uncontaminated — evals, design research, cold critique,
  baseline comparisons, or plugin testing. Cross-platform (Linux + macOS),
  no containers required. Triggers on 'blank slate claude', 'fresh claude',
  'isolated claude', 'clean claude', 'run without context', 'test plugin install',
  'out of box claude', 'ardoise'. (user)
---

# Ardoise

Run Claude on a blank slate. The spawned Claude sees only its training weights and built-in skills — no CLAUDE.md, no custom skills, no hooks, no plugins, no project context. Like a restaurant's ardoise wiped clean.

Two modes:
- **Interactive** (default) — opens Claude's TUI as a fresh user would see it. For manual testing: plugin installs, onboarding flows, "what does a new user experience?"
- **Print** (`-p`) — runs `claude -p` for automated/scripted use. For surveys, evals, cold critique.

## When to Use

- **Plugin testing** — does `claude plugin install` work for someone with a default `~/.claude`?
- **Design research** — what verbs, patterns, or names would a Claude naturally produce?
- **Skill evaluation** — does a naive Claude understand a SKILL.md on first read?
- **Eval baselines** — "without skill" control group for A/B testing
- **Isolation testing** — verify a prompt works without your ecosystem's context
- **Cold critique** — get feedback uncoloured by your conventions

## When NOT to Use

- **Security sandboxing** — this is context isolation, not filesystem/process isolation. The spawned Claude can still read host files if it knows the paths. Use containers for security.
- **Testing your skills work** — you want context loaded for that, not stripped

## How It Works

Three mechanisms, all cross-platform (POSIX):

| Mechanism | What it blocks |
|-----------|---------------|
| `env -i` | All inherited env vars including `CLAUDECODE=1` (nesting detection) |
| `HOME=<tmpdir>` with stripped `claude.json` + credentials only | CLAUDE.md, settings.json, hooks, skills, plugins, MCP config |
| `cd /tmp` (or chosen dir) | Project CLAUDE.md, git repo context, local `.claude/` directories |

Additional env vars suppress noise:

| Var | Effect |
|-----|--------|
| `CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY=1` | No survey popups |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` | No telemetry |
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` | No auto memory files |
| `ENABLE_CLAUDEAI_MCP_SERVERS=false` | No built-in Gmail/Calendar MCP |

The `claude.json` is copied from the real one (preserving onboarding state and feature flags) but stripped of project data, skill usage, and marketplace auto-install.

## Usage

The script lives in the trousse plugin. Find it at runtime:

```bash
SCRIPT=$(find ~/.claude/plugins/cache -path "*/trousse/*/scripts/ardoise.sh" 2>/dev/null | head -1)
[ -z "$SCRIPT" ] && SCRIPT="${CLAUDE_PLUGIN_ROOT}/scripts/ardoise.sh"
```

### Interactive mode (default)

```bash
"$SCRIPT"                    # TUI in /tmp
"$SCRIPT" ~/some/project     # TUI in a specific directory
```

Opens Claude's interactive TUI. You type commands yourself — `claude plugin install`, `/doctor`, whatever you want to test manually.

### Print mode

```bash
"$SCRIPT" -p "What is the best way to structure a CLI?"
"$SCRIPT" -p --max-turns 1 "Reply with only: hello"
echo "Design a work tracker" | "$SCRIPT" -p --stdin --max-turns 1
```

### From Claude Code (OuterClaude calling InnerClaude)

```bash
# In a Bash tool call:
"$SCRIPT" -p --max-turns 1 "Your prompt here"
```

The `env -i` scrub removes `CLAUDECODE=1`, so the inner Claude doesn't know it's nested. No launch resistance.

## What the Ardoise Claude Sees

| Layer | Visible? |
|-------|----------|
| Global CLAUDE.md | No |
| Project CLAUDE.md | No |
| Custom skills (plugin cache) | No |
| Built-in skills (simplify, loop, claude-api) | Yes — compiled into Claude Code |
| Hooks | No |
| MCP servers | No |
| Plugins | No |
| Host filesystem | Yes — context isolation, not security sandboxing |

## Key Discovery: The ~/.claude.json Symlink

Claude Code reads config from `$HOME/.claude.json` (a symlink in HOME root), not directly from `$HOME/.claude/claude.json`. Without this symlink in the temp HOME, Claude treats every launch as brand new and shows the onboarding wizard. The script creates this symlink automatically.

## Composing with Other Skills

| Skill | How they compose |
|-------|-----------------|
| **claude-survey** | Survey uses ardoise in print mode as its isolation backend |
| **skill-forge** | Eval baselines — run prompts without the skill for A/B comparison |
| **sandbox** | Sandbox provides security isolation (containers/VMs); ardoise provides context isolation. Different threat models. |
| **sprite** | Sprite handles TTY interaction for remote VMs; ardoise handles local context stripping. They compose for isolated remote testing. |

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------|-----------|-----|
| Use Agent/Task tool for "naive" testing | Subagents inherit full parent context | Use this script via Bash tool |
| Pass `--system-prompt` and assume isolation | CLAUDE.md still loads | Use ardoise.sh |
| Use `--allowed-tools ""` for tool-free mode | Model burns turns trying tools | Pass `--tools ""` |
| Mount the real HOME | Context leaks | Let the script handle HOME |
| Forget the `~/.claude.json` symlink | Onboarding wizard every time | Script handles this automatically |

# Cowork Environment Reference

Captured 2026-03-27 from a live Cowork session. Use this when building or debugging plugins for Desktop.

## Detection

```bash
if [ "$CLAUDE_CODE_IS_COWORK" = "1" ]; then
  # Cowork environment — adjust accordingly
fi
```

## OS and Runtime

- **Kernel:** Linux 6.8.0 aarch64 (ARM64 VM)
- **Distro:** Ubuntu 22.04.5 LTS
- **Python:** 3.10.12 (no pyenv, no upgrade path)
- **Node.js:** 22.22.0
- **Git:** 2.34.1
- **uv:** 0.10.4
- **pip:** available, `--break-system-packages` required

## Package Installation

```bash
# pip — installs to /usr/local/bin (in PATH)
pip install --break-system-packages git+https://github.com/user/repo.git

# uv — installs to ~/.local/bin (NOT in PATH by default)
export PATH="$HOME/.local/bin:$PATH"
uv tool install git+https://github.com/user/repo.git
```

**Prefer pip** in Cowork — it puts binaries in `/usr/local/bin` which is already in PATH.

## Filesystem

| Path | What | Writable | Persistent |
|------|------|----------|-----------|
| `$HOME/` | Session home (ephemeral username) | Yes | No |
| `$HOME/mnt/work/` | User's mounted workspace | Yes | Yes |
| `$HOME/mnt/.claude/` | Claude config | Read-only | Yes |
| `$HOME/mnt/.remote-plugins/` | Installed plugins | Read-only | Yes |
| `$HOME/mnt/.auto-memory/` | Cowork persistent memory | Yes | Yes |
| `$HOME/mnt/uploads/` | User-uploaded files | Read-only | N/A |
| `$HOME/tmp/` | CLAUDE_TMPDIR | Yes | No |
| `/tmp/` | System temp | Yes | No |

**Root disk:** ~2.4GB free. Session volume: ~9.3GB free.

## What Doesn't Work

| Feature | CLI | Cowork | Notes |
|---------|-----|--------|-------|
| Hooks (SessionStart, etc.) | Yes | **No** | Skills are the only plugin interface |
| `CLAUDE_PLUGIN_ROOT` | Yes | **No** | Plugins can't self-reference |
| `~/.local/bin` in PATH | Yes | **No** | Must export PATH or use pip |
| Access to `~/Repos/` | Yes | **No** | Only selected workspace mounted |
| Persistent pip installs | N/A | **No** | Gone each session |
| Background tasks / cron | Yes | **No** | Disabled via env vars |
| `.bashrc` persistence | Yes | **No** | Ephemeral home dir |

## SKILL.md Frontmatter Rules

The Cowork backend is stricter than CLI. Invalid frontmatter silently drops skills.

```yaml
# GOOD — works in both CLI and Cowork
---
name: my-skill
description: "Plain quoted string, no special annotations."
allowed-tools: Bash, Read, Glob, "Bash(bon:*)"
---

# BAD — breaks Cowork
---
name: my-skill
description: >
  Multi-line with (user) annotation. (user)
allowed-tools: [Bash, Read, Glob]
requires:
  - cli: something
    check: "something --version"
---
```

**Rules:**
- `allowed-tools`: comma-separated string, not YAML array
- `description`: quoted string, no `(user)` suffix
- No `requires:` field (not recognised, nested YAML fails)
- Skill name cannot contain "claude" (reserved word)

## Key Environment Variables

| Variable | Value |
|----------|-------|
| `CLAUDE_CODE_IS_COWORK` | `1` |
| `CLAUDE_CODE_HOST_PLATFORM` | `darwin` (user's actual OS) |
| `CLAUDE_CODE_WORKSPACE_HOST_PATHS` | Host-side path of mounted workspace |
| `CLAUDE_CODE_SUBAGENT_MODEL` | `claude-haiku-4-5-20251001` |
| `CLAUDE_CODE_DISABLE_CRON` | `1` |
| `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` | `1` |

## Plugin Author Checklist

- [ ] Skills use flat frontmatter (no arrays, no nested objects)
- [ ] Skill name doesn't contain "claude"
- [ ] CLI tools installed via `pip install --break-system-packages git+https://...`
- [ ] No dependency on `CLAUDE_PLUGIN_ROOT`
- [ ] No dependency on hooks firing
- [ ] Python code compatible with 3.10 (no `datetime.UTC`, no `tomllib`, no `StrEnum`)
- [ ] No assumption about `~/.local/bin` being in PATH
- [ ] All public repos (private repos need auth tokens Cowork doesn't have)

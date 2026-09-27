#!/bin/bash
# SessionStart hook: ensure the sonner CLI is on PATH and the always-on rules
# shard is linked, and that the CLI is no older than the wheel this plugin
# ships. The comparison is against the WHEEL's filename (the tool's own
# version), never plugin.json's stamped SUITE version, which is
# structurally false (bds-japoca). Silent when fine.

export PATH="$HOME/.local/bin:$PATH"
FIXED=""
ISSUES=""

# Capture auto-install output so failures are diagnosable, not silent.
UPDATE_LOG="$HOME/.cache/sonner/auto-update.log"
mkdir -p "$(dirname "$UPDATE_LOG")" 2>/dev/null

# --- Instruction shard ---
# Copy into <config dir>/rules/ so the always-on shard loads every session.
# Idempotent — temp+mv replaces whatever entry is there, a stale symlink included.
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(dirname "$HOOK_DIR")"
if [ -f "$PLUGIN_ROOT/instructions.md" ]; then
    # Honour CLAUDE_CONFIG_DIR (bds-wuvola): a second config dir (the commis
    # seat) loads its own rules/. Copy via temp+mv, NOT a symlink (bds-zilesu):
    # the plugin root can be an ephemeral session dir that Desktop or Cowork
    # purges, and a symlink into it dies silently. The copy is rewritten every
    # session start, so it cannot go stale for long — edit instructions.md, not
    # the copy. Same pattern as mise, accomplis and passe.
    RULES_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/rules"
    mkdir -p "$RULES_DIR"
    _tmp="$(mktemp "$RULES_DIR/sonner.md.XXXXXX")" \
        && cat "$PLUGIN_ROOT/instructions.md" > "$_tmp" \
        && mv -f "$_tmp" "$RULES_DIR/sonner.md"
fi

# Resolve install source. A source checkout carries pyproject.toml; the
# vendored marketplace plugin does not (skill-plugin copy list ships no
# Python), but it does carry a wheel the assembler builds (bds-timule).
if [ -n "$PLUGIN_ROOT" ] && [ -f "$PLUGIN_ROOT/pyproject.toml" ]; then
    INSTALL_SRC="$PLUGIN_ROOT"
elif _WHEELS=("$(dirname "$HOOK_DIR")"/wheels/sonner-*.whl) && [ -f "${_WHEELS[0]}" ]; then
    # The marketplace plugin ships no pyproject.toml, but the assembler builds
    # this CLI into a wheel beside this hook (bds-timule, 2026-09-23) — so a
    # clean machine installs from the public marketplace alone, and the source
    # repo can stay private.
    INSTALL_SRC="${_WHEELS[0]}"
    WHEEL="${_WHEELS[0]}"
else
    # Maintainer fallback: the source repo is private, so this works only with
    # GitHub credentials. Reached when a plugin copy predates shipped wheels.
    INSTALL_SRC="git+https://github.com/spm1001/sonner"
fi

# CLI missing → auto-install. No version claim in the report — sonner has no
# --version flag, and claiming a number nobody read is the bds-zelowe bug.
if ! command -v sonner &>/dev/null; then
    if uv tool install "$INSTALL_SRC" --force --reinstall --no-cache >"$UPDATE_LOG" 2>&1; then
        FIXED="${FIXED}• sonner CLI installed\n"
    else
        ISSUES="${ISSUES}• sonner CLI not found and auto-install failed (full error: ${UPDATE_LOG}). Run manually:\n\n  uv tool install \"$INSTALL_SRC\" --force --reinstall --no-cache\n"
    fi
fi

# CLI older than the shipped wheel → reinstall from it (local file, no
# network). The wheel's filename carries sonner's own version, so this compares
# like with like, unlike plugin.json's suite stamp (bds-japoca). Upgrade only:
# a maintainer's newer from-source install is never replaced. Without this
# the skills auto-update while the CLI keeps its first install forever on any
# machine where nobody runs /batterie:update (a family Mac, 2026-09-23;
# bon-rikaka carries the same fix for bon).
if [ -n "${WHEEL:-}" ] && command -v sonner &>/dev/null; then
    WANT=$(basename "$WHEEL" | sed -E 's/^sonner-([0-9]+\.[0-9]+\.[0-9]+).*/\1/')
    HAVE=$(uv tool list 2>/dev/null | awk '$1=="sonner"{sub(/^v/,"",$2); print $2}' | head -1)
    OLDEST=$(printf '%s\n%s\n' "${HAVE:-0.0.0}" "$WANT" | sort -V | head -1)
    if [ "${HAVE:-0.0.0}" != "$WANT" ] && [ "$OLDEST" = "${HAVE:-0.0.0}" ]; then
        if uv tool install "$INSTALL_SRC" --force --reinstall --no-cache >"$UPDATE_LOG" 2>&1; then
            FIXED="${FIXED}• sonner CLI updated v${HAVE:-unknown} → v${WANT} from the plugin's own wheel\n"
        else
            ISSUES="${ISSUES}• sonner CLI is v${HAVE:-unknown}, older than the plugin's v${WANT}, and the update failed (full error: ${UPDATE_LOG}). Run manually:\n\n  uv tool install \"$INSTALL_SRC\" --force --reinstall --no-cache\n"
        fi
    fi
fi

# Silent exit if nothing happened
[ -z "$FIXED" ] && [ -z "$ISSUES" ] && exit 0

# Report
MSG=""
[ -n "$FIXED" ] && MSG="${MSG}✓ sonner auto-fixed:\n\n${FIXED}"
[ -n "$ISSUES" ] && MSG="${MSG}⚠️ sonner needs attention:\n\n${ISSUES}"

python3 -c "import json; print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': '''${MSG}'''}}))"

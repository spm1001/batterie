#!/bin/bash
# SessionStart hook: ensure the passe CLI is available and no older than the
# wheel this plugin ships. The comparison is against the WHEEL's filename (the tool's own
# version), never plugin.json's stamped SUITE version, which is
# structurally false (bds-japoca). Silent when fine.

# Skip for subagent invocations (fork bomb prevention)
[ -n "${CLAUDE_SUBAGENT:-}" ] && exit 0

export PATH="$HOME/.local/bin:$PATH"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXED=""
ISSUES=""

# Capture auto-update output so failures are diagnosable, not silent (bon-babuse / bon-mavemi).
UPDATE_LOG="$HOME/.cache/passe/auto-update.log"
mkdir -p "$(dirname "$UPDATE_LOG")" 2>/dev/null

# Resolve install source
if [ -n "$PLUGIN_ROOT" ] && [ -f "$PLUGIN_ROOT/pyproject.toml" ]; then
    INSTALL_SRC="$PLUGIN_ROOT"
elif _WHEELS=("$(dirname "$HOOK_DIR")"/wheels/passe-*.whl) && [ -f "${_WHEELS[0]}" ]; then
    # The marketplace plugin ships no pyproject.toml, but the assembler builds
    # this CLI into a wheel beside this hook (bds-timule, 2026-09-23) — so a
    # clean machine installs from the public marketplace alone, and the source
    # repo can stay private.
    INSTALL_SRC="${_WHEELS[0]}"
    WHEEL="${_WHEELS[0]}"
else
    # Maintainer fallback: the source repo is private, so this works only with
    # GitHub credentials. Reached when a plugin copy predates shipped wheels.
    INSTALL_SRC="passe @ git+https://github.com/spm1001/passe"
fi

# Check 1: CLI missing → auto-install.
# Report the version that ACTUALLY landed (re-read post-install), never an
# expected number — the old hook claimed the plugin.json version without
# checking, and misreported every session (bds-zelowe).
if ! command -v passe &>/dev/null; then
    if uv tool install "$INSTALL_SRC" --force --reinstall --no-cache >"$UPDATE_LOG" 2>&1; then
        LANDED=$(passe --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")
        FIXED="${FIXED}• passe CLI installed (v${LANDED})\n"
    else
        ISSUES="${ISSUES}• passe CLI not found and auto-install failed (full error: ${UPDATE_LOG}). Run manually:\n\n  uv tool install \"$INSTALL_SRC\" --force --reinstall --no-cache\n"
    fi
fi

# CLI older than the shipped wheel → reinstall from it (local file, no
# network). The wheel's filename carries passe's own version, so this compares
# like with like, unlike plugin.json's suite stamp (bds-japoca). Upgrade only:
# a maintainer's newer from-source install is never replaced. Without this
# the skills auto-update while the CLI keeps its first install forever on any
# machine where nobody runs /batterie:update (a family Mac, 2026-09-23;
# bon-rikaka carries the same fix for bon).
if [ -n "${WHEEL:-}" ] && command -v passe &>/dev/null; then
    WANT=$(basename "$WHEEL" | sed -E 's/^passe-([0-9]+\.[0-9]+\.[0-9]+).*/\1/')
    HAVE=$(passe --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    OLDEST=$(printf '%s\n%s\n' "${HAVE:-0.0.0}" "$WANT" | sort -V | head -1)
    if [ "${HAVE:-0.0.0}" != "$WANT" ] && [ "$OLDEST" = "${HAVE:-0.0.0}" ]; then
        if uv tool install "$INSTALL_SRC" --force --reinstall --no-cache >"$UPDATE_LOG" 2>&1; then
            FIXED="${FIXED}• passe CLI updated v${HAVE:-unknown} → v${WANT} from the plugin's own wheel\n"
        else
            ISSUES="${ISSUES}• passe CLI is v${HAVE:-unknown}, older than the plugin's v${WANT}, and the update failed (full error: ${UPDATE_LOG}). Run manually:\n\n  uv tool install \"$INSTALL_SRC\" --force --reinstall --no-cache\n"
        fi
    fi
fi

# Silent exit if nothing happened
[ -z "$FIXED" ] && [ -z "$ISSUES" ] && exit 0

# Report
MSG=""
[ -n "$FIXED" ] && MSG="${MSG}✓ passe auto-fixed:\n\n${FIXED}"
[ -n "$ISSUES" ] && MSG="${MSG}⚠️ passe needs attention:\n\n${ISSUES}"

# Render via json.dumps so messages containing quotes (e.g. the quoted INSTALL_SRC in
# recovery commands) produce valid JSON — a raw heredoc does not escape them (bon-mavemi).
python3 -c "import json; print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': '''${MSG}'''}}))"

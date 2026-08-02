#!/bin/bash
# SessionStart hook: ensure todoist CLI is available and has a token.
# Install-if-MISSING only — no version-drift check here. Post single-version
# cutover the vendored plugin.json carries the stamped SUITE version, not
# todoist-gtd's own, so any version comparison at session start is
# structurally false (bds-japoca). Freshness is /batterie:update's job
# (commit-based). Silent when fine.

export PATH="$HOME/.local/bin:$PATH"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
FIXED=""
ISSUES=""

# Capture auto-update output so failures are diagnosable, not silent (bon-babuse / bon-mavemi).
UPDATE_LOG="$HOME/.cache/todoist/auto-update.log"
mkdir -p "$(dirname "$UPDATE_LOG")" 2>/dev/null

# Resolve install source
if [ -n "$PLUGIN_ROOT" ] && [ -f "$PLUGIN_ROOT/pyproject.toml" ]; then
    INSTALL_SRC="$PLUGIN_ROOT"
else
    # Vendored marketplace plugin ships no pyproject.toml (post-2026-06-10 cutover),
    # so install from the source repo over git — the bare name is not published on PyPI.
    INSTALL_SRC="todoist-gtd @ git+https://github.com/spm1001/todoist-gtd"
fi

# Check 1: CLI missing → auto-install.
# Report the version that ACTUALLY landed (re-read post-install), never an
# expected number — the old hook claimed the plugin.json version without
# checking, and misreported every session (bds-zelowe).
if ! command -v todoist &>/dev/null; then
    if uv tool install "$INSTALL_SRC" --force --reinstall --no-cache >"$UPDATE_LOG" 2>&1; then
        LANDED=$(todoist --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")
        FIXED="${FIXED}• todoist CLI installed (v${LANDED})\n"
    else
        ISSUES="${ISSUES}• todoist CLI not found and auto-install failed (full error: ${UPDATE_LOG}). Run manually:\n\n  uv tool install \"$INSTALL_SRC\" --force --reinstall --no-cache\n"
    fi
fi

# Check 2: API token (env var, macOS Keychain, or file)
HAS_TOKEN=false
if [ -n "${TODOIST_API_KEY:-}" ]; then
    HAS_TOKEN=true
elif command -v security &>/dev/null && security find-generic-password -s "todoist-api-key" -w &>/dev/null; then
    HAS_TOKEN=true
elif [ -f "$HOME/.todoist-token" ]; then
    HAS_TOKEN=true
elif [ -f "$HOME/.claude/plugins/data/todoist-gtd-batterie/token" ]; then
    HAS_TOKEN=true
elif [ -f "$HOME/.claude/plugins/data/todoist-gtd-batterie-de-savoir/token" ]; then
    # Pre-cutover dir name — token_store migrates it on first CLI read
    HAS_TOKEN=true
fi
if [ "$HAS_TOKEN" = false ]; then
    ISSUES="${ISSUES}• No Todoist API token found. Run: todoist auth\n"
fi

# Silent exit if nothing happened
[ -z "$FIXED" ] && [ -z "$ISSUES" ] && exit 0

# Report
MSG=""
[ -n "$FIXED" ] && MSG="${MSG}✓ todoist auto-fixed:\n\n${FIXED}"
[ -n "$ISSUES" ] && MSG="${MSG}⚠️ Todoist needs attention:\n\n${ISSUES}"

# Render via json.dumps so messages containing quotes (e.g. the quoted INSTALL_SRC in
# recovery commands) produce valid JSON — a raw heredoc does not escape them (bon-mavemi).
python3 -c "import json; print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': '''${MSG}'''}}))"

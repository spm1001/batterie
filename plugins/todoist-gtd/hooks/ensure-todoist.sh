#!/bin/bash
# SessionStart hook: ensure todoist CLI is available, version-aligned, and has a token.
# Auto-fixes drift; reports what it did. Silent when everything is fine.

export PATH="$HOME/.local/bin:$PATH"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
FIXED=""
ISSUES=""

# Resolve install source
if [ -n "$PLUGIN_ROOT" ] && [ -f "$PLUGIN_ROOT/pyproject.toml" ]; then
    INSTALL_SRC="$PLUGIN_ROOT"
else
    # Vendored marketplace plugin ships no pyproject.toml (post-2026-06-10 cutover),
    # so install from the source repo over git — the bare name is not published on PyPI.
    INSTALL_SRC="todoist-gtd @ git+https://github.com/spm1001/todoist-gtd"
fi

# Check 1: CLI missing → auto-install
if ! command -v todoist &>/dev/null; then
    if uv tool install "$INSTALL_SRC" --force --reinstall >/dev/null 2>&1; then
        FIXED="${FIXED}• todoist CLI installed\n"
    else
        ISSUES="${ISSUES}• todoist CLI not found and auto-install failed. Run manually:\n\n  uv tool install \"$INSTALL_SRC\"\n"
    fi
fi

# Check 2: version drift → auto-update
if [ -z "$ISSUES" ] && command -v todoist &>/dev/null; then
    if [ -n "$PLUGIN_ROOT" ] && [ -f "$PLUGIN_ROOT/.claude-plugin/plugin.json" ]; then
        INSTALLED=$(todoist --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || true)
        EXPECTED=$(python3 -c "import json; print(json.load(open('$PLUGIN_ROOT/.claude-plugin/plugin.json'))['version'])" 2>/dev/null || true)
        if [ -n "$INSTALLED" ] && [ -n "$EXPECTED" ] && [ "$INSTALLED" != "$EXPECTED" ]; then
            CLI_BEHIND=$(python3 -c "print(tuple(int(x) for x in '$INSTALLED'.split('.')) < tuple(int(x) for x in '$EXPECTED'.split('.')))" 2>/dev/null || true)
            if [ "$CLI_BEHIND" = "True" ]; then
                if uv tool install "$INSTALL_SRC" --force --reinstall >/dev/null 2>&1; then
                    FIXED="${FIXED}• todoist CLI updated: v${INSTALLED} → v${EXPECTED}\n"
                else
                    ISSUES="${ISSUES}• todoist CLI is v${INSTALLED} but plugin is v${EXPECTED}. Auto-update failed.\n"
                fi
            fi
        fi
    fi
fi

# Check 3: API token (env var, macOS Keychain, or file)
HAS_TOKEN=false
if [ -n "${TODOIST_API_KEY:-}" ]; then
    HAS_TOKEN=true
elif command -v security &>/dev/null && security find-generic-password -s "todoist-api-key" -w &>/dev/null; then
    HAS_TOKEN=true
elif [ -f "$HOME/.todoist-token" ]; then
    HAS_TOKEN=true
elif [ -f "$HOME/.claude/plugins/data/todoist-gtd-batterie-de-savoir/token" ]; then
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

cat <<EOF
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "${MSG}"}}
EOF

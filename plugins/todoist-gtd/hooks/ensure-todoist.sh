#!/bin/bash
# SessionStart hook: ensure todoist CLI and API token are available
# Silent when everything is fine; helpful when it's not.

# Ensure ~/.local/bin is in PATH (where uv tool install puts binaries)
export PATH="$HOME/.local/bin:$PATH"

ISSUES=""

# 1. Check CLI
if ! command -v todoist &>/dev/null; then
    PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
    if [ -n "$PLUGIN_ROOT" ] && [ -f "$PLUGIN_ROOT/pyproject.toml" ]; then
        ISSUES="${ISSUES}• todoist CLI not found. Install: uv tool install \"$PLUGIN_ROOT\" && export PATH=\"\$HOME/.local/bin:\$PATH\"\n"
    else
        ISSUES="${ISSUES}• todoist CLI not found. Install: uv tool install todoist-gtd && export PATH=\"\$HOME/.local/bin:\$PATH\"\n"
    fi
fi

# 2. Check API token (env var, macOS Keychain, or file)
HAS_TOKEN=false
if [ -n "${TODOIST_API_KEY:-}" ]; then
    HAS_TOKEN=true
elif command -v security &>/dev/null && security find-generic-password -s "todoist-api-key" -w &>/dev/null; then
    HAS_TOKEN=true
elif [ -f "$HOME/.todoist-token" ]; then
    HAS_TOKEN=true
fi
if [ "$HAS_TOKEN" = false ]; then
    ISSUES="${ISSUES}• No Todoist API token found. Run: todoist auth\n"
fi

# If no issues, exit silently
[ -z "$ISSUES" ] && exit 0

cat <<EOF
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "⚠️ Todoist setup needed:\n\n${ISSUES}"}}
EOF

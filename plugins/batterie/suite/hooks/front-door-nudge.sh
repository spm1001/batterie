#!/bin/sh
# Launcher for front-door-nudge.py (plugin.json wires it on SessionStart,
# UserPromptSubmit and PreToolUse). The nudge never blocks anything, so every
# failure here is fail-open: no python3, or a python3 that will not run, lets
# the call through silently (a reminder is not worth a refused call).
#
# Fast path: PreToolUse fires on every tool call in every session. Python
# leaves <session>.on in the state dir only while a session is a live front
# door, so any other session pays one file test here instead of ~30 ms of
# interpreter start (measured 22 Nov 2026 on the atelier).
case " $* " in
  *" --event tool "*)
    input=$(cat)
    # First occurrence: Claude Code writes session_id before tool_input, whose text may quote the key.
    sid=$(printf '%s' "$input" | grep -o '"session_id" *: *"[^"]*"' | head -n 1 | sed 's/.*"\([^"]*\)"$/\1/' | tr -c 'A-Za-z0-9_\n-' '_' | cut -c1-80)
    dir=${BATTERIE_NUDGE_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/batterie/front-door}
    [ -n "$sid" ] && [ -e "$dir/$sid.on" ] || exit 0
    ;;
esac
command -v python3 >/dev/null 2>&1 || exit 0
if [ "$(uname -s)" = Darwin ] && [ "$(command -v python3)" = /usr/bin/python3 ] \
    && ! /usr/bin/xcode-select -p >/dev/null 2>&1; then
  exit 0
fi
if [ -n "${input+set}" ]; then
  printf '%s' "$input" | python3 "$(dirname "$0")/front-door-nudge.py" "$@"
else
  python3 "$(dirname "$0")/front-door-nudge.py" "$@"
fi
exit 0

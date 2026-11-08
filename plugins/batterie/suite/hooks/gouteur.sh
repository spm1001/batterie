#!/bin/sh
# goûteur's launcher (plugin.json wires it for PreToolUse, PostToolUse and
# PermissionRequest). python3 is the one dependency: without it, say so on
# stderr and let the call through, because a missing interpreter is a
# designed failure. Everything else, including the --pre gate's fail-closed
# crash handling, is gouteur.py's job.
command -v python3 >/dev/null 2>&1 || {
  echo "goûteur: skipped, no python3 on PATH (fail-open)" >&2
  exit 0
}
# macOS ships /usr/bin/python3 as a stub that offers to install the command
# line tools; without them, running it pops a dialog and fails. Treat that as
# "no python3" rather than prompting on every tool call.
if [ "$(uname -s)" = Darwin ] && [ "$(command -v python3)" = /usr/bin/python3 ] \
    && ! /usr/bin/xcode-select -p >/dev/null 2>&1; then
  echo "goûteur: skipped, macOS python3 needs the command line tools (xcode-select --install) (fail-open)" >&2
  exit 0
fi
exec python3 "$(dirname "$0")/gouteur.py" "$@"

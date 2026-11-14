#!/bin/sh
# goûteur's launcher (plugin.json wires it for PreToolUse, PostToolUse and
# PermissionRequest). python3 is the one dependency: without it, say so on
# stderr and let the call through, because a missing interpreter is a
# designed failure. A crash INSIDE gouteur.py's main() is gouteur.py's job
# (it denies with a reason); a crash before main() runs is this file's.
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

# --pre fails CLOSED when gouteur.py cannot even start. A SyntaxError or a
# module-level ImportError (a 3.10+ construct reaching macOS's 3.9) exits 1,
# and Claude Code runs the call on any PreToolUse exit other than 2 — measured
# 2026-11-14 with claude -p and a stub hook (exit 1: the call ran; exit 2:
# blocked). Without this, a broken import silently switched every guard off on
# every session (facobi; Bright Lines' hook command does the same thing).
# Escape: a session locked out of Bash/Read/Grep/Glob cannot Read the file to
# Edit it, but Write can make a NEW file, so a fresh pass file lets calls
# through. It counts only while gouteur.py is broken, and only for 24 hours.
case " $* " in
  *" --pre "*)
    python3 "$(dirname "$0")/gouteur.py" "$@"
    rc=$?
    [ "$rc" -eq 0 ] || [ "$rc" -eq 2 ] && exit "$rc"
    # A broken INTERPRETER (a pyenv/asdf shim pinned to a Python that is not
    # installed, a Mac's stale command line tools) is the designed no-python3
    # case above, not a broken gouteur.py: let it through and say so.
    if ! python3 -c pass >/dev/null 2>&1; then
      echo "goûteur: skipped, python3 is on PATH but will not run (fail-open)" >&2
      exit 0
    fi
    pass="${GOUTEUR_STATE_DIR:-$HOME/.local/state/gouteur}/broken-pass"
    if [ -n "$(find "$pass" -mmin -1440 2>/dev/null)" ]; then
      echo "{\"systemMessage\": \"goûteur could not start (exit $rc): this call ran UNGUARDED because $pass is under 24 h old. Fix gouteur.py, then delete that file.\"}"
      exit 0
    fi
    echo "goûteur could not start (exit $rc), so this call is refused rather than run with every guard off. The cause is in $(dirname "$0")/gouteur.py: a human shell can see it with 'python3 $(dirname "$0")/gouteur.py --self-test'. To work unguarded until it is fixed, create an empty file at $pass (the Write tool can, since it is a new file); it is honoured only while goûteur is broken, for 24 hours." >&2
    exit 2
    ;;
esac
exec python3 "$(dirname "$0")/gouteur.py" "$@"

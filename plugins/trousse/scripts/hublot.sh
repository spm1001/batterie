#!/usr/bin/env bash
# hublot.sh — Drive and watch a real interactive TUI session from a Claude
#
# The oven porthole: watch the real thing cooking, in its real environment,
# without opening the door and changing what you are measuring.
#
# WHY THIS EXISTS
#   `claude -p` is a DIFFERENT PRODUCT SURFACE, not a cheaper layer of the same
#   one. CC itself distinguishes them: CLAUDE_CODE_ENTRYPOINT reads "sdk-cli"
#   headless and "cli" interactive, and real behaviour differs. Inbound mesh
#   <channel> tags, trust and permission dialogs, the statusline, session-start
#   rituals — none of them exist in -p. Testing those headless and concluding
#   about interactive is the unearned green in its most convincing costume.
#   (Measured 2026-07-26, aboyeur aby-masogo.)
#
#   Before this script the technique was hand-rolled at least twice in one week
#   (aboyeur aby-lesefu 07-19; aby-masogo 07-26), losing the same time to the
#   same traps both times. The traps are baked in below.
#
# VERBS
#   start NAME [--cwd DIR] [--unset VAR]... [--] CMD...   launch under tmux
#   keys  NAME TEXT [--no-enter]                          type into it (literal)
#   key   NAME KEY [KEY...]                               named keys: Down Escape PPage ...
#   enter NAME                                            bare Enter (confirm a dialog)
#   read  NAME [-n LINES] [--all]                         what is on screen now
#   wait  NAME REGEX [TIMEOUT_S]                          block until it appears
#   stop  NAME [--no-exit]                                clean teardown
#   list                                                  live hublot sessions
#
# THE THREE TRAPS THIS SCRIPT EXISTS TO ABSORB
#   1. Shell functions need an INTERACTIVE shell. Wrappers like `claudem` are
#      bashrc functions: `bash -lc 'claudem'` fails (bashrc returns early when
#      non-interactive) and `env -u FOO claudem` fails harder (env execs a
#      binary; a function is not one). So `start` always sends the command into
#      a genuine interactive shell, and --unset scrubs env INSIDE it.
#   2. Launch from an ALREADY-TRUSTED folder. A new cwd raises CC's folder-trust
#      dialog, and answering it writes a durable trust entry into the user's
#      ~/.claude.json — a config change as a side effect of a test. Check first:
#      the trusted list is .projects[].hasTrustDialogAccepted.
#   3. Poll for a pattern, never sleep-and-hope. `wait` is the whole point:
#      hand-rolled `sleep 30; capture-pane` is flaky and slow at once.
#
# TYPICAL SESSION (what aby-masogo actually needed)
#   hublot.sh start probe --cwd <an-already-trusted-repo> \
#       --unset CLAUDE_CODE_USE_VERTEX --unset ANTHROPIC_MODEL -- claudem
#   hublot.sh wait  probe 'I am using this for local development' 60
#   hublot.sh enter probe                     # accept the channels dialog
#   hublot.sh wait  probe 'Channels .experimental.' 60
#   ... probe from outside, then:
#   hublot.sh read  probe
#   hublot.sh stop  probe

set -euo pipefail

PREFIX="hublot-"

die() { echo "hublot: $*" >&2; exit 1; }
need_tmux() { command -v tmux >/dev/null || die "tmux is not installed"; }
session_of() { echo "${PREFIX}$1"; }

usage() { sed -n '2,48p' "$0" | sed 's/^# \{0,1\}//'; }

cmd_start() {
    local name="$1"; shift
    local cwd="" unsets=() cmd=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --cwd)   cwd="$2"; shift 2 ;;
            --unset) unsets+=("$2"); shift 2 ;;
            --)      shift; cmd=("$@"); break ;;
            *)       cmd=("$@"); break ;;
        esac
    done
    [[ ${#cmd[@]} -gt 0 ]] || die "start needs a command (after --)"

    local s; s=$(session_of "$name")
    tmux has-session -t "$s" 2>/dev/null && die "session '$name' already exists (stop it first)"

    # A genuine interactive shell — trap 1. No -c, no -lc.
    tmux new-session -d -s "$s" -x "${HUBLOT_COLS:-200}" -y "${HUBLOT_ROWS:-50}"
    # tmux needs a beat before the shell is ready to receive keys.
    sleep 2

    local line=""
    [[ ${#unsets[@]} -gt 0 ]] && line+="unset ${unsets[*]}; "
    [[ -n "$cwd" ]] && line+="cd '$cwd' && "
    line+="${cmd[*]}"
    tmux send-keys -t "$s" "$line" Enter
    echo "started: $name (tmux session $s)"
}

cmd_keys() {
    local name="$1" text="$2"; shift 2
    local enter=Enter
    [[ "${1:-}" == "--no-enter" ]] && enter=""
    local s; s=$(session_of "$name")
    # -l sends TEXT literally, so prose that happens to be a tmux key name
    # ("Enter", "Space", "Down") is typed rather than interpreted. Named
    # keys are `key`'s job.
    tmux send-keys -t "$s" -l "$text"
    if [[ -n "$enter" ]]; then tmux send-keys -t "$s" Enter; fi
}

# Named keys for driving TUI menus (/config, /hooks): each argument is a tmux
# key name — Down, Up, Escape, PPage, NPage, Tab, Enter, C-c ... Repeat a key
# by repeating the argument: `key probe Down Down Down Enter`. Added 2026-08-17
# after a settings-scope investigation fell back to raw `tmux send-keys` five
# times in one evening (carte session 0bafcb96).
cmd_key() {
    local name="$1"; shift
    [[ $# -ge 1 ]] || die "key: need at least one key name"
    local s; s=$(session_of "$name")
    local k
    for k in "$@"; do tmux send-keys -t "$s" "$k"; done
}

cmd_enter() { tmux send-keys -t "$(session_of "$1")" Enter; }

cmd_read() {
    local name="$1"; shift
    local lines=40 scroll=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -n)    lines="$2"; shift 2 ;;
            --all) scroll=(-S -); lines=100000; shift ;;
            *)     shift ;;
        esac
    done
    tmux capture-pane -t "$(session_of "$name")" -p "${scroll[@]}" | grep -v '^$' | tail -n "$lines"
}

# Poll the pane until REGEX appears. Exit 0 on match, 1 on timeout — so a caller
# can branch. This is what replaces sleep-and-hope (trap 3).
cmd_wait() {
    local name="$1" pattern="$2" timeout="${3:-60}"
    local s; s=$(session_of "$name") deadline=$(( SECONDS + timeout ))
    while (( SECONDS < deadline )); do
        if tmux capture-pane -t "$s" -p 2>/dev/null | grep -qE "$pattern"; then
            echo "matched: $pattern"
            return 0
        fi
        sleep 2
    done
    echo "hublot: TIMEOUT after ${timeout}s waiting for: $pattern" >&2
    echo "--- pane at timeout ---" >&2
    tmux capture-pane -t "$s" -p 2>/dev/null | grep -v '^$' | tail -20 >&2
    return 1
}

# Clean teardown: let the app exit on its own terms first (a CC session
# deregisters from the mesh on /exit; SIGKILL leaves a roster ghost for the
# 60-120s expiry window), then kill the tmux session.
cmd_stop() {
    local name="$1"; shift
    local s; s=$(session_of "$name")
    tmux has-session -t "$s" 2>/dev/null || { echo "no such session: $name"; return 0; }
    if [[ "${1:-}" != "--no-exit" ]]; then
        tmux send-keys -t "$s" "/exit" Enter 2>/dev/null || true
        sleep 5
    fi
    tmux kill-session -t "$s" 2>/dev/null || true
    echo "stopped: $name"
}

cmd_list() {
    tmux list-sessions -F '#{session_name}' 2>/dev/null | grep "^${PREFIX}" | sed "s/^${PREFIX}//" || echo "(no hublot sessions)"
}

need_tmux
verb="${1:-}"; shift || true
case "$verb" in
    start) cmd_start "$@" ;;
    keys)  cmd_keys  "$@" ;;
    key)   cmd_key   "$@" ;;
    enter) cmd_enter "$@" ;;
    read)  cmd_read  "$@" ;;
    wait)  cmd_wait  "$@" ;;
    stop)  cmd_stop  "$@" ;;
    list)  cmd_list  "$@" ;;
    ""|-h|--help) usage ;;
    *) die "unknown verb '$verb' (try --help)" ;;
esac

#!/bin/bash
# remote-sessions — list Claude Code sessions that were spawned programmatically
# (teleport / Remote Control / SDK). These are invisible-or-nameless in the
# `claude --resume` picker, because they never get an `ai-title` entry — the
# title lives server-side only.
#
#   remote-sessions.sh          # 20 most recent
#   remote-sessions.sh 50       # 50 most recent
#   remote-sessions.sh -t       # only ones still teleport-resolvable
#
# The tell: these get a version-5 UUID (char 15 of the filename) because the id
# is derived by hashing a caller-supplied session id; ordinary interactive
# sessions get a v4. Measured: every v5 sampled had entrypoint=sdk-cli, while
# v4 is mixed — so v5 implies sdk-cli, not the converse.
#
# Portability: bash 3.2 clean (macOS /bin/bash) — no mapfile, no find -printf,
# no grep -P. jq is required.
set -eu

only_tp=0
[ "${1:-}" = "-t" ] && { only_tp=1; shift; }
n="${1:-20}"
command -v jq >/dev/null 2>&1 || { echo "remote-sessions: jq is required" >&2; exit 3; }

# stat/date differ between BSD (macOS) and GNU (Linux); pick once.
if stat -f '%m' / >/dev/null 2>&1; then
  _mtime() { stat -f '%m' "$1"; }
  _fmt()   { date -r "$1" '+%Y-%m-%d %H:%M'; }
else
  _mtime() { stat -c '%Y' "$1"; }
  _fmt()   { date -d "@$1" '+%Y-%m-%d %H:%M'; }
fi
first_line() { { IFS= read -r _x || true; } ; printf '%s\n' "${_x:-}"; }

map=$(mktemp); cand=$(mktemp); sorted=$(mktemp)
trap 'rm -f "$map" "$cand" "$sorted"' EXIT

# cse -> local uuid, read STRUCTURALLY from .session_id. A raw grep for a uuid
# over a bridge transcript also matches uuids merely mentioned inside it, which
# made two different sessions claim one teleport id.
for b in "$HOME"/.claude/logs/bridge-transcript-cse_*.jsonl; do
  [ -f "$b" ] || continue
  cse=$(basename "$b" .jsonl); cse="${cse#bridge-transcript-}"
  u=$(sed -n '1,200p' "$b" | jq -r 'select(.session_id) | .session_id' 2>/dev/null | first_line)
  [ -n "$u" ] && printf '%s\t%s\n' "$u" "$cse" >> "$map"
done

# Filter to v5 by filename BEFORE stat'ing — 6k sessions, ~60 candidates.
command find "$HOME/.claude/projects" -mindepth 2 -maxdepth 2 -name '*.jsonl' 2>/dev/null \
  | awk -F/ '{ f=$NF; if (substr(f,15,1)=="5") print }' > "$cand"
while IFS= read -r p; do
  [ -n "$p" ] || continue
  printf '%s\t%s\n' "$(_mtime "$p")" "$p"
done < "$cand" | sort -rn > "$sorted"

total=$(wc -l < "$sorted" | tr -d ' ')
printf '%-17s %-38s %-28s %s\n' DATE UUID CWD 'FIRST PROMPT'
shown=0
while IFS="$(printf '\t')" read -r epoch path; do
  [ -n "${path:-}" ] || continue
  [ "$shown" -ge "$n" ] && break
  uuid=$(basename "$path" .jsonl)
  cse=$(awk -F'\t' -v u="$uuid" '$1==u {print $2; exit}' "$map" 2>/dev/null || true)
  tp=""; [ -n "$cse" ] && tp="  [teleport ${cse/cse_/session_}]"
  [ "$only_tp" -eq 1 ] && [ -z "$tp" ] && continue
  head60=$(sed -n '1,400p' "$path" 2>/dev/null)
  # cwd comes from the transcript, never decoded from the directory name.
  cwd=$(printf '%s\n' "$head60" | jq -r 'select(.cwd) | .cwd' 2>/dev/null | first_line)
  first=$(printf '%s\n' "$head60" \
    | jq -r 'select(.type=="user" and (.message.content|type)=="string" and (.isMeta|not)) | .message.content' 2>/dev/null \
    | first_line | tr -d '\n' | sed 's/\(.\{1,50\}\).*/\1/')
  printf '%-17s %-38s %-28s %s%s\n' "$(_fmt "$epoch")" "$uuid" "$(printf '%s' "${cwd:-?}" | sed 's/\(.\{1,28\}\).*/\1/')" "${first:-?}" "$tp"
  shown=$((shown+1))
done < "$sorted"
tpn=0; [ -f "$map" ] && tpn=$(wc -l < "$map" | tr -d ' ')
echo "($total programmatic sessions; $tpn still teleport-resolvable; showed $shown)" >&2

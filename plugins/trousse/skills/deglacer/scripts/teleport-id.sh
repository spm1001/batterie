#!/bin/bash
# teleport-id — translate a Claude Code teleport / Remote Control session id
# (session_… or cse_…) into the local session UUID for `claude --resume`.
#
#   teleport-id.sh session_01SJ6FncRfJsipguyykkbvQZ
#   teleport-id.sh --lookup cse_01SJ…     # skip the computation, use the logs
#
# PRIMARY — computation, no logs needed, works for any session of any age:
#   uuid5("3ab19d7e-9f35-45c2-926e-75e271cc60b3",
#         "https://api.anthropic.com/v1/code/sessions/cse_<body>")
# The namespace and the URL name-form are read out of the CC bundle itself
# (`var Z="3ab19d7e-…"`, `QY(t.href, Z)`); confirmed on 6/6 sessions that still
# had a bridge transcript, then out-of-sample on 6 more that did not.
#
# FALLBACKS, for when a future CC changes the namespace or the URL shape:
#   1. ~/.claude/logs/bridge-transcript-cse_<body>.jsonl → `.session_id`.
#      Read STRUCTURALLY: a raw grep for a uuid over that file also matches
#      uuids merely quoted in its own tool output.
#   2. the bridge log's "derived title for session_<body>: …" line, matched
#      against the first prompt of local transcripts.
# When a transcript IS present the script cross-checks it against the computed
# value and shouts if they disagree — that disagreement is the tell that the
# constant has moved.
#
# Portability: bash 3.2 clean (macOS /bin/bash). Needs jq and python3.
set -eu

NS="3ab19d7e-9f35-45c2-926e-75e271cc60b3"
URL_PREFIX="https://api.anthropic.com/v1/code/sessions/"

usage() { echo "usage: teleport-id.sh [--lookup] <session_… | cse_… | bare body>" >&2; exit 2; }
mode=auto
[ "${1:-}" = "--lookup" ] && { mode=lookup; shift; }
[ "${1:-}" = "--fallback" ] && { mode=lookup; shift; }   # old flag name, kept working
[ $# -ge 1 ] || usage
body="${1#session_}"; body="${body#cse_}"
command -v jq >/dev/null 2>&1 || { echo "teleport-id: jq is required" >&2; exit 3; }

first_line() { { IFS= read -r _x || true; } ; printf '%s\n' "${_x:-}"; }

compute() {
  python3 -c 'import uuid,sys; print(uuid.uuid5(uuid.UUID(sys.argv[1]), sys.argv[2]+sys.argv[3]))' \
    "$NS" "$URL_PREFIX" "cse_$body" 2>/dev/null || true
}

find_file() { command find "$HOME/.claude/projects" -mindepth 2 -maxdepth 2 -name "$1.jsonl" 2>/dev/null | first_line; }

# A LIVE session's registry record (~/.claude/sessions/<pid>.json, and the commis
# seat's ~/.claude-commis/sessions/) already carries the join: bridgeSessionId
# (session_…) beside sessionId. While that record exists no computation is
# needed — and no plain resume is safe, because the record means a live process
# still drives the transcript, and a second resumer shares its JSONL (2026-09-09:
# a phone session that had hit its model limit was still a live bridge child
# twenty minutes after its last turn).
registry_dirs() { for _d in "$HOME/.claude/sessions" "$HOME/.claude-commis/sessions"; do [ -d "$_d" ] && echo "$_d"; done; return 0; }
registry_by_bridge() {  # -> local uuid for session_<body>, from any live record
  for _d in $(registry_dirs); do for _r in "$_d"/*.json; do
    [ -f "$_r" ] || continue
    jq -r --arg b "session_$body" 'select(.bridgeSessionId==$b) | .sessionId // empty' "$_r" 2>/dev/null
  done; done | first_line
}
live_holder() {  # uuid -> "pid dir" when a live process holds it
  for _d in $(registry_dirs); do for _r in "$_d"/*.json; do
    [ -f "$_r" ] || continue
    _p=$(jq -r --arg u "$1" 'select(.sessionId==$u) | .pid // empty' "$_r" 2>/dev/null)
    [ -n "$_p" ] && kill -0 "$_p" 2>/dev/null && { echo "$_p $_d"; return 0; }
  done; done
  return 1
}

report() {
  _uuid="$1"; _how="$2"; _f=$(find_file "$_uuid")
  printf '%s\n' "$_uuid"
  echo "  via:    $_how" >&2
  if [ -n "$_f" ]; then
    _cwd=$(sed -n '1,60p' "$_f" | jq -r 'select(.cwd) | .cwd' 2>/dev/null | first_line)
    echo "  file:   $_f" >&2
    [ -n "$_cwd" ] && echo "  resume: (cd $_cwd && claude --resume $_uuid)" >&2 \
                   || echo "  resume: claude --resume $_uuid   (run from the original directory)" >&2
  else
    echo "  WARNING: no local transcript for this uuid — the session did not run on this machine" >&2
  fi
  if _h=$(live_holder "$_uuid"); then
    echo "  WARNING: a live process still holds this session — pid ${_h%% *} (registry ${_h#* })." >&2
    echo "  End it first (kill -TERM ${_h%% *} — graceful, resumable) or add --fork-session; two drivers on one JSONL corrupt it." >&2
  fi
}

t="$HOME/.claude/logs/bridge-transcript-cse_${body}.jsonl"
looked_up=""
[ -f "$t" ] && looked_up=$(sed -n '1,200p' "$t" | jq -r 'select(.session_id) | .session_id' 2>/dev/null | first_line)

if [ "$mode" = auto ]; then
  computed=$(compute)
  reg=$(registry_by_bridge)
  if [ -n "$reg" ]; then
    if [ -n "$computed" ] && [ "$computed" != "$reg" ]; then
      echo "teleport-id: WARNING — computed $computed but the live session registry says $reg." >&2
      echo "  The CC namespace or URL form has probably changed; trusting the registry." >&2
    fi
    report "$reg" "session registry (live record — see WARNING below)"; exit 0
  fi
  if [ -n "$computed" ]; then
    if [ -n "$looked_up" ] && [ "$computed" != "$looked_up" ]; then
      echo "teleport-id: WARNING — computed $computed but the bridge transcript says $looked_up." >&2
      echo "  The CC namespace or URL form has probably changed; trusting the transcript." >&2
      report "$looked_up" "bridge transcript (computation disagreed)"; exit 0
    fi
    [ -n "$looked_up" ] && { report "$computed" "computed (cross-checked against bridge transcript)"; exit 0; }
    [ -n "$(find_file "$computed")" ] && { report "$computed" "computed"; exit 0; }
    # computed but no local file: still the right answer if the session ran elsewhere,
    # but try the logs before settling, in case the constant has moved.
    [ -z "$looked_up" ] && looked_up=""
  fi
fi

[ -n "$looked_up" ] && { report "$looked_up" "bridge transcript"; exit 0; }

title=""
for lg in "$HOME"/.claude/logs/claude-remote-*.log*; do
  [ -f "$lg" ] || continue
  title=$(sed -n "s/.*derived title for session_${body}: //p" "$lg" 2>/dev/null | first_line)
  [ -n "$title" ] && break
done
if [ -z "$title" ]; then
  if [ "$mode" = auto ] && [ -n "${computed:-}" ]; then
    report "$computed" "computed (unverified — no local transcript, no bridge record)"; exit 0
  fi
  echo "teleport-id: cannot resolve cse_${body}" >&2; exit 1
fi
echo "  searching local transcripts for first prompt: $(printf '%s' "$title" | cut -c1-60)" >&2
hits=$(mktemp); trap 'rm -f "$hits"' EXIT
if command -v rg >/dev/null 2>&1; then
  rg --no-ignore -l -F "$title" "$HOME/.claude/projects" -g '*.jsonl' > "$hits" 2>/dev/null || true
else
  command grep -rlF --include='*.jsonl' "$title" "$HOME/.claude/projects" > "$hits" 2>/dev/null || true
fi
while IFS= read -r f; do
  [ -n "$f" ] || continue
  u=$(basename "$f" .jsonl)
  [ "$(printf '%s' "$u" | cut -c15)" = "5" ] || continue
  first=$(sed -n '1,400p' "$f" 2>/dev/null \
    | jq -r 'select(.type=="user" and (.message.content|type)=="string" and (.isMeta|not)) | .message.content' 2>/dev/null | first_line)
  case "$first" in "$title"*) report "$u" "title match in bridge log"; exit 0 ;; esac
done < "$hits"
echo "teleport-id: title found, but no local transcript opens with it" >&2; exit 1

#!/bin/bash
# teleport-id — translate a Claude Code teleport / Remote Control session id
# (session_… or cse_…) into the local session UUID for `claude --resume`.
#
#   teleport-id.sh session_01SJ6FncRfJsipguyykkbvQZ
#   teleport-id.sh --fallback cse_01SJ…    # force the slow title-match path
#
# Primary : ~/.claude/logs/bridge-transcript-cse_<body>.jsonl carries the local
#           UUID in its .session_id field. Read STRUCTURALLY — a raw grep for a
#           uuid over that file also matches uuids merely mentioned inside it,
#           which mis-attributes one session's id to another.
# Fallback: the bridge log records "derived title for session_<body>: <first
#           prompt>"; match that prompt against local transcripts. Slower, but
#           survives the bridge transcripts being cleaned up.
#
# Portability: bash 3.2 clean (macOS /bin/bash) — no mapfile, no find -printf,
# no grep -P. jq is required.
set -eu

usage() { echo "usage: teleport-id.sh [--fallback] <session_… | cse_… | bare body>" >&2; exit 2; }
force_fb=0
[ "${1:-}" = "--fallback" ] && { force_fb=1; shift; }
[ $# -ge 1 ] || usage
id="$1"
body="${id#session_}"; body="${body#cse_}"
command -v jq >/dev/null 2>&1 || { echo "teleport-id: jq is required" >&2; exit 3; }

first_line() { { IFS= read -r _x || true; } ; printf '%s\n' "${_x:-}"; }

report() {  # $1 = uuid, $2 = how it was found
  _uuid="$1"; _how="$2"
  printf '%s\n' "$_uuid"
  _f=$(command find "$HOME/.claude/projects" -mindepth 2 -maxdepth 2 -name "${_uuid}.jsonl" 2>/dev/null | first_line)
  if [ -n "$_f" ]; then
    # Read the cwd from the transcript. Do NOT decode it from the directory
    # name: that encoding replaces every "/" with "-" and is one-way, so
    # "-home-user-repos-acme-data-tools" decodes wrongly to ".../acme/data/tools".
    _cwd=$(sed -n '1,60p' "$_f" | jq -r 'select(.cwd) | .cwd' 2>/dev/null | first_line)
    echo "  via:    $_how" >&2
    echo "  file:   $_f" >&2
    if [ -n "$_cwd" ]; then
      echo "  resume: (cd $_cwd && claude --resume $_uuid)" >&2
    else
      echo "  resume: claude --resume $_uuid   (cwd not recorded — run from the original directory)" >&2
    fi
  else
    echo "  via:    $_how" >&2
    echo "  WARNING: no local transcript for this uuid — resume will fail" >&2
  fi
}

t="$HOME/.claude/logs/bridge-transcript-cse_${body}.jsonl"
if [ -f "$t" ] && [ "$force_fb" -eq 0 ]; then
  uuid=$(sed -n '1,200p' "$t" | jq -r 'select(.session_id) | .session_id' 2>/dev/null | first_line)
  [ -n "$uuid" ] && { report "$uuid" "bridge transcript"; exit 0; }
fi

# Fallback: recover the first prompt from the bridge logs, then match it locally.
title=""
for lg in "$HOME"/.claude/logs/claude-remote-*.log*; do
  [ -f "$lg" ] || continue
  title=$(sed -n "s/.*derived title for session_${body}: //p" "$lg" 2>/dev/null | first_line)
  [ -n "$title" ] && break
done
if [ -z "$title" ]; then
  echo "teleport-id: no bridge transcript and no derived title for cse_${body}" >&2
  echo "  (bridge transcripts are kept only for recent sessions; nothing else records this mapping)" >&2
  exit 1
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
  # Programmatically-spawned sessions get a version-5 uuid; char 15 is the version.
  [ "$(printf '%s' "$u" | cut -c15)" = "5" ] || continue
  first=$(sed -n '1,400p' "$f" 2>/dev/null \
    | jq -r 'select(.type=="user" and (.message.content|type)=="string" and (.isMeta|not)) | .message.content' 2>/dev/null \
    | first_line)
  case "$first" in "$title"*) report "$u" "title match in bridge log"; exit 0 ;; esac
done < "$hits"
echo "teleport-id: title found, but no local transcript opens with it (session may be deleted)" >&2
exit 1

#!/usr/bin/env bash
# repo-sweep — cross-machine git hygiene sweep.
# Inventories every git repo under given roots (optionally on a remote ssh host),
# reports uncommitted work, TRUE ahead/behind vs remote (fetches for accuracy),
# and flags repos that have drifted.
#
# Usage:
#   repo-sweep.sh local <root>...            # sweep local roots (fetches each repo)
#   repo-sweep.sh ssh <host> <root>...       # sweep a remote host over ssh
#   repo-sweep.sh --no-fetch local <root>... # fast mode (ahead/behind may be stale!)
#
# WHY --fetch matters: without a fetch, ahead/behind is measured vs the last
# `git fetch`, which lies after a while — a repo can look "ahead" purely from a
# stale origin ref (this bit us: a marketplace clone looked 7-ahead but was in
# sync). Default fetches for truth; --no-fetch is a quick dirty-only scan.

fetch=1
[ "$1" = "--no-fetch" ] && { fetch=0; shift; }
mode="$1"; shift

read -r -d '' sweep_body <<BODY
fetch=$fetch
host=\$(hostname -s 2>/dev/null || hostname)
for r in "\$@"; do
  [ -d "\$r" ] || continue
  find "\$r" -maxdepth 4 -name .git -type d 2>/dev/null | sed "s#/\\.git\\\$##"
done | sort -u | while IFS= read -r d; do
  [ -z "\$d" ] && continue
  dirty=\$(git -C "\$d" status --porcelain 2>/dev/null | wc -l | tr -d " ")
  stash=\$(git -C "\$d" stash list 2>/dev/null | wc -l | tr -d " ")
  remote=\$(git -C "\$d" config --get remote.origin.url 2>/dev/null)
  slug=\$(echo "\$remote" | sed -E "s#(git@github.com:|https://github.com/)##; s#\\.git\\\$##; s#/\\\$##")
  [ -z "\$remote" ] && slug="(no-remote)"
  ahead="-"; behind="-"
  if [ -n "\$remote" ]; then
    [ "\$fetch" = "1" ] && git -C "\$d" fetch -q origin 2>/dev/null
    defb=\$(git -C "\$d" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed "s#origin/##"); [ -z "\$defb" ] && defb=main
    set -- \$(git -C "\$d" rev-list --left-right --count "origin/\$defb...HEAD" 2>/dev/null)
    behind=\${1:-?}; ahead=\${2:-?}
  fi
  flag=""
  [ "\$dirty" != "0" ] && flag="\${flag}DIRTY:\$dirty "
  [ "\$ahead" != "0" ] && [ "\$ahead" != "-" ] && flag="\${flag}UNPUSHED:\$ahead "
  [ "\$behind" != "0" ] && [ "\$behind" != "-" ] && flag="\${flag}behind:\$behind "
  [ "\$stash" != "0" ] && flag="\${flag}stash:\$stash "
  [ "\$slug" = "(no-remote)" ] && flag="\${flag}NO-REMOTE "
  printf "%s\\t%s\\t%s\\t%s\\n" "\$host" "\$d" "\$slug" "\${flag:-clean}"
done
BODY

case "$mode" in
  local) bash -c "$sweep_body" _ "$@" ;;
  ssh)   host="$1"; shift; ssh "$host" "bash -s" -- "$@" <<<"$sweep_body" ;;
  *) echo "usage: repo-sweep.sh [--no-fetch] local <root>... | ssh <host> <root>..." >&2; exit 1 ;;
esac

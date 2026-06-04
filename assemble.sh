#!/bin/bash
# Assemble all Batterie de Savoir plugins into this repo for Desktop marketplace.
# Copies .claude-plugin/ directories from each source repo.
# Run from the repo root: ./assemble.sh

set -euo pipefail

BATTERIE_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DIR="$(dirname "$BATTERIE_DIR")"

# plugin_name:repo_dir pairs
# batterie (suite-level plugin) is sourced from batterie-de-savoir's root —
# its .claude-plugin/ also holds that repo's marketplace.json, hence the
# rsync --exclude below.
PLUGINS="
batterie:batterie-de-savoir
bon:bon
trousse:trousse
mise:mise-en-space
passe:passe
garde-manger:garde-manger
todoist-gtd:todoist-gtd
tafelmusik:tafelmusik
"

echo "Assembling plugins from $SOURCE_DIR"

RATCHET_FAILURES=""

for entry in $PLUGINS; do
  plugin="${entry%%:*}"
  repo="${entry##*:}"
  src="$SOURCE_DIR/$repo"

  if [ ! -d "$src/.claude-plugin" ]; then
    echo "  SKIP $plugin — no .claude-plugin/ in $src"
    continue
  fi

  dest="$BATTERIE_DIR/plugins/$plugin"
  mkdir -p "$dest"

  # Sync the .claude-plugin directory (marketplace.json excluded: a source
  # repo's own marketplace manifest is not plugin content)
  rsync -a --delete --exclude marketplace.json "$src/.claude-plugin/" "$dest/.claude-plugin/"

  # Copy plugin-level files that skills/agents/hooks might reference
  for item in commands skills agents hooks .mcp.json CLAUDE.md instructions.md; do
    if [ -e "$src/$item" ]; then
      if [ -d "$src/$item" ]; then
        rsync -a --delete "$src/$item/" "$dest/$item/"
      else
        cp "$src/$item" "$dest/$item"
      fi
    else
      rm -rf "$dest/$item" 2>/dev/null || true
    fi
  done

  # Forensic line: version + source SHA, so any future "why is X stale?"
  # is answerable from the commit message alone (the May 2026 drift was
  # undiagnosable because runs logged neither).
  version=$(python3 -c "import json; print(json.load(open('$dest/.claude-plugin/plugin.json'))['version'])" 2>/dev/null || echo "?")
  sha=$(git -C "$src" rev-parse --short HEAD 2>/dev/null || echo "?")
  echo "  OK $plugin ← $repo ($version @ $sha)"

  # Version ratchet: content changed but version didn't → the source repo
  # forgot to bump plugin.json. Without this, clients see "no update
  # available" forever while content silently drifts under them.
  # git status --porcelain (not git diff) — diff is blind to new files.
  # Escape hatch for deliberate local runs: ASSEMBLE_NO_RATCHET=1
  if [ -z "${ASSEMBLE_NO_RATCHET:-}" ]; then
    old_version=$(git -C "$BATTERIE_DIR" show "HEAD:plugins/$plugin/.claude-plugin/plugin.json" 2>/dev/null \
      | python3 -c "import json,sys; print(json.load(sys.stdin)['version'])" 2>/dev/null || echo "")
    content_changes=$(git -C "$BATTERIE_DIR" status --porcelain -- "plugins/$plugin" \
      | grep -v '\.claude-plugin/plugin\.json' | grep -c . || true)
    if [ -n "$old_version" ] && [ "$content_changes" -gt 0 ] && [ "$version" = "$old_version" ]; then
      RATCHET_FAILURES="${RATCHET_FAILURES}  $plugin: $content_changes content change(s) but version still $version — bump .claude-plugin/plugin.json in $repo\n"
    fi
  fi
done

# Invariant check 1 (fail): every relative-source plugin in marketplace.json
# must have vendored content — a manifest entry over nothing is how the
# gueridon "could not sync" and the batterie-0.1.6 husk happened.
while read -r mp; do
  if [ ! -f "$BATTERIE_DIR/plugins/$mp/.claude-plugin/plugin.json" ]; then
    echo "FAIL: marketplace.json declares '$mp' but plugins/$mp has no plugin.json" >&2
    exit 1
  fi
done < <(python3 -c "
import json
m = json.load(open('$BATTERIE_DIR/.claude-plugin/marketplace.json'))
for p in m['plugins']:
    src = p.get('source')
    if isinstance(src, str) and src.startswith('./plugins/'):
        print(src.removeprefix('./plugins/'))
")

# Invariant check 2 (warn only): vendored content not in the manifest is
# assembled-but-unpublished — probably an oversight, but listing it is a
# publishing decision for a human, not this script.
for d in "$BATTERIE_DIR"/plugins/*/; do
  name=$(basename "$d")
  python3 -c "
import json, sys
m = json.load(open('$BATTERIE_DIR/.claude-plugin/marketplace.json'))
sys.exit(0 if any(p.get('source') == './plugins/$name' for p in m['plugins']) else 1)
" || echo "  WARN $name vendored in plugins/ but absent from marketplace.json — unpublished"
done

if [ -n "$RATCHET_FAILURES" ]; then
  echo "" >&2
  echo "FAIL: version ratchet — content drifted without a version bump:" >&2
  printf "%b" "$RATCHET_FAILURES" >&2
  exit 1
fi

echo "Done. Review with: git status"

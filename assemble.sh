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
done

echo "Done. Review with: git status"

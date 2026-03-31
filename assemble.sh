#!/bin/bash
# Assemble all Batterie de Savoir plugins into this repo for Desktop marketplace.
# Copies .claude-plugin/ directories from each source repo.
# Run from the repo root: ./assemble.sh

set -euo pipefail

BATTERIE_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DIR="$(dirname "$BATTERIE_DIR")"

# plugin_name:repo_dir pairs
PLUGINS="
bon:bon
trousse:trousse
mise:mise-en-space
passe:passe
garde-manger:garde-manger
todoist-gtd:todoist-gtd
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

  # Sync the .claude-plugin directory
  rsync -a --delete "$src/.claude-plugin/" "$dest/.claude-plugin/"

  # Copy plugin-level files that skills/agents/hooks might reference
  for item in commands skills agents hooks .mcp.json CLAUDE.md; do
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

  echo "  OK $plugin ← $repo"
done

echo "Done. Review with: git status"

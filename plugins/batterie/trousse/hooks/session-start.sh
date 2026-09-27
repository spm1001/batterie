#!/bin/bash
# SessionStart hook: copy the instruction shard into rules/
# set -euo pipefail  # removed: races with plugin autoUpdate cache swap
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(dirname "$HOOK_DIR")"
if [ -f "$PLUGIN_ROOT/instructions.md" ]; then
    # Honour CLAUDE_CONFIG_DIR (bds-wuvola): a second config dir (the commis
    # seat) loads its own rules/. Copy via temp+mv, NOT a symlink (bds-zilesu):
    # the plugin root can be an ephemeral session dir that Desktop or Cowork
    # purges, and a symlink into it dies silently. The copy is rewritten every
    # session start, so it cannot go stale for long — edit instructions.md, not
    # the copy. Same pattern as mise, accomplis and passe.
    RULES_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/rules"
    mkdir -p "$RULES_DIR"
    _tmp="$(mktemp "$RULES_DIR/trousse.md.XXXXXX")" \
        && cat "$PLUGIN_ROOT/instructions.md" > "$_tmp" \
        && mv -f "$_tmp" "$RULES_DIR/trousse.md"
fi
# Consume stdin (hook protocol)
cat > /dev/null
exit 0

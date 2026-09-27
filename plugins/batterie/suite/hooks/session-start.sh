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
    _tmp="$(mktemp "$RULES_DIR/batterie.md.XXXXXX")" \
        && cat "$PLUGIN_ROOT/instructions.md" > "$_tmp" \
        && mv -f "$_tmp" "$RULES_DIR/batterie.md"
fi

# Migration nag (bds-jakemi). Since the kit fold every tool ships inside this
# one plugin, and Claude Code does not uninstall a plugin its marketplace stops
# listing — so a machine that updated batterie@batterie can still carry the old
# bon@batterie, mise@batterie… beside it, running every hook twice and starting
# a second Google Workspace server. Say so once per session, with the fix. An
# absent or unreadable registry is a fresh machine or a sandbox, not a fault:
# say nothing. The pre-fold batterie plugin never shipped this block, so the nag
# cannot fire on a machine that has not taken the fold.
# And it fires only from INSIDE the kit (this hook's root is the kit's suite/
# subtree): vendored by a pre-fold assembler, this same file sits at the old
# batterie plugin's root beside the seven per-tool plugins it must not nag about
# (cold-read finding, 27 Sep — a source merged before the assembler would
# otherwise tell every machine to uninstall the tools it still depends on).
REGISTRY="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/installed_plugins.json"
if [ -f "$REGISTRY" ] && [ "$(basename "$PLUGIN_ROOT")" = "suite" ] && [ -d "$(dirname "$PLUGIN_ROOT")/bon" ]; then
    python3 - "$REGISTRY" <<'PYEOF'
import json, sys
OLD = ("bon", "trousse", "mise", "accomplis", "sonner", "passe", "arete")
try:
    keys = json.load(open(sys.argv[1])).get("plugins", {})
except (OSError, ValueError):
    sys.exit(0)
stale = [k for k in keys if k.rsplit("@", 1)[0] in OLD and k.endswith("@batterie")]
if stale and "batterie@batterie" in keys:
    print("⚠️ batterie: the old per-tool plugins " + ", ".join(sorted(stale))
          + " are still installed beside batterie@batterie, which now carries them"
          + " all — their hooks run twice. Run /batterie:update to move over"
          + " (or `claude plugin uninstall <name>@batterie` for each).")
PYEOF
fi
# Consume stdin (hook protocol)
cat > /dev/null
exit 0

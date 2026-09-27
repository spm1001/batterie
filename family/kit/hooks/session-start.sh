#!/bin/bash
# SessionStart hook for the family kit (family@family, bds-cofico).
#
# The kit carries the mise engine unmodified, wired to the Planet Modha OAuth
# client through mcpServers.mise.env (MISE_EN_SPACE_OAUTH_CLIENT and
# MISE_EN_SPACE_DATA_DIR). mise's own SessionStart hooks are NOT wired here:
# they carry ITV identity and never see the server's env. This hook does the
# three things a family session needs from them instead:
#   1. writes the family shard, rules/family.md, every session start;
#   2. syncs the engine's dependencies once, so the first MCP start is not a
#      cold install racing its connect timeout;
#   3. says, once per session, when there is no Google sign-in yet — and stays
#      quiet when the engine will adopt the pre-kit mise-home token by itself.
# Silent when all is well.
#
# THE SHARD IS REWRITTEN FROM HERE EVERY SESSION START. Editing rules/family.md
# by hand lasts until the next session — edit this file (spm1001/batterie,
# family/kit/hooks/) and re-assemble.

cat > /dev/null   # SessionStart hands us JSON on stdin; nothing here reads it

KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENGINE="$KIT_ROOT/mise"
CLIENT="$ENGINE/planetmodha-client.json"
CONFIG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
RULES_DIR="$CONFIG/rules"
REG="$CONFIG/plugins/installed_plugins.json"
# The store mcpServers.mise.env points the engine at. Claude Code names a
# plugin's data dir <plugin>-<marketplace>, so family@family → family-family;
# the fallback only matters if a harness runs this hook without the variable.
DATA="${CLAUDE_PLUGIN_DATA:-$CONFIG/plugins/data/family-family}"

# --- 1. The shard -------------------------------------------------------------
# A routing rule plus the engine's own instructions. When the public batterie
# kit is installed too (Sameer's machines), its mise already writes the same
# engine instructions to rules/mise.md, and every rules/*.md loads — so this
# shard then carries the routing lines only, instead of the text twice.
mkdir -p "$RULES_DIR"
_tmp="$(mktemp "$RULES_DIR/family.md.XXXXXX")"
{
    printf '<!-- written by the family kit (family@family) at every session start -->\n'
    printf "**The family's Google Workspace is Planet Modha (planetmodha.com).** "
    printf "The family kit's mise acts on it; its tools are "
    printf '`mcp__plugin_family_mise__search`, `…__fetch` and `…__do`, and its skill is `family:mise`. '
    printf "If an ITV (itv.com) mise is also installed, it is a different Workspace: "
    printf "route by where the content lives, never by which tool answered first.\n\n"
    if [ -f "$RULES_DIR/mise.md" ] && grep -q '"batterie@batterie"' "$REG" 2>/dev/null; then
        :
    elif [ -f "$ENGINE/instructions.md" ]; then
        cat "$ENGINE/instructions.md"
    fi
} > "$_tmp"
mv -f "$_tmp" "$RULES_DIR/family.md"

# The pre-kit family plugin (mise-home@batterie-home) wrote rules/mise-home.md,
# naming tool ids this kit does not have. Once that plugin is uninstalled
# nothing rewrites or removes it, so remove it here — only our predecessor's own
# stamped file, and only while it is no longer registered.
if [ -f "$RULES_DIR/mise-home.md" ] \
   && head -1 "$RULES_DIR/mise-home.md" | grep -q '^<!-- mise flavour: Mise Home -->' \
   && ! grep -q '"mise-home@' "$REG" 2>/dev/null; then
    rm -f "$RULES_DIR/mise-home.md"
fi

ISSUES=""

# --- 2. uv and the engine's dependencies --------------------------------------
# Hook shells can run with a PATH that omits uv's real home (mise-cuveza), so
# probe the usual install places too.
UV_BIN="$(command -v uv 2>/dev/null)"
if [ -z "$UV_BIN" ]; then
    for _c in /usr/local/bin/uv "$HOME/.local/bin/uv" /opt/homebrew/bin/uv /usr/bin/uv; do
        [ -x "$_c" ] && { UV_BIN="$_c"; break; }
    done
fi
if [ -z "$UV_BIN" ]; then
    ISSUES="${ISSUES}• uv is not installed, so the Google Workspace tools cannot start. Install it from https://docs.astral.sh/uv/ and start a new session.\n"
elif [ ! -d "$ENGINE/.venv" ]; then
    SYNC_LOG="$HOME/.cache/family-kit/sync.log"
    mkdir -p "$(dirname "$SYNC_LOG")"
    # Same extras as the server command, so the MCP start finds nothing to add.
    if ! "$UV_BIN" sync --project "$ENGINE" --extra extraction --quiet >"$SYNC_LOG" 2>&1; then
        ISSUES="${ISSUES}• The Google Workspace tools' dependencies failed to install (log: ${SYNC_LOG}). Retry with: uv sync --project \"$ENGINE\" --extra extraction\n"
    fi
fi

# --- 3. Is there a Google sign-in? --------------------------------------------
# Mirrors the engine's own search (token_store.resolve_token_path): this kit's
# store, then a pre-kit store holding a token minted by THIS client — the
# engine adopts that by copy on first load, so it is not "no token". Stores are
# only named, never read beyond their client_id.
if [ -f "$CLIENT" ] && [ ! -f "$DATA/token.json" ]; then
    SIGNED_IN=$(python3 - "$CLIENT" <<'PYEOF'
import json, subprocess, sys
from pathlib import Path

def client_id_of(text):
    try:
        d = json.loads(text)
    except ValueError:
        return None
    return d.get("client_id") if isinstance(d, dict) else None

want = json.loads(Path(sys.argv[1]).read_text())["installed"]["client_id"]
home_data = Path.home() / ".claude" / "plugins" / "data"
for d in ("mise-batterie-de-savoir", "mise-home"):
    p = home_data / d / "token.json"
    try:
        if p.is_file() and client_id_of(p.read_text()) == want:
            print("yes"); sys.exit()
    except OSError:
        pass
if sys.platform == "darwin" and Path("/usr/bin/security").exists():
    for svc in (f"mise-oauth-token:{want}", "mise-oauth-token", "mise-home-oauth-token"):
        r = subprocess.run(["/usr/bin/security", "find-generic-password", "-s", svc, "-w"],
                           capture_output=True, text=True)
        if r.returncode == 0 and client_id_of(r.stdout.strip()) == want:
            print("yes"); sys.exit()
print("no")
PYEOF
)
    if [ "$SIGNED_IN" != "yes" ]; then
        ISSUES="${ISSUES}• The Planet Modha Google Workspace tools are not signed in yet. To sign in, ask Claude to call the family mise tool do(operation=\"setup_oauth\"): it opens a browser (or gives you a link to click) and saves the sign-in for every later session.\n"
    fi
fi

[ -z "$ISSUES" ] && exit 0
MSG="$(printf '%b' "Family kit — Google Workspace setup:\n\n${ISSUES}")"
python3 -c 'import json, sys; print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": sys.argv[1]}}))' "$MSG"

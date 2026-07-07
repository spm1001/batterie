#!/usr/bin/env bash
# make-mise-flavour.sh — produce a renamed, re-credentialled mise plugin variant
# from a vendored mise plugin dir. Pure packaging: the mise runtime is unchanged;
# this rewrites only the distinct-identity strings + swaps the OAuth client.
#
# Why a substitution transform (not a runtime env axis): mise's SessionStart hooks
# carry hardcoded identity strings (keychain service, data-dir name, the
# rules/<name>.md symlink target) and run in the session env, so an mcpServers.env
# block can't reach them. Rewriting the vendored copy keeps the variant fully
# self-contained and needs no change to mise itself.
#
# Usage:
#   make-mise-flavour.sh <input_mise_dir> <output_dir> <instance> <credentials.json>
#   e.g. make-mise-flavour.sh ~/repos/spm1001/batterie/plugins/mise ./mise-home home pm-cred.json
#
# <instance> becomes the suffix everywhere: plugin name `mise-<instance>`,
# MCP server key `mise-<instance>`, keychain `mise-<instance>-oauth-token`,
# data dir `mise-<instance>`, rules symlink `mise-<instance>.md`.
set -euo pipefail

IN="${1:?input mise dir}"; OUT="${2:?output dir}"; INST="${3:?instance name}"; CRED="${4:?credentials.json}"
NAME="mise-${INST}"

[ -d "$IN/.claude-plugin" ] || { echo "ERROR: $IN is not a vendored mise plugin (no .claude-plugin/)"; exit 1; }
[ -f "$CRED" ] || { echo "ERROR: credentials file $CRED not found"; exit 1; }

echo "→ Building flavour '$NAME' from $IN"

# 1. Clean copy (drop any local build artefacts that shouldn't ship).
rm -rf "$OUT"
mkdir -p "$OUT"
rsync -a --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' "$IN"/ "$OUT"/

# 2. Identity-string substitutions (exact, bounded — see enumeration in bds-maluve).
#    data-dir name + keychain service + rules-symlink target, across .py and hooks.
grep -rl --include='*.py' --include='*.sh' 'mise-batterie-de-savoir' "$OUT" | xargs -r sed -i "s|mise-batterie-de-savoir|${NAME}|g"
grep -rl --include='*.py' --include='*.sh' 'mise-oauth-token'        "$OUT" | xargs -r sed -i "s|mise-oauth-token|${NAME}-oauth-token|g"
grep -rl --include='*.sh'                   'rules/mise.md'          "$OUT" | xargs -r sed -i "s|rules/mise.md|rules/${NAME}.md|g"

# 3. plugin.json + mcp-local.json: structured edits (name + rekey mcpServers).
python3 - "$OUT" "$NAME" "$INST" <<'PY'
import json, sys
out, name, inst = sys.argv[1], sys.argv[2], sys.argv[3]
for rel in (".claude-plugin/plugin.json", "mcp-local.json"):
    p = f"{out}/{rel}"
    try:
        d = json.load(open(p))
    except FileNotFoundError:
        continue
    if "name" in d:
        d["name"] = name
    if "description" in d:
        d["description"] = d["description"].rstrip(".") + f" (planetmodha estate, '{inst}' instance)"
    srv = d.get("mcpServers", {})
    if "mise" in srv:
        srv[name] = srv.pop("mise")
        d["mcpServers"] = srv
    json.dump(d, open(p, "w"), indent=2)
    open(p, "a").write("\n")
print(f"  plugin.json/mcp-local.json rekeyed → {name}")
PY

# 4. Swap the OAuth client (installed-app secret — public by design).
cp "$CRED" "$OUT/credentials.json"
echo "  credentials.json ← $(basename "$CRED")"

# 5. GUARD — fail loudly on any leftover ITV-identifying string (ratchet philosophy).
echo "→ Guard: scanning for un-rewritten ITV identity..."
FAIL=0
scan() { # pattern, human label
  local hits
  hits=$(grep -rn --include='*.py' --include='*.sh' --include='*.json' -F "$1" "$OUT" || true)
  if [ -n "$hits" ]; then echo "  ✗ leftover [$2]:"; echo "$hits" | sed 's/^/      /'; FAIL=1; fi
}
scan "mise-oauth-token"          "keychain service"   # mise-home-oauth-token does NOT contain this
scan "mise-batterie-de-savoir"   "data dir name"
scan "rules/mise.md"             "rules symlink"
scan "413373784317"              "ITV client_id"
scan "mit-workspace-mcp-server"  "ITV project"
# plugin.json name/server must be the flavour, not 'mise'
python3 - "$OUT" "$NAME" <<'PY' || FAIL=1
import json, sys
out, name = sys.argv[1], sys.argv[2]
d = json.load(open(f"{out}/.claude-plugin/plugin.json"))
ok = d.get("name") == name and list(d.get("mcpServers", {})) == [name]
if not ok:
    print(f"  ✗ plugin.json name/server not '{name}': name={d.get('name')} servers={list(d.get('mcpServers',{}))}")
    sys.exit(1)
PY
[ "$FAIL" -eq 0 ] || { echo "GUARD FAILED — flavour would collide with ITV mise. Aborting."; exit 1; }
echo "✓ Guard clean. Flavour '$NAME' built at $OUT"

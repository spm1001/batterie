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

  # MCP plugins need their full runtime source, not the skill-plugin file
  # list — a vendored plugin.json pointing at ${CLAUDE_PLUGIN_ROOT}/server.py
  # with no server.py shipped is the mise-0.7.4 Cowork husk (diagnosis:
  # notes/raw/2026-06-10-mise-cowork-husk-diagnosis.md). uv.lock rides along
  # by design: the package must be self-contained for `uv sync` on the host.
  has_mcp=$(python3 -c "
import json
d = json.load(open('$src/.claude-plugin/plugin.json'))
print('yes' if d.get('mcpServers') else 'no')
" 2>/dev/null || echo no)

  if [ "$has_mcp" = "yes" ]; then
    # Full-source vendor. Excludes: non-runtime bulk (tests/docs/fixtures/
    # bakeoff), repo plumbing (.git/.github/.bon), the source repo's own
    # marketplace.json, and local-run hygiene (caches, venvs, deposit dirs,
    # secrets) that clean clones lack but working trees may carry.
    # --delete-excluded: plugins/ is fully generated, so anything in dest
    # matching an exclude (e.g. cruft vendored before the exclude existed)
    # is stale and must go — without it, --exclude protects old cruft.
    # Repo-shaped excludes are ROOT-ANCHORED (leading /): an unanchored
    # `mise/` matches at every depth and ate skills/mise/ — Desktop showed
    # "no skills" on 0.7.6. Only genuinely-anywhere patterns stay bare.
    rsync -a --delete --delete-excluded \
      --exclude /.git --exclude /.github --exclude /.bon \
      --exclude /tests --exclude /docs --exclude /fixtures --exclude /bakeoff \
      --exclude /.claude-plugin/marketplace.json \
      --exclude /mise --exclude /mise-fetch --exclude /.mcp-workspace \
      --exclude /data --exclude /uploads \
      --exclude /.oauth-stash --exclude /.claude --exclude /.coverage \
      --exclude .venv --exclude node_modules --exclude __pycache__ --exclude '*.pyc' \
      --exclude .pytest_cache --exclude .mypy_cache --exclude .ruff_cache \
      --exclude .hypothesis --exclude '*.db' --exclude token.json --exclude .env \
      --exclude .gitignore --exclude .gitattributes \
      "$src/" "$dest/"
    # .gitignore exclusion is load-bearing, not cosmetic: a vendored source
    # .gitignore (mise's lists uv.lock) makes THIS repo's git treat vendored
    # files as ignorable, so the workflow's `git add` would silently skip
    # them — shipping a package that resolves deps unpinned. Nested
    # gitignores change the host repo's commit behaviour.

    # Parity guard: a copy rule must never eat plugin content. Whatever
    # capability dirs the source ships, the vendored package ships.
    for must in skills hooks commands; do
      if [ -d "$src/$must" ] && [ ! -d "$dest/$must" ]; then
        echo "FAIL: $plugin has $must/ in source but not in vendored package — an exclude is eating content" >&2
        exit 1
      fi
    done
  else
    # Skill plugins: the lean copy-list.
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
  fi

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

# Invariant check 3 (fail): MCP entry points must resolve. The manifest
# invariant above only proves plugin.json exists — the mise-0.7.4 husk
# shipped a valid plugin.json whose mcpServers pointed at files that were
# never vendored, and every Cowork session got a dead server. For each
# vendored plugin.json declaring mcpServers: every ${CLAUDE_PLUGIN_ROOT}-
# relative path in command/args must exist; `uv run --project|--directory`
# requires a vendored pyproject.toml; `python -m pkg.mod` must resolve to
# a module under the plugin root. Kills the class at build time.
python3 - "$BATTERIE_DIR" <<'PYEOF'
import json, re, sys
from pathlib import Path

root = Path(sys.argv[1]) / "plugins"
failures = []
for pj in sorted(root.glob("*/.claude-plugin/plugin.json")):
    plugin_dir = pj.parent.parent
    servers = (json.load(open(pj)).get("mcpServers") or {})
    for name, cfg in servers.items():
        tokens = [str(cfg.get("command", ""))] + [str(a) for a in (cfg.get("args") or [])]
        where = f"{plugin_dir.name}: mcpServers[{name}]"

        for tok in tokens:
            for m in re.finditer(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s\"']+)", tok):
                rel = m.group(1)
                if not (plugin_dir / rel).exists():
                    failures.append(f"{where} references {rel} — not vendored")

        if any(t in ("--project", "--directory") for t in tokens):
            if not (plugin_dir / "pyproject.toml").exists():
                failures.append(f"{where} uses uv --project/--directory but no pyproject.toml vendored")

        for i, t in enumerate(tokens):
            if t == "-m" and i + 1 < len(tokens):
                mod = tokens[i + 1].replace(".", "/")
                if not ((plugin_dir / f"{mod}.py").exists()
                        or (plugin_dir / mod / "__init__.py").exists()
                        or (plugin_dir / "src" / f"{mod}.py").exists()
                        or (plugin_dir / "src" / mod / "__init__.py").exists()):
                    failures.append(f"{where} runs -m {tokens[i+1]} — module not vendored")

for f in failures:
    print(f"FAIL: {f}", file=sys.stderr)
if failures:
    sys.exit(1)
PYEOF

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

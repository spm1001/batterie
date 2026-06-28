#!/bin/bash
# Assemble all Batterie de Savoir plugins into this repo for Desktop marketplace.
# Copies .claude-plugin/ directories from each source repo.
# Run from the repo root: ./assemble.sh
#
# Every vendored plugin is stamped with ONE suite version (the batterie/suite
# plugin's — bds-suwoho), so all published plugins carry an identical number.
#
# Failure model is two-tier. STRUCTURAL faults (husk/parity guard, manifest
# invariant, MCP entry-point) hard-exit 1 immediately — corrupt content is
# never published. A VERSION-RATCHET lag (content changed but the suite
# version didn't bump) is QUARANTINED, not fatal: the laggard's vendored dir is
# reverted to last-published and named in a sentinel file
# ($ASSEMBLE_QUARANTINE_FILE, default /tmp/assemble-quarantine.txt); the run
# still exits 0 so the healthy plugins publish, and assemble.yml's final step
# fails the build red on the sentinel. One missed bump no longer wedges the
# whole bus (bds-pujaki, 2026-06-17).

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
todoist-gtd:todoist-gtd
"
# garde-manger delisted 2026-06-10 (decommissioned per the estate audit;
# Sameer confirmed). tafelmusik unvendored 2026-06-10 (too experimental to
# publish; Sameer's call — source repo lives on, just not distributed).
# De-registration is manual by design: the assembler never deletes a dest
# dir for an unmapped plugin, so retiring one means removing it from this
# list, marketplace.json, and plugins/ together.

# The single suite version (bds-suwoho): one number stamped onto every
# vendored plugin so all published plugins carry an identical version. It
# lives in the batterie/suite plugin's plugin.json; source repos keep their
# own plugin.json versions for local dev + the CLI footnote, but those are
# overwritten in the vendored copies below. BATTERIE_SRC_REPO is read from
# the PLUGINS map so there's no second hardcoding of the source repo name.
BATTERIE_SRC_REPO=$(echo "$PLUGINS" | awk -F: '$1=="batterie"{print $2}')
SUITE_VERSION=$(python3 -c "import json; print(json.load(open('$SOURCE_DIR/$BATTERIE_SRC_REPO/.claude-plugin/plugin.json'))['version'])")
# Last-published suite version, for the suite-level ratchet below: the
# committed batterie plugin in HEAD is the canonical holder. Empty on a fresh
# repo (no HEAD yet) — the ratchet treats empty as "can't compare, allow".
OLD_SUITE_VERSION=$(git -C "$BATTERIE_DIR" show "HEAD:plugins/batterie/.claude-plugin/plugin.json" 2>/dev/null \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['version'])" 2>/dev/null || echo "")

# Stamp a vendored plugin.json's version to the suite version via a TARGETED
# string edit — NOT json.dumps, which reformats every array (self.md
# surgical-JSON note). Each plugin.json carries exactly one top-level
# "version"; the regex rewrites only that value, leaving the file byte-for-
# byte elsewhere. Fails LOUD if the field isn't matched exactly once: a silent
# no-op stamp would let a plugin ship at the wrong number.
stamp_version() {
  python3 - "$1" "$2" <<'PYEOF'
import re, sys
path, new = sys.argv[1], sys.argv[2]
text = open(path).read()
text2, n = re.subn(r'("version"\s*:\s*")[^"]*(")',
                   lambda m: m.group(1) + new + m.group(2), text, count=1)
if n != 1:
    sys.stderr.write(f"FAIL: stamp_version matched {n} version fields in {path} (expected 1)\n")
    sys.exit(1)
open(path, "w").write(text2)
PYEOF
}

echo "Assembling plugins from $SOURCE_DIR (suite version $SUITE_VERSION, last published ${OLD_SUITE_VERSION:-none})"

RATCHET_FAILURES=""
QUARANTINED=""

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
    # --checksum, not rsync's default size+mtime quick-check: a same-byte-size
    # version bump (e.g. 0.26.2→0.26.3) with an aligned mtime is otherwise
    # silently skipped — the bump never propagates, and the ratchet then
    # either misses it or FALSELY quarantines a plugin that did bump (mtimes
    # come from sequential git clones, so alignment is incidental, not
    # impossible; confirmed 2026-06-17). Tiny trees — checksum cost is noise.
    rsync -a --checksum --delete --delete-excluded \
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

  else
    # Skill plugins: the lean copy-list.
    # Sync the .claude-plugin directory (marketplace.json excluded: a source
    # repo's own marketplace manifest is not plugin content)
    # --checksum: defeat the size+mtime skip on same-size bumps (see MCP branch)
    rsync -a --checksum --delete --exclude marketplace.json "$src/.claude-plugin/" "$dest/.claude-plugin/"

    # Copy plugin-level files that skills/agents/hooks might reference.
    # scripts/ is load-bearing: bon's close/open context scripts and
    # trousse's ardoise.sh live there — its omission at the 2026-06-10
    # cutover broke /close and silently degraded bon's session-start hook.
    # NB: for some plugins (e.g. batterie) every script runs from SOURCE —
    # CI runs scripts/batterie-lint.py from the checkout, /batterie:publish
    # runs scripts/publish.py from ~/repos — so their vendored scripts/ is
    # harmless dead weight. Kept anyway: the copy-list and the parity guard
    # below are deliberately uniform, and special-casing one plugin to strip
    # dead weight would mean exempting it from the guard that protects the
    # plugins whose scripts DO run vendored. Not worth the assembler risk.
    for item in commands skills agents hooks scripts .mcp.json CLAUDE.md instructions.md; do
      if [ -e "$src/$item" ]; then
        if [ -d "$src/$item" ]; then
          # Same genuinely-anywhere hygiene patterns as the MCP branch:
          # source scripts/ dirs can carry __pycache__ and local secrets.
          # --checksum: defeat the size+mtime skip on same-size bumps (see MCP branch)
          rsync -a --checksum --delete --delete-excluded \
            --exclude __pycache__ --exclude '*.pyc' \
            --exclude token.json --exclude .env \
            "$src/$item/" "$dest/$item/"
        else
          cp "$src/$item" "$dest/$item"
        fi
      else
        rm -rf "$dest/$item" 2>/dev/null || true
      fi
    done
  fi

  # Parity guard (BOTH branches): a copy rule must never eat plugin content.
  # Whatever capability dirs the source ships, the vendored package ships.
  # Guarding only the MCP branch is how the lean branch dropped scripts/
  # for a day unnoticed (2026-06-11) — the consuming hook failed open.
  for must in skills hooks commands agents scripts; do
    if [ -d "$src/$must" ] && [ ! -d "$dest/$must" ]; then
      echo "FAIL: $plugin has $must/ in source but not in vendored package — a copy rule is eating content" >&2
      exit 1
    fi
  done

  # Single-version stamp (bds-suwoho): overwrite this plugin's vendored
  # plugin.json version with the suite version, so every published plugin
  # carries one identical number. The source repo's own version is untouched
  # (local-dev / CLI footnote only). Done here, after vendoring + the parity
  # guard, so the version read below reflects the stamp.
  stamp_version "$dest/.claude-plugin/plugin.json" "$SUITE_VERSION"

  # Version + source SHA for the status line below — so any future "why is
  # X stale?" is answerable from the commit message alone (the May 2026
  # drift was undiagnosable because runs logged neither). version now reads
  # the stamped value (== suite version) — a free check the stamp landed.
  version=$(python3 -c "import json; print(json.load(open('$dest/.claude-plugin/plugin.json'))['version'])" 2>/dev/null || echo "?")
  sha=$(git -C "$src" rev-parse --short HEAD 2>/dev/null || echo "?")

  # Suite-level version ratchet (bds-suwoho): the whole suite ships under ONE
  # version. If a plugin's vendored content changed but the suite version
  # wasn't bumped, clients would see "no update available" forever while
  # content drifts under them. So the gate is: this plugin's content changed
  # AND the suite version still equals the last-published suite version → the
  # source forgot to bump the suite. The per-plugin content check stays (so
  # only the drifted plugins are quarantined), but the version comparison is
  # suite-wide, read once above (SUITE_VERSION vs OLD_SUITE_VERSION).
  # git status --porcelain (not git diff) — diff is blind to new files. The
  # stamped plugin.json is filtered out (the stamp always rewrites it, so it's
  # never itself "content drift"). Escape hatch for local runs: ASSEMBLE_NO_RATCHET=1.
  #
  # QUARANTINE, don't abort (2026-06-17, bds-pujaki): on a trip we revert THIS
  # plugin's vendored dir to its last-published state and record it, instead
  # of failing the whole run. Healthy plugins still publish; a final
  # assemble.yml step fails the run RED naming the laggards. Reverting to HEAD
  # is safe for the post-loop structural invariants (marketplace, MCP) —
  # last-published already satisfied them. Applies ONLY to the version
  # ratchet; the husk/parity guard above stays a hard exit.
  quarantined_this=0
  if [ -z "${ASSEMBLE_NO_RATCHET:-}" ]; then
    content_changes=$(git -C "$BATTERIE_DIR" status --porcelain -- "plugins/$plugin" \
      | grep -v '\.claude-plugin/plugin\.json' | grep -c . || true)
    if [ -n "$OLD_SUITE_VERSION" ] && [ "$content_changes" -gt 0 ] && [ "$SUITE_VERSION" = "$OLD_SUITE_VERSION" ]; then
      # Restore the laggard's vendored dir to EXACTLY last-published:
      # checkout restores tracked files; clean -fd drops newly-added drift
      # files checkout leaves behind (porcelain counts new files, so the
      # revert must drop them too — else `git add -A` would republish them).
      git -C "$BATTERIE_DIR" checkout HEAD -- "plugins/$plugin"
      git -C "$BATTERIE_DIR" clean -fdq -- "plugins/$plugin"
      RATCHET_FAILURES="${RATCHET_FAILURES}  $plugin: $content_changes content change(s) but suite version still $SUITE_VERSION — bump the suite version ($BATTERIE_SRC_REPO/.claude-plugin/plugin.json)\n"
      QUARANTINED="${QUARANTINED}${plugin}\n"
      quarantined_this=1
    fi
  fi

  # Exactly one status line per plugin, AFTER the ratchet, so the committed
  # commit message tells the truth about what shipped: OK = vendored and
  # published; QUARANTINE = reverted to last-published for a missing bump.
  if [ "$quarantined_this" = 1 ]; then
    echo "  QUARANTINE $plugin ← $repo (held at last-published $version — $repo content drifted, version not bumped)"
  else
    echo "  OK $plugin ← $repo ($version @ $sha)"
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

# Version-ratchet laggards are QUARANTINED, not fatal: their vendored dirs
# were reverted to last-published in the loop, so the healthy plugins still
# publish this run. Emit the laggard list to a sentinel file; the final
# assemble.yml step fails the run RED (after commit/push) naming them —
# loud, but blast-radius-isolated, so one missed bump no longer wedges the
# whole bus (bds-pujaki 2026-06-17). The structural/husk guards above
# already exit hard; only the ratchet reaches here.
QUARANTINE_FILE="${ASSEMBLE_QUARANTINE_FILE:-/tmp/assemble-quarantine.txt}"
rm -f "$QUARANTINE_FILE"
if [ -n "$QUARANTINED" ]; then
  echo "" >&2
  echo "QUARANTINE: version-ratchet drift without a bump — reverted to last-published, healthy plugins still ship:" >&2
  printf "%b" "$RATCHET_FAILURES" >&2
  printf "%b" "$QUARANTINED" > "$QUARANTINE_FILE"
fi

echo "Done. Review with: git status"

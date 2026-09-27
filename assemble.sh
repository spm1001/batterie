#!/bin/bash
# Assemble every Batterie de Savoir marketplace from the source repos.
# Run from the repo root: ./assemble.sh
#
# ONE pipeline, TWO outputs (bds-nagoru / bds-mumise):
#   PUBLIC  "batterie"      → this repo (plugins/ + .claude-plugin/marketplace.json,
#                             committed + pushed by assemble.yml — the update bus).
#   PRIVATE "batterie-home" → a LOCAL dir (default dist/batterie-home, gitignored),
#                             mise only, transformed to mise-home via
#                             transforms/make-mise-flavour.sh with the planetmodha
#                             cred. Emitted ONLY when MISE_HOME_CRED is set; the
#                             flavour derives from the just-vendored PUBLIC mise,
#                             so both marketplaces carry identical runtime bytes
#                             and the same suite version — they cannot drift.
#                             Never committed here (it carries the planetmodha
#                             credential); assemble.yml pushes it to the private
#                             spm1001/batterie-home repo over a write deploy key
#                             (bds-susugu — cred + key arrive as Actions secrets).
#
# Every vendored plugin is stamped with ONE suite version (the batterie/suite
# plugin's — bds-suwoho), so all published plugins carry an identical number.
#
# ONE PLUGIN, batterie@batterie (bds-jakemi, 2026-09-27). The public shelf is
# one marketplace holding one plugin named after its ring, because claude.ai
# and Desktop mishandle catalogue changes (deletions above all — sonnette stayed
# installed on claude.ai after it was delisted); with a fixed catalogue, adding
# or retiring a tool is an ordinary version bump inside the kit. Each source
# repo is a COMPONENT vendored whole into plugins/batterie/<component>/, exactly
# as it used to be vendored into plugins/<name>/ — five components ship a
# hooks/session-start.sh and every hook finds its root from its own path, so
# keeping each tree whole means no hook or script changes shape. The kit's
# root .claude-plugin/plugin.json is GENERATED from the component manifests
# (write_kit_manifest below): a skills array, the union of their hooks with
# each command re-rooted, and their MCP servers re-rooted. Design:
# batterie-de-savoir docs/plans/jakemi-fold-design-2026-09-27.md.
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

# The kit: one plugin, named after the ring, and its one marketplace field no
# plugin.json carries (bds-dekava). No colon in these on purpose: assemble.yml's
# clone list greps every `name:repo` line in this file.
KIT="batterie"
KIT_CATEGORY="productivity"

# component:repo_dir pairs, in load order. Each lands in plugins/$KIT/<component>/.
# `suite` is batterie-de-savoir's own content (update, version, the batterie
# shard) — its .claude-plugin/ also supplies the kit's identity (name,
# description, keywords) to write_kit_manifest. The component name is the
# kitchen name the CLI, shard and wheel already carry; it never reaches a
# user-visible id, which is batterie:<skill> and mcp__plugin_batterie_<server>.
# arete left for the sameer kit with the fold (Sameer-only: macOS + MindNode).
COMPONENTS="
suite:batterie-de-savoir
bon:bon
trousse:trousse
mise:mise-en-space
accomplis:accomplis
sonner:sonner
passe:passe
"
# sonnette DELISTED 2026-08-24 (son-pilalu, Sameer's call): superseded by sonner,
# which shipped two suite versions earlier. Its conductor-channel MCP traffic
# stopped 2026-07-19 (measured, harness-ergonomics data/calls-2026-08-16.csv.gz)
# and it was already disabled-but-installed on tube. Per the de-registration note
# below, this removal comes WITH the marketplace.json entry and plugins/sonnette
# in the same commit — the assembler never deletes a dest dir for an unmapped
# plugin, so leaving the directory would ship a frozen copy forever. The aboyeur
# SOURCE repo keeps the code and its sonnette-bundle-fresh CI guard; only
# distribution stops here.
# garde-manger delisted 2026-06-10 (decommissioned per the estate audit;
# Sameer confirmed). tafelmusik unvendored 2026-06-10 (too experimental to
# publish; Sameer's call — source repo lives on, just not distributed).
# passe delisted 2026-07-07 (bds-wobari via bds-mumise: browser infra, not a
# knowledge plugin — the CLI installs standalone from spm1001/passe), then
# RELISTED 2026-07-26 (passe-mezigo, Sameer's call): the standalone-CLI
# rationale left the guidance shard, skills and hooks with no rot-proof
# install route — tube's shard died for a week via a Cowork-sandbox symlink.
# The plugin route plus a hook-generated shard (passe df1dbbc) is durable.
# Retiring a component is ONE edit: drop it from COMPONENTS. The run prunes its
# plugins/$KIT/<component>/ dir and regenerates the kit manifest without it —
# an ordinary version bump for every client, which is the point of one plugin.
# (bds-dekava made de-registration one edit when there were eight plugins; the
# accomplis rename had stranded the marketplace for ~30 min on 2026-08-02
# because marketplace.json and the map were both hand-kept.)

# Wheels shipped inside the kit (bds-timule, 2026-09-23): component:source_repo.
# Each source repo is built into a wheel that lands in plugins/$KIT/<component>/wheels/,
# so every CLI and library a plugin needs installs from THIS public repo and the
# workshop repos can go private — batterie is the one public strand (Sameer:
# "a spider web when it should be a rope"). The SessionStart hooks install from
# these wheels; git+https survives only as a maintainer fallback. Repos listed
# here but absent from COMPONENTS (deglacer, jeton) are cloned by assemble.yml,
# whose clone list greps every `name:repo` line in this file — keep the shape.
# Hatchling wheels are reproducible, so an unchanged source rebuilds to the same
# bytes and the ratchet stays quiet; a changed source is content drift like any
# other and rides the suite bump.
WHEELS="
bon:bon
accomplis:accomplis
passe:passe
sonner:sonner
trousse:deglacer
mise:jeton
"

# Build the wheels mapped to $1 into $2/wheels/ (wiped first, so a renamed or
# retired wheel cannot linger). uv build writes a `*` .gitignore into its output
# dir, which would make git silently skip the wheel — so build into a temp dir
# and copy only the .whl across. Exactly one wheel per source, or fail loud.
build_wheels() {
  local plugin="$1" dest="$2" entry repo tmp whl n
  rm -rf "$dest/wheels"
  for entry in $WHEELS; do
    [ "${entry%%:*}" = "$plugin" ] || continue
    repo="${entry##*:}"
    [ -f "$SOURCE_DIR/$repo/pyproject.toml" ] || { echo "FAIL: wheel source $repo has no pyproject.toml (for $plugin)" >&2; exit 1; }
    tmp=$(mktemp -d)
    if ! uv build --wheel --quiet -o "$tmp" "$SOURCE_DIR/$repo" >"$tmp/build.log" 2>&1; then
      echo "FAIL: uv build of $repo (wheel for $plugin) failed:" >&2; cat "$tmp/build.log" >&2; exit 1
    fi
    n=$(find "$tmp" -maxdepth 1 -name '*.whl' | wc -l)
    [ "$n" -eq 1 ] || { echo "FAIL: $repo built $n wheels, expected 1" >&2; exit 1; }
    whl=$(find "$tmp" -maxdepth 1 -name '*.whl')
    mkdir -p "$dest/wheels"
    cp "$whl" "$dest/wheels/"
    rm -rf "$tmp"
    repoint_uv_source "$dest" "$(basename "$whl")"
  done
}

# If the vendored plugin is a uv project whose [tool.uv.sources] fetches this
# wheel's package from git, point it at the shipped wheel instead and relock —
# mise's jeton is the case: `uv run --project` would otherwise clone jeton from
# GitHub on every host. Targeted line edit, not a TOML rewrite (same reason as
# stamp_version). No matching source line → nothing to do.
repoint_uv_source() {
  local dest="$1" whl="$2" changed
  [ -f "$dest/pyproject.toml" ] || return 0
  changed=$(python3 - "$dest/pyproject.toml" "$whl" <<'PYEOF'
import re, sys
path, whl = sys.argv[1], sys.argv[2]
pkg = whl.split("-")[0].replace("_", "[-_]")
text = open(path).read()
new, n = re.subn(rf'(?m)^({pkg})\s*=\s*\{{\s*git\s*=[^}}]*\}}[ \t]*$',
                 lambda m: f'{m.group(1)} = {{ path = "wheels/{whl}" }}', text)
if n > 1:
    sys.stderr.write(f"FAIL: {n} uv source lines for {pkg} in {path}\n"); sys.exit(1)
if n:
    open(path, "w").write(new)
print(n)
PYEOF
) || exit 1
  if [ "$changed" = 1 ]; then
    uv lock --quiet --directory "$dest" || { echo "FAIL: uv lock after repointing $whl in $dest" >&2; exit 1; }
    if grep -q 'git = "https://github.com/spm1001/' "$dest/uv.lock"; then
      echo "FAIL: $dest/uv.lock still fetches from a spm1001 git repo after repointing $whl" >&2; exit 1
    fi
  fi
}

# Private-marketplace manifest (bds-mumise): which plugin, which transform,
# where it lands. Kept as plain variables — two marketplaces don't earn a
# data-driven loop; the shared machinery is the vendor loop above the guards
# below, which both outputs pass through.
HOME_OUT="${ASSEMBLE_HOME_OUT:-$BATTERIE_DIR/dist/batterie-home}"
HOME_NAME="batterie-home"

# The single suite version (bds-suwoho): one number stamped onto every
# vendored plugin so all published plugins carry an identical version. It
# lives in the batterie/suite plugin's plugin.json; source repos keep their
# own plugin.json versions for local dev + the CLI footnote, but those are
# overwritten in the vendored copies below. BATTERIE_SRC_REPO is read from
# the COMPONENTS map so there's no second hardcoding of the source repo name.
BATTERIE_SRC_REPO=$(echo "$COMPONENTS" | awk -F: '$1=="suite"{print $2}')
SUITE_VERSION=$(python3 -c "import json; print(json.load(open('$SOURCE_DIR/$BATTERIE_SRC_REPO/.claude-plugin/plugin.json'))['version'])")
# Last-published suite version, for the suite-level ratchet below: the
# committed batterie plugin in HEAD is the canonical holder. Empty on a fresh
# repo (no HEAD yet) — the ratchet treats empty as "can't compare, allow".
KIT_DIR="$BATTERIE_DIR/plugins/$KIT"
OLD_SUITE_VERSION=$(git -C "$BATTERIE_DIR" show "HEAD:plugins/$KIT/.claude-plugin/plugin.json" 2>/dev/null \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['version'])" 2>/dev/null || echo "")

# Stamp a vendored plugin.json's version to the suite version via a TARGETED
# string edit — NOT json.dumps, which reformats every array it touches,
# turning a one-field stamp into a whole-file diff. Each plugin.json carries exactly one top-level
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

# Generate a plugin's shipped CHANGELOG.md as a STUB (bds-mawitu): the suite has
# one canonical changelog (batterie-de-savoir/CHANGELOG.md); every plugin ships
# a generated pointer to it, stamped with the current suite version. Because the
# stub is (re)generated with $SUITE_VERSION on every assemble, a shipped
# changelog can never predate the release — the "stale changelog" failure class
# is inexpressible, not merely caught. Uniform across ALL plugins (batterie
# included) — no special case. It points at the marketplace README rather than
# the canonical changelog, whose repo is private (bds-juwone, 2026-09-23).
write_changelog_stub() {
  dest_dir="$1"; version="$2"
  cat > "$dest_dir/CHANGELOG.md" <<EOF
# Changelog

This plugin ships as part of the **Batterie de Savoir** suite and carries the
single suite version — currently **$version**.

What each plugin does and needs is in the marketplace README:

  $MARKETPLACE_HOME

The suite's release notes stay with its private source repo; this file is a
generated stub, so it can never fall behind the version this plugin ships at.
EOF
}

# Point a vendored plugin.json's "repository" at the marketplace README unless
# its source repo is public (bds-juwone, 2026-09-23). Most source repos are
# private, so their URLs 404 for teammates and strangers alike. Deny by
# default: a source missing from PUBLIC_SOURCES gets the README, so a repo that
# goes private later cannot leave a dead link behind — one that goes public
# merely keeps pointing at the README until it is added here. Targeted string
# edit, same reason as stamp_version; plugin.json is already filtered from the
# ratchet, and a plugin.json with no "repository" field is left alone.
MARKETPLACE_HOME="https://github.com/spm1001/batterie#readme"
PUBLIC_SOURCES="mise-en-space gueridon"
stamp_repository() {
  case " $PUBLIC_SOURCES " in *" $2 "*) return 0 ;; esac
  python3 - "$1" "$MARKETPLACE_HOME" <<'PYEOF'
import re, sys
path, home = sys.argv[1], sys.argv[2]
text = open(path).read()
text2, n = re.subn(r'("repository"\s*:\s*")[^"]*(")',
                   lambda m: m.group(1) + home + m.group(2), text)
if n > 1:
    sys.stderr.write(f"FAIL: stamp_repository matched {n} repository fields in {path}\n")
    sys.exit(1)
open(path, "w").write(text2)
PYEOF
}

# Skill, command and agent bodies are the one place Claude Code substitutes
# ${CLAUDE_PLUGIN_ROOT} inline — with the KIT root, not the component's. So a
# component's Markdown gets every ${CLAUDE_PLUGIN_ROOT} re-rooted to
# ${CLAUDE_PLUGIN_ROOT}/<component>, and a leftover bare root (braced or not)
# fails the run: resolved against the kit root, it names a path that does not
# exist, and a skill's primary route would silently fall through to its
# cache-glob fallback — which finds a stale pre-fold copy. rsync restores the
# source text on every run (checksums differ once rewritten), so this applies
# exactly once per run and the ratchet compares like with like.
reroot_markdown() {
  python3 - "$1" "$2" <<'PYEOF'
import re, sys
from pathlib import Path
root, comp = Path(sys.argv[1]), sys.argv[2]
bad = []
for sub in ("skills", "commands", "agents"):
    for md in sorted((root / sub).rglob("*.md")) if (root / sub).is_dir() else []:
        text = md.read_text()
        new = re.sub(r"\$\{CLAUDE_PLUGIN_ROOT\}(?!/" + re.escape(comp) + r"(?![\w-]))",
                     "${CLAUDE_PLUGIN_ROOT}/" + comp, text)
        if new != text:
            md.write_text(new)
        if re.search(r"\$CLAUDE_PLUGIN_ROOT(?![\w{])", new):
            bad.append(f"{md.relative_to(root)} uses $CLAUDE_PLUGIN_ROOT unbraced")
for b in bad:
    print(f"FAIL: {comp}: {b} — Claude Code only substitutes the braced form; write ${{CLAUDE_PLUGIN_ROOT}}", file=sys.stderr)
sys.exit(1 if bad else 0)
PYEOF
}

echo "Assembling $KIT from $SOURCE_DIR (suite version $SUITE_VERSION, last published ${OLD_SUITE_VERSION:-none})"

RATCHET_FAILURES=""
QUARANTINED=""

for entry in $COMPONENTS; do
  plugin="${entry%%:*}"   # the component name (kept as $plugin: the WHEELS map and the quarantine file speak it)
  repo="${entry##*:}"
  src="$SOURCE_DIR/$repo"

  if [ ! -d "$src/.claude-plugin" ]; then
    echo "FAIL: component $plugin has no .claude-plugin/ in $src — a missing component would ship a kit with a hole in it" >&2
    exit 1
  fi

  dest="$KIT_DIR/$plugin"
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
    # /handoffs + /HANDOFF.md (2026-08-23): session handoffs are internal
    # work notes and must NEVER ship to this public marketplace. The
    # visible-handoffs migration (bon-sanita) moved them out from behind
    # the /.bon exclusion and mise+sonnette handoffs went public for ~2
    # days before a /close self-check caught it. --delete-excluded sweeps
    # the already-vendored copies on this assemble.
    # Repo-shaped excludes are ROOT-ANCHORED (leading /): an unanchored
    # `mise/` matches at every depth and ate skills/mise/ — Desktop showed
    # "no skills" on 0.7.6. Only genuinely-anywhere patterns stay bare.
    # /dist: build output, gitignored in source repos (aboyeur's tsc output)
    # — absent from clean clones, present in working trees; local previews
    # were vendoring it (2026-07-19). NB sonnette's SHIPPED bundle lives in
    # sonnette/, deliberately not dist/, so this exclude can't eat it.
    # --checksum, not rsync's default size+mtime quick-check: a same-byte-size
    # version bump (e.g. 0.26.2→0.26.3) with an aligned mtime is otherwise
    # silently skipped — the bump never propagates, and the ratchet then
    # either misses it or FALSELY quarantines a plugin that did bump (mtimes
    # come from sequential git clones, so alignment is incidental, not
    # impossible; confirmed 2026-06-17). Tiny trees — checksum cost is noise.
    rsync -a --checksum --delete --delete-excluded \
      --exclude /.git --exclude /.github --exclude /.bon \
      --exclude /handoffs --exclude /HANDOFF.md \
      --exclude /tests --exclude /docs --exclude /fixtures --exclude /bakeoff \
      --exclude /.claude-plugin/marketplace.json \
      --exclude /mise --exclude /mise-fetch --exclude /.mcp-workspace \
      --exclude /.mise --exclude /data --exclude /uploads \
      --exclude /.oauth-stash --exclude /.claude --exclude /.coverage \
      --exclude /dist \
      --exclude .venv --exclude node_modules --exclude __pycache__ --exclude '*.pyc' \
      --exclude .pytest_cache --exclude .mypy_cache --exclude .ruff_cache \
      --exclude .hypothesis --exclude '*.db' --exclude token.json --exclude .env \
      --exclude .gitignore --exclude .gitattributes \
      --exclude /CHANGELOG.md \
      "$src/" "$dest/"
    # /CHANGELOG.md exclusion (bds-mawitu): per-repo changelogs are no longer
    # shipped — the suite has ONE canonical changelog and every plugin ships a
    # generated stub (below) instead. Root-anchored + --delete-excluded, so a
    # CHANGELOG.md vendored before this rule (mise had a stale one) is removed.
    # Skill plugins never vendored CHANGELOG.md (it's not in their copy-list),
    # so only the full-source MCP branch needs the explicit exclude.
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

  # Wheels after the copy (the MCP branch's rsync --delete clears wheels/, which
  # the source never has) and before the ratchet, so a rebuilt wheel counts as
  # content like everything else (bds-timule).
  build_wheels "$plugin" "$dest"

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

  reroot_markdown "$dest" "$plugin" || exit 1

  # Single-version stamp (bds-suwoho) on the COMPONENT manifest too. Claude
  # Code never reads it (the kit root's is the plugin manifest), but it is the
  # input write_kit_manifest reads hooks and servers from, and the family
  # flavour derives mise-home from mise's — whose version must be the suite's
  # (bds-jupize's coherence check below). And no shipped file may point at a
  # private repo (bds-juwone), manifests included.
  stamp_version "$dest/.claude-plugin/plugin.json" "$SUITE_VERSION"
  stamp_repository "$dest/.claude-plugin/plugin.json" "$repo"

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
  # stamped plugin.json AND the generated CHANGELOG.md stub are filtered out:
  # both are pure functions of the suite version (rewritten identically every
  # run), so neither is ever "source content drift". Escape hatch for local
  # runs: ASSEMBLE_NO_RATCHET=1.
  #
  # QUARANTINE, don't abort (2026-06-17, bds-pujaki): on a trip we revert THIS
  # plugin's vendored dir to its last-published state and record it, instead
  # of failing the whole run. Healthy plugins still publish; a final
  # assemble.yml step fails the run RED naming the laggards. Reverting to HEAD
  # is safe for the post-loop structural invariants (marketplace, MCP) —
  # last-published already satisfied them. Applies ONLY to the version
  # ratchet; the husk/parity guard above stays a hard exit.
  #
  # Per COMPONENT since the fold (bds-jakemi): the subtree is the unit that
  # reverts, and the kit manifest is generated after this loop from the
  # (possibly reverted) component manifests, so a held-back component's hooks
  # match its held-back files. A component with no last-published copy cannot
  # be held back at all — that is a first appearance, and it needs the suite
  # bump that /batterie:publish brings; fail rather than ship a kit without it.
  quarantined_this=0
  if [ -z "${ASSEMBLE_NO_RATCHET:-}" ]; then
    content_changes=$(git -C "$BATTERIE_DIR" status --porcelain -- "plugins/$KIT/$plugin" \
      | grep -v '\.claude-plugin/plugin\.json' | grep -v 'CHANGELOG\.md' | grep -c . || true)
    if [ -n "$OLD_SUITE_VERSION" ] && [ "$content_changes" -gt 0 ] && [ "$SUITE_VERSION" = "$OLD_SUITE_VERSION" ]; then
      if [ -z "$(git -C "$BATTERIE_DIR" ls-tree -d HEAD "plugins/$KIT/$plugin")" ]; then
        echo "FAIL: component $plugin is new in plugins/$KIT/ but the suite version is still $SUITE_VERSION — a first appearance cannot be quarantined; release it with /batterie:publish" >&2
        exit 1
      fi
      # Restore the laggard's vendored dir to EXACTLY last-published:
      # checkout restores tracked files; clean -fd drops newly-added drift
      # files checkout leaves behind (porcelain counts new files, so the
      # revert must drop them too — else `git add -A` would republish them).
      git -C "$BATTERIE_DIR" checkout HEAD -- "plugins/$KIT/$plugin"
      git -C "$BATTERIE_DIR" clean -fdq -- "plugins/$KIT/$plugin"
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

# The public face (bds-mokava, 2026-09-23): most source repos are private, so
# this repo's README is the only place a stranger or teammate can read what the
# suite is. It is authored in batterie-de-savoir (marketplace/README.md, plugin
# table rendered from brigade.toml) and copied verbatim — a hand edit here is
# overwritten. Outside plugins/, so the ratchet never sees it; a missing source
# is a failed checkout, not something to paper over.
MARKETPLACE_README="$SOURCE_DIR/batterie-de-savoir/marketplace/README.md"
if [ ! -f "$MARKETPLACE_README" ]; then
  echo "FAIL: $MARKETPLACE_README missing — the marketplace README is generated there" >&2
  exit 1
fi
cp "$MARKETPLACE_README" "$BATTERIE_DIR/README.md"

# Prune: plugins/ holds the kit and nothing else, and the kit holds its
# components, its generated manifest and its changelog stub and nothing else.
# The first pass is what removes the eight pre-fold plugin dirs; the second
# removes a retired component's subtree and the pre-fold batterie plugin's own
# top-level skills/, hooks/ and scripts/ (now under suite/).
COMPONENT_NAMES=$(for e in $COMPONENTS; do echo "${e%%:*}"; done)
for d in "$BATTERIE_DIR"/plugins/*/; do
  n=$(basename "$d")
  if [ "$n" != "$KIT" ]; then
    rm -rf "$d"
    echo "  PRUNED plugins/$n (folded into $KIT@$KIT)"
  fi
done
for d in "$KIT_DIR"/* "$KIT_DIR"/.[!.]*; do
  [ -e "$d" ] || continue
  n=$(basename "$d")
  case "$n" in .claude-plugin|CHANGELOG.md) continue ;; esac
  if ! printf '%s\n' $COMPONENT_NAMES | grep -qx "$n"; then
    rm -rf "$d"
    echo "  PRUNED plugins/$KIT/$n (not a component)"
  fi
done

# The kit manifest is GENERATED from the component manifests (bds-jakemi),
# after the loop so a quarantined component contributes its held-back hooks.
# Identity (name, displayName, description, author, license, keywords) comes
# from the suite component; version and repository are stamped below like any
# plugin.json. Three merges, each deny-by-default so a manifest feature the
# fold does not yet carry fails the run instead of being dropped in silence:
#   skills      — an array of ./<component>/skills/ (adds to the default skills/)
#   hooks       — the union of every component's hooks. Each command is
#                 re-rooted and prefixed CLAUDE_PLUGIN_ROOT="…/<component>", so a
#                 hook reading that variable sees its own subtree, as before the
#                 fold. Hook commands are shell-form, which is what makes the
#                 prefix an environment assignment.
#   mcpServers  — every component's servers, strings re-rooted; a duplicate
#                 server name across components fails (it would change a tool id).
write_kit_manifest() {
  python3 - "$KIT_DIR" "$KIT" "$COMPONENT_NAMES" <<'PYEOF'
import json, re, sys
from pathlib import Path

kit_dir, kit, comps = Path(sys.argv[1]), sys.argv[2], sys.argv[3].split()
ROOT = "${CLAUDE_PLUGIN_ROOT}"
# Keys a component manifest may carry. Anything else (userConfig, channels,
# dependencies, monitors, lspServers, commands, agents, skills, settings…)
# needs a designed merge first.
ALLOWED = {"name", "displayName", "identity", "version", "description", "author",
           "repository", "homepage", "license", "keywords", "hooks", "mcpServers"}
fails = []

def reroot(s, comp):
    return re.sub(r"\$\{CLAUDE_PLUGIN_ROOT\}(?!/" + re.escape(comp) + r"(?![\w-]))",
                  ROOT + "/" + comp, s)

suite = json.load(open(kit_dir / "suite/.claude-plugin/plugin.json"))
manifest = {"name": kit}
for k in ("displayName", "version", "description", "author", "repository", "license", "keywords"):
    if k in suite:
        manifest[k] = suite[k]
skills, hooks, servers, owner = [], {}, {}, {}

for comp in comps:
    cdir = kit_dir / comp
    pj = json.load(open(cdir / ".claude-plugin/plugin.json"))
    extra = set(pj) - ALLOWED
    if extra:
        fails.append(f"{comp}: manifest keys {sorted(extra)} have no fold merge yet")
    for d in ("commands", "agents"):
        if (cdir / d).is_dir():
            fails.append(f"{comp}: ships {d}/, which the fold does not wire yet")
    for f in (".mcp.json", "hooks/hooks.json"):
        if (cdir / f).exists():
            fails.append(f"{comp}: ships {f}, which only loads at a plugin root")
    if (cdir / "skills").is_dir():
        skills.append(f"./{comp}/skills/")

    h = pj.get("hooks") or {}
    if not isinstance(h, dict):
        fails.append(f"{comp}: hooks must be inline in plugin.json for the fold")
        h = {}
    for event, groups in h.items():
        for g in groups:
            new_hooks = []
            for hk in g.get("hooks", []):
                if hk.get("type") != "command" or "args" in hk:
                    fails.append(f"{comp}: {event} hook is not a shell-form command")
                    continue
                cmd = reroot(hk["command"], comp)
                m = re.match(r"^(\$\{CLAUDE_PLUGIN_ROOT\}/\S+)(.*)$", cmd)
                if not m:
                    fails.append(f"{comp}: {event} hook command does not start with its plugin root: {hk['command']}")
                    continue
                new_hooks.append({**hk, "command":
                    f'CLAUDE_PLUGIN_ROOT="{ROOT}/{comp}" "{m.group(1)}"{m.group(2)}'})
            hooks.setdefault(event, []).append({**g, "hooks": new_hooks})

    for name, cfg in (pj.get("mcpServers") or {}).items():
        if name in servers:
            fails.append(f"{comp}: MCP server '{name}' already declared by {owner[name]}")
            continue
        def walk(v):
            if isinstance(v, str): return reroot(v, comp)
            if isinstance(v, list): return [walk(x) for x in v]
            if isinstance(v, dict): return {k: walk(x) for k, x in v.items()}
            return v
        servers[name], owner[name] = walk(cfg), comp

if skills: manifest["skills"] = skills
if hooks: manifest["hooks"] = hooks
if servers: manifest["mcpServers"] = servers
for f in fails:
    print(f"FAIL: kit manifest — {f}", file=sys.stderr)
if fails:
    sys.exit(1)
(kit_dir / ".claude-plugin").mkdir(exist_ok=True)
with open(kit_dir / ".claude-plugin/plugin.json", "w") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
    f.write("\n")
PYEOF
}
write_kit_manifest || exit 1
stamp_version "$KIT_DIR/.claude-plugin/plugin.json" "$SUITE_VERSION"
stamp_repository "$KIT_DIR/.claude-plugin/plugin.json" "batterie"
# Shipped CHANGELOG is a generated stub pointing at the canonical suite
# changelog (bds-mawitu) — one, at the kit root. Like the stamped manifests it
# is filtered out of the ratchet's content-drift check.
write_changelog_stub "$KIT_DIR" "$SUITE_VERSION"

# Bare skill names must be unique inside the kit and must not shadow a Claude
# Code built-in: a built-in wins the bare name and the kit's skill then answers
# only to its prefix (measured headless 2026-09-27: /code-review ran the
# built-in 3/3). The built-in list is a pinned file beside this script, because
# the names come from the harness, not from anything this repo can read. A
# skill directory whose frontmatter name disagrees fails too — the directory is
# what Claude Code surfaces.
check_skill_names() {
  python3 - "$KIT_DIR" "$BATTERIE_DIR/builtin-names.txt" <<'PYEOF'
import re, sys
from pathlib import Path
kit_dir, builtin_file = Path(sys.argv[1]), Path(sys.argv[2])
builtins = {l.split("#")[0].strip() for l in builtin_file.read_text().splitlines()} - {""}
seen, fails = {}, []
for sk in sorted(kit_dir.glob("*/skills/*/SKILL.md")):
    comp, name = sk.parts[-4], sk.parent.name
    m = re.search(r"^name:\s*(\S+)\s*$", sk.read_text(), re.M)
    if not m or m.group(1) != name:
        fails.append(f"{comp}/skills/{name}: frontmatter name {m.group(1) if m else 'missing'} ≠ directory")
    if name in seen:
        fails.append(f"bare name '{name}' shipped by both {seen[name]} and {comp}")
    seen.setdefault(name, comp)
    if name in builtins:
        fails.append(f"bare name '{name}' ({comp}) shadows a Claude Code built-in")
for f in fails:
    print(f"FAIL: skill names — {f}", file=sys.stderr)
if fails:
    sys.exit(1)
print(f"  OK {len(seen)} skill names unique, none a built-in: {' '.join(sorted(seen))}")
PYEOF
}
check_skill_names || exit 1

# marketplace.json is GENERATED (bds-dekava), never hand-kept: one entry, the
# kit, read from its just-generated manifest.
write_public_marketplace() {
  python3 - "$1" "$KIT" "$KIT_CATEGORY" <<'PYEOF'
import json, sys
root, kit, category = sys.argv[1], sys.argv[2], sys.argv[3]
pj = json.load(open(f"{root}/plugins/{kit}/.claude-plugin/plugin.json"))
entry = {"name": kit, "source": f"./plugins/{kit}",
         "description": pj["description"], "category": category}
if pj.get("repository"):
    entry["homepage"] = pj["repository"]
if pj.get("keywords"):
    entry["keywords"] = pj["keywords"]
manifest = {
    "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
    "name": kit,
    "description": "Kitchen tools for knowledge work — one plugin for GTD tracking, session rituals, Google Workspace, browser automation, cross-session messaging and more",
    "owner": {"name": "Sameer Modha", "email": "sameer@modha.dev"},
    "plugins": [entry],
}
with open(f"{root}/.claude-plugin/marketplace.json", "w") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
    f.write("\n")
PYEOF
}
write_public_marketplace "$BATTERIE_DIR"

# Invariant check 1 (fail): every relative-source plugin in marketplace.json
# must have vendored content — a manifest entry over nothing is how the
# gueridon "could not sync" and the batterie-0.1.6 husk happened.
# Parameterised over the marketplace ROOT (a dir holding .claude-plugin/
# marketplace.json + plugins/) so both outputs run the same guard.
check_manifest() {
  local mroot="$1"
  while read -r mp; do
    if [ ! -f "$mroot/plugins/$mp/.claude-plugin/plugin.json" ]; then
      echo "FAIL: marketplace.json declares '$mp' but plugins/$mp has no plugin.json (in $mroot)" >&2
      exit 1
    fi
  done < <(python3 -c "
import json
m = json.load(open('$mroot/.claude-plugin/marketplace.json'))
for p in m['plugins']:
    src = p.get('source')
    if isinstance(src, str) and src.startswith('./plugins/'):
        print(src.removeprefix('./plugins/'))
")
}
check_manifest "$BATTERIE_DIR"

# Invariant check 3 (fail): MCP entry points must resolve. The manifest
# invariant above only proves plugin.json exists — the mise-0.7.4 husk
# shipped a valid plugin.json whose mcpServers pointed at files that were
# never vendored, and every Cowork session got a dead server. For each
# vendored plugin.json declaring mcpServers: every ${CLAUDE_PLUGIN_ROOT}-
# relative path in command/args must exist; `uv run --project|--directory`
# requires a vendored pyproject.toml; `python -m pkg.mod` must resolve to
# a module under the plugin root. Kills the class at build time.
# Also a function of the marketplace root, reused by the private output.
check_mcp_entrypoints() {
python3 - "$1" <<'PYEOF'
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

        # The project dir is the token after the flag, resolved against the
        # plugin root — since the fold it is a component subtree (…/mise), not
        # the plugin root itself.
        for i, t in enumerate(tokens):
            if t in ("--project", "--directory") and i + 1 < len(tokens):
                proj = tokens[i + 1].replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_dir))
                if not (Path(proj) / "pyproject.toml").exists():
                    failures.append(f"{where} uses uv {t} {tokens[i+1]} but no pyproject.toml is vendored there")

        for i, t in enumerate(tokens):
            if t == "-m" and i + 1 < len(tokens):
                mod = tokens[i + 1].replace(".", "/")
                bases = [plugin_dir] + [d for d in plugin_dir.iterdir() if d.is_dir()]
                if not any((b / f"{mod}.py").exists() or (b / mod / "__init__.py").exists()
                           or (b / "src" / f"{mod}.py").exists() or (b / "src" / mod / "__init__.py").exists()
                           for b in bases):
                    failures.append(f"{where} runs -m {tokens[i+1]} — module not vendored")

for f in failures:
    print(f"FAIL: {f}", file=sys.stderr)
if failures:
    sys.exit(1)
PYEOF
}
check_mcp_entrypoints "$BATTERIE_DIR"

# ---- PRIVATE marketplace: batterie-home (bds-mumise) -------------------------
# Derived from the just-vendored PUBLIC mise — already stamped, already through
# the husk/parity + ratchet machinery above — so the two marketplaces carry
# identical runtime bytes by construction (if public mise was quarantined this
# run, the flavour inherits last-published: still coherent, never divergent).
# The transform rewrites only identity strings + swaps the OAuth client, and
# its built-in guard fails loudly on any leftover ITV-identifying string.
# Gated on MISE_HOME_CRED: CI public runs skip this until bds-susugu wires
# cred delivery; a local run with the cred produces both outputs.
if [ -n "${MISE_HOME_CRED:-}" ]; then
  echo ""
  echo "Assembling private marketplace '$HOME_NAME' → $HOME_OUT"
  [ -f "$MISE_HOME_CRED" ] || { echo "FAIL: MISE_HOME_CRED=$MISE_HOME_CRED not found" >&2; exit 1; }
  rm -rf "$HOME_OUT"
  mkdir -p "$HOME_OUT/plugins" "$HOME_OUT/.claude-plugin"
  "$BATTERIE_DIR/transforms/make-mise-flavour.sh" \
    "$KIT_DIR/mise" "$HOME_OUT/plugins/mise-home" home "$MISE_HOME_CRED"
  # The mise component's skill bodies were re-rooted to ${CLAUDE_PLUGIN_ROOT}/mise
  # for the kit; mise-home is a stand-alone plugin, so a re-rooted path there
  # would point one level too deep. None exist today — fail if one appears.
  if grep -rq 'CLAUDE_PLUGIN_ROOT}/mise' "$HOME_OUT/plugins/mise-home/skills" 2>/dev/null; then
    echo "FAIL: mise-home skills carry a kit-re-rooted \${CLAUDE_PLUGIN_ROOT}/mise path — derive the flavour before reroot_markdown, or drop the reference" >&2
    exit 1
  fi

  # Family stub (bds-rikeno): batterie-home carries ONLY mise-home — the one
  # plugin that MUST be private (it holds the planetmodha Google cred). The rest
  # of the suite is public, so rather than mirror public content into a private
  # repo (which would drag along each plugin's CLI-auto-install + rules-injection
  # SessionStart hooks — per-session noise for tools family never asked for), we
  # ship the onboarding guide with the flavour. "Ask a Claude" is the support
  # model; this is the trail it follows. (Whole-suite mirror was built + rejected
  # 2026-07-12 — the hook footprint made it heavier than the one command it saved.)
  #
  # An ON-DEMAND SKILL, not an append to instructions.md (2026-07-26): that shard
  # auto-loads via ~/.claude/rules/ in EVERY session on EVERY machine carrying
  # mise-home — including Sameer's own ITV work sessions, where twenty lines of
  # family install guidance is pure standing noise. A skill keeps the whole point
  # of making it always-on (its description sits in the skill picker every
  # session, so a family Claude still finds it unprompted and can offer) at one
  # line of standing context instead of twenty. Do NOT move it back into
  # instructions.md — the ratchet below fails the build if it returns.
  MH_SKILL="$HOME_OUT/plugins/mise-home/skills/batterie-suite"
  mkdir -p "$MH_SKILL"
  cat > "$MH_SKILL/SKILL.md" <<'STUBEOF'
---
name: batterie-suite
description: Offers the planetmodha family the rest of the Batterie suite — load BEFORE suggesting or installing any Claude plugin on a family machine. Names the one tool that fits what they just asked for, says what it needs (an account, a CLI, an API token) before they commit, and gives the two commands that add it. Triggers on 'what else can you do', 'are there other tools', 'is there a plugin for that', 'how do I install X', 'can you track my to-dos', 'can you review my code', 'can you draw me a diagram'. (user)
---

# The rest of the Batterie suite (planetmodha family)

This is the planetmodha family install. **mise-home** lives in the private
`batterie-home` marketplace only because it carries the family's Google login —
**everything else in the suite is public** and free to add.

## When to use

- They ask for a capability mise-home doesn't cover — to-dos, code review, diagrams, data analysis.
- They ask what else this Claude can do, or whether a plugin exists for something.
- You're about to suggest installing anything: check here first for what it needs.

## When not to use

- **mise-home itself is misbehaving** — that's an auth or MCP problem, not a missing plugin. Nothing here helps.
- They already have the tool installed and want to *use* it — go straight to its own skill.
- They're on an ITV machine. This is the planetmodha family path; ITV colleagues have their own commons.

## Adding a tool

```
claude plugin marketplace add spm1001/batterie
claude plugin install <name>@batterie
```

The marketplace only needs adding once; after that, install as many as they want.

## What's there, and the honest per-tool guide

- **trousse** — utility skills (diagrams, code review, data analysis). Works immediately, nothing to set up. Good default add.
- **batterie** — keeps their plugins current (`/batterie:update`). Worth having.
- **accomplis** — Todoist with GTD coaching. Needs the `accomplis` CLI *and* a Todoist account + API token. Worth it if they already live in Todoist.
- **bon** — a power-user GTD work-tracker. Needs the `bon` CLI and a local store. Suits someone who wants to track work across sessions (e.g. Isaac); ask before setting it up.

## How to offer it

Name the one tool that fits what they just asked for, say what it needs up
front, and let them choose. Offering beats installing: a tool that turns out to
want an account they don't have is worse than no tool. One good suggestion lands
better than the whole list.
STUBEOF
  [ -s "$MH_SKILL/SKILL.md" ] || { echo "FAIL: family onboarding skill not written → $MH_SKILL/SKILL.md" >&2; exit 1; }
  echo "  OK family onboarding skill → mise-home/skills/batterie-suite"

  # Ratchet (2026-07-26): the guide must never return to the always-on shard.
  # rules/*.md loads unconditionally in every session, so an append here is a
  # standing-context regression on Sameer's work machine, not a cosmetic one.
  if grep -q 'planetmodha family' "$HOME_OUT/plugins/mise-home/instructions.md" 2>/dev/null; then
    echo "FAIL: family onboarding is back in mise-home/instructions.md — it belongs in skills/batterie-suite/ (always-on context regression)" >&2
    exit 1
  fi

  # marketplace.json is generated (a derived artifact of a derived artifact —
  # nothing hand-maintained to drift). NB the marketplace NAME sets the
  # @suffix in plugin keys; the updater matches by the REPO the marketplace
  # is served from (spm1001/batterie-*), which is bds-picefu's concern.
  python3 - "$HOME_OUT" "$HOME_NAME" <<'PYEOF'
import json, sys
out, name = sys.argv[1], sys.argv[2]
manifest = {
    "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
    "name": name,
    "description": "Batterie de Savoir — planetmodha family flavour (mise-home: Google Workspace MCP against the planetmodha estate)",
    "owner": {"name": "Sameer Modha", "email": "sameer@modha.dev"},
    "plugins": [{
        "name": "mise-home",
        "displayName": "Mise Home",
        "source": "./plugins/mise-home",
        "description": "Google Workspace MCP for the planetmodha estate — search Drive, fetch Gmail, act on documents. Requires planetmodha Google OAuth.",
        "category": "integration",
        "homepage": "https://github.com/spm1001/mise-en-space",
        "keywords": ["google", "workspace", "mcp", "family"],
    }],
}
with open(f"{out}/.claude-plugin/marketplace.json", "w") as f:
    json.dump(manifest, f, indent=2)
    f.write("\n")
PYEOF

  # The private repo is a pure artifact — make the output self-describing so
  # a Claude landing there knows not to hand-edit and where the source lives.
  cat > "$HOME_OUT/README.md" <<'READMEEOF'
# batterie-home — Private Family Marketplace (generated)

Private Claude plugin marketplace for the planetmodha estate. Carries ONLY
`mise-home` — the planetmodha-credentialled flavour of mise. Family members
get everything else (bon, trousse, accomplis, batterie) from the PUBLIC
marketplace `spm1001/batterie`; `/batterie:update` spans both automatically
(it matches marketplaces by source repo: `spm1001/batterie` or
`spm1001/batterie-*`).

**Every file here is GENERATED** by `spm1001/batterie`'s `assemble.sh`
(the private output of the shared pipeline — bds-mumise). Never hand-edit;
change mise-en-space or the transform (`transforms/make-mise-flavour.sh`
in spm1001/batterie) and re-assemble. The vendored `credentials.json` is an
installed-app OAuth client (secret public by design); this repo stays
private for the Teams Directory requirement, not for the credential.
READMEEOF
  cat > "$HOME_OUT/CLAUDE.md" <<'CLAUDEEOF'
# batterie-home — Agent Guide

Generated artifact repo — the private output of `spm1001/batterie`'s
`assemble.sh` (one pipeline, two marketplaces; see that repo's CLAUDE.md,
"Two outputs, one pipeline"). **Never hand-edit anything here.** To change
mise-home: change mise-en-space (runtime) or spm1001/batterie's
`transforms/make-mise-flavour.sh` (identity/cred), re-assemble with
`MISE_HOME_CRED` set, and push the fresh `dist/batterie-home` here.
CLAUDEEOF

  # Same guards as the public output, same code.
  check_manifest "$HOME_OUT"
  check_mcp_entrypoints "$HOME_OUT"

  # Version coherence (bds-jupize): the flavour must carry exactly the version
  # the public vendored mise shipped this run — same number on both outputs.
  pub_v=$(python3 -c "import json; print(json.load(open('$KIT_DIR/mise/.claude-plugin/plugin.json'))['version'])")
  home_v=$(python3 -c "import json; print(json.load(open('$HOME_OUT/plugins/mise-home/.claude-plugin/plugin.json'))['version'])")
  if [ "$pub_v" != "$home_v" ]; then
    echo "FAIL: version skew — public mise $pub_v vs mise-home $home_v" >&2
    exit 1
  fi
  echo "  OK mise-home ← plugins/$KIT/mise ($home_v, transformed, cred: $(basename "$MISE_HOME_CRED"))"
else
  echo "  SKIP private marketplace '$HOME_NAME' — MISE_HOME_CRED not set (public-only run)"
fi

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

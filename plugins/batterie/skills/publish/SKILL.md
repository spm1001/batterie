---
name: publish
description: "Ship a Batterie shard or CLI change end-to-end in one verb — bump plugin.json, commit, push, trigger the assemble CI, watch it green, then pull this machine current. Use when you've edited a batterie source repo (instructions.md, a skill, a hook, CLI code) and want it live. Triggers on 'publish this', 'ship this shard', 'release this', 'cut a version', '/batterie:publish'."
allowed-tools: ["Bash", "Read"]
---

# Publish a Batterie shard

The dance — bump version → commit → push → assemble → pull — collapsed into one
command. The engine is `scripts/publish.py`; this skill is the safe wrapper:
it previews with `--dry-run`, you confirm, then it runs for real.

**Publishing runs from any host with the source repos (`~/repos`) and `gh`** —
tube (the primary since the 2026-07 hezza turndown) or hezza while it lasts. On a
machine without `~/repos` (the Mac) there's nothing to push from — use
`/batterie:update` to pull instead.

## This repo (publish target)

!`python3 - <<'PYEOF'
import json, subprocess
from pathlib import Path
cwd = Path.cwd()
pj = cwd / ".claude-plugin" / "plugin.json"
suite_pj = Path.home() / "repos/spm1001/batterie-de-savoir/.claude-plugin/plugin.json"
if not pj.exists():
    print(f"cwd {cwd} has no .claude-plugin/plugin.json — cd into the source repo you want to publish.")
else:
    d = json.load(open(pj))
    suite_v = json.load(open(suite_pj))["version"] if suite_pj.exists() else "?"
    is_suite = cwd.resolve() == suite_pj.parent.parent.resolve()
    print(f"publishing:  {d['name']}   ({cwd.name})")
    print(f"bump target: SUITE version {suite_v} (batterie-de-savoir) — every plugin ships this one number")
    print(f"mode:        {'single-repo (cwd IS the suite repo)' if is_suite else '2-repo push (content here + suite bump in batterie-de-savoir)'}")
    st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
    pending = st.stdout.rstrip()
    print("\nPending in this content repo (tracked edits ship in the content commit; untracked files are REFUSED unless you pass --all — bds-fifuko):")
    print(pending or "  (clean tree)")
PYEOF`

## Your task

### 1. Pick the bump level and the changelog line

**Bump level** — default **patch**. Use minor for a new capability, major for a
breaking change. Map the user's words ("ship the docs fix" → patch; "release the
new skill" → minor) and state which you picked. Under single-version (bds-suwoho)
the bump always applies to the **suite version** (batterie-de-savoir's
plugin.json) — the one number every plugin ships — whichever repo you're
publishing from.

**Changelog line** — the suite ships ONE canonical CHANGELOG (bds-mawitu), and
`publish.py` prepends an entry to it every release, so a shipped plugin's
changelog can never predate its version. Draft a **one-line** human narrative of
what this release does (e.g. *"Carrying mise: fetch handles Shared Drives"*) and
pass it as `--changelog "…"`. If you don't, the commit message is used verbatim —
fine for a mechanical release, but a written line reads far better to the family
Claudes who orient off these files. Confirm the line with the user alongside the
bump level.

### 2. Dry-run first — always

Resolve the engine from the local source tree and preview:

```
uv run --script ~/repos/spm1001/batterie-de-savoir/scripts/publish.py --patch --changelog "one-line narrative" --dry-run
```

(run from the **cwd of the repo being published** — it operates on cwd). Swap
`--patch` for the chosen level. The dry-run shows the `changelog: [x.y.z] …`
line it will prepend.

### 3. Review the plan with the human

Show the dry-run output and **call out the staging list explicitly**. In the
**content repo** `publish.py` stages tracked modifications (`git add -u`), so
every *tracked* pending file there ships in the content commit — if a tracked
edit looks unrelated to this release, stop and ask. **Untracked files are a hard
stop** (bds-fifuko): the engine refuses rather than sweep them, so a stray
scratch/WIP file can't leak into a pushed, marketplace-triggering commit. If an
untracked file genuinely belongs in the release (e.g. a brand-new skill file),
re-run with `--all` — deliberately, after the human has seen it. (The
suite-version bump is a separate, targeted plugin.json+CHANGELOG commit in
batterie-de-savoir, so it can't sweep that repo's WIP.) Confirm: suite bump (old
→ new), commit message, wait+pull on, and — when publishing a non-batterie repo
— that it's a **2-repo push** (content here, suite bump in batterie-de-savoir).

### 4. Run it for real

On confirmation, drop `--dry-run` (keep the same `--changelog`). If the release
legitimately includes new/untracked files the dry-run flagged, also pass `--all`
(the engine refuses untracked files otherwise):

```
uv run --script ~/repos/spm1001/batterie-de-savoir/scripts/publish.py --patch --changelog "one-line narrative"
```

It will: push the content change (cwd repo), bump the **suite version** +
prepend the **CHANGELOG entry** in batterie-de-savoir (one combined commit if
you're publishing batterie-de-savoir itself; a targeted plugin.json+CHANGELOG
commit otherwise), push, trigger `assemble.yml`, and **watch the run to green**
(~1–2 min). The assembler stamps every plugin to the new suite number and
regenerates each plugin's shipped CHANGELOG stub (which just points back at the
canonical suite changelog — so no shipped changelog can ever look stale).
A red run is almost always a suite-level version-ratchet quarantine — content
drifted but the suite version wasn't bumped; the message names the failing run.
Then it pulls this machine current for the published plugin (marketplace update
→ plugin update → CLI reinstall from source with `--no-cache` if this repo
ships a CLI).

Escape hatches if asked: `--no-wait` (trigger, don't watch), `--no-pull` (push
only), `-m "msg"` (commit message).

### 5. Report + restart

Report the new version and that it went green. If the pull ran, remind the user:

```
Restart Claude Code (/exit then claude) to activate hook/skill changes —
SessionStart hooks only fire on a full restart. (Any CLI reinstall is already live.)
```

## Notes

- **Why no local assemble step:** `assemble.yml` CI owns assembling every repo
  into the marketplace (daily 07:00 UTC + the dispatch this verb triggers).
  Running `assemble.sh` locally would fight it. `publish.py` triggers and watches
  the CI; it never assembles.
- **One plugin, not all:** the suite bump re-versions every plugin in the
  marketplace, but this pulls only the plugin you just shipped. The others show
  "update available" until `/batterie:update` — the "bring everything current"
  sibling.
- **Lazy CLI convergence (jomiwa):** when you publish a *non*-batterie source
  repo, its own `plugin.json` is also stamped to the new suite version inside the
  content commit — so that CLI's `--version` reads "the suite release that last
  changed it" and ticks toward the suite number as it changes. Only the repo being
  published is stamped (never its siblings), so there's no per-release multi-repo
  dance — CLIs converge lazily, not on every bump.

---
name: publish
description: "Ship a Batterie shard or CLI change end-to-end in one verb — bump plugin.json, commit, push, trigger the assemble CI, watch it green, then pull this machine current. Use when you've edited a batterie source repo (instructions.md, a skill, a hook, CLI code) and want it live. Triggers on 'publish this', 'ship this shard', 'release this', 'cut a version', '/batterie:publish'."
allowed-tools: ["Bash", "Read"]
---

# Publish a Batterie shard

The dance — bump version → commit → push → assemble → pull — collapsed into one
command. The engine is `scripts/publish.py`; this skill is the safe wrapper:
it previews with `--dry-run`, you confirm, then it runs for real.

**Publishing is a hezza operation.** It needs the source repos (`~/repos`) and
`gh`. On a machine without `~/repos` there's nothing to push from — use
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
    print("\nPending in this content repo (git add -A sweeps ALL of these into the content commit):")
    print(pending or "  (clean tree)")
PYEOF`

## Your task

### 1. Pick the bump level

Default **patch**. Use minor for a new capability, major for a breaking change.
Map the user's words ("ship the docs fix" → patch; "release the new skill" →
minor) and state which you picked. Under single-version (bds-suwoho) the bump
always applies to the **suite version** (batterie-de-savoir's plugin.json) — the
one number every plugin ships — whichever repo you're publishing from.

### 2. Dry-run first — always

Resolve the engine from the hezza source tree and preview:

```
uv run --script ~/repos/spm1001/batterie-de-savoir/scripts/publish.py --patch --dry-run
```

(run from the **cwd of the repo being published** — it operates on cwd). Swap
`--patch` for the chosen level.

### 3. Review the plan with the human

Show the dry-run output and **call out the staging list explicitly**. In the
**content repo** `publish.py` runs `git add -A`, so every pending file there
ships in the content commit — if anything looks unrelated to this release, stop
and ask; don't sweep WIP into a push. (The suite-version bump is a separate,
targeted plugin.json-only commit in batterie-de-savoir, so it can't sweep that
repo's WIP.) Confirm: suite bump (old → new), commit message, wait+pull on, and
— when publishing a non-batterie repo — that it's a **2-repo push** (content
here, suite bump in batterie-de-savoir).

### 4. Run it for real

On confirmation, drop `--dry-run`:

```
uv run --script ~/repos/spm1001/batterie-de-savoir/scripts/publish.py --patch
```

It will: push the content change (cwd repo), bump + push the **suite version**
in batterie-de-savoir (one combined commit if you're publishing
batterie-de-savoir itself), trigger `assemble.yml`, and **watch the run to
green** (~1–2 min). The assembler stamps every plugin to the new suite number.
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

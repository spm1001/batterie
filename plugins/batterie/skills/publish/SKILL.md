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
pj = Path.cwd() / ".claude-plugin" / "plugin.json"
if not pj.exists():
    print(f"cwd {Path.cwd()} has no .claude-plugin/plugin.json — cd into the source repo you want to publish.")
else:
    d = json.load(open(pj))
    print(f"plugin: {d['name']}   current version: {d['version']}   ({Path.cwd().name})")
    st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
    pending = st.stdout.rstrip()
    print("\nPending changes (git add -A will sweep ALL of these into the release commit):")
    print(pending or "  (clean tree — publish would create a version-bump-only commit)")
PYEOF`

## Your task

### 1. Pick the bump level

Default **patch**. Use minor for a new capability, major for a breaking change.
Map the user's words ("ship the docs fix" → patch; "release the new skill" →
minor) and state which you picked.

### 2. Dry-run first — always

Resolve the engine from the hezza source tree and preview:

```
uv run --script ~/repos/spm1001/batterie-de-savoir/scripts/publish.py --patch --dry-run
```

(run from the **cwd of the repo being published** — it operates on cwd). Swap
`--patch` for the chosen level.

### 3. Review the plan with the human

Show the dry-run output and **call out the staging list explicitly**. `publish.py`
runs `git add -A`, so every pending file ships in the release commit. If anything
there looks unrelated to this release, stop and ask — don't sweep WIP into a
push. Confirm: version bump (old → new), commit message, that wait+pull are on.

### 4. Run it for real

On confirmation, drop `--dry-run`:

```
uv run --script ~/repos/spm1001/batterie-de-savoir/scripts/publish.py --patch
```

It will: write the bump, commit (`-m` to override the default message), push,
trigger `assemble.yml`, and **watch the run to green** (~1–2 min). A red run is
almost always a version-ratchet quarantine — a plugin's content drifted without
a bump; the message names the failing run. Then it pulls this machine current
(marketplace update → plugin update → CLI reinstall from source with
`--no-cache` if this repo ships a CLI).

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
- **One plugin, not all:** this pulls only the plugin you just shipped.
  `/batterie:update` is the "bring everything current" sibling.

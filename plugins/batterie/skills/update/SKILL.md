---
name: update
description: "Update all installed batterie plugins in one go"
allowed-tools: ["Bash", "Read"]
---

# Update Batterie Plugins

## Currently installed (before update)

!`python3 << 'PYEOF'
import json, os, re, subprocess, shutil

# Default to the real plugins dir. BATTERIE_PLUGINS_DIR is a test seam (lets the
# regression test point discovery at a fixture); unset in normal use.
PLUGINS = os.environ.get("BATTERIE_PLUGINS_DIR") or os.path.join(
    os.path.expanduser("~"), ".claude", "plugins")

def is_batterie_family(repo):
    # The suite's marketplaces are spm1001/batterie (public) plus spm1001/batterie-*
    # (e.g. a private Directory flavour). Match by source repo, not by "contains the
    # batterie plugin": someone may cherry-pick a single plugin from a second
    # batterie-family marketplace WITHOUT installing the batterie plugin from it, so
    # plugin-membership is not a sufficient test. Source-repo matching also survives
    # plugin renames. The pattern stays generic — no specific marketplace is named.
    return repo == "spm1001/batterie" or repo.startswith("spm1001/batterie-")

def source_repo(info):
    # Normalise a known_marketplaces.json entry to "owner/repo". Shapes seen in
    # the wild: {"source":"github","repo":"o/r"} (shorthand add); {"source":"git",
    # "url":"https://github.com/o/r.git"} (URL add — a normal, PERSISTENT shape:
    # tube ran this way and every @batterie plugin silently vanished from this
    # snapshot, bds-mifubu); {"source":"directory","path":...} (local dev, no repo).
    src = info.get("source") if isinstance(info, dict) else None
    if not isinstance(src, dict):
        return ""
    if src.get("repo"):
        return src["repo"]
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/*$", src.get("url") or "")
    return m.group(1) if m else ""

def family_marketplaces():
    # Read CC's marketplace-name -> source registry. Fall back to the public
    # marketplace name if it can't be read, so single-marketplace users keep
    # working (only a private flavour would be missed, in that rare case).
    try:
        reg = json.load(open(os.path.join(PLUGINS, "known_marketplaces.json")))
    except Exception:
        return {"batterie"}
    fam = {name for name, info in reg.items() if is_batterie_family(source_repo(info))}
    return fam or {"batterie"}

try:
    plugins = json.load(open(os.path.join(PLUGINS, "installed_plugins.json"))).get("plugins", {})
except Exception as e:
    # A failed read must never render like an empty install (bds-mifubu).
    print(f"⚠️ SNAPSHOT FAILED: could not read installed_plugins.json ({e}).")
    print("Do NOT treat this as 'nothing to update' — Read ~/.claude/plugins/installed_plugins.json directly and use it as the before-state.")
    raise SystemExit(0)

fam = family_marketplaces()
mkt = lambda key: key.rsplit("@", 1)[1] if "@" in key else ""
suite_plugins = {k: v[0] for k, v in plugins.items() if mkt(k) in fam and v}

# A family-NAMED marketplace that didn't resolve as family means the discovery
# above has a gap (an unrecognised source shape): its plugins would vanish from
# this snapshot while remaining installed — the bds-mifubu failure. Warn, never
# silently drop.
suspicious = sorted({m for m in {mkt(k) for k in plugins}
                     if (m == "batterie" or m.startswith("batterie-")) and m not in fam})
if suspicious:
    print(f"⚠️ SNAPSHOT WARNING: marketplace(s) {', '.join(suspicious)} carry installed plugins and family-style names but did not resolve as batterie-family — unrecognised source shape in known_marketplaces.json? Their plugins are MISSING below. Read that file and reconcile before trusting this snapshot.\n")

if not suite_plugins:
    if suspicious:
        print("Snapshot unusable — do NOT treat as 'nothing to update'. Read ~/.claude/plugins/installed_plugins.json for the true before-state.")
    elif os.path.isdir(os.path.join(PLUGINS, "cache", "batterie")):
        print("⚠️ Registry lists no batterie plugins but a batterie plugin cache exists — possible silent registry drop (bds-wezubo). Verify before proceeding; 'claude plugin install <name>@batterie' restores entries.")
    else:
        print("No batterie plugins installed.")
else:
    markets = sorted({mkt(k) for k in suite_plugins})
    multi = len(markets) > 1
    base_names = {k.rsplit("@", 1)[0] for k in suite_plugins}

    suite = next((i["version"] for k, i in suite_plugins.items()
                  if k.rsplit("@", 1)[0] == "batterie"), None)
    if suite:
        print(f"📦 Batterie suite v{suite}\n")
    if multi:
        print(f"Marketplaces to refresh: {', '.join(markets)}\n")
    print(f"Found {len(suite_plugins)} batterie plugin(s):\n")
    for key, info in sorted(suite_plugins.items()):
        # Show the full name@marketplace key only when more than one marketplace
        # is in play, so the single-marketplace view is unchanged.
        label = key if multi else key.rsplit("@", 1)[0]
        print(f"- {label}: v{info['version']} (sha: {info['gitCommitSha'][:12]})")

    # CLI version check — keyed by plugin base-name (a CLI's source repo is the
    # same whichever marketplace shipped the plugin).
    cli_tools = {"bon": "bon", "accomplis": "accomplis"}
    print("\nCLI tool versions:")
    for plugin_name, cli_name in cli_tools.items():
        if plugin_name in base_names:
            path = shutil.which(cli_name)
            if path:
                try:
                    result = subprocess.run([cli_name, "--version"], capture_output=True, text=True, timeout=5)
                    ver = result.stdout.strip() or result.stderr.strip()
                    print(f"- {cli_name}: {ver}")
                except Exception:
                    print(f"- {cli_name}: (version check failed)")
            else:
                print(f"- {cli_name}: NOT IN PATH")
PYEOF`

## Your task

Update every batterie plugin listed above. Follow these steps exactly:

**Snapshot sanity gate:** if the snapshot above shows any ⚠️ line — or claims nothing is installed while batterie plugins are plainly active in this session — do not proceed from it. Read `~/.claude/plugins/installed_plugins.json` directly and use that as the before-state (and `known_marketplaces.json` to see what the marketplace list should have been). A false-empty snapshot otherwise turns the whole update into a silent no-op (bds-mifubu).

### 1. Refresh each batterie-family marketplace

Refresh every marketplace shown above. For each marketplace name listed, run:

```
claude plugin marketplace update <marketplace>
```

In the common single-marketplace case there's just one — `batterie` — so this is a single `claude plugin marketplace update batterie`. Refreshing pulls the latest index so plugin updates can see new versions; without it, `claude plugin update` compares against a stale index.

**If this fails with "corrupted installLocation (…) — expected a path inside <this config dir>":** nothing is corrupted. The session is running under a secondary `CLAUDE_CONFIG_DIR` that shares the primary's plugins tree (e.g. a symlinked `plugins/`), and CC's prefix check can't see through the alias. The error itself names the owner — the path above `/plugins/marketplaces/` — so rerun this step and step 2's commands with `CLAUDE_CONFIG_DIR=<that dir>`. Do **not** follow the error's remove-and-re-add advice: on a shared tree it forks the plugin state (bds-nawidu).

### 2. Update each plugin from its own marketplace

For each plugin shown above, update it by its **full `<name>@<marketplace>` key** — the marketplace suffix is part of the listing (e.g. `<plugin>@<marketplace>`):

```
claude plugin update <name>@<marketplace>
```

A plugin must be updated from the marketplace it was installed from, so keep the suffix. In the single-marketplace case every key ends `@batterie` (e.g. `claude plugin update bon@batterie`). Run them sequentially — each must complete before the next starts. Report the output of each.

### 3. Check what changed

After all updates, read `~/.claude/plugins/installed_plugins.json` again. For each batterie plugin, compare the **version** and **gitCommitSha** against the "before" snapshot above. Report:
- Which plugins had version changes (old → new)
- Which were already up to date

**Registry-drop guard (bds-vegowo).** Also diff the *set of keys*: every batterie plugin present in the "before" snapshot must still be present in the after-state. A plugin registry entry can vanish silently — Claude Desktop has been caught bulk-rewriting `installed_plugins.json` and emptying `@batterie` entries while leaving the plugin cache intact — and the loss is invisible (the plugin's skills just stop loading, no error, no log) until you happen to look. This update run is exactly when a human is looking. So if any batterie plugin from the "before" list is **absent** from the after-state, **warn loudly** — it's a silent registry drop, not a normal update — and offer the known fix (it restores the entry cleanly from the intact cache):

```
claude plugin install <name>@<marketplace>
```

**JSON structure of `installed_plugins.json`:**

```json
{
  "version": "...",
  "plugins": {
    "bon@batterie": [
      {"scope": "user", "installPath": "/path/to/cache/bon/0.8.0", "version": "0.8.0", "gitCommitSha": "..."}
    ],
    ...
  }
}
```

Each plugin key maps to a **list** of installations (one per scope). Use `v[0]` to get the user-scope entry.

### 4. Detect CLI drift — by commit, never by version number

Two batterie plugins ship CLI tools installed via `uv tool install`:

| Plugin | CLI binary | Package | Source repo | Extras |
|--------|-----------|---------|-------------|--------|
| bon | `bon` | `bon` | `spm1001/bon` | `[dolt]` |
| accomplis | `accomplis` | `accomplis` | `spm1001/accomplis` | |

(passe left the suite 2026-07-07 — its CLI installs standalone and its shard/tunnel live in `spm1001/passe-partout`; this skill no longer manages it.)

**Do NOT compare the plugin version against the CLI version.** Post-cutover (bds-suwoho) every vendored plugin.json carries the stamped **suite** version while each CLI reports its own source-repo number — those differ by design, so a version comparison fires a false reinstall on every run (bds-zojide / bds-japoca). The truthful drift signal is the **git commit**.

For each CLI in the table:

1. **Installed commit:** read `commit_id` from the tool's provenance record:
   ```
   cat ~/.local/share/uv/tools/<plugin>/lib/python*/site-packages/*.dist-info/direct_url.json
   ```
   (the dist-info dir uses the package name with underscores, e.g. `accomplis-…`; the glob handles it).
2. **Origin commit:** `git ls-remote https://github.com/<source-repo> HEAD`.
3. Decide:
   - `commit_id` **equals** origin HEAD → current, skip (report "up to date").
   - `commit_id` **differs**, or the CLI is **not in PATH** → reinstall **from git** (command below).
   - `direct_url.json` has **no `commit_id`** (a `file://` URL — this machine deliberately installs from a local working tree) → reinstall from that same working-tree path. **Provenance is sticky:** never switch a machine's install source just because a `~/repos` clone happens to exist or not — a clone present for editing must not silently become the operational install (bds-zojide).
4. Reinstall commands — `--no-cache` is load-bearing: uv reuses a cached *build* of the source and `uv cache clean` does NOT clear it, so a src-light change silently reinstalls the old wheel (bds-vanuta; verified 2026-06-17):
   - **Git** (the default): `uv tool install "<pkg>[<extras>] @ git+https://github.com/<source-repo>" --force --reinstall --no-cache` — PEP 508 form, extras go **before** the `@`.
   - **Working-tree** (only when step 3 says provenance is a local dir): `uv tool install "~/repos/<source-repo>[<extras>]" --force --reinstall --no-cache`.
   Always include extras from the table (bon is always `[dolt]` — PyMySQL is tiny and harmless; always installing it avoids silent breakage when any project uses the Dolt backend). **Never install from `installPath` or a bare PyPI name** — the plugin cache ships no `pyproject.toml` and none of these CLIs are on PyPI.
5. After any reinstall, **re-read `<cli> --version` and report the version that actually landed** — never report an expected number (a claim the probe hasn't confirmed). The CLI's number is its own source-repo version, not the suite number; matching is neither expected nor checked.

### 5. Summarise

Lead with the **Batterie suite version** — read the post-update version of the `batterie` plugin from `installed_plugins.json` (its `batterie@<marketplace>` key, normally `batterie@batterie`) and report it as the headline (e.g. `📦 Batterie suite v1.0.0`), since that's the single number the user quotes. Then:

If any plugins were updated:
```
Updates complete. Exit and restart Claude Code (`/exit` then `claude`) to activate changes.
SessionStart hooks only fire on full restart — /reload-plugins won't trigger them.
```

If nothing changed: just say all plugins are up to date, no restart needed.

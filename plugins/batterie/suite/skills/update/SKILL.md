---
name: update
description: "Update the batterie plugin and its CLIs in one go — and move a machine from the old per-tool plugins (bon, trousse, mise…) to the one plugin"
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
# One key can carry several install entries — a user-scope one plus a
# project-scope one per projectPath (bds-getaka). Headline the user entry; list
# the rest beneath it so step 2 updates every scope, not just the one a bare
# "claude plugin update" touches.
user_entry = lambda v: next((e for e in v if e.get("scope") == "user"), v[0])
suite_plugins = {k: user_entry(v) for k, v in plugins.items() if mkt(k) in fam and v}
other_scopes = {k: [e for e in plugins[k] if e is not suite_plugins[k]] for k in suite_plugins}

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
        for e in other_scopes[key]:
            where = f" {e['projectPath']}" if e.get("projectPath") else ""
            print(f"  ↳ {e.get('scope', '?')} scope{where}: v{e.get('version', '?')} (sha: {(e.get('gitCommitSha') or '')[:12]})")

    # CLI version check. Since the kit fold every CLI ships inside batterie, so
    # the kit being installed is enough; a pre-fold per-tool plugin still counts.
    cli_tools = {"bon": "bon", "accomplis": "accomplis"}
    print("\nCLI tool versions:")
    for plugin_name, cli_name in cli_tools.items():
        if plugin_name in base_names or "batterie" in base_names:
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

# The kit fold (bds-jakemi): the public marketplace now lists ONE plugin,
# batterie, carrying every tool. Claude Code does not uninstall a plugin its
# marketplace stops listing, so name every old per-tool install, every scope.
OLD = ("bon", "trousse", "mise", "accomplis", "sonner", "passe", "arete")
public = {m for m, info in (lambda: (json.load(open(os.path.join(PLUGINS, "known_marketplaces.json")))
          if os.path.exists(os.path.join(PLUGINS, "known_marketplaces.json")) else {}))().items()
          if source_repo(info) == "spm1001/batterie"} or {"batterie"}
# Only once the installed batterie IS the kit (its install holds the suite/ and
# bon/ components): a pre-fold batterie beside the per-tool plugins is the
# normal pre-release state, and uninstalling them then would strip the tools.
kit_entries = [e for m in public for e in plugins.get(f"batterie@{m}", [])]
folded = any(os.path.isdir(os.path.join(e.get("installPath", ""), "suite"))
             and os.path.isdir(os.path.join(e.get("installPath", ""), "bon")) for e in kit_entries)
stale = sorted(k for k in plugins if k.rsplit("@", 1)[0] in OLD and mkt(k) in public) if folded else []
synced_root = os.path.join(PLUGINS, "synced")
synced = sorted({os.path.basename(r) for r, dirs, _ in os.walk(synced_root)
                 if os.path.basename(r) in OLD and r.count(os.sep) - synced_root.count(os.sep) <= 3}) \
         if os.path.isdir(synced_root) else []
if folded and (stale or synced):
    print("\n🔀 MOVE TO ONE PLUGIN NEEDED — step 1b below:")
    for k in stale:
        for e in plugins[k]:
            where = f" {e['projectPath']}" if e.get("projectPath") else ""
            print(f"  - {k} ({e.get('scope', '?')} scope{where}, v{e.get('version', '?')})")
    for n in synced:
        print(f"  - {n}: synced from claude.ai (plugins/synced) — the terminal cannot remove it; uninstall it in claude.ai or Desktop, Customize → Plugins")
    has_kit = any(f"batterie@{m}" in plugins for m in public)
    print(f"  batterie@batterie is {'installed' if has_kit else 'NOT installed — step 1b installs it'}")
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

### 1b. Move from the per-tool plugins to the one plugin (only if the snapshot shows 🔀)

Until the kit fold each tool was its own plugin in the public marketplace (`bon@batterie`, `trousse@batterie`, `mise@batterie`, `accomplis@batterie`, `sonner@batterie`, `passe@batterie`, `arete@batterie`). Now `batterie@batterie` carries them all, and an old one left installed runs its hooks a second time and starts a second Google Workspace server. For each old key the snapshot listed, every scope:

```
claude plugin uninstall <name>@batterie                                   # user scope
cd <projectPath> && claude plugin uninstall <name>@batterie --scope project  # each project-scope line
```

The `$HOME` guard in step 2 applies to a project-scope uninstall at the home directory, doubly so: a project-scope uninstall there once deleted user `enabledPlugins` entries. Then, if the snapshot said `batterie@batterie` is not installed:

```
claude plugin install batterie@batterie
```

Report what you removed, and name anything you could not: a plugin synced from claude.ai lives in `plugins/synced/` and only claude.ai or Desktop can remove it (Customize → Plugins); tell the user to do that there. An empty registry is a normal case here — a machine whose plugins all came from claude.ai — so don't read it as nothing to do; the snapshot's synced lines are the list. Permission rules naming `mcp__plugin_mise_mise__…` now need `mcp__plugin_batterie_mise__…`; say so if you see one in `settings.json`. After this step, carry on with step 2 for what remains (normally just `batterie@batterie`).

### 2. Update each plugin from its own marketplace

For each plugin shown above, update it by its **full `<name>@<marketplace>` key** — the marketplace suffix is part of the listing (e.g. `<plugin>@<marketplace>`):

```
claude plugin update <name>@<marketplace>
```

A plugin must be updated from the marketplace it was installed from, so keep the suffix. In the single-marketplace case every key ends `@batterie` (e.g. `claude plugin update bon@batterie`). Run them sequentially — each must complete before the next starts. Report the output of each.

**Then update every `↳ project scope` line the snapshot showed** (bds-getaka). The bare command only ever touches the **user**-scope install, whatever directory it runs from — it says so ("at user scope") — so a project-scope copy stays silently behind. For each one, run from its `projectPath`:

```
cd <projectPath> && claude plugin update <name>@<marketplace> --scope project
```

Don't remove these duplicates instead: on a machine with a second config dir (the commis seat), a session launched at `$HOME` re-mints a project-scope entry for every enabled plugin, so a removal is undone by the next such session (measured 2026-08-31, carte-tikije). Why it matters: on 2026-09-23 tube's `/home/modha` copies sat at 1.85.20 — before CLIs shipped as wheels — while user scope was on 1.86.5, and sessions launched at `~` are the estate's normal pattern.

**Guard when `<projectPath>` is the home directory:** a `$HOME` project's config dir is the user config dir, so scope-targeted commands there can edit **user** `settings.json` (a `--scope project` *uninstall* once deleted user `enabledPlugins` entries, 2026-08-17). Take `git -C ~/.claude status --short settings.json` before and after, or a copy of the file where `~/.claude` isn't git-tracked, and restore anything that changed.

### 3. Check what changed

After all updates, read `~/.claude/plugins/installed_plugins.json` again. For each batterie plugin, compare the **version** and **gitCommitSha** of **every install entry** (each scope separately) against the "before" snapshot above. Report:
- Which plugins had version changes (old → new), per scope
- Which were already up to date
- **Any plugin whose scopes still disagree after the run** — say so loudly; that is the failure this step exists to catch, not a detail

**Registry-drop guard (bds-vegowo).** Also diff the *set of keys*: every batterie plugin present in the "before" snapshot must still be present in the after-state. A plugin registry entry can vanish silently — Claude Desktop has been caught bulk-rewriting `installed_plugins.json` and emptying `@batterie` entries while leaving the plugin cache intact — and the loss is invisible (the plugin's skills just stop loading, no error, no log) until you happen to look. This update run is exactly when a human is looking. So if any batterie plugin from the "before" list is **absent** from the after-state, **warn loudly** — it's a silent registry drop, not a normal update — and offer the known fix (it restores the entry cleanly from the intact cache):

```
claude plugin install <name>@<marketplace>
```

**JSON structure of `installed_plugins.json`:**

```json
{
  "version": "...",
  "plugins": {
    "batterie@batterie": [
      {"scope": "user", "installPath": "/path/to/cache/batterie/batterie/1.88.0", "version": "1.88.0", "gitCommitSha": "..."}
    ],
    ...
  }
}
```

Each plugin key maps to a **list** of installations — one `user`-scope entry plus one `project`-scope entry per `projectPath`. Pick the user entry by its `scope` field, not by position.

### 4. Converge the CLIs onto the wheels the plugins ship

Four batterie tools install a CLI with `uv tool install`, and since bds-timule (2026-09-23) the assembler builds each one into a wheel inside the plugin itself — since the kit fold, under its component: `<installPath>/<component>/wheels/<package>-*.whl` in the `batterie@batterie` install. The source repos are private, so the wheel is the install source for everyone; the git URL is a maintainer fallback that only works with GitHub credentials.

| Component | CLI binary / package | Extras |
|--------|----------------------|--------|
| bon | `bon` | `[dolt]` |
| accomplis | `accomplis` | |
| passe | `passe` | |
| sonner | `sonner` | |

Plus **deglacer**, shipped in `trousse/wheels/`: converge it the same way *if it is already installed* (`command -v deglacer`), never install it unasked.

**Do NOT compare the plugin version against the CLI version.** Every vendored plugin.json carries the stamped **suite** version while each CLI reports its own number — they differ by design (bds-zojide / bds-japoca). The truthful signal is whether the installed CLI came from the wheel this plugin now ships.

For each CLI (all four ship in the kit):

1. **Shipped wheel:** the `batterie@batterie` user-scope `installPath` from `installed_plugins.json` (step 3), then `ls <installPath>/<component>/wheels/<package>-*.whl`. Exactly one is expected.
2. **Installed provenance:** `cat ~/.local/share/uv/tools/<package>/lib/python*/site-packages/*.dist-info/direct_url.json`.
3. Decide:
   - `url` is `file://<the shipped wheel>` → current, skip ("up to date").
   - `url` is a `file://….whl` elsewhere (an older plugin version's copy) → current if that file still exists and `cmp -s` says it is byte-identical to the shipped wheel (hatchling builds are reproducible, so an unchanged CLI rebuilds to the same bytes); otherwise reinstall.
   - `url` carries `vcs_info` (an old git install) or the CLI is **not on PATH** → reinstall from the shipped wheel.
   - `url` carries `dir_info` (a local working tree, e.g. a maintainer's `~/repos` clone) → reinstall from the shipped wheel too, and say so in the report ("was a working-tree install — now on the shipped wheel"). **Every machine runs what everyone else runs**, maintainers included, even when that is a faff (Sameer, 2026-09-23: a maintainer running something different from teammates has bitten us before). Testing a local build is a deliberate, temporary act; the next update puts the machine back. The old rule from bds-zojide still holds in its original direction: never switch an install *onto* a working tree just because a clone exists.
   - The component ships **no** `wheels/` (a copy older than bds-timule) → say so and fall back to `uv tool install "<package>[<extras>] @ git+https://github.com/spm1001/<package>"`, which needs GitHub credentials.
4. Reinstall: `uv tool install "<shipped wheel><extras>" --force --reinstall --no-cache` — e.g. `uv tool install "/…/batterie/1.88.0/bon/wheels/bon-1.85.19-py3-none-any.whl[dolt]" …`. Extras follow the path directly. `--no-cache` is load-bearing (bds-vanuta). Never install from a bare PyPI name: none of these CLIs is on PyPI.
5. After any reinstall, **re-read `<cli> --version` and report the version that actually landed** (sonner has no `--version`; report "installed"). The CLI's number is its own, not the suite number.

### 5. Summarise

Lead with the **Batterie suite version** — read the post-update version of the `batterie` plugin from `installed_plugins.json` (its `batterie@<marketplace>` key, normally `batterie@batterie`) and report it as the headline (e.g. `📦 Batterie suite v1.0.0`), since that's the single number the user quotes. Then:

If any plugins were updated:
```
Updates complete. Exit and restart Claude Code (`/exit` then `claude`) to activate changes.
SessionStart hooks only fire on full restart — /reload-plugins won't trigger them.
```

If nothing changed: just say all plugins are up to date, no restart needed.

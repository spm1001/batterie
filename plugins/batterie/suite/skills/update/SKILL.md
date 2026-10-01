---
name: update
description: "Update the batterie plugin and its CLIs in one go — and move a machine from the old per-tool plugins (bon, trousse, mise…) to the one plugin"
allowed-tools: ["Bash", "Read"]
---

# Update Batterie Plugins

## Currently installed (before update)

!`python3 << 'PYEOF'
import json, os, re, subprocess, shutil

# Default to the real plugins dir — under CLAUDE_CONFIG_DIR when set, as Claude
# Code itself reads it. BATTERIE_PLUGINS_DIR is a test seam (lets the regression
# test point discovery at a fixture); unset in normal use.
PLUGINS = os.environ.get("BATTERIE_PLUGINS_DIR") or os.path.join(
    os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude"), "plugins")
# User settings sit beside plugins/: the file 'claude plugin marketplace add' writes.
SETTINGS = os.path.join(os.path.dirname(PLUGINS), "settings.json")

def is_batterie_family(repo):
    # The suite's marketplaces are spm1001/batterie (public) plus spm1001/batterie-*
    # (e.g. a private Directory flavour). Match by source repo, not by "contains the
    # batterie plugin": someone may cherry-pick a single plugin from a second
    # batterie-family marketplace WITHOUT installing the batterie plugin from it, so
    # plugin-membership is not a sufficient test. Source-repo matching also survives
    # plugin renames. The family kit left the pattern when batterie-home became
    # spm1001/family-kit (27 Sep 2026), so it is named (bds-lecote).
    return repo in ("spm1001/batterie", "spm1001/family-kit") or repo.startswith("spm1001/batterie-")

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

def describe(src):
    target = src.get("repo") or src.get("url") or src.get("path")
    extra = " ".join(f"{k}={json.dumps(v)}" for k, v in src.items() if k not in ("source", "repo", "url", "path"))
    return " ".join(p for p in (str(src.get("source")), target, extra) if p)

def add_arg(decl):
    # What 'claude plugin marketplace add' takes to reproduce this declaration, or
    # None: the add rewrites the settings entry from its argument alone (2.1.283;
    # how autoUpdate went missing on the Mac), so a ref or headers would be lost.
    src = decl["source"]
    if set(decl) - {"source", "autoUpdate"}:
        return None
    for kind, field in (("github", "repo"), ("git", "url"), ("directory", "path")):
        if src.get("source") == kind and set(src) == {"source", field}:
            return src[field]
    return None

def same_place(a, b):
    # Two sources naming one repo (github shorthand or a git URL) or one path.
    ra, rb = source_repo({"source": a}), source_repo({"source": b})
    return (ra == rb) if (ra and rb) else (bool(a.get("path")) and a.get("path") == b.get("path"))

def committed_declarations():
    # Where the config dir is a git repo (on some machines it is, shared between
    # them), the committed settings.json is the only record of an autoUpdate that
    # a re-add has since removed. None when there is no such record.
    real = os.path.realpath(SETTINGS)
    try:
        r = subprocess.run(["git", "-C", os.path.dirname(real), "show", "HEAD:./" + os.path.basename(real)],
                           capture_output=True, text=True, timeout=10)
        if r.returncode:
            return None  # not a git repo, or settings.json not committed: the usual case
        return json.loads(r.stdout).get("extraKnownMarketplaces") or {}
    except (OSError, subprocess.TimeoutExpired, ValueError, AttributeError):
        return None

def check_marketplaces():
    # bds-facofo. Claude Code keeps two records of a marketplace: the declaration
    # in settings.json (extraKnownMarketplaces) and its registry
    # (known_marketplaces.json). When they name different sources — the same repo
    # by git URL instead of github shorthand, say — it refuses the record: the
    # marketplace drops out of 'marketplace list' and every plugin from it "failed
    # to load". Both files still look fine, so ask Claude Code what it loads, and
    # compare the files only when it can't be asked. Separately, every
    # 'marketplace add' drops autoUpdate from the settings entry, and from the
    # registry too when it rewrites the record, so look for that as well.
    # Returns (lost, drift, notes): lost = [(name, decl, why, installed, hand)],
    # drift = [(name, why)]; hand is None when the printed re-add is safe.
    notes = []
    try:
        declared = json.load(open(SETTINGS)).get("extraKnownMarketplaces") or {}
    except FileNotFoundError:
        return [], [], notes
    except (OSError, ValueError, AttributeError) as e:
        return [], [], [f"could not read {SETTINGS} ({e}), so the marketplace check was skipped"]
    declared = {n: d for n, d in declared.items()
                if isinstance(d, dict) and isinstance(d.get("source"), dict)}
    if not declared:
        return [], [], notes
    try:
        registry = json.load(open(os.path.join(PLUGINS, "known_marketplaces.json")))
    except FileNotFoundError:
        registry = {}
    except (OSError, ValueError) as e:
        registry = None
        notes.append(f"could not read known_marketplaces.json ({e})")
    try:
        r = subprocess.run(["claude", "plugin", "marketplace", "list", "--json"],
                           capture_output=True, text=True, timeout=30)
        if r.returncode:
            raise ValueError(f"exit {r.returncode}: {(r.stderr or r.stdout).strip()[:160]}")
        listing = {m["name"]: m for m in json.loads(r.stdout)}
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError, KeyError) as e:
        listing = None
        notes.append(f"could not ask Claude Code which marketplaces it loads ({e}), so this check read the files alone")
    committed = committed_declarations()
    lost, drift = [], []
    for name, decl in sorted(declared.items()):
        rec = (registry or {}).get(name)
        rec = rec if isinstance(rec, dict) else None
        rec_src = rec.get("source") if rec else None
        installed = sorted(k for k in plugins if mkt(k) == name)
        if listing is not None:
            healthy = name in listing  # Claude Code loads it, whatever the files say
        else:
            healthy = registry is None or rec_src == decl["source"]
        if healthy:
            was = (committed or {}).get(name)
            if decl.get("autoUpdate") is True and rec and rec.get("autoUpdate") is not True:
                drift.append((name, "your settings have autoUpdate on but Claude Code's registry has lost it"))
            elif "autoUpdate" not in decl and isinstance(was, dict) and was.get("autoUpdate") is True:
                drift.append((name, "your last committed settings.json had autoUpdate on and the working "
                                    "copy has lost the key (a re-add removes it)"))
            continue
        if rec_src is None and not installed:
            continue  # declared but never added, and nothing from it installed: nothing is off
        if rec_src is None:
            why = f"your settings declare it ({describe(decl['source'])}) but Claude Code has no record of it"
        elif rec_src != decl["source"]:
            why = (f"your settings declare {describe(decl['source'])} but Claude Code's registry holds "
                   f"{describe(rec_src)}, and it won't load a marketplace whose two records disagree")
        else:
            why = "both records agree but Claude Code doesn't list it (its local copy may be unreadable)"
        # The add names a marketplace after its manifest (or an entry already holding
        # that source); a different name means a second settings entry, not a repair.
        others = sorted(n for n, m in (listing or {}).items() if n != name and same_place(
            {k: m[k] for k in ("source", "repo", "url", "path") if k in m}, decl["source"]))
        try:
            own = json.load(open(os.path.join(rec.get("installLocation", ""), ".claude-plugin",
                                              "marketplace.json"))).get("name") if rec else None
        except (OSError, ValueError, AttributeError):
            own = None
        if others:
            hand = f"Claude Code already has that source loaded as '{others[0]}', so the add would not repair '{name}'"
        elif own and own != name:
            hand = f"that marketplace calls itself '{own}', so the add would register it under that name, not '{name}'"
        elif not add_arg(decl):
            hand = (f"its settings entry ({json.dumps(decl)}) carries more than the add command keeps, "
                    "and the add would drop the rest")
        else:
            hand = None
        lost.append((name, decl, why, installed, hand))
    return lost, drift, notes

try:
    plugins, read_error = json.load(open(os.path.join(PLUGINS, "installed_plugins.json"))).get("plugins", {}), None
except Exception as e:
    plugins, read_error = {}, e

mkt = lambda key: key.rsplit("@", 1)[1] if "@" in key else ""
lost, drift, notes = check_marketplaces()
for n in notes:
    print(f"ℹ️ Marketplace check: {n}.\n")
if lost or drift:
    print("🩹 MARKETPLACE REPAIR NEEDED — step 0 below.")
    for name, decl, why, installed, hand in lost:
        print(f"  - {name}: Claude Code has stopped loading it: {why}. "
              f"Plugins from it that are off: {', '.join(installed) or 'none installed'}.")
        if hand:
            print(f"    Re-add by hand: {hand}.")
        else:
            print(f"    Re-add: claude plugin marketplace add {add_arg(decl)}")
            for k in installed:
                print(f"    Then:   claude plugin update {k}")
    for name, why in drift:
        print(f"  - {name}: {why}.")
    restore = [n for n, d, _, _, hand in lost if d.get("autoUpdate") is True and not hand] + [n for n, _ in drift]
    if restore:
        print(f"  Finish with step 0's block, which turns autoUpdate back on for these (a re-add switches it off): "
              f"python3 - {' '.join(restore)} << 'AUTOEOF'")
    print()

if read_error is not None:
    # A failed read must never render like an empty install (bds-mifubu).
    print(f"⚠️ SNAPSHOT FAILED: could not read installed_plugins.json ({read_error}).")
    print("Do NOT treat this as 'nothing to update' — Read ~/.claude/plugins/installed_plugins.json directly and use it as the before-state.")
    raise SystemExit(0)

fam = family_marketplaces()
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
# A claude.ai-synced plugin's root is synced/<sync-id>/<name>/ — only that
# level names a plugin. Deeper matches are components (the family kit's own
# synced/<id>/family/mise), which a walk read as a leftover mise plugin.
synced_root = os.path.join(PLUGINS, "synced")
synced = sorted({n for sid in os.listdir(synced_root) if os.path.isdir(os.path.join(synced_root, sid))
                 for n in os.listdir(os.path.join(synced_root, sid))
                 if n in OLD and os.path.isdir(os.path.join(synced_root, sid, n))}) \
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

### 0. Repair a marketplace Claude Code has stopped loading, or its lost autoUpdate (only if the snapshot shows 🩹)

Claude Code keeps two records of each marketplace: the declaration in `settings.json` (`extraKnownMarketplaces`) and its own registry, `plugins/known_marketplaces.json`. When they disagree — on 27 Sep 2026 a Mac's registry held batterie by git URL (`https://github.com/spm1001/batterie.git`) while settings declared `spm1001/batterie` — Claude Code won't load it. The marketplace drops out of `claude plugin marketplace list`, `marketplace update` says it isn't found, and every plugin from it shows "failed to load — Marketplace … not found". Nothing is uninstalled, but the tools are off from the next session, with no message (bds-facofo). Re-adding the marketplace from the declared source fixes it. For each marketplace the snapshot says has stopped loading, run the lines it printed, in order:

```
claude plugin marketplace add <source>        # the "Re-add:" line
claude plugin update <name>@<marketplace>      # each "Then:" line
```

A "Re-add by hand" line means the printed add would do the wrong thing: it would drop part of the declaration, or register the marketplace under a different name and leave this one broken. Pass that line to the user with its reason rather than improvising.

Every add rewrites that marketplace's settings entry without `"autoUpdate": true`, even when the source already matched. When it also rewrites the registry record (a new or changed source, as in the repair above), that record has no autoUpdate either; when the source already matched, the registry is left as it was (both measured on Claude Code 2.1.283). So the snapshot also flags a marketplace Claude Code does load whose autoUpdate is provably gone. That means settings still say on but the registry has lost it, or, where `~/.claude` is under version control, the last commit had it on and the working file has lost the key. It usually follows someone running the add by hand. Nothing needs re-adding there; the block alone puts it back. So if the snapshot printed a "Finish with step 0's block" line, run this block, with the names it gave on the first line in place of `batterie`. It turns autoUpdate back on for those names only, in both files. It rewrites `settings.json` only when it can reproduce the file's layout exactly, so the change is one key and nothing else. That matters because on some machines `~/.claude` is a git repo shared between machines.

```bash
python3 - batterie << 'AUTOEOF'
import json, os, sys
PLUGINS = os.environ.get("BATTERIE_PLUGINS_DIR") or os.path.join(
    os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude"), "plugins")
SETTINGS = os.path.join(os.path.dirname(PLUGINS), "settings.json")
names = sys.argv[1:] or sys.exit("name the marketplaces, e.g. python3 - batterie")

def layout(text, data):
    # The json.dumps layout that reproduces this file byte for byte, or None.
    for indent in (2, 4, "\t"):
        for end in ("\n", ""):
            for ascii_only in (False, True):
                if json.dumps(data, indent=indent, ensure_ascii=ascii_only) + end == text:
                    return lambda d, i=indent, e=end, a=ascii_only: json.dumps(d, indent=i, ensure_ascii=a) + e
    return None

def turn_on(path, entries, label, keep_layout):
    text = open(path).read()
    data = json.loads(text)
    fmt, table, changed = layout(text, data), entries(data), []
    for n in names:
        entry = table.get(n)
        if not isinstance(entry, dict):
            print(f"- {label}: no entry for {n}, nothing to set")
        elif entry.get("autoUpdate") is True:
            print(f"- {label}: autoUpdate already on for {n}")
        else:
            entry["autoUpdate"] = True
            changed.append(n)
    if not changed:
        return
    if fmt is None and keep_layout:
        print(f"- {label}: left alone, because its layout isn't one this block reproduces and a rewrite would "
              f"reformat the whole file. Add \"autoUpdate\": true by hand to {', '.join(changed)} "
              f"under extraKnownMarketplaces in {path}.")
        return
    open(path, "w").write((fmt or (lambda d: json.dumps(d, indent=2)))(data))
    print(f"- {label}: turned autoUpdate back on for {', '.join(changed)}")

turn_on(SETTINGS, lambda d: d.get("extraKnownMarketplaces", {}), "settings.json", True)
turn_on(os.path.join(PLUGINS, "known_marketplaces.json"), lambda d: d, "known_marketplaces.json", False)
AUTOEOF
```

Then check the repair took: `claude plugin marketplace list` names each repaired marketplace, and `claude plugin list --json` shows no `errors` for each plugin from it. Don't rely on `"enabled": true` there, because it stays true while a plugin fails to load. Where `~/.claude` is a git repo, `git -C ~/.claude diff settings.json` should show nothing from this step. Tell the user plainly what was off, why, and what you ran. Then carry on with step 1 as normal.

This step only runs in a session where batterie itself loaded. When the kit is off in a fresh session, this skill isn't there to run. The recovery for that case is two commands in the marketplace README ("If the kit stops loading"), and the next `/batterie:update` then restores whatever autoUpdate it can prove was on. Where nothing proves it (settings.json not under version control, both flags gone) the snapshot says nothing about it, so if step 0 didn't run for a marketplace the user re-added by hand, tell them they can switch auto-update back on in `/plugin` → Marketplaces → the marketplace → Enable auto-update.

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

Report what you removed, and name anything you could not: a plugin synced from claude.ai lives in `plugins/synced/` and only claude.ai or Desktop can remove it (Customize → Plugins); tell the user to do that there. An empty registry is a normal case here — a machine whose plugins all came from claude.ai — so don't read it as nothing to do; the snapshot's synced lines are the list. Permission rules naming `mcp__plugin_mise_mise__…` or `mcp__plugin_batterie_mise__…` now need `mcp__plugin_mit_mise__…` (the ITV Google server moved to mit@mit); say so if you see one in `settings.json`. After this step, carry on with step 2 for what remains (normally just `batterie@batterie`).

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

If step 0 ran, run its block once more with the same names. It changes nothing while autoUpdate is still on, and puts it back if a marketplace refresh in step 1 dropped it from the registry. On the Mac a refresh that replaced a clone did exactly that.

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

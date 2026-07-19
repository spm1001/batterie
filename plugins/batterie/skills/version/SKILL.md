---
name: version
description: "Show the Batterie suite version and every installed plugin/CLI version"
allowed-tools: ["Bash"]
---

# Batterie Version

!`python3 << 'PYEOF'
import json, os, re, subprocess, shutil

# Default to the real plugins dir. BATTERIE_PLUGINS_DIR is a test seam; unset in normal use.
PLUGINS = os.environ.get("BATTERIE_PLUGINS_DIR") or os.path.join(
    os.path.expanduser("~"), ".claude", "plugins")

def is_batterie_family(repo):
    # Suite marketplaces: spm1001/batterie (public) + spm1001/batterie-* (e.g. a
    # private flavour). Match by source repo so a cherry-picked single plugin and
    # plugin renames still resolve — not by "contains the batterie plugin".
    return repo == "spm1001/batterie" or repo.startswith("spm1001/batterie-")

def source_repo(info):
    # Normalise a known_marketplaces.json entry to "owner/repo". Shapes seen in
    # the wild: {"source":"github","repo":"o/r"} (shorthand add); {"source":"git",
    # "url":"https://github.com/o/r.git"} (URL add — a normal, persistent shape;
    # bds-mifubu); {"source":"directory","path":...} (local dev, no repo).
    src = info.get("source") if isinstance(info, dict) else None
    if not isinstance(src, dict):
        return ""
    if src.get("repo"):
        return src["repo"]
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/*$", src.get("url") or "")
    return m.group(1) if m else ""

def family_marketplaces():
    try:
        reg = json.load(open(os.path.join(PLUGINS, "known_marketplaces.json")))
    except Exception:
        return {"batterie"}  # registry unreadable: fall back to the public name
    fam = {name for name, info in reg.items() if is_batterie_family(source_repo(info))}
    return fam or {"batterie"}

try:
    plugins = json.load(open(os.path.join(PLUGINS, "installed_plugins.json"))).get("plugins", {})
except Exception as e:
    print(f"Could not read installed plugins ({e}).")
    plugins = {}

fam = family_marketplaces()
mkt = lambda key: key.rsplit("@", 1)[1] if "@" in key else ""
# full key -> user-scope entry, for batterie-family plugins only
installed = {k: v[0] for k, v in plugins.items() if mkt(k) in fam and v}

# Family-named marketplaces that didn't resolve = a discovery gap, never a
# silent drop (bds-mifubu).
suspicious = sorted({m for m in {mkt(k) for k in plugins}
                     if (m == "batterie" or m.startswith("batterie-")) and m not in fam})
if suspicious:
    print(f"⚠️ WARNING: marketplace(s) {', '.join(suspicious)} look batterie-family but did not resolve from known_marketplaces.json — unrecognised source shape? Their plugins are missing from this report (bds-mifubu).")

multi = len({mkt(k) for k in installed}) > 1
base_names = {k.rsplit("@", 1)[0] for k in installed}

suite = next((i.get("version") for k, i in installed.items()
              if k.rsplit("@", 1)[0] == "batterie"), None)
if suite:
    print(f"📦  Batterie suite  v{suite}")
else:
    print("📦  Batterie suite  — not installed (no batterie plugin found)")

if installed:
    print("\nPlugins:")
    for key, info in sorted(installed.items()):
        name = key.rsplit("@", 1)[0]
        # annotate the marketplace only when more than one is present
        label = key if multi else name
        marker = "  (suite)" if name == "batterie" else ""
        print(f"  - {label}: v{info.get('version', '?')}{marker}")

# CLI tools shipped by some plugins (keyed by plugin base-name)
cli_tools = {"bon": "bon", "todoist-gtd": "todoist"}
header = False
for plugin_name, cli_name in cli_tools.items():
    if plugin_name in base_names and shutil.which(cli_name):
        if not header:
            print("\nCLI tools:")
            header = True
        try:
            r = subprocess.run([cli_name, "--version"], capture_output=True, text=True, timeout=5)
            print(f"  - {cli_name}: {(r.stdout or r.stderr).strip() or '(no version output)'}")
        except Exception:
            print(f"  - {cli_name}: (version check failed)")
PYEOF`

## Report

Tell the user their **Batterie suite version** (the `📦` line above) — that's the single number to quote ("I'm on Batterie vX") or to check against ("you need ≥ vY"). List the per-plugin versions underneath if useful. If anything looks behind, point them at `/batterie:update`.

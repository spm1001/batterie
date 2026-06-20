---
name: version
description: "Show the Batterie suite version and every installed plugin/CLI version"
allowed-tools: ["Bash"]
---

# Batterie Version

!`python3 << 'PYEOF'
import json, os, subprocess, shutil

plugins_path = os.path.join(os.path.expanduser("~"), ".claude", "plugins", "installed_plugins.json")
try:
    plugins = json.load(open(plugins_path)).get("plugins", {})
except Exception as e:
    print(f"Could not read installed plugins ({e}).")
    plugins = {}

# Keyed <name>@batterie; take the user-scope entry [0].
batterie = {k.split("@")[0]: v[0] for k, v in plugins.items() if k.endswith("@batterie") and v}

suite = batterie.get("batterie", {}).get("version")
if suite:
    print(f"📦  Batterie suite  v{suite}")
else:
    print("📦  Batterie suite  — not installed (no batterie@batterie plugin found)")

if batterie:
    print("\nPlugins:")
    for name, info in sorted(batterie.items()):
        marker = "  (suite)" if name == "batterie" else ""
        print(f"  - {name}: v{info.get('version', '?')}{marker}")

# CLI tools shipped by some plugins
cli_tools = {"bon": "bon", "passe": "passe", "todoist-gtd": "todoist"}
header = False
for plugin_name, cli_name in cli_tools.items():
    if plugin_name in batterie and shutil.which(cli_name):
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

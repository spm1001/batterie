---
description: "Update all installed batterie-de-savoir plugins in one go"
allowed-tools: ["Bash", "Read"]
---

# Update Batterie Plugins

## Currently installed (before update)

!`python3 << 'PYEOF'
import json, os, subprocess, shutil

plugins_path = os.path.join(os.path.expanduser("~"), ".claude", "plugins", "installed_plugins.json")
plugins_file = json.load(open(plugins_path))
plugins = plugins_file.get("plugins", {})

batterie = {k: v[0] for k, v in plugins.items() if k.endswith("@batterie-de-savoir")}

if not batterie:
    print("No batterie-de-savoir plugins installed.")
else:
    print(f"Found {len(batterie)} batterie plugin(s):\n")
    for key, info in sorted(batterie.items()):
        name = key.split("@")[0]
        print(f"- {name}: v{info['version']} (sha: {info['gitCommitSha'][:12]})")

    # CLI version check
    cli_tools = {"bon": "bon", "garde-manger": "garde", "passe": "passe", "todoist-gtd": "todoist"}
    print("\nCLI tool versions:")
    for plugin_name, cli_name in cli_tools.items():
        if f"{plugin_name}@batterie-de-savoir" in batterie:
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

Update every batterie-de-savoir plugin listed above. Follow these steps exactly:

### 1. Refresh the marketplace

```
claude plugin marketplace update batterie-de-savoir
```

This pulls the latest marketplace index so plugin updates can see new versions. Without this, `claude plugin update` compares against a stale index.

### 2. Update each plugin

For each plugin shown above, run:

```
claude plugin update <name>@batterie-de-savoir
```

Run them sequentially — each must complete before the next starts. Report the output of each.

### 3. Check what changed

After all updates, read `~/.claude/plugins/installed_plugins.json` again. For each batterie plugin, compare the **version** and **gitCommitSha** against the "before" snapshot above. Report:
- Which plugins had version changes (old → new)
- Which were already up to date

**JSON structure of `installed_plugins.json`:**

```json
{
  "version": "...",
  "plugins": {
    "bon@batterie-de-savoir": [
      {"scope": "user", "installPath": "/path/to/cache/bon/0.8.0", "version": "0.8.0", "gitCommitSha": "..."}
    ],
    ...
  }
}
```

Each plugin key maps to a **list** of installations (one per scope). Use `v[0]` to get the user-scope entry.

### 4. Detect CLI version drift

Four batterie plugins ship CLI tools installed via `uv tool install`:

| Plugin | CLI binary |
|--------|-----------|
| bon | `bon` |
| garde-manger | `garde` |
| passe | `passe` |
| todoist-gtd | `todoist` |

For each installed plugin that has a CLI:
1. Get the plugin's `installPath` from the JSON above (e.g. `plugins["bon@batterie-de-savoir"][0]["installPath"]`)
2. The plugin version is already in the same entry — use `["version"]`
3. Compare against the CLI version shown in the "before" snapshot above
4. If they differ (or the CLI is not in PATH), run:
   ```
   uv tool install "<installPath>" --force --reinstall
   ```
   Report success or failure. If `uv` is not available or the install fails, fall back to showing the manual command.

### 5. Summarise

If any plugins were updated:
```
Updates complete. Exit and restart Claude Code (`/exit` then `claude`) to activate changes.
SessionStart hooks only fire on full restart — /reload-plugins won't trigger them.
```

If nothing changed: just say all plugins are up to date, no restart needed.

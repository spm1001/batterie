---
name: update
description: "Update all installed batterie plugins in one go"
allowed-tools: ["Bash", "Read"]
---

# Update Batterie Plugins

## Currently installed (before update)

!`python3 << 'PYEOF'
import json, os, subprocess, shutil

plugins_path = os.path.join(os.path.expanduser("~"), ".claude", "plugins", "installed_plugins.json")
plugins_file = json.load(open(plugins_path))
plugins = plugins_file.get("plugins", {})

batterie = {k: v[0] for k, v in plugins.items() if k.endswith("@batterie")}

if not batterie:
    print("No batterie plugins installed.")
else:
    print(f"Found {len(batterie)} batterie plugin(s):\n")
    for key, info in sorted(batterie.items()):
        name = key.split("@")[0]
        print(f"- {name}: v{info['version']} (sha: {info['gitCommitSha'][:12]})")

    # CLI version check
    cli_tools = {"bon": "bon", "passe": "passe", "todoist-gtd": "todoist"}
    print("\nCLI tool versions:")
    for plugin_name, cli_name in cli_tools.items():
        if f"{plugin_name}@batterie" in batterie:
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

### 1. Refresh the marketplace

```
claude plugin marketplace update batterie
```

This pulls the latest marketplace index so plugin updates can see new versions. Without this, `claude plugin update` compares against a stale index.

### 2. Update each plugin

For each plugin shown above, run:

```
claude plugin update <name>@batterie
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
    "bon@batterie": [
      {"scope": "user", "installPath": "/path/to/cache/bon/0.8.0", "version": "0.8.0", "gitCommitSha": "..."}
    ],
    ...
  }
}
```

Each plugin key maps to a **list** of installations (one per scope). Use `v[0]` to get the user-scope entry.

### 4. Detect CLI version drift

Three batterie plugins ship CLI tools installed via `uv tool install`:

| Plugin | CLI binary | Source repo | Extras |
|--------|-----------|-------------|--------|
| bon | `bon` | `~/repos/spm1001/bon` | `[dolt]` |
| passe | `passe` | `~/repos/spm1001/passe` | |
| todoist-gtd | `todoist` | `~/repos/spm1001/todoist-gtd` | |

**Install from source, never from `installPath` or PyPI.** Post-cutover the marketplace vendors only skills/hooks/CLAUDE.md for skill plugins — there is **no `pyproject.toml`** in the plugin cache, so `uv tool install <installPath>` fails with *"does not appear to be a Python project"*. The bare PyPI name is **not** a fallback either — none of these CLIs are published to PyPI (`uv tool install bon[dolt]` → *"unsatisfiable"*). Install from the source repo, preferring a local working tree and falling back to git:

- **Local** (fast; dev machines with `~/repos`): `uv tool install "~/repos/spm1001/<repo>[<extras>]"`
- **Git** (portable; fresh users, the Mac, Cowork — anything without `~/repos`): `uv tool install "<pkg>[<extras>] @ git+https://github.com/spm1001/<repo>"` — PEP 508 form, extras go **before** the `@`.

For each plugin in the table:
1. Read the plugin's `version` from the JSON above (`plugins["bon@batterie"][0]["version"]`) — used only to detect drift.
2. Compare against the CLI version shown in the "before" snapshot above.
3. If they differ (or the CLI is not in PATH), reinstall — pick the local working tree if `~/repos/spm1001/<repo>` exists, else the git source:
   ```
   uv cache clean <cli_name> --force && uv tool install "<source-spec>" --force --reinstall
   ```
   e.g. local `uv tool install "~/repos/spm1001/bon[dolt]" --force --reinstall`, or fresh `uv tool install "bon[dolt] @ git+https://github.com/spm1001/bon" --force --reinstall`. Always include extras from the table (bon is always `[dolt]` — PyMySQL is tiny and harmless; always installing it avoids silent breakage when any project uses the Dolt backend). The `--force` on `uv cache clean` prevents blocking on lock contention from other uv processes (e.g. marketplace refresh). Report success or failure.
4. The git source works anywhere with network, so a machine without `~/repos` (a fresh user, the Mac) is no longer a dead end — fall back to it rather than failing. Cowork additionally has its own skill-level provisioning path (`bds-dacase`).

### 5. Summarise

If any plugins were updated:
```
Updates complete. Exit and restart Claude Code (`/exit` then `claude`) to activate changes.
SessionStart hooks only fire on full restart — /reload-plugins won't trigger them.
```

If nothing changed: just say all plugins are up to date, no restart needed.

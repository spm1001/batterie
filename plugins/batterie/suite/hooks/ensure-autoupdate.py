#!/usr/bin/env python3
"""Switch on autoUpdate for the marketplace this plugin was installed from.

Claude Code keeps autoUpdate per marketplace but per machine, and a marketplace
not run by Anthropic defaults to off — a silent version pin on any machine where
nobody flipped it (Sameer's rule: no pinning). So each kit's SessionStart hook
runs this, and it makes sure the user's settings.json carries
extraKnownMarketplaces.<marketplace>.autoUpdate: true.

Copies kept byte-identical in three kits: spm1001/sameer-kit
plugins/sameer/hooks/, spm1001/batterie-de-savoir hooks/ and ITV/mit-kit hooks/.
Their hooks fire at once at session start, so the read-merge-write runs under a
shared lock file. Edit one, copy to the other two (sameer-kit's test checks).

Usage: ensure-autoupdate.py [--leave-false] <plugin root>
  The hook passes its plugin root. --leave-false is for a kit shared with
  teammates (mit-kit): it sets the flag only when it is absent, leaves an
  explicit false alone (a teammate chose it), and when it does set the flag says
  how to switch it off. Without it (Sameer's own kits) a false is flipped too,
  since there a false is exactly the silent pin this exists to remove.

Silent when the flag is already on (in the user's settings or the machine's
managed settings — the atelier sets mit there for everyone), when the plugin
was not installed from a marketplace (loaded with --plugin-dir, say), and on a
machine with no plugin registry. One line when it adds the flag. One line, file untouched, when
settings.json is unreadable or invalid, or the marketplace is not registered.
"""
import fcntl
import json
import os
import sys
import tempfile

PREFIX = "autoupdate:"
# Where Claude Code reads managed (machine-wide) settings. The env var is a
# test seam only, so a test can stand in a fake managed dir.
MANAGED_DIR = os.environ.get("ENSURE_AUTOUPDATE_MANAGED_DIR") or (
    "/Library/Application Support/ClaudeCode" if sys.platform == "darwin" else "/etc/claude-code"
)


def say(msg):
    print(f"{PREFIX} {msg}")


def marketplace_of(plugin_root):
    """plugins/cache/<marketplace>/<plugin>/<version>/... -> <marketplace>."""
    parts = os.path.realpath(plugin_root).split(os.sep)
    for i in range(len(parts) - 2):
        if parts[i] == "plugins" and parts[i + 1] == "cache":
            return parts[i + 2]
    return None


def managed_value(name):
    """The autoUpdate a managed settings file gives name: True, False, or None
    when none says. A managed file we cannot read counts as not saying: the
    user-settings write that follows is harmless, so nothing to warn about."""
    files = [os.path.join(MANAGED_DIR, "managed-settings.json")]
    d = os.path.join(MANAGED_DIR, "managed-settings.d")
    if os.path.isdir(d):
        files += [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".json")]
    for path in files:
        try:
            with open(path) as f:
                data = json.load(f)
            value = data["extraKnownMarketplaces"][name]["autoUpdate"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if isinstance(value, bool):
            return value
    return None


def main():
    args = sys.argv[1:]
    leave_false = "--leave-false" in args
    args = [a for a in args if a != "--leave-false"]
    if len(args) != 1:
        return
    name = marketplace_of(args[0])
    if not name:
        return  # not a marketplace install: nothing to keep current
    managed = managed_value(name)
    if managed is True or (managed is False and leave_false):
        return  # the machine already decides it for everyone

    cfg = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    settings_path = os.path.join(cfg, "settings.json")
    known_path = os.path.join(cfg, "plugins", "known_marketplaces.json")

    try:
        with open(known_path) as f:
            known = json.load(f)
    except FileNotFoundError:
        return  # fresh machine or sandbox: no registry yet
    except (OSError, ValueError) as e:
        say(f"could not read {known_path} ({e}); left {name}'s autoUpdate alone.")
        return
    source = (known.get(name) or {}).get("source")
    if not source:
        say(f"marketplace '{name}' is not in {known_path}; left settings.json alone.")
        return

    lock_path = os.path.join(cfg, ".ensure-autoupdate.lock")
    try:
        lock = open(lock_path, "a")
    except OSError as e:
        say(f"could not open lock {lock_path} ({e}); left settings.json alone.")
        return
    with lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        merge(settings_path, name, source, leave_false)


def merge(path, name, source, leave_false):
    try:
        with open(path) as f:
            text = f.read()
    except FileNotFoundError:
        text = None
    except OSError as e:
        say(f"could not read {path} ({e}); left it untouched — {name} autoUpdate not set.")
        return

    if text is None or not text.strip():
        settings = {}
    else:
        try:
            settings = json.loads(text)
        except ValueError as e:
            say(f"{path} is not valid JSON ({e}); left it untouched — {name} autoUpdate not set.")
            return
    if not isinstance(settings, dict):
        say(f"{path} is not a JSON object; left it untouched — {name} autoUpdate not set.")
        return

    ekm = settings.get("extraKnownMarketplaces")
    if ekm is None:
        ekm = {}
    if not isinstance(ekm, dict):
        say(f"extraKnownMarketplaces in {path} is not an object; left it untouched.")
        return
    entry = ekm.get(name)
    if entry is not None and not isinstance(entry, dict):
        say(f"extraKnownMarketplaces.{name} in {path} is not an object; left it untouched.")
        return
    if entry and entry.get("autoUpdate") is True:
        return  # already on: the every-session case, so say nothing
    if leave_false and entry and entry.get("autoUpdate") is False:
        return  # someone chose off on this machine: theirs to keep

    new_entry = dict(entry or {})
    new_entry.setdefault("source", source)
    new_entry["autoUpdate"] = True
    new_ekm = dict(ekm)
    new_ekm[name] = new_entry
    new = dict(settings)
    new["extraKnownMarketplaces"] = new_ekm

    out = json.dumps(new, indent=2, ensure_ascii=False) + "\n"
    # Validate before writing: it parses, and only our one entry changed.
    back = json.loads(out)
    others_before = {k: v for k, v in settings.items() if k != "extraKnownMarketplaces"}
    others_after = {k: v for k, v in back.items() if k != "extraKnownMarketplaces"}
    ekm_before = {k: v for k, v in ekm.items() if k != name}
    ekm_after = {k: v for k, v in back["extraKnownMarketplaces"].items() if k != name}
    if others_before != others_after or ekm_before != ekm_after or back["extraKnownMarketplaces"][name] != new_entry:
        say(f"merge check failed for {path}; left it untouched — {name} autoUpdate not set.")
        return

    d = os.path.dirname(path) or "."
    tmp = None
    try:
        mode = os.stat(path).st_mode & 0o777 if text is not None else 0o600
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".settings.json.")
        with os.fdopen(fd, "w") as f:
            f.write(out)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except OSError as e:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
        say(f"could not write {path} ({e}); {name} autoUpdate not set.")
        return
    was = "absent" if "autoUpdate" not in (entry or {}) else f"autoUpdate={entry['autoUpdate']!r}"
    msg = (f"turned on autoUpdate for the '{name}' plugin marketplace in {path} (was {was}), "
           "so this machine follows its latest release.")
    if leave_false:
        msg += (f" To switch it off, set extraKnownMarketplaces.{name}.autoUpdate to false"
                " there; this hook leaves a false alone.")
    say(msg)


if __name__ == "__main__":
    main()

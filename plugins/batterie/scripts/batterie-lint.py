# /// script
# requires-python = ">=3.9"
# ///
"""plugin-lint.py — Structural and alignment validation for batterie plugins.

Reads marketplace.json from the spm1001/batterie sibling checkout (the
single assembled marketplace since the 2026-06-10 cutover), resolves each
plugin to its local source repo, and runs two tiers of checks:

Structural (original):
  - plugin.json is valid JSON with required fields
  - Hook scripts referenced in plugin.json exist
  - SKILL.md files have frontmatter with name, description, allowed-tools
  - Commands have frontmatter with description
  - LICENSE exists

Alignment (from batterie-ci-recommendation.md):
  1. Skill routing — directory name matches SKILL.md name: frontmatter
  2. Hook registration — every hooks/*.sh on disk is registered in plugin.json
  3. Version consistency — plugin.json version readable from pyproject.toml
  4. Instruction shards — instructions.md has matching SessionStart hook
  5. Hook executability — every hooks/*.sh is chmod +x

Lints SOURCE repos (working trees/clones), not the vendored copies in
spm1001/batterie — assemble.sh's invariant checks guard the vendored side.
Expects source repos as siblings of this repo: the assemble workflow
clones them next to the batterie checkout; locally that's ~/repos/spm1001/.

Usage:
  uv run --script tests/plugin-lint.py            # all plugins
  uv run --script tests/plugin-lint.py bon passe   # specific plugins
  uv run --script tests/plugin-lint.py --local     # skip cloning, local only
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# ── Repo name mapping (marketplace name → repo directory name) ────────

REPO_NAMES = {
    "mise": "mise-en-space",
    "todoist-gtd": "todoist-gtd",
    "batterie": "batterie-de-savoir",
    "sonnette": "aboyeur",
}

REQUIRED_PLUGIN_FIELDS = {"name", "version", "description"}
REQUIRED_FRONTMATTER = {"name", "description"}

# Hook scripts that are helpers, not standalone hooks
HOOK_HELPERS = {"lib.sh", "utils.sh", "common.sh"}


def parse_frontmatter(path: Path) -> dict[str, str]:
    """Extract YAML-ish frontmatter between --- markers."""
    text = path.read_text()
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    fields: dict[str, str] = {}
    for line in text[3:end].strip().splitlines():
        if ":" in line:
            key = line.split(":")[0].strip()
            fields[key] = line.split(":", 1)[1].strip()
    return fields


def find_truncated_context_blocks(text: str) -> list[tuple[int, str]]:
    """Find inner backticks that truncate !`...` dynamic-context blocks.

    A dynamic-context block (!`command`) runs at skill load: the harness
    takes everything between the opening backtick and the NEXT backtick as
    the command. In a multi-line block, any backtick before the intended
    terminator therefore cuts the command mid-token — the bds-dazaja bug,
    which shipped broken for a week because every existing guard passed
    (valid Markdown, valid embedded Python, complete frontmatter).

    The intended terminator is taken to be the next line whose only
    backtick sits at end-of-line (e.g. a PYEOF` heredoc closer). Returns
    (line_number, message) pairs; empty list = clean.
    """
    lines = text.splitlines()
    findings: list[tuple[int, str]] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        # Not an opener, or a single-line block (closes on its own line).
        if not stripped.startswith("!`") or "`" in stripped[2:]:
            i += 1
            continue
        term = None
        for j in range(i + 1, len(lines)):
            s = lines[j].rstrip()
            if s.count("`") == 1 and s.endswith("`"):
                term = j
                break
        if term is None:
            findings.append(
                (i + 1, "dynamic-context block opened here is never terminated")
            )
            break
        for k in range(i + 1, term):
            if "`" in lines[k]:
                findings.append(
                    (
                        k + 1,
                        "backtick inside dynamic-context block truncates "
                        "the command here",
                    )
                )
        i = term + 1
    return findings


def resolve_plugin_dir(plugin: dict, repo_root: Path) -> Path | None:
    """Resolve a marketplace plugin entry to its local SOURCE repo.

    Marketplace sources are ./plugins/<name> vendored paths; the lint
    target is the source repo of the same name, expected as a sibling
    of this repo (CI clones them there; locally it's the owner bucket).
    """
    name = plugin["name"]
    repo_name = REPO_NAMES.get(name, name)
    local = repo_root.parent / repo_name
    if (local / ".claude-plugin" / "plugin.json").exists():
        return local
    return None


def _resolve_plugin_root(pj_path: Path) -> Path:
    """Get the plugin root directory from the plugin.json path."""
    # .claude-plugin/plugin.json → parent.parent is repo root
    # Except self-referencing where plugin_dir IS .claude-plugin
    if pj_path.parent.name == ".claude-plugin":
        return pj_path.parent.parent
    return pj_path.parent


def _collect_registered_hook_scripts(pj: dict, plugin_root: Path) -> set[str]:
    """Extract all hook script basenames registered in plugin.json."""
    registered: set[str] = set()
    for _event, groups in pj.get("hooks", {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                cmd = hook.get("command", "")
                resolved = cmd.replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_root))
                if resolved:
                    script = resolved.split()[0]
                    registered.add(Path(script).name)
    return registered


def lint_plugin(name: str, plugin_dir: Path) -> list[str]:
    """Run structural and alignment checks. Returns list of failures."""
    fails: list[str] = []

    # ── plugin.json ───────────────────────────────────────────────
    pj_path = plugin_dir / ".claude-plugin" / "plugin.json"
    # Self-referencing plugin has plugin_dir == .claude-plugin already
    if not pj_path.exists():
        pj_path = plugin_dir / "plugin.json"
    if not pj_path.exists():
        fails.append(f"{name}: plugin.json not found")
        return fails

    try:
        pj = json.loads(pj_path.read_text())
    except json.JSONDecodeError as e:
        fails.append(f"{name}: plugin.json invalid JSON: {e}")
        return fails

    missing = REQUIRED_PLUGIN_FIELDS - set(pj.keys())
    if missing:
        fails.append(f"{name}: plugin.json missing fields: {missing}")

    plugin_root = _resolve_plugin_root(pj_path)

    # ── Hook scripts referenced in plugin.json exist ──────────────
    for _event, groups in pj.get("hooks", {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                cmd = hook.get("command", "")
                resolved = cmd.replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_root))
                script_path = resolved.split()[0] if resolved else ""
                if script_path and not Path(script_path).exists():
                    rel = plugin_root / script_path.lstrip("./")
                    if not rel.exists():
                        fails.append(f"{name}: hook script missing: {script_path}")

    # ── SKILL.md files ────────────────────────────────────────────
    skills_dir = plugin_root / "skills"
    if skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                fails.append(f"{name}/skills/{skill_dir.name}: missing SKILL.md")
                continue
            fm = parse_frontmatter(skill_md)
            if not fm:
                fails.append(
                    f"{name}/skills/{skill_dir.name}: SKILL.md has no frontmatter"
                )
                continue
            for field in REQUIRED_FRONTMATTER:
                if field not in fm:
                    fails.append(
                        f"{name}/skills/{skill_dir.name}: SKILL.md missing '{field}'"
                    )
            if "allowed-tools" not in fm:
                print(
                    f"  WARN {name}/skills/{skill_dir.name}: SKILL.md missing 'allowed-tools'"
                )

            for ln, msg in find_truncated_context_blocks(skill_md.read_text()):
                fails.append(
                    f"{name}/skills/{skill_dir.name}: SKILL.md line {ln}: {msg}"
                )

            # ── ALIGNMENT 1: Skill routing ────────────────────────
            # Directory name controls /plugin:skill invocation.
            # Frontmatter name: controls model-triggered matching.
            # Mismatch is a design choice, not a bug — but worth flagging.
            fm_name = fm.get("name", "")
            fm_name = fm_name.strip("'\"")
            if fm_name and fm_name != skill_dir.name:
                print(
                    f"  INFO {name}/skills/{skill_dir.name}: invoked as "
                    f"/{name}:{skill_dir.name}, model matches on name: '{fm_name}'"
                )

    # ── Commands (legacy format) ──────────────────────────────────
    commands_dir = plugin_root / "commands"
    if commands_dir.is_dir():
        for cmd_file in sorted(commands_dir.glob("*.md")):
            fm = parse_frontmatter(cmd_file)
            if not fm:
                fails.append(f"{name}/commands/{cmd_file.name}: no frontmatter")
            elif "description" not in fm:
                fails.append(
                    f"{name}/commands/{cmd_file.name}: missing 'description'"
                )
            for ln, msg in find_truncated_context_blocks(cmd_file.read_text()):
                fails.append(f"{name}/commands/{cmd_file.name}: line {ln}: {msg}")

    # ── LICENSE ────────────────────────────────────────────────────
    if not (plugin_root / "LICENSE").exists():
        fails.append(f"{name}: missing LICENSE")

    # ── ALIGNMENT 2: Hook registration (disk → plugin.json) ──────
    # Every hooks/*.sh on disk should be registered in plugin.json
    hooks_dir = plugin_root / "hooks"
    if hooks_dir.is_dir():
        registered = _collect_registered_hook_scripts(pj, plugin_root)
        for script in sorted(hooks_dir.glob("*.sh")):
            if script.name in HOOK_HELPERS:
                continue
            if script.name not in registered:
                fails.append(
                    f"{name}: hooks/{script.name} exists on disk but not "
                    f"registered in plugin.json"
                )

            # ── ALIGNMENT 5: Hook executability ───────────────────
            if not os.access(script, os.X_OK):
                fails.append(
                    f"{name}: hooks/{script.name} is not executable (chmod +x)"
                )

    # ── ALIGNMENT 3: Version consistency ──────────────────────────
    # If pyproject.toml exists, plugin.json version should be readable
    # via hatchling's regex pattern
    pyproject = plugin_root / "pyproject.toml"
    if pyproject.exists() and "version" in pj:
        try:
            pyproject_text = pyproject.read_text()
            # Check if version is dynamic (read from plugin.json)
            if "dynamic" in pyproject_text and '"version"' in pyproject_text:
                # Hatchling reads version from plugin.json via regex.
                # Verify plugin.json version is a valid semver-ish string
                version = pj["version"]
                if not re.match(r"^\d+\.\d+\.\d+", version):
                    fails.append(
                        f"{name}: plugin.json version '{version}' is not semver"
                    )
                # Verify hatch config points at plugin.json
                if "plugin.json" not in pyproject_text:
                    fails.append(
                        f"{name}: pyproject.toml has dynamic version but "
                        f"doesn't reference plugin.json"
                    )
            elif "version" in pyproject_text:
                # Static version in pyproject.toml — check it matches
                m = re.search(r'version\s*=\s*"([^"]+)"', pyproject_text)
                if m and m.group(1) != pj.get("version", ""):
                    fails.append(
                        f"{name}: pyproject.toml version '{m.group(1)}' != "
                        f"plugin.json version '{pj['version']}'"
                    )
        except Exception:
            pass  # pyproject.toml parsing is best-effort

    # ── ALIGNMENT 4: Instruction shards ───────────────────────────
    # If instructions.md exists, there should be a SessionStart hook
    # that creates the rules/ symlink
    instructions = plugin_root / "instructions.md"
    if instructions.exists():
        has_session_start = "SessionStart" in pj.get("hooks", {})
        if not has_session_start:
            fails.append(
                f"{name}: instructions.md exists but no SessionStart hook "
                f"registered to symlink it"
            )

    return fails


def main() -> int:
    args = sys.argv[1:]
    # --local is vestigial (everything resolves locally now) but the
    # assemble workflow still passes it — tolerate, don't treat as a name.
    if "--local" in args:
        args.remove("--local")

    repo_root = Path(__file__).resolve().parent.parent
    # The marketplace moved to spm1001/batterie (2026-06-10 cutover).
    # It's a sibling of this repo in both CI (the assemble workflow's
    # checkout layout) and local checkouts (~/repos/spm1001/).
    marketplace_path = (
        repo_root.parent / "batterie" / ".claude-plugin" / "marketplace.json"
    )

    try:
        marketplace = json.loads(marketplace_path.read_text())
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"FAIL: marketplace.json (expected at {marketplace_path}): {e}")
        return 1

    plugins = marketplace.get("plugins", [])
    if not plugins:
        print("FAIL: marketplace.json has no plugins")
        return 1

    # Filter to requested plugins
    if args:
        plugins = [p for p in plugins if p["name"] in args]
        if not plugins:
            print(f"FAIL: no matching plugins for: {args}")
            return 1

    all_fails: list[str] = []
    all_pass = 0
    all_skip = 0

    for plugin in plugins:
        name = plugin["name"]
        plugin_dir = resolve_plugin_dir(plugin, repo_root)
        if plugin_dir is None:
            print(f"  SKIP {name} (not resolvable)")
            all_skip += 1
            continue

        fails = lint_plugin(name, plugin_dir)
        if fails:
            for f in fails:
                print(f"  FAIL {f}")
            all_fails.extend(fails)
        else:
            print(f"  PASS {name}")
            all_pass += 1

    print()
    print(f"=== {all_pass} pass, {len(all_fails)} fail, {all_skip} skip ===")
    return 1 if all_fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

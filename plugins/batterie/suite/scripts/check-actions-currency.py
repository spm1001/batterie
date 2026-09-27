#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
"""
check-actions-currency.py — sweep batterie workflows against Simon Willison's
actions-latest list (https://simonw.github.io/actions-latest/versions.txt) and
flag any major-version drift.

Usage:
    uv run --script scripts/check-actions-currency.py

Exit codes:
    0 — every official actions/* use is at Simon's current major version
    1 — at least one drift found

Notes:
    Only checks the `actions/*` namespace (what Simon tracks). Third-party
    actions (astral-sh/setup-uv, anthropics/claude-code-action, etc.) are
    listed in an "Untracked" section but don't affect the exit code — those
    are Dependabot's job.

    Reads the comment after `# vN` on each `uses:` line as the declared major
    version. The SHA is not validated here (Dependabot handles SHA currency).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import httpx

VERSIONS_URL = "https://simonw.github.io/actions-latest/versions.txt"
BATTERIE_ROOT = Path.home() / "Repos" / "batterie"

USES_RE = re.compile(
    r"uses:\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([a-f0-9]{7,40})\s*#\s*(v\S+)"
)


def fetch_simon_list() -> dict[str, str]:
    """Return {action_name: major_version} from Simon's list."""
    resp = httpx.get(VERSIONS_URL, timeout=10)
    resp.raise_for_status()
    out: dict[str, str] = {}
    for line in resp.text.splitlines():
        line = line.strip()
        if not line or "@" not in line:
            continue
        name, version = line.split("@", 1)
        out[name] = version
    return out


def find_workflow_files() -> list[Path]:
    return sorted(BATTERIE_ROOT.glob("*/.github/workflows/*.yml"))


def parse_workflow(path: Path) -> list[tuple[str, str, str]]:
    """Return [(action, sha, declared_version), ...] for each `uses:` line."""
    results = []
    for line in path.read_text().splitlines():
        m = USES_RE.search(line)
        if m:
            results.append((m.group(1), m.group(2), m.group(3)))
    return results


def main() -> int:
    try:
        simon = fetch_simon_list()
    except httpx.HTTPError as e:
        print(f"Failed to fetch {VERSIONS_URL}: {e}", file=sys.stderr)
        return 2

    workflows = find_workflow_files()
    if not workflows:
        print(f"No workflow files found under {BATTERIE_ROOT}/*/.github/workflows/")
        return 0

    drift: list[tuple[Path, str, str, str]] = []  # (file, action, declared, simon)
    untracked: dict[str, list[Path]] = {}  # action -> [files using it]
    aligned: set[str] = set()

    for wf in workflows:
        for action, _sha, declared in parse_workflow(wf):
            if action in simon:
                expected = simon[action]
                # Compare major only: "v6.0.2" matches "v6", "v7" doesn't.
                declared_major = declared.split(".")[0]
                if declared_major != expected:
                    drift.append((wf, action, declared, expected))
                else:
                    aligned.add(action)
            else:
                untracked.setdefault(action, []).append(wf)

    print(f"Checked {len(workflows)} workflow files across batterie.")
    print(f"Simon's list: {len(simon)} official actions tracked.\n")

    if aligned:
        print(f"✓ {len(aligned)} action(s) at Simon's current major:")
        for action in sorted(aligned):
            print(f"    {action}@{simon[action]}")
        print()

    if drift:
        print(f"⚠ {len(drift)} drift(s) found:")
        for wf, action, declared, expected in drift:
            rel = wf.relative_to(BATTERIE_ROOT)
            print(f"    {rel}: {action}@{declared} (Simon: @{expected})")
        print()

    if untracked:
        print(f"ℹ {len(untracked)} third-party action(s) not in Simon's list "
              "(Dependabot tracks these):")
        for action, files in sorted(untracked.items()):
            repos = sorted({f.parts[-4] for f in files})
            print(f"    {action} — used by {', '.join(repos)}")
        print()

    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())

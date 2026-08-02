#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "jinja2",
#   "tomli; python_version < '3.11'",
# ]
# ///
"""
lint.py — detect drift between brigade.toml and GENERATED sections in docs.

Usage:
    uv run --script scripts/lint.py

Exit codes:
    0 — all sections are up to date
    1 — one or more sections are stale (diff printed to stdout)

Run render.py to fix any drift found.
"""

import re
import sys
from pathlib import Path

# Import render.py's rendering functions without running main().
# This is intentional — not a hack to "fix" by duplicating the rendering logic.
# render.py's module-level code (load TOML, build templates) runs on import;
# main() is guarded by __name__ == "__main__" so it doesn't execute.
# Keeping one set of templates means lint is always testing exactly what render produces.
sys.path.insert(0, str(Path(__file__).parent))
import render  # noqa: E402 — must come after sys.path manipulation

# ---------------------------------------------------------------------------
# Extract actual content between markers
# ---------------------------------------------------------------------------

# Match both HTML and Liquid marker formats (see render.py for rationale).
_OPEN = r"(?:<!-- |{%\s*comment\s*%})"
_CLOSE = r"(?:\s*-->|{%\s*endcomment\s*%})"

MARKER_RE = re.compile(
    rf"{_OPEN}GENERATED:(?P<name>[^:]+):START{_CLOSE}\n"
    r"(?P<content>.*?)"
    rf"{_OPEN}GENERATED:(?P=name):END{_CLOSE}",
    re.DOTALL,
)


def extract_sections(path: Path) -> dict[str, str]:
    """Return {marker_name: content_between_markers} for all markers in file."""
    text = path.read_text()
    sections = {}
    for m in MARKER_RE.finditer(text):
        name = m.group("name")
        # content includes a trailing newline before the END marker
        content = m.group("content").rstrip("\n")
        sections[name] = content
    return sections


# ---------------------------------------------------------------------------
# Expected sections per file
# ---------------------------------------------------------------------------

EXPECTED = {
    render.README: {
        "brigade-table": render.render_brigade_table_readme,
    },
    render.DOCS_INDEX: {
        "brigade-table": render.render_brigade_table_docs,
    },
    render.FOR_AGENTS: {
        "vocabulary": render.render_vocabulary,
        "tool-routing": render.render_tool_routing,
        "dependency-direction": render.render_dependency_direction,
        "key-repos": render.render_key_repos,
    },
}

# ---------------------------------------------------------------------------
# Diff helper
# ---------------------------------------------------------------------------


def show_diff(name: str, expected: str, actual: str) -> None:
    import difflib
    expected_lines = expected.splitlines(keepends=True)
    actual_lines = actual.splitlines(keepends=True)
    diff = list(difflib.unified_diff(
        actual_lines,
        expected_lines,
        fromfile=f"{name} (in file)",
        tofile=f"{name} (from registry)",
        lineterm="",
    ))
    print("".join(diff))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def check_tool_pages() -> list[str]:
    """Every registry slug needs a docs/tools/<slug>.md page — the generated
    brigade table in docs/index.md links tools/<slug> for every row, so a
    missing page is a dead link on the live site (plongeur and accomplis
    shipped as 404s for weeks this way). Extra pages are fine: consomme.md is
    a deliberate vocabulary-station page with no registry row."""
    problems = []
    tools_dir = render.ROOT / "docs" / "tools"
    slugs = {t["slug"] for t in render.tools}
    for slug in sorted(slugs):
        if not (tools_dir / f"{slug}.md").is_file():
            print(f"MISSING: docs/tools/{slug}.md — registry slug '{slug}' "
                  f"is a dead link in the generated brigade table")
            problems.append(f"tools/{slug}.md")
    orphans = sorted(p.stem for p in tools_dir.glob("*.md") if p.stem not in slugs)
    if orphans:
        print(f"info: tool pages with no registry row (deliberate is fine): "
              f"{', '.join(orphans)}")
    return problems


def main() -> None:
    stale: list[str] = []
    stale.extend(check_tool_pages())

    for path, sections in EXPECTED.items():
        actual = extract_sections(path)
        rel = path.relative_to(render.ROOT)

        for marker_name, renderer in sections.items():
            expected_content = renderer()
            actual_content = actual.get(marker_name)

            if actual_content is None:
                print(f"ERROR: marker '{marker_name}' not found in {rel}")
                stale.append(f"{rel}:{marker_name}")
                continue

            if expected_content != actual_content:
                print(f"STALE: {rel} — {marker_name}")
                show_diff(marker_name, expected_content, actual_content)
                stale.append(f"{rel}:{marker_name}")

    if stale:
        print(f"\n{len(stale)} problem(s). GENERATED drift: run scripts/render.py."
              " MISSING tool pages are hand-authored — write them.")
        sys.exit(1)
    else:
        print("OK — all GENERATED sections are up to date.")


if __name__ == "__main__":
    main()

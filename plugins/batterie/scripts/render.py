#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "jinja2",
#   "tomli; python_version < '3.11'",
# ]
# ///
"""
render.py — regenerate all GENERATED sections in docs from brigade.toml.

Usage:
    uv run --script scripts/render.py

Idempotent: safe to run repeatedly. Only writes a file if content changes.

Marker format in target files:
    <!-- GENERATED:{name}:START -->
    ...content replaced here...
    <!-- GENERATED:{name}:END -->
"""

import re
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

from jinja2 import Environment

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent
TOML_PATH = ROOT / "brigade.toml"
README = ROOT / "README.md"
DOCS_INDEX = ROOT / "docs" / "index.md"
FOR_AGENTS = ROOT / "docs" / "for-agents.md"

# ---------------------------------------------------------------------------
# Load registry
# ---------------------------------------------------------------------------

with open(TOML_PATH, "rb") as f:
    registry = tomllib.load(f)

tools_by_slug = registry["tool"]
order = registry["meta"]["order"]
tools = [tools_by_slug[slug] for slug in order]
dependencies = registry.get("dependency", [])

MATURITY_EMOJI = {
    "stable": "⚡ Stable",
    "beta": "🔧 Beta",
    "alpha": "🧪 Alpha",
}

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

env = Environment(autoescape=False, keep_trailing_newline=True)

# Brigade table row — README variant (links to GitHub)
README_ROW = env.from_string(
    "| [**{{ name }}**](https://github.com/{{ repo }}) "
    "| {{ station }} | {{ what }} | {{ maturity_label }} |"
)

# Brigade table row — docs/index.md variant (links to tools/ pages)
DOCS_ROW = env.from_string(
    "| [**{{ name }}**](tools/{{ slug }}) "
    "| {{ station }} | {{ what }} | {{ maturity_label }} |"
)

# Vocabulary row
VOCAB_ROW = env.from_string(
    "| **{{ term }}** | {{ meaning }} |"
)

# Tool routing row
ROUTING_ROW = env.from_string(
    "| {{ need }} | **{{ slug }}** | {{ not_this }} |"
)

# Dependency direction row
DEP_ROW = env.from_string(
    "| {{ from_label }} | → | {{ to }}{{ label_suffix }} |"
)

# Key repos row
REPO_ROW = env.from_string(
    "| {{ name }} | [{{ repo }}](https://github.com/{{ repo }}) |"
)

# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def render_brigade_table_readme() -> str:
    rows = [
        "| Tool | Station | Description | Status |",
        "|------|---------|-------------|--------|",
    ]
    for t in tools:
        rows.append(README_ROW.render(
            name=t["name"],
            repo=t["repo"],
            station=t["station"],
            what=t["what"],
            maturity_label=MATURITY_EMOJI[t["maturity"]],
        ))
    return "\n".join(rows)


def render_brigade_table_docs() -> str:
    rows = [
        "| Tool | Station | Description | Status |",
        "|------|---------|-------------|--------|",
    ]
    for t in tools:
        rows.append(DOCS_ROW.render(
            name=t["name"],
            slug=t["slug"],
            station=t["station"],
            what=t["what"],
            maturity_label=MATURITY_EMOJI[t["maturity"]],
        ))
    return "\n".join(rows)


def render_vocabulary() -> str:
    rows = [
        "| Term | Meaning |",
        "|------|---------|",
    ]
    for t in tools:
        term = t.get("vocab_term", t["name"])
        rows.append(VOCAB_ROW.render(term=term, meaning=t["vocab_meaning"]))
    return "\n".join(rows)


def render_tool_routing() -> str:
    rows = [
        "| Need | Use | NOT this |",
        "|------|-----|----------|",
    ]
    for t in tools:
        for r in t.get("routing", []):
            not_this = r["not"] if r["not"] else "—"
            rows.append(ROUTING_ROW.render(
                need=r["need"],
                slug=t["slug"],
                not_this=not_this,
            ))
    return "\n".join(rows)


def render_dependency_direction() -> str:
    rows = [
        "| Source | → | Destination |",
        "|--------|---|-------------|",
    ]
    for dep in dependencies:
        from_slugs = dep["from"]
        if from_slugs == ["all"]:
            from_label = "All tools"
        else:
            # Resolve slug → display name, fall back to slug
            names = []
            for s in from_slugs:
                t = tools_by_slug.get(s)
                names.append(t["name"] if t else s)
            from_label = ", ".join(names)

        label = dep.get("label", "")
        label_suffix = f" ({label})" if label else ""
        rows.append(DEP_ROW.render(
            from_label=from_label,
            to=dep["to"],
            label_suffix=label_suffix,
        ))
    return "\n".join(rows)


def render_key_repos() -> str:
    rows = [
        "| Tool | Repo |",
        "|------|------|",
    ]
    for t in tools:
        rows.append(REPO_ROW.render(name=t["name"], repo=t["repo"]))
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Marker replacement engine
# ---------------------------------------------------------------------------

# Two marker formats:
#   HTML:   <!-- GENERATED:name:START --> / <!-- GENERATED:name:END -->
#   Liquid: {% comment %}GENERATED:name:START{% endcomment %} / ...
#
# HTML markers are for files rendered by GitHub's GFM (README.md).
# Liquid markers are for Jekyll docs — Jekyll strips them before kramdown
# sees the content, so markdown tables render correctly. HTML comments
# would survive into kramdown and break table parsing.

# Matches either marker format — the (?:...|...) alternation covers both styles.
_OPEN = r"(?:<!-- |{%\s*comment\s*%})"    # start delimiter
_CLOSE = r"(?:\s*-->|{%\s*endcomment\s*%})"  # end delimiter

MARKER_RE = re.compile(
    rf"(?P<start>{_OPEN}GENERATED:(?P<name>[^:]+):START{_CLOSE})\n"
    r"(?P<content>.*?)"
    rf"{_OPEN}GENERATED:(?P=name):END{_CLOSE}",
    re.DOTALL,
)


def _marker_pair(start_tag: str, name: str) -> tuple[str, str]:
    """Return (start, end) markers matching the format of the matched tag."""
    if start_tag.startswith("<!--"):
        return (
            f"<!-- GENERATED:{name}:START -->",
            f"<!-- GENERATED:{name}:END -->",
        )
    return (
        f"{{% comment %}}GENERATED:{name}:START{{% endcomment %}}",
        f"{{% comment %}}GENERATED:{name}:END{{% endcomment %}}",
    )


def replace_markers(text: str, sections: dict[str, str]) -> tuple[str, list[str]]:
    """Replace all GENERATED marker regions. Returns (new_text, list_of_replaced_names)."""
    replaced = []

    def replacer(m: re.Match) -> str:
        name = m.group("name")
        if name not in sections:
            print(f"  WARNING: unknown marker '{name}' — skipping", file=sys.stderr)
            return m.group(0)
        new_content = sections[name] + "\n"
        replaced.append(name)
        start_tag, end_tag = _marker_pair(m.group("start"), name)
        return f"{start_tag}\n{new_content}{end_tag}"

    new_text = MARKER_RE.sub(replacer, text)
    return new_text, replaced


def update_file(path: Path, sections: dict[str, str]) -> None:
    original = path.read_text()
    updated, replaced = replace_markers(original, sections)
    if updated == original:
        print(f"  {path.relative_to(ROOT)} — no changes")
    else:
        path.write_text(updated)
        print(f"  {path.relative_to(ROOT)} — updated: {', '.join(replaced)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("render.py — regenerating GENERATED sections from brigade.toml")

    update_file(README, {
        "brigade-table": render_brigade_table_readme(),
    })

    update_file(DOCS_INDEX, {
        "brigade-table": render_brigade_table_docs(),
    })

    update_file(FOR_AGENTS, {
        "vocabulary": render_vocabulary(),
        "tool-routing": render_tool_routing(),
        "dependency-direction": render_dependency_direction(),
        "key-repos": render_key_repos(),
    })

    print("Done.")


if __name__ == "__main__":
    main()

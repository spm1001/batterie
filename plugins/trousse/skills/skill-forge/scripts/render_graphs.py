#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
DOT Graph Renderer - Extract and render DOT graphs from SKILL.md files.

Extracts DOT graph blocks from markdown and renders them to SVG using graphviz.
Follows Obra's superpowers conventions for node shapes.

Usage:
    render_graphs.py <skill-path>           # Render to skill/assets/
    render_graphs.py <skill-path> --output <dir>
    render_graphs.py --dot <file.dot>       # Render single DOT file

Node shape conventions (from superpowers):
    - diamond: decisions/questions (end with ?)
    - box: actions (default)
    - plaintext: literal commands
    - ellipse: states/situations
    - octagon (red): STOP/critical warnings
    - doublecircle: entry/exit points
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


def check_graphviz() -> bool:
    """Check if graphviz is installed."""
    try:
        result = subprocess.run(
            ['dot', '-V'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def extract_dot_blocks(content: str) -> list[tuple[str, str]]:
    """Extract DOT blocks from markdown content.

    Returns list of (name, dot_content) tuples.
    """
    blocks = []

    # Pattern for ```dot blocks with optional name
    pattern = r'```dot(?:\s+(\w+))?\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL)

    for i, (name, dot_content) in enumerate(matches):
        if not name:
            name = f"graph_{i+1}"
        blocks.append((name, dot_content.strip()))

    # Also look for digraph/graph declarations to extract name
    for i, (name, dot_content) in enumerate(blocks):
        if name.startswith('graph_'):
            # Try to extract name from digraph declaration
            match = re.match(r'(?:di)?graph\s+(\w+)\s*\{', dot_content)
            if match:
                blocks[i] = (match.group(1), dot_content)

    return blocks


def validate_dot(dot_content: str) -> tuple[bool, str]:
    """Validate DOT syntax."""
    try:
        result = subprocess.run(
            ['dot', '-Tsvg'],
            input=dot_content,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return False, result.stderr
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "DOT rendering timed out"
    except Exception as e:
        return False, str(e)


def render_dot_to_svg(dot_content: str) -> Optional[str]:
    """Render DOT content to SVG string."""
    try:
        result = subprocess.run(
            ['dot', '-Tsvg'],
            input=dot_content,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            print(f"Error rendering DOT: {result.stderr}")
            return None
        return result.stdout
    except Exception as e:
        print(f"Error: {e}")
        return None


def render_dot_to_png(dot_content: str) -> Optional[bytes]:
    """Render DOT content to PNG bytes."""
    try:
        result = subprocess.run(
            ['dot', '-Tpng', '-Gdpi=150'],
            input=dot_content.encode(),
            capture_output=True,
            timeout=30
        )
        if result.returncode != 0:
            print(f"Error rendering DOT: {result.stderr.decode()}")
            return None
        return result.stdout
    except Exception as e:
        print(f"Error: {e}")
        return None


def add_style_defaults(dot_content: str) -> str:
    """Add style defaults for consistent rendering."""
    # Check if already has graph attributes
    if 'graph [' in dot_content or 'graph[' in dot_content:
        return dot_content

    # Add defaults after the opening brace
    match = re.search(r'((?:di)?graph\s+\w+\s*\{)', dot_content)
    if match:
        defaults = '''
    // Style defaults
    graph [fontname="Helvetica", fontsize=12, rankdir=TB];
    node [fontname="Helvetica", fontsize=11];
    edge [fontname="Helvetica", fontsize=10];
'''
        return dot_content.replace(match.group(1), match.group(1) + defaults)

    return dot_content


def process_skill(skill_path: Path, output_dir: Optional[Path] = None) -> int:
    """Process a skill directory, rendering all DOT graphs."""
    skill_md = skill_path / 'SKILL.md'

    if not skill_md.exists():
        print(f"Error: SKILL.md not found in {skill_path}")
        return 1

    content = skill_md.read_text()
    blocks = extract_dot_blocks(content)

    if not blocks:
        print(f"No DOT graphs found in {skill_md}")
        return 0

    # Determine output directory
    if output_dir is None:
        output_dir = skill_path / 'assets' / 'graphs'
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(blocks)} DOT graph(s)")

    rendered = 0
    for name, dot_content in blocks:
        print(f"  Rendering: {name}")

        # Validate
        valid, error = validate_dot(dot_content)
        if not valid:
            print(f"    Error: {error}")
            continue

        # Add style defaults
        styled_dot = add_style_defaults(dot_content)

        # Render SVG
        svg = render_dot_to_svg(styled_dot)
        if svg:
            svg_path = output_dir / f"{name}.svg"
            svg_path.write_text(svg)
            print(f"    Created: {svg_path}")
            rendered += 1

        # Also render PNG for convenience
        png = render_dot_to_png(styled_dot)
        if png:
            png_path = output_dir / f"{name}.png"
            png_path.write_bytes(png)
            print(f"    Created: {png_path}")

    print(f"\nRendered {rendered}/{len(blocks)} graphs to {output_dir}")
    return 0 if rendered == len(blocks) else 1


def process_dot_file(dot_path: Path, output_dir: Optional[Path] = None) -> int:
    """Process a single DOT file."""
    if not dot_path.exists():
        print(f"Error: File not found: {dot_path}")
        return 1

    content = dot_path.read_text()
    name = dot_path.stem

    if output_dir is None:
        output_dir = dot_path.parent

    # Validate
    valid, error = validate_dot(content)
    if not valid:
        print(f"Error: {error}")
        return 1

    # Add style defaults
    styled_dot = add_style_defaults(content)

    # Render
    svg = render_dot_to_svg(styled_dot)
    if svg:
        svg_path = output_dir / f"{name}.svg"
        svg_path.write_text(svg)
        print(f"Created: {svg_path}")

    png = render_dot_to_png(styled_dot)
    if png:
        png_path = output_dir / f"{name}.png"
        png_path.write_bytes(png)
        print(f"Created: {png_path}")

    return 0


def print_conventions():
    """Print DOT graph conventions."""
    print("""
DOT Graph Conventions (from Obra's superpowers)
================================================

NODE SHAPES:
  shape=diamond       Questions/decisions (end with ?)
  shape=box           Actions (default)
  shape=plaintext     Literal commands (git status)
  shape=ellipse       States/situations
  shape=doublecircle  Entry/exit points
  shape=octagon       Critical warnings (use with red fill)

CRITICAL WARNING STYLE:
  "STOP: Never do X" [shape=octagon, style=filled, fillcolor=red, fontcolor=white];

EDGE LABELS:
  Binary decisions: label="yes" or label="no"
  Multiple paths: Use condition names
  Cross-process: label="triggers", style=dotted

NAMING PATTERNS:
  Questions end with ?      "Is test passing?"
  Actions start with verb   "Write the test"
  Commands are literal      "npm test"
  States describe situation "Build complete"

EXAMPLE:
  digraph workflow {
      "Test failing" [shape=ellipse];
      "Is cause obvious?" [shape=diamond];
      "Read error message" [shape=box];
      "git diff HEAD~1" [shape=plaintext];
      "NEVER ignore errors" [shape=octagon, style=filled, fillcolor=red, fontcolor=white];

      "Test failing" -> "Is cause obvious?";
      "Is cause obvious?" -> "Read error message" [label="no"];
      "Is cause obvious?" -> "git diff HEAD~1" [label="yes"];
  }
""")


def main():
    parser = argparse.ArgumentParser(
        description="Extract and render DOT graphs from skills"
    )
    parser.add_argument("skill_path", type=Path, nargs="?", help="Path to skill directory")
    parser.add_argument("--dot", type=Path, help="Render a single DOT file")
    parser.add_argument("--output", "-o", type=Path, help="Output directory")
    parser.add_argument("--conventions", action="store_true", help="Print DOT conventions")
    args = parser.parse_args()

    if args.conventions:
        print_conventions()
        return 0

    # Check graphviz
    if not check_graphviz():
        print("Error: graphviz not installed")
        print("Install with: brew install graphviz")
        return 1

    if args.dot:
        return process_dot_file(args.dot.expanduser().resolve(), args.output)
    elif args.skill_path:
        return process_skill(args.skill_path.expanduser().resolve(), args.output)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

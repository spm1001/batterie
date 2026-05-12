#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Scaffold a new batterie-de-savoir Python repo.

Creates the full directory skeleton with deterministic content.
CLAUDE.md gets [TODO] markers for the LLM to fill in later.

Usage:
    init_repo.py --name deglacer --prefix dgc --description "CC JSONL parser"
    init_repo.py --name deglacer --prefix dgc --description "CC JSONL parser" --visibility private
    init_repo.py --name deglacer --prefix dgc --description "test" --dry-run
"""

import argparse
import subprocess
import sys
from pathlib import Path
from textwrap import dedent


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command, exit on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(f"FAIL: {' '.join(cmd)}", file=sys.stderr)
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        sys.exit(1)
    return result


def pkg_name(name: str) -> str:
    """Convert project name to Python package name (hyphens to underscores)."""
    return name.replace("-", "_")


def safe_desc(description: str) -> str:
    """Escape description for use in Python strings and TOML values."""
    return description.replace("\\", "\\\\").replace('"', '\\"')


def gh_username() -> str:
    """Get the authenticated GitHub username."""
    result = subprocess.run(
        ["gh", "api", "user", "--jq", ".login"],
        capture_output=True, text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    print("FAIL: could not determine GitHub username via `gh api user`", file=sys.stderr)
    sys.exit(1)


def create_pyproject(root: Path, name: str, description: str) -> None:
    pkg = pkg_name(name)
    desc = safe_desc(description)
    content = dedent(f"""\
        [project]
        name = "{name}"
        version = "0.1.0"
        description = "{desc}"
        requires-python = ">=3.11"
        license = "MIT"

        [dependency-groups]
        dev = ["pytest"]

        [build-system]
        requires = ["hatchling"]
        build-backend = "hatchling.build"

        [tool.hatch.build.targets.wheel]
        packages = ["src/{pkg}"]

        [tool.pytest.ini_options]
        testpaths = ["tests"]
        pythonpath = ["src"]
    """)
    (root / "pyproject.toml").write_text(content)


def create_init_py(root: Path, name: str, description: str) -> None:
    pkg = pkg_name(name)
    src_dir = root / "src" / pkg
    src_dir.mkdir(parents=True)
    desc = safe_desc(description)
    content = dedent(f'''\
        """{name.capitalize()} — {desc}."""

        from importlib.metadata import version as _version

        __version__ = _version("{name}")
    ''')
    (src_dir / "__init__.py").write_text(content)


def create_gitignore(root: Path) -> None:
    content = dedent("""\
        __pycache__/
        *.py[cod]
        *.egg-info/
        dist/
        build/
        .venv/
        .pytest_cache/
    """)
    (root / ".gitignore").write_text(content)


def create_tests(root: Path) -> None:
    tests_dir = root / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("")
    content = dedent('''\
        """Test fixtures."""

        # import pytest
    ''')
    (tests_dir / "conftest.py").write_text(content)


def create_claude_md(root: Path, name: str, description: str) -> None:
    content = dedent(f"""\
        # {name.capitalize()}

        {description}

        ## Quick Commands

        ```bash
        uv run --group dev pytest          # run tests
        uv pip install -e .                # editable install
        ```

        ## Module Map

        [TODO: Fill in module table — one row per module under src/{pkg_name(name)}/]

        | Module | Role |
        |--------|------|
        | `[TODO]` | [TODO] |

        ## Key Conventions

        [TODO: Fill in project-specific conventions, patterns, and things not to "fix"]
    """)
    (root / "CLAUDE.md").write_text(content)


def create_understanding(root: Path, name: str, description: str) -> None:
    bon_dir = root / ".bon"
    content = dedent(f"""\
        # Understanding

        {name.capitalize()} is a new repo. {description}

        [TODO: This understanding doc will grow as sessions accumulate knowledge about this project.]
    """)
    (bon_dir / "understanding.md").write_text(content)


def git_init(root: Path) -> None:
    run(["git", "init", "-b", "main"], cwd=root)


def bon_init(root: Path, prefix: str) -> None:
    run(["bon", "init", "--prefix", prefix], cwd=root)


def gh_create(root: Path, name: str, description: str, visibility: str, owner: str) -> None:
    run([
        "gh", "repo", "create", f"{owner}/{name}",
        f"--{visibility}",
        "--description", description,
        "--source", str(root),
        "--remote", "origin",
    ], cwd=root)


def git_first_commit(root: Path, name: str) -> None:
    run(["git", "add", "-A"], cwd=root)
    run(["git", "commit", "-m", f"Scaffold {name} repo"], cwd=root)


def git_push(root: Path) -> None:
    run(["git", "push", "-u", "origin", "main"], cwd=root)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scaffold a new batterie-de-savoir Python repo."
    )
    parser.add_argument("--name", required=True, help="Project name (e.g. deglacer)")
    parser.add_argument("--prefix", required=True, help="Bon prefix (e.g. dgc)")
    parser.add_argument("--description", required=True, help="One-line description")
    parser.add_argument(
        "--visibility", default="public", choices=["public", "private"],
        help="GitHub repo visibility (default: public)"
    )
    parser.add_argument(
        "--owner", default=None,
        help="GitHub owner (default: authenticated gh user)"
    )
    parser.add_argument(
        "--dir", default=".", help="Target directory (default: current)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Create local skeleton only — skip gh repo create and git push"
    )
    args = parser.parse_args()

    root = Path(args.dir).resolve()

    # Safety: refuse if directory has existing git repo
    if (root / ".git").exists():
        print(f"FAIL: {root} already has a .git directory", file=sys.stderr)
        sys.exit(1)

    # Check for non-empty directory (warn, don't fail — adopt mode may use this)
    existing = [f for f in root.iterdir() if not f.name.startswith(".")]
    if existing:
        print(f"WARN: {root} is not empty ({len(existing)} items)", file=sys.stderr)

    owner = args.owner or gh_username()

    print(f"Scaffolding {args.name} in {root}")
    if args.dry_run:
        print("  (dry run — skipping GitHub and push)")

    # 1. Git init
    git_init(root)
    print("  git init")

    # 2. File structure
    create_pyproject(root, args.name, args.description)
    print("  pyproject.toml")

    create_init_py(root, args.name, args.description)
    print(f"  src/{pkg_name(args.name)}/__init__.py")

    create_gitignore(root)
    print("  .gitignore")

    create_tests(root)
    print("  tests/")

    create_claude_md(root, args.name, args.description)
    print("  CLAUDE.md")

    # 3. Bon init
    bon_init(root, args.prefix)
    print(f"  bon init --prefix {args.prefix}")

    # 4. Understanding seed (after bon init creates .bon/)
    create_understanding(root, args.name, args.description)
    print("  .bon/understanding.md")

    # 5. First commit (always — even dry-run gets a local commit)
    git_first_commit(root, args.name)
    print("  first commit")

    if not args.dry_run:
        # 6. GitHub repo + push
        gh_create(root, args.name, args.description, args.visibility, owner)
        print(f"  gh repo create {owner}/{args.name} ({args.visibility})")

        git_push(root)
        print("  pushed to origin/main")

    print(f"\nDone. {args.name} is ready at {root}")


if __name__ == "__main__":
    main()

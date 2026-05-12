#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["tomli; python_version < '3.11'"]
# ///
"""
Repo conformance checker for batterie-de-savoir Python packages.

Validates that a repo matches the scaffold checklist:
- Git repo on named branch
- .gitignore with Python patterns
- pyproject.toml with hatchling, src layout, pytest config
- src/<pkg>/__init__.py with __version__
- tests/ with conftest.py
- CLAUDE.md present and non-empty
- .bon/ initialized
- GitHub remote configured

Usage:
    validate_repo.py [path]        # default: current directory
    validate_repo.py [path] --json
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib


@dataclass
class Check:
    name: str
    passed: bool
    message: str
    severity: str = "error"


@dataclass
class Report:
    repo_path: str
    valid: bool
    checks: list[Check] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    score: int = 100


def run_quiet(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def check_git(root: Path) -> list[Check]:
    checks = []

    git_dir = root / ".git"
    if not git_dir.exists():
        checks.append(Check("git_repo", False, "No .git directory"))
        return checks
    checks.append(Check("git_repo", True, "Git repo exists"))

    result = run_quiet(["git", "branch", "--show-current"], cwd=root)
    branch = result.stdout.strip()
    if branch:
        checks.append(Check("git_branch", True, f"On branch: {branch}"))
    else:
        checks.append(Check("git_branch", False, "Detached HEAD — must be on a named branch"))

    return checks


def check_gitignore(root: Path) -> Check:
    gi = root / ".gitignore"
    if not gi.exists():
        return Check("gitignore", False, "No .gitignore file")

    content = gi.read_text()
    patterns = ["__pycache__", "*.py[cod]", ".venv"]
    missing = [p for p in patterns if p not in content]
    if missing:
        return Check("gitignore", False, f"Missing patterns: {', '.join(missing)}", severity="warning")
    return Check("gitignore", True, ".gitignore present with Python patterns")


def check_pyproject(root: Path) -> list[Check]:
    checks = []
    pyproject = root / "pyproject.toml"

    if not pyproject.exists():
        checks.append(Check("pyproject_exists", False, "No pyproject.toml"))
        return checks
    checks.append(Check("pyproject_exists", True, "pyproject.toml exists"))

    try:
        data = tomllib.loads(pyproject.read_text())
    except Exception as e:
        checks.append(Check("pyproject_valid", False, f"Invalid TOML: {e}"))
        return checks

    # Build backend
    build_sys = data.get("build-system", {})
    backend = build_sys.get("build-backend", "")
    if "hatchling" in backend:
        checks.append(Check("pyproject_backend", True, "Hatchling build backend"))
    else:
        checks.append(Check("pyproject_backend", False, f"Expected hatchling, got: {backend}"))

    # Src layout
    hatch_wheel = data.get("tool", {}).get("hatch", {}).get("build", {}).get("targets", {}).get("wheel", {})
    packages = hatch_wheel.get("packages", [])
    has_src = any(p.startswith("src/") for p in packages)
    if has_src:
        checks.append(Check("pyproject_src_layout", True, f"Src layout: {packages}"))
    else:
        checks.append(Check("pyproject_src_layout", False, "No src/ layout in hatch wheel packages"))

    # Dependency groups
    dep_groups = data.get("dependency-groups", {})
    if "dev" in dep_groups:
        checks.append(Check("pyproject_dev_deps", True, "Has [dependency-groups] dev"))
    else:
        checks.append(Check("pyproject_dev_deps", False, "Missing [dependency-groups] dev", severity="warning"))

    # Pytest config
    pytest_opts = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    if pytest_opts.get("pythonpath"):
        checks.append(Check("pyproject_pytest", True, "Pytest config with pythonpath"))
    else:
        checks.append(Check("pyproject_pytest", False, "Missing [tool.pytest.ini_options] pythonpath"))

    return checks


def check_src_package(root: Path) -> list[Check]:
    checks = []
    src = root / "src"

    if not src.exists():
        checks.append(Check("src_exists", False, "No src/ directory"))
        return checks

    pkgs = [d for d in src.iterdir() if d.is_dir() and not d.name.startswith("_")]
    if not pkgs:
        checks.append(Check("src_package", False, "No package directory under src/"))
        return checks

    pkg = pkgs[0]
    init = pkg / "__init__.py"
    if not init.exists():
        checks.append(Check("src_init", False, f"No __init__.py in {pkg.name}"))
        return checks

    content = init.read_text()
    if "__version__" in content and "importlib.metadata" in content:
        checks.append(Check("src_version", True, f"src/{pkg.name}/__init__.py with importlib.metadata version"))
    elif "__version__" in content:
        checks.append(Check("src_version", False, f"__version__ found but not using importlib.metadata", severity="warning"))
    else:
        checks.append(Check("src_version", False, f"No __version__ in src/{pkg.name}/__init__.py"))

    return checks


def check_tests(root: Path) -> list[Check]:
    checks = []
    tests = root / "tests"

    if not tests.exists():
        checks.append(Check("tests_dir", False, "No tests/ directory"))
        return checks
    checks.append(Check("tests_dir", True, "tests/ directory exists"))

    init = tests / "__init__.py"
    if init.exists():
        checks.append(Check("tests_init", True, "tests/__init__.py present"))
    else:
        checks.append(Check("tests_init", False, "No tests/__init__.py", severity="warning"))

    conftest = tests / "conftest.py"
    if conftest.exists():
        checks.append(Check("tests_conftest", True, "tests/conftest.py present"))
    else:
        checks.append(Check("tests_conftest", False, "No tests/conftest.py", severity="warning"))

    return checks


def check_claude_md(root: Path) -> Check:
    claude_md = root / "CLAUDE.md"
    if not claude_md.exists():
        return Check("claude_md", False, "No CLAUDE.md")

    content = claude_md.read_text().strip()
    if not content:
        return Check("claude_md", False, "CLAUDE.md is empty")
    if "[TODO]" in content:
        return Check("claude_md", False, "CLAUDE.md still has [TODO] markers", severity="warning")
    return Check("claude_md", True, "CLAUDE.md present and filled in")


def check_bon(root: Path) -> Check:
    bon = root / ".bon"
    if not bon.exists():
        return Check("bon_init", False, "No .bon/ directory")

    prefix = bon / "prefix"
    if prefix.exists():
        pfx = prefix.read_text().strip()
        return Check("bon_init", True, f".bon/ initialized (prefix: {pfx})")
    return Check("bon_init", False, ".bon/ exists but no prefix file")


def check_remote(root: Path) -> Check:
    result = run_quiet(["git", "remote", "-v"], cwd=root)
    if result.returncode != 0:
        return Check("git_remote", False, "Could not check git remotes")

    if "origin" in result.stdout:
        line = [l for l in result.stdout.strip().split("\n") if "origin" in l and "(push)" in l]
        url = line[0].split()[1] if line else "unknown"
        return Check("git_remote", True, f"Remote: {url}")
    return Check("git_remote", False, "No origin remote configured")


def validate(root: Path) -> Report:
    report = Report(repo_path=str(root), valid=True)

    all_checks = []
    all_checks.extend(check_git(root))
    all_checks.append(check_gitignore(root))
    all_checks.extend(check_pyproject(root))
    all_checks.extend(check_src_package(root))
    all_checks.extend(check_tests(root))
    all_checks.append(check_claude_md(root))
    all_checks.append(check_bon(root))
    all_checks.append(check_remote(root))

    report.checks = all_checks

    for c in all_checks:
        if c.passed:
            report.passed += 1
        elif c.severity == "error":
            report.failed += 1
            report.valid = False
            report.score -= (100 // len(all_checks))
        else:
            report.warnings += 1
            report.score -= (50 // len(all_checks))

    report.score = max(0, report.score)
    return report


def print_report(report: Report) -> None:
    total = len(report.checks)
    print("=" * 60)
    print(f"REPO CONFORMANCE: {report.passed}/{total} checks passed")
    print(f"Score: {report.score}/100  |  Errors: {report.failed}  Warnings: {report.warnings}")
    print("=" * 60)
    print()

    for c in report.checks:
        icon = "\u2713" if c.passed else ("\u26a0" if c.severity == "warning" else "\u2717")
        label = "PASS" if c.passed else ("WARN" if c.severity == "warning" else "FAIL")
        print(f"  {icon} [{label:4}] {c.name}: {c.message}")

    print()
    if report.valid:
        print("Status: PASS")
    else:
        print("Status: FAIL — fix errors above")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate batterie repo conformance.")
    parser.add_argument("path", nargs="?", default=".", help="Repo path (default: current directory)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        sys.exit(1)

    report = validate(root)

    if args.json:
        data = asdict(report)
        print(json.dumps(data, indent=2))
    else:
        print_report(report)

    sys.exit(0 if report.valid else 1)


if __name__ == "__main__":
    main()

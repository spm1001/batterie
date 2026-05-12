# /// script
# requires-python = ">=3.10"
# ///
"""
Toise architecture metrics — automated health checks for Claude-maintained codebases.

Scans a git repository and reports metrics aligned to the five principles:
  1. Self-documenting files (first-breath score)
  2. One shape, everywhere (pattern signals)
  3. Boundaries (artefact checklist)
  4. Small, pure, explicit (file size distribution)
  5. Extend by recipe (CLAUDE.md recipe presence)

Usage:
    uv run --script metrics.py [repo_path]

If repo_path is omitted, scans the current directory.
"""

import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

# File extensions to treat as source code.
SOURCE_EXTENSIONS = {
    ".py", ".rs", ".ts", ".tsx", ".js", ".jsx",
    ".go", ".rb", ".java", ".kt", ".swift", ".c", ".h",
    ".cpp", ".hpp", ".zig", ".sh", ".bash", ".zsh",
    ".lua", ".ex", ".exs", ".clj", ".sql", ".toml", ".yaml", ".yml",
}

# Extensions that are clearly not source (skip for all checks).
SKIP_EXTENSIONS = {
    ".lock", ".sum", ".snap", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".ico", ".woff", ".woff2", ".ttf", ".eot", ".pdf", ".zip", ".tar",
    ".gz", ".br", ".wasm", ".min.js", ".min.css", ".map",
}

# Patterns indicating a file is generated (skip for quality checks).
GENERATED_PATTERNS = [
    re.compile(r"(?i)generated\b.*do not edit", re.IGNORECASE),
    re.compile(r"(?i)auto-?generated", re.IGNORECASE),
    re.compile(r"@generated"),
]

# Comment patterns by extension for first-breath detection.
COMMENT_STARTERS = {
    ".py":    (re.compile(r'^("""|\'\'\')'), re.compile(r"^\s*#")),
    ".rs":    (re.compile(r"^\s*//[!/]"), re.compile(r"^\s*//")),
    ".ts":    (re.compile(r"^\s*/\*\*"), re.compile(r"^\s*//")),
    ".tsx":   (re.compile(r"^\s*/\*\*"), re.compile(r"^\s*//")),
    ".js":    (re.compile(r"^\s*/\*\*"), re.compile(r"^\s*//")),
    ".jsx":   (re.compile(r"^\s*/\*\*"), re.compile(r"^\s*//")),
    ".go":    (re.compile(r"^\s*//"), re.compile(r"^\s*/\*")),
    ".rb":    (re.compile(r"^\s*#"),),
    ".sh":    (re.compile(r"^\s*#"),),
    ".bash":  (re.compile(r"^\s*#"),),
    ".zsh":   (re.compile(r"^\s*#"),),
    ".lua":   (re.compile(r"^\s*--"),),
    ".sql":   (re.compile(r"^\s*--"),),
    ".zig":   (re.compile(r"^\s*//[!/]"), re.compile(r"^\s*//")),
    ".c":     (re.compile(r"^\s*/\*"), re.compile(r"^\s*//")),
    ".h":     (re.compile(r"^\s*/\*"), re.compile(r"^\s*//")),
    ".cpp":   (re.compile(r"^\s*/\*"), re.compile(r"^\s*//")),
    ".hpp":   (re.compile(r"^\s*/\*"), re.compile(r"^\s*//")),
    ".java":  (re.compile(r"^\s*/\*\*"), re.compile(r"^\s*//")),
    ".kt":    (re.compile(r"^\s*/\*\*"), re.compile(r"^\s*//")),
    ".swift": (re.compile(r"^\s*///"), re.compile(r"^\s*//")),
    ".ex":    (re.compile(r'^\s*@moduledoc'), re.compile(r"^\s*#")),
    ".exs":   (re.compile(r"^\s*#"),),
}

BAD_MODULE_NAMES = {
    "utils", "util", "helpers", "helper", "common", "misc",
    "shared", "stuff", "base", "core", "general",
}

# Filenames that are idiomatic in their language (not bad names).
IDIOMATIC_FILENAMES = {"lib.rs", "mod.rs", "index.ts", "index.js", "__init__.py"}


def git_tracked_files(repo: Path) -> list[Path]:
    """Return all git-tracked files as Path objects relative to repo root."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Error: not a git repository: {repo}", file=sys.stderr)
        sys.exit(1)
    return [Path(f) for f in result.stdout.split("\0") if f]


def is_source_file(path: Path) -> bool:
    return path.suffix in SOURCE_EXTENSIONS


def is_generated(lines: list[str]) -> bool:
    """Check first 5 lines for generated-file markers."""
    header = "\n".join(lines[:5])
    return any(p.search(header) for p in GENERATED_PATTERNS)


def read_lines(repo: Path, path: Path) -> list[str] | None:
    """Read file lines, returning None on decode errors."""
    try:
        return (repo / path).read_text(encoding="utf-8", errors="strict").splitlines()
    except (UnicodeDecodeError, OSError):
        return None


# ── Principle 1: Self-documenting files ─────────────────────────────────────

def has_first_breath(lines: list[str], ext: str) -> bool:
    """Check if the first meaningful lines contain a comment or docstring."""
    patterns = COMMENT_STARTERS.get(ext, ())
    if not patterns:
        return True  # Can't check — don't penalise unknown languages.

    # Skip shebang, encoding declarations, blank lines, license headers.
    meaningful_start = 0
    for i, line in enumerate(lines[:20]):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#!") and i == 0:
            continue
        if stripped.startswith("# -*-") or stripped.startswith("# coding"):
            continue
        # License/copyright headers count — they tell you something.
        meaningful_start = i
        break

    # Check lines from meaningful_start through meaningful_start + 10.
    window = lines[meaningful_start:meaningful_start + 10]
    for line in window:
        stripped = line.strip()
        if not stripped:
            continue
        for pattern in patterns:
            if pattern.search(stripped):
                return True
        # If the first non-empty line isn't a comment, fail.
        return False

    return False


def check_module_names(source_files: list[Path]) -> list[str]:
    """Find source files with bad module names (utils, helpers, etc.)."""
    bad = []
    for f in source_files:
        if f.name in IDIOMATIC_FILENAMES:
            continue
        stem = f.stem.lower()
        if stem in BAD_MODULE_NAMES:
            bad.append(str(f))
    return bad


# ── Principle 3: Boundaries ─────────────────────────────────────────────────

CLAUDE_MD_SECTIONS = {
    "architecture": re.compile(r"(?i)^#+\s*.*\b(architecture|overview|structure)\b", re.MULTILINE),
    "module_map": re.compile(r"(?i)^#+\s*(module|directory|key (files|directories))", re.MULTILINE),
    "dependency_rules": re.compile(r"(?i)^#+\s*(dependenc|layer|import rules)", re.MULTILINE),
    "recipes": re.compile(r"(?i)(how to add|extension|recipe|adding a\b)", re.MULTILINE),
    "anti_patterns": re.compile(r"(?i)(don.t|do not|never|anti.?pattern|what not)", re.MULTILINE),
}


def assess_claude_md(repo: Path) -> dict:
    """Score CLAUDE.md + AGENTS.md quality against a section checklist.

    Scans both files and takes the union — sections found in either count.
    """
    combined_content = ""
    found_files = []
    for name in ("CLAUDE.md", "claude.md", "AGENTS.md"):
        path = repo / name
        if path.exists():
            content = path.read_text(encoding="utf-8", errors="replace")
            combined_content += "\n" + content
            found_files.append(name)

    if not found_files:
        return {"exists": False, "bytes": 0, "sections": {}, "score": "0/5", "files": []}

    sections_found = {
        section: bool(pattern.search(combined_content))
        for section, pattern in CLAUDE_MD_SECTIONS.items()
    }
    return {
        "exists": True,
        "bytes": len(combined_content),
        "sections": sections_found,
        "score": f"{sum(sections_found.values())}/{len(sections_found)}",
        "files": found_files,
    }


def check_boundary_artefacts(repo: Path) -> dict:
    """Check for key architectural artefacts."""
    artefacts = {}

    # CLAUDE.md / AGENTS.md
    for name in ("CLAUDE.md", "AGENTS.md"):
        path = repo / name
        artefacts[name] = "present" if path.exists() else "missing"

    # understanding.md
    understanding = repo / ".bon" / "understanding.md"
    artefacts["understanding.md"] = "present" if understanding.exists() else "missing"

    # Generated-files manifest
    found_manifest = False
    for candidate in ("generated-files.txt", "tools/generated-files.txt"):
        if (repo / candidate).exists():
            artefacts["generated_files_manifest"] = f"present ({candidate})"
            found_manifest = True
            break
    if not found_manifest:
        artefacts["generated_files_manifest"] = "missing"

    return artefacts


# ── Principle 5: Extension recipes ──────────────────────────────────────────

def check_extension_recipes(repo: Path) -> dict:
    """Check CLAUDE.md for extension recipe patterns."""
    for name in ("CLAUDE.md", "claude.md"):
        path = repo / name
        if path.exists():
            content = path.read_text(encoding="utf-8", errors="replace")
            recipe_patterns = [
                re.compile(r"(?i)how to add", re.MULTILINE),
                re.compile(r"(?i)^#+.*recipe", re.MULTILINE),
                re.compile(r"(?i)^#+.*\badding\b", re.MULTILINE),
                re.compile(r"(?i)^#+.*extension", re.MULTILINE),
                re.compile(r"(?i)(step \d|^\d+\.\s)", re.MULTILINE),
            ]
            matches = {p.pattern: bool(p.search(content)) for p in recipe_patterns}
            has_recipes = sum(matches.values()) >= 2
            return {"has_recipes": has_recipes, "signals": matches}
    return {"has_recipes": False, "signals": {}}


# ── Main analysis ───────────────────────────────────────────────────────────

def analyse(repo_path: str) -> dict:
    repo = Path(repo_path).resolve()
    all_files = git_tracked_files(repo)

    # Filter to source files.
    source_files = [f for f in all_files if is_source_file(f)]

    # Read all source files, skip generated.
    file_data: list[tuple[Path, list[str]]] = []
    generated_count = 0
    for f in source_files:
        lines = read_lines(repo, f)
        if lines is None:
            continue
        if is_generated(lines):
            generated_count += 1
            continue
        file_data.append((f, lines))

    total_source = len(file_data)

    # ── Principle 4: File sizes ──
    sizes = [(str(f), len(lines)) for f, lines in file_data]
    sizes.sort(key=lambda x: x[1], reverse=True)
    line_counts = [s[1] for s in sizes]

    if line_counts:
        line_counts_sorted = sorted(line_counts)
        p50 = line_counts_sorted[len(line_counts_sorted) // 2]
        p90_idx = int(len(line_counts_sorted) * 0.9)
        p90 = line_counts_sorted[min(p90_idx, len(line_counts_sorted) - 1)]
        max_size = line_counts_sorted[-1]
        over_500 = sum(1 for c in line_counts if c > 500)
        over_1000 = sum(1 for c in line_counts if c > 1000)
    else:
        p50 = p90 = max_size = over_500 = over_1000 = 0

    largest_files = sizes[:5]

    # ── Principle 1: First breath ──
    breath_results = []
    for f, lines in file_data:
        # Skip tiny files (< 10 lines), __init__.py, config files.
        if len(lines) < 10:
            continue
        if f.name == "__init__.py":
            continue
        if f.suffix in (".toml", ".yaml", ".yml"):
            continue
        has_breath = has_first_breath(lines, f.suffix)
        if not has_breath:
            breath_results.append(str(f))

    breath_eligible = sum(
        1 for f, lines in file_data
        if len(lines) >= 10
        and f.name != "__init__.py"
        and f.suffix not in (".toml", ".yaml", ".yml")
    )
    breath_passing = breath_eligible - len(breath_results)

    # ── Principle 1: Bad module names ──
    bad_names = check_module_names(source_files)

    # ── Principle 2: Pattern signals ──
    # Count test file patterns (do they use a consistent framework?).
    test_frameworks: Counter[str] = Counter()
    for f, lines in file_data:
        header = "\n".join(lines[:30])
        if "test" in f.stem.lower() or "test" in str(f.parent).lower():
            if "pytest" in header or "def test_" in header:
                test_frameworks["pytest"] += 1
            elif "unittest" in header or "TestCase" in header:
                test_frameworks["unittest"] += 1
            elif "describe(" in header or "it(" in header:
                test_frameworks["jest/mocha"] += 1
            elif "#[test]" in header or "#[cfg(test)]" in header:
                test_frameworks["rust-test"] += 1
            elif "func Test" in header:
                test_frameworks["go-test"] += 1

    # Count error handling patterns.
    error_patterns: Counter[str] = Counter()
    for f, lines in file_data:
        content = "\n".join(lines)
        if "raise " in content or "except " in content:
            error_patterns["exceptions"] += 1
        if "Result<" in content or "-> Result" in content:
            error_patterns["result-type"] += 1
        if "if err != nil" in content:
            error_patterns["go-errors"] += 1

    # ── Principle 3: Boundaries ──
    artefacts = check_boundary_artefacts(repo)
    claude_md = assess_claude_md(repo)

    # ── Principle 5: Recipes ──
    recipes = check_extension_recipes(repo)

    # ── Extension counts by type ──
    ext_counts: Counter[str] = Counter()
    for f in source_files:
        ext_counts[f.suffix] += 1

    return {
        "repo": str(repo),
        "total_tracked_files": len(all_files),
        "total_source_files": total_source,
        "generated_files_skipped": generated_count,
        "language_breakdown": dict(ext_counts.most_common()),
        "file_sizes": {
            "p50": p50,
            "p90": p90,
            "max": max_size,
            "largest": largest_files[:5],
            "over_500": over_500,
            "over_1000": over_1000,
            "total": total_source,
        },
        "first_breath": {
            "eligible": breath_eligible,
            "passing": breath_passing,
            "score": f"{breath_passing}/{breath_eligible}" if breath_eligible else "n/a",
            "percent": round(100 * breath_passing / breath_eligible, 1) if breath_eligible else 0,
            "missing": breath_results[:15],
            "bad_module_names": bad_names,
        },
        "boundaries": {
            "artefacts": artefacts,
            "claude_md": claude_md,
        },
        "pattern_signals": {
            "test_frameworks": dict(test_frameworks),
            "error_patterns": dict(error_patterns),
        },
        "extension_recipes": recipes,
    }


def format_report(data: dict) -> str:
    """Format metrics as a structured text report for agent consumption."""
    lines = []
    lines.append(f"# Toise Metrics: {data['repo']}")
    lines.append(f"Tracked files: {data['total_tracked_files']}  "
                 f"Source files: {data['total_source_files']}  "
                 f"Generated (skipped): {data['generated_files_skipped']}")
    lines.append("")

    # Language breakdown.
    lines.append("## Languages")
    for ext, count in sorted(data["language_breakdown"].items(), key=lambda x: -x[1]):
        lines.append(f"  {ext:8s} {count:4d}")
    lines.append("")

    # Principle 4: File sizes.
    fs = data["file_sizes"]
    lines.append("## File Size Distribution (Principle 4)")
    lines.append(f"  p50: {fs['p50']} lines")
    lines.append(f"  p90: {fs['p90']} lines")
    lines.append(f"  max: {fs['max']} lines")
    lines.append(f"  over 500 lines: {fs['over_500']}/{fs['total']}")
    lines.append(f"  over 1000 lines: {fs['over_1000']}/{fs['total']}")
    if fs["largest"]:
        lines.append("  largest files:")
        for name, size in fs["largest"]:
            lines.append(f"    {size:5d}  {name}")
    lines.append("")

    # Principle 1: First breath.
    fb = data["first_breath"]
    lines.append("## First Breath Score (Principle 1)")
    lines.append(f"  score: {fb['score']} ({fb['percent']}%)")
    if fb["missing"]:
        lines.append(f"  files missing first breath ({len(fb['missing'])} shown):")
        for f in fb["missing"]:
            lines.append(f"    {f}")
    if fb["bad_module_names"]:
        lines.append(f"  bad module names:")
        for f in fb["bad_module_names"]:
            lines.append(f"    {f}")
    lines.append("")

    # Principle 3: Boundaries.
    b = data["boundaries"]
    lines.append("## Boundary Artefacts (Principle 3)")
    for name, status in b["artefacts"].items():
        lines.append(f"  {name}: {status}")
    cm = b["claude_md"]
    if cm["exists"]:
        lines.append(f"  CLAUDE.md quality: {cm['score']}")
        for section, found in cm["sections"].items():
            marker = "+" if found else "-"
            lines.append(f"    {marker} {section}")
    lines.append("")

    # Principle 2: Pattern signals.
    ps = data["pattern_signals"]
    lines.append("## Pattern Signals (Principle 2)")
    if ps["test_frameworks"]:
        lines.append("  test frameworks: " + ", ".join(
            f"{k} ({v})" for k, v in ps["test_frameworks"].items()
        ))
    if ps["error_patterns"]:
        lines.append("  error handling: " + ", ".join(
            f"{k} ({v})" for k, v in ps["error_patterns"].items()
        ))
    if not ps["test_frameworks"] and not ps["error_patterns"]:
        lines.append("  (insufficient signal for automated pattern detection)")
    lines.append("")

    # Principle 5: Extension recipes.
    er = data["extension_recipes"]
    lines.append("## Extension Recipes (Principle 5)")
    lines.append(f"  has recipes: {'yes' if er['has_recipes'] else 'no'}")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "."
    data = analyse(repo_path)

    if "--json" in sys.argv:
        print(json.dumps(data, indent=2))
    else:
        print(format_report(data))

#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""
Skill Linter - Comprehensive validation for Claude Code skills.

Checks:
- YAML frontmatter validity
- Name/directory match
- Description patterns (BEFORE/MANDATORY/FIRST)
- Line count (<500)
- Reference depth (one level)
- Required sections

Usage:
    lint_skill.py <skill-path>
    lint_skill.py <skill-path> --json
    lint_skill.py <skill-path> --fix  # Auto-fix where possible
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class Check:
    """A single validation check result."""
    name: str
    passed: bool
    message: str
    severity: str = "error"  # error, warning, info
    auto_fixable: bool = False
    suggestion: Optional[str] = None


@dataclass
class LintResult:
    """Complete lint result for a skill."""
    skill_path: str
    skill_name: str
    valid: bool
    checks: list[Check] = field(default_factory=list)
    errors: int = 0
    warnings: int = 0
    score: int = 100  # Start at 100, deduct for issues


def extract_frontmatter(content: str) -> tuple[Optional[dict], Optional[str]]:
    """Extract YAML frontmatter from SKILL.md content."""
    if not content.startswith('---'):
        return None, "No YAML frontmatter found (must start with ---)"

    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None, "Invalid frontmatter format (missing closing ---)"

    try:
        frontmatter = yaml.safe_load(match.group(1))
        if not isinstance(frontmatter, dict):
            return None, "Frontmatter must be a YAML dictionary"
        return frontmatter, None
    except yaml.YAMLError as e:
        return None, f"Invalid YAML: {e}"


def check_frontmatter_fields(frontmatter: dict) -> list[Check]:
    """Validate frontmatter has required fields and no extras."""
    checks = []

    ALLOWED_FIELDS = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'user-invocable'}

    # Required fields
    if 'name' not in frontmatter:
        checks.append(Check(
            name="frontmatter_name",
            passed=False,
            message="Missing required 'name' field",
            severity="error"
        ))

    if 'description' not in frontmatter:
        checks.append(Check(
            name="frontmatter_description",
            passed=False,
            message="Missing required 'description' field",
            severity="error"
        ))

    # Unexpected fields
    unexpected = set(frontmatter.keys()) - ALLOWED_FIELDS
    if unexpected:
        checks.append(Check(
            name="frontmatter_extra_fields",
            passed=False,
            message=f"Unexpected fields: {', '.join(sorted(unexpected))}",
            severity="warning",
            suggestion=f"Remove these fields or move to 'metadata' section"
        ))
    else:
        checks.append(Check(
            name="frontmatter_fields",
            passed=True,
            message="Frontmatter fields valid"
        ))

    return checks


def check_name(frontmatter: dict, skill_dir: Path) -> list[Check]:
    """Validate skill name conventions."""
    checks = []
    name = frontmatter.get('name', '')

    if not isinstance(name, str):
        checks.append(Check(
            name="name_type",
            passed=False,
            message=f"Name must be string, got {type(name).__name__}",
            severity="error"
        ))
        return checks

    name = name.strip()

    # Kebab-case check
    if not re.match(r'^[a-z0-9-]+$', name):
        checks.append(Check(
            name="name_kebab_case",
            passed=False,
            message=f"Name '{name}' must be kebab-case (lowercase, digits, hyphens)",
            severity="error",
            suggestion=f"Use: {name.lower().replace(' ', '-').replace('_', '-')}"
        ))
    else:
        checks.append(Check(
            name="name_kebab_case",
            passed=True,
            message="Name is valid kebab-case"
        ))

    # No leading/trailing/consecutive hyphens
    if name.startswith('-') or name.endswith('-') or '--' in name:
        checks.append(Check(
            name="name_hyphens",
            passed=False,
            message="Name cannot start/end with hyphen or have consecutive hyphens",
            severity="error"
        ))

    # Length check
    if len(name) > 64:
        checks.append(Check(
            name="name_length",
            passed=False,
            message=f"Name too long ({len(name)} chars, max 64)",
            severity="error"
        ))

    # Directory match
    if name != skill_dir.name:
        checks.append(Check(
            name="name_dir_match",
            passed=False,
            message=f"Name '{name}' doesn't match directory '{skill_dir.name}'",
            severity="error",
            auto_fixable=True,
            suggestion=f"Rename directory to '{name}' or change name to '{skill_dir.name}'"
        ))
    else:
        checks.append(Check(
            name="name_dir_match",
            passed=True,
            message="Name matches directory"
        ))

    # Gerund/capability form check (heuristic)
    GOOD_SUFFIXES = ('ing', 'ity', 'ment', 'tion', 'ness', 'check', 'forge', 'fluency',
                     'ist', 'er', 'or', 'yst', 'ant')  # Role nouns (analyst, builder, etc.)
    GOOD_PATTERNS = ('test-driven', 'root-cause', 'crash-recovery')

    if any(name.endswith(s) for s in GOOD_SUFFIXES) or any(p in name for p in GOOD_PATTERNS):
        checks.append(Check(
            name="name_form",
            passed=True,
            message="Name uses gerund/capability form"
        ))
    else:
        checks.append(Check(
            name="name_form",
            passed=True,  # Warning only
            message=f"Consider gerund form (e.g., '{name}-ing' or similar capability noun)",
            severity="info"
        ))

    return checks


def check_description(frontmatter: dict) -> list[Check]:
    """Validate description content and patterns."""
    checks = []
    desc = frontmatter.get('description', '')

    if not isinstance(desc, str):
        checks.append(Check(
            name="description_type",
            passed=False,
            message=f"Description must be string, got {type(desc).__name__}",
            severity="error"
        ))
        return checks

    desc = desc.strip()

    # Length check
    if len(desc) > 1024:
        checks.append(Check(
            name="description_length",
            passed=False,
            message=f"Description too long ({len(desc)} chars, max 1024)",
            severity="error"
        ))
    elif len(desc) < 50:
        checks.append(Check(
            name="description_length",
            passed=False,
            message=f"Description too short ({len(desc)} chars, aim for 100-500)",
            severity="warning"
        ))
    else:
        checks.append(Check(
            name="description_length",
            passed=True,
            message=f"Description length OK ({len(desc)} chars)"
        ))

    # Angle brackets
    if '<' in desc or '>' in desc:
        checks.append(Check(
            name="description_brackets",
            passed=False,
            message="Description cannot contain angle brackets (< or >)",
            severity="error"
        ))

    # Third person check (should NOT start with "Use" or "Invoke")
    first_word = desc.split()[0] if desc else ""
    if first_word.lower() in ('use', 'invoke', 'call', 'run'):
        checks.append(Check(
            name="description_third_person",
            passed=False,
            message=f"Description starts with '{first_word}' - use third person instead",
            severity="warning",
            suggestion="Start with action verb: 'Orchestrates', 'Validates', 'Guides'"
        ))

    # Timing patterns (CSO)
    timing_patterns = ['before', 'first', 'mandatory', 'after', 'when']
    has_timing = any(p in desc.lower() for p in timing_patterns)
    if has_timing:
        checks.append(Check(
            name="description_timing",
            passed=True,
            message="Description includes timing condition"
        ))
    else:
        checks.append(Check(
            name="description_timing",
            passed=False,
            message="No timing condition (BEFORE/FIRST/MANDATORY/WHEN)",
            severity="warning",
            suggestion="Add: 'Use BEFORE...', 'Invoke FIRST when...'"
        ))

    # Trigger phrases in quotes
    trigger_phrases = re.findall(r"'[^']+?'", desc)
    if trigger_phrases:
        checks.append(Check(
            name="description_triggers",
            passed=True,
            message=f"Has {len(trigger_phrases)} trigger phrase(s) in quotes"
        ))
    else:
        checks.append(Check(
            name="description_triggers",
            passed=False,
            message="No trigger phrases in quotes",
            severity="warning",
            suggestion="Add: Triggers on 'phrase1', 'phrase2'"
        ))

    # (user) tag check
    if desc.endswith('(user)'):
        checks.append(Check(
            name="description_user_tag",
            passed=True,
            message="Has (user) tag"
        ))
    else:
        checks.append(Check(
            name="description_user_tag",
            passed=False,
            message="Missing (user) tag for user-defined skills",
            severity="info",
            auto_fixable=True,
            suggestion="Add ' (user)' at end of description"
        ))

    # Vague pattern detection
    # "Provides" is only vague when not followed by specific content
    vague_patterns = [
        (r'\bhelps? with\b', "'Helps with' is vague"),
        (r'\bassists?\b', "'Assists' is vague"),
        (r'\bprovides?\s+(?:a\s+)?(?:way|tool|method)\b', "'Provides a way/tool/method' is vague - name the thing"),
        (r'\bcan be used\b', "Passive voice - use active"),
    ]

    for pattern, msg in vague_patterns:
        if re.search(pattern, desc, re.IGNORECASE):
            checks.append(Check(
                name="description_vague",
                passed=False,
                message=msg,
                severity="warning"
            ))

    return checks


def check_structure(skill_dir: Path, content: str) -> list[Check]:
    """Check SKILL.md structure and organization."""
    checks = []
    lines = content.split('\n')

    # Line count
    if len(lines) > 500:
        checks.append(Check(
            name="line_count",
            passed=False,
            message=f"SKILL.md has {len(lines)} lines (max 500)",
            severity="warning",
            suggestion="Split detailed content into references/"
        ))
    else:
        checks.append(Check(
            name="line_count",
            passed=True,
            message=f"SKILL.md has {len(lines)} lines"
        ))

    # Check for key sections
    section_patterns = {
        'when_to_use': r'^##\s+when\s+to\s+use',
        'when_not_to_use': r'^##\s+when\s+not\s+to\s+use',
        'anti_patterns': r'^##\s+anti[- ]?patterns?',
    }

    # Anti-patterns are less important for methodology/reference skills
    # (those with references/ dirs — they're cookbooks, not process gates)
    has_references = (skill_dir / 'references').exists()

    for section, pattern in section_patterns.items():
        found = any(re.match(pattern, line, re.IGNORECASE) for line in lines)
        if not found and section == 'anti_patterns' and has_references:
            severity = "info"  # Downgrade for reference-heavy skills
        else:
            severity = "info" if found else "warning"
        checks.append(Check(
            name=f"section_{section}",
            passed=found,
            message=f"{'Has' if found else 'Missing'} '{section.replace('_', ' ')}' section",
            severity=severity
        ))

    # Reference depth check
    refs_dir = skill_dir / 'references'
    if refs_dir.exists():
        nested = list(refs_dir.glob('**/*.md'))
        too_deep = [f for f in nested if len(f.relative_to(refs_dir).parts) > 1]
        if too_deep:
            checks.append(Check(
                name="reference_depth",
                passed=False,
                message=f"Nested references found: {[str(f.relative_to(refs_dir)) for f in too_deep[:3]]}",
                severity="warning",
                suggestion="Keep references one level deep from SKILL.md"
            ))
        else:
            checks.append(Check(
                name="reference_depth",
                passed=True,
                message="Reference files are one level deep"
            ))

    return checks


def check_resources(skill_dir: Path) -> list[Check]:
    """Check scripts, references, assets organization."""
    checks = []

    # Scripts should be executable
    scripts_dir = skill_dir / 'scripts'
    if scripts_dir.exists():
        py_files = list(scripts_dir.glob('*.py'))
        for script in py_files:
            if not script.stat().st_mode & 0o111:
                checks.append(Check(
                    name="script_executable",
                    passed=False,
                    message=f"{script.name} is not executable",
                    severity="warning",
                    auto_fixable=True,
                    suggestion=f"chmod +x {script}"
                ))

    # Check for example files that should be deleted
    example_patterns = ['example.py', 'example_asset.txt', 'api_reference.md']
    for pattern in example_patterns:
        found = list(skill_dir.rglob(pattern))
        for f in found:
            # Check if it's still template content
            try:
                content = f.read_text()
                if 'TODO' in content or 'placeholder' in content.lower():
                    checks.append(Check(
                        name="template_files",
                        passed=False,
                        message=f"Template file not customized: {f.relative_to(skill_dir)}",
                        severity="warning",
                        suggestion="Customize or delete template files"
                    ))
            except:
                pass

    return checks


def detect_alias(content: str, frontmatter: Optional[dict]) -> Optional[str]:
    """Detect if skill is an alias and return target skill name."""
    # Check description for "Alias for X"
    if frontmatter:
        desc = frontmatter.get('description', '')
        if 'alias' in desc.lower():
            # Try to extract target from "Alias for close" pattern
            match = re.search(r'[Aa]lias\s+for\s+([a-z0-9-]+)', desc)
            if match:
                return match.group(1)

    # Check body for "Immediately invoke the `skill-name` skill"
    # Must be "Immediately" to avoid matching composition mentions like "also invoke"
    match = re.search(r'[Ii]mmediately\s+invoke\s+the\s+`([a-z0-9-]+)`\s+skill', content)
    if match:
        return match.group(1)

    return None


def find_skill_path(skill_name: str, search_paths: list[Path]) -> Optional[Path]:
    """Find skill directory by name in common locations."""
    for base in search_paths:
        candidate = base / skill_name
        if candidate.exists() and (candidate / 'SKILL.md').exists():
            return candidate
    return None


def lint_skill(skill_path: Path, follow_aliases: bool = True, _alias_chain: list[str] = None) -> LintResult:
    """Run all checks on a skill.

    Args:
        skill_path: Path to skill directory
        follow_aliases: If True, detect aliases and lint target skill instead
        _alias_chain: Internal tracking to prevent infinite loops
    """
    if _alias_chain is None:
        _alias_chain = []

    result = LintResult(
        skill_path=str(skill_path),
        skill_name=skill_path.name,
        valid=True
    )

    # Check SKILL.md exists
    skill_md = skill_path / 'SKILL.md'
    if not skill_md.exists():
        result.checks.append(Check(
            name="skill_md_exists",
            passed=False,
            message="SKILL.md not found",
            severity="error"
        ))
        result.valid = False
        result.errors = 1
        return result

    result.checks.append(Check(
        name="skill_md_exists",
        passed=True,
        message="SKILL.md found"
    ))

    # Read content
    try:
        content = skill_md.read_text()
    except Exception as e:
        result.checks.append(Check(
            name="skill_md_readable",
            passed=False,
            message=f"Cannot read SKILL.md: {e}",
            severity="error"
        ))
        result.valid = False
        result.errors = 1
        return result

    # Check for alias and follow if enabled
    if follow_aliases:
        # Quick frontmatter parse just for alias detection
        fm, _ = extract_frontmatter(content)
        target_name = detect_alias(content, fm)

        if target_name:
            # Prevent infinite loops
            if target_name in _alias_chain:
                result.checks.append(Check(
                    name="alias_loop",
                    passed=False,
                    message=f"Alias loop detected: {' -> '.join(_alias_chain + [target_name])}",
                    severity="error"
                ))
                result.valid = False
                result.errors = 1
                return result

            # Find target skill
            search_paths = [
                skill_path.parent,  # Same directory (skills/)
                Path.home() / '.claude' / 'skills',  # Global skills
            ]
            target_path = find_skill_path(target_name, search_paths)

            if target_path:
                # Record alias relationship
                result.checks.append(Check(
                    name="alias_detected",
                    passed=True,
                    message=f"Alias for '{target_name}' — following to target skill",
                    severity="info"
                ))

                # Lint the target instead
                target_result = lint_skill(
                    target_path,
                    follow_aliases=True,
                    _alias_chain=_alias_chain + [skill_path.name]
                )

                # Merge results but keep alias context
                result.skill_path = f"{skill_path} -> {target_result.skill_path}"
                result.skill_name = f"{skill_path.name} -> {target_result.skill_name}"
                result.checks.extend(target_result.checks)
                result.errors = target_result.errors
                result.warnings = target_result.warnings
                result.score = target_result.score
                result.valid = target_result.valid
                return result
            else:
                result.checks.append(Check(
                    name="alias_target_missing",
                    passed=False,
                    message=f"Alias target '{target_name}' not found",
                    severity="error"
                ))
                result.valid = False
                result.errors = 1
                return result

    # Extract and validate frontmatter
    frontmatter, error = extract_frontmatter(content)
    if error:
        result.checks.append(Check(
            name="frontmatter_valid",
            passed=False,
            message=error,
            severity="error"
        ))
        result.valid = False
    else:
        result.checks.append(Check(
            name="frontmatter_valid",
            passed=True,
            message="Frontmatter is valid YAML"
        ))

        # Run checks that need frontmatter
        result.checks.extend(check_frontmatter_fields(frontmatter))
        result.checks.extend(check_name(frontmatter, skill_path))
        result.checks.extend(check_description(frontmatter))

    # Structure checks
    result.checks.extend(check_structure(skill_path, content))
    result.checks.extend(check_resources(skill_path))

    # Calculate results
    for check in result.checks:
        if not check.passed:
            if check.severity == "error":
                result.errors += 1
                result.score -= 15
            elif check.severity == "warning":
                result.warnings += 1
                result.score -= 5
            else:
                result.score -= 1

    result.score = max(0, result.score)
    result.valid = result.errors == 0

    return result


def format_result(result: LintResult, format_type: str = "text") -> str:
    """Format lint result for output."""
    if format_type == "json":
        return json.dumps({
            "skill_path": result.skill_path,
            "skill_name": result.skill_name,
            "valid": result.valid,
            "score": result.score,
            "errors": result.errors,
            "warnings": result.warnings,
            "checks": [asdict(c) for c in result.checks]
        }, indent=2)

    # Text format
    lines = [
        f"\n{'='*60}",
        f"LINT: {result.skill_name}",
        f"{'='*60}",
        f"Path: {result.skill_path}",
        f"Score: {result.score}/100",
        f"Status: {'PASS' if result.valid else 'FAIL'}",
        f"Errors: {result.errors}  Warnings: {result.warnings}",
    ]

    # Group by severity
    errors = [c for c in result.checks if not c.passed and c.severity == "error"]
    warnings = [c for c in result.checks if not c.passed and c.severity == "warning"]
    infos = [c for c in result.checks if not c.passed and c.severity == "info"]
    passed = [c for c in result.checks if c.passed]

    if errors:
        lines.append("\n--- ERRORS (must fix) ---")
        for c in errors:
            lines.append(f"  [{c.name}] {c.message}")
            if c.suggestion:
                lines.append(f"    -> {c.suggestion}")

    if warnings:
        lines.append("\n--- WARNINGS (should fix) ---")
        for c in warnings:
            lines.append(f"  [{c.name}] {c.message}")
            if c.suggestion:
                lines.append(f"    -> {c.suggestion}")

    if infos:
        lines.append("\n--- INFO ---")
        for c in infos:
            lines.append(f"  [{c.name}] {c.message}")

    if passed and format_type != "brief":
        lines.append(f"\n--- PASSED ({len(passed)} checks) ---")
        for c in passed:
            lines.append(f"  [{c.name}] {c.message}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Lint Claude Code skills for quality issues"
    )
    parser.add_argument("skill_path", type=Path, help="Path to skill directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--brief", action="store_true", help="Show only failures")
    parser.add_argument("--no-follow-aliases", action="store_true",
                        help="Don't follow alias skills to their targets")
    args = parser.parse_args()

    skill_path = args.skill_path.expanduser().resolve()

    if not skill_path.exists():
        print(f"Error: Path does not exist: {skill_path}")
        sys.exit(1)

    if not skill_path.is_dir():
        print(f"Error: Path is not a directory: {skill_path}")
        sys.exit(1)

    result = lint_skill(skill_path, follow_aliases=not args.no_follow_aliases)

    format_type = "json" if args.json else ("brief" if args.brief else "text")
    print(format_result(result, format_type))

    sys.exit(0 if result.valid else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""
CSO (Claude Search Optimization) Description Scorer

Scores skill descriptions 0-100 based on discovery effectiveness.
Higher scores = Claude more likely to invoke the skill when appropriate.

Scoring dimensions:
- Timing gates (BEFORE, FIRST, MANDATORY)
- Trigger phrases in quotes
- Method/value preview
- Specificity vs vagueness
- Third-person action verbs

Usage:
    score_description.py <skill-path>
    score_description.py <skill-path> --json
    score_description.py --text "description text"
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
class ScoreComponent:
    """A single scoring dimension."""
    name: str
    score: int  # Points earned
    max_points: int  # Maximum possible
    details: str
    suggestions: list[str] = field(default_factory=list)


@dataclass
class CSOScore:
    """Complete CSO score for a description."""
    description: str
    total_score: int
    max_score: int
    grade: str  # A, B, C, D, F
    components: list[ScoreComponent] = field(default_factory=list)
    overall_suggestions: list[str] = field(default_factory=list)


def score_timing_gates(desc: str) -> ScoreComponent:
    """Score timing-related language that creates invocation gates."""
    max_points = 25
    score = 0
    details = []
    suggestions = []

    # Strong gates (highest value)
    strong_gates = {
        'mandatory': 10,
        'must': 8,
        'required': 8,
        'before': 7,
        'first': 7,
        'always': 5,
    }

    # Moderate gates
    moderate_gates = {
        'after': 4,
        'when': 4,
        'during': 3,
        'triggers on': 5,
    }

    desc_lower = desc.lower()

    found_strong = []
    found_moderate = []

    for gate, points in strong_gates.items():
        if gate in desc_lower:
            found_strong.append(gate)
            score += points

    for gate, points in moderate_gates.items():
        if gate in desc_lower:
            found_moderate.append(gate)
            score += points

    score = min(score, max_points)  # Cap at max

    if found_strong:
        details.append(f"Strong gates: {', '.join(found_strong)}")
    if found_moderate:
        details.append(f"Moderate gates: {', '.join(found_moderate)}")

    if not found_strong and not found_moderate:
        details.append("No timing gates found")
        suggestions.append("Add: 'MANDATORY gate before...', 'Invoke FIRST when...', 'Use BEFORE...'")
    elif not found_strong:
        suggestions.append("Consider adding stronger gate: 'MANDATORY', 'BEFORE', 'FIRST'")

    return ScoreComponent(
        name="timing_gates",
        score=score,
        max_points=max_points,
        details="; ".join(details) if details else "No gates found",
        suggestions=suggestions
    )


def score_trigger_phrases(desc: str) -> ScoreComponent:
    """Score explicit trigger phrases in quotes."""
    max_points = 20
    score = 0
    details = []
    suggestions = []

    # Find phrases in single quotes
    single_quoted = re.findall(r"'([^']+)'", desc)
    # Find phrases in double quotes (but not YAML strings)
    double_quoted = re.findall(r'"([^"]+)"', desc)

    all_triggers = single_quoted + double_quoted

    if all_triggers:
        # Filter out likely non-trigger content
        real_triggers = [t for t in all_triggers if len(t) < 50 and not t.startswith('http')]

        if real_triggers:
            # Score: 5 points per trigger, up to 4 triggers
            score = min(len(real_triggers) * 5, max_points)
            details.append(f"{len(real_triggers)} trigger(s): {', '.join(real_triggers[:4])}")
        else:
            details.append("Quoted text found but no trigger phrases")
            suggestions.append("Add natural language triggers: 'check this', 'validate skill'")
    else:
        details.append("No trigger phrases in quotes")
        suggestions.append("Add: Triggers on 'phrase1', 'phrase2', 'phrase3'")

    return ScoreComponent(
        name="trigger_phrases",
        score=score,
        max_points=max_points,
        details="; ".join(details),
        suggestions=suggestions
    )


def score_method_preview(desc: str) -> ScoreComponent:
    """Score whether description previews the method/approach."""
    max_points = 15
    score = 0
    details = []
    suggestions = []

    # Method indicators
    method_patterns = [
        (r'\d+-step', 5, "numbered steps"),
        (r'\d+-phase', 5, "numbered phases"),
        (r'framework', 4, "framework"),
        (r'workflow', 4, "workflow"),
        (r'checklist', 4, "checklist"),
        (r'process', 3, "process"),
        (r'pattern', 3, "pattern"),
        (r'approach', 3, "approach"),
        (r'method', 3, "method"),
        (r'template', 3, "template"),
    ]

    # Value indicators (what user gets)
    value_patterns = [
        (r'ensures?', 4, "ensures outcome"),
        (r'prevents?', 4, "prevents problem"),
        (r'validates?', 3, "validates"),
        (r'guides?', 2, "guides"),
        (r'provides?', 2, "provides"),
    ]

    found_methods = []
    found_values = []

    for pattern, points, label in method_patterns:
        if re.search(pattern, desc, re.IGNORECASE):
            found_methods.append(label)
            score += points

    for pattern, points, label in value_patterns:
        if re.search(pattern, desc, re.IGNORECASE):
            found_values.append(label)
            score += points

    score = min(score, max_points)

    if found_methods:
        details.append(f"Method: {', '.join(found_methods[:3])}")
    if found_values:
        details.append(f"Value: {', '.join(found_values[:2])}")

    if not found_methods and not found_values:
        details.append("No method or value preview")
        suggestions.append("Add: '4-step process that ensures X', 'workflow for Y'")
    elif not found_methods:
        suggestions.append("Consider describing the method: 'uses X-step process'")
    elif not found_values:
        suggestions.append("Add value statement: 'ensures X', 'prevents Y'")

    return ScoreComponent(
        name="method_preview",
        score=score,
        max_points=max_points,
        details="; ".join(details) if details else "No preview",
        suggestions=suggestions
    )


def score_specificity(desc: str) -> ScoreComponent:
    """Score specificity vs vagueness."""
    max_points = 20
    score = max_points  # Start at max, deduct for vague patterns
    details = []
    suggestions = []

    # Vague patterns (deduct points)
    vague_patterns = [
        (r'\bhelps? with\b', -5, "'helps with' is vague"),
        (r'\bassists?\b', -4, "'assists' is passive"),
        (r'\bcan be used\b', -5, "passive voice"),
        (r'\bmay be\b', -3, "uncertain language"),
        (r'\bvarious\b', -3, "'various' is vague"),
        (r'\bgeneral\b', -3, "'general' lacks specificity"),
        (r'\bsimply\b', -2, "'simply' adds nothing"),
        (r'\bjust\b', -2, "'just' minimizes value"),
        (r'\bbasically\b', -2, "'basically' is filler"),
    ]

    # Specific patterns (bonus points)
    specific_patterns = [
        (r'\b\d+\b', 2, "includes numbers"),
        (r'\([^)]+\)', 2, "has parenthetical detail"),
        (r':', 1, "uses colon for structure"),
    ]

    found_vague = []
    found_specific = []

    for pattern, points, label in vague_patterns:
        if re.search(pattern, desc, re.IGNORECASE):
            found_vague.append(label)
            score += points  # points are negative

    for pattern, points, label in specific_patterns:
        if re.search(pattern, desc):
            found_specific.append(label)
            score += points

    score = max(0, min(score, max_points))

    if found_vague:
        details.append(f"Vague: {len(found_vague)} pattern(s)")
        for v in found_vague[:2]:
            suggestions.append(f"Remove or replace: {v}")
    if found_specific:
        details.append(f"Specific: {', '.join(found_specific)}")

    if not found_vague and not found_specific:
        details.append("Neutral specificity")

    return ScoreComponent(
        name="specificity",
        score=score,
        max_points=max_points,
        details="; ".join(details) if details else "No patterns found",
        suggestions=suggestions
    )


def score_action_verbs(desc: str) -> ScoreComponent:
    """Score use of strong third-person action verbs."""
    max_points = 10
    score = 0
    details = []
    suggestions = []

    # Strong third-person verbs (best for discovery)
    strong_verbs = [
        'orchestrates', 'validates', 'guides', 'tracks', 'manages',
        'analyzes', 'transforms', 'generates', 'synthesizes', 'integrates',
        'coordinates', 'calibrates', 'enforces', 'automates'
    ]

    # Weak/imperative verbs (Claude might not invoke)
    weak_starters = ['use', 'invoke', 'call', 'run', 'apply', 'help']

    first_word = desc.split()[0].lower() if desc else ""

    # Check first word — domain-noun openers (e.g. "BigQuery data analysis —") are
    # valid for methodology/reference skills, scored same as strong verbs
    has_dash_separator = '—' in desc[:80] or ' - ' in desc[:80]

    if first_word in weak_starters:
        details.append(f"Starts with weak verb '{first_word}'")
        suggestions.append(f"Change '{first_word.capitalize()}...' to third-person: 'Orchestrates...', 'Validates...'")
    elif any(desc.lower().startswith(v) for v in strong_verbs):
        score += 7
        details.append("Starts with strong third-person verb")
    elif has_dash_separator:
        score += 5
        details.append("Domain-noun opener with qualifier")
    else:
        details.append("Neutral opening")
        score += 3

    # Check for strong verbs anywhere
    strong_found = [v for v in strong_verbs if v in desc.lower()]
    if strong_found:
        score += min(len(strong_found) * 2, 5)
        details.append(f"Strong verbs: {', '.join(strong_found[:3])}")

    score = min(score, max_points)

    return ScoreComponent(
        name="action_verbs",
        score=score,
        max_points=max_points,
        details="; ".join(details) if details else "No strong verbs",
        suggestions=suggestions
    )


def score_length(desc: str) -> ScoreComponent:
    """Score description length (not too short, not too long)."""
    max_points = 10
    length = len(desc)
    details = []
    suggestions = []

    if length < 50:
        score = 2
        details.append(f"Too short ({length} chars)")
        suggestions.append("Expand to 100-500 characters with triggers and method preview")
    elif length < 100:
        score = 5
        details.append(f"Short ({length} chars)")
        suggestions.append("Consider adding more trigger phrases or method details")
    elif length <= 500:
        score = 10
        details.append(f"Good length ({length} chars)")
    elif length <= 800:
        score = 7
        details.append(f"Long ({length} chars)")
        suggestions.append("Consider trimming - focus on most important triggers")
    else:
        score = 4
        details.append(f"Too long ({length} chars)")
        suggestions.append("Trim to under 500 chars - prioritize timing gates and triggers")

    return ScoreComponent(
        name="length",
        score=score,
        max_points=max_points,
        details=details[0],
        suggestions=suggestions
    )


def calculate_grade(score: int, max_score: int) -> str:
    """Calculate letter grade from score."""
    pct = (score / max_score) * 100
    if pct >= 90:
        return "A"
    elif pct >= 80:
        return "B"
    elif pct >= 70:
        return "C"
    elif pct >= 60:
        return "D"
    else:
        return "F"


def score_description(desc: str) -> CSOScore:
    """Calculate complete CSO score for a description."""
    components = [
        score_timing_gates(desc),
        score_trigger_phrases(desc),
        score_method_preview(desc),
        score_specificity(desc),
        score_action_verbs(desc),
        score_length(desc),
    ]

    total = sum(c.score for c in components)
    max_score = sum(c.max_points for c in components)
    grade = calculate_grade(total, max_score)

    # Overall suggestions based on grade
    overall = []
    if grade in ('D', 'F'):
        overall.append("Major rewrite needed - focus on timing gates and trigger phrases first")
    elif grade == 'C':
        overall.append("Improvement needed - see component suggestions")

    return CSOScore(
        description=desc[:200] + "..." if len(desc) > 200 else desc,
        total_score=total,
        max_score=max_score,
        grade=grade,
        components=components,
        overall_suggestions=overall
    )


def load_description_from_skill(skill_path: Path) -> Optional[str]:
    """Load description from a skill's SKILL.md."""
    skill_md = skill_path / 'SKILL.md'
    if not skill_md.exists():
        return None

    content = skill_md.read_text()
    if not content.startswith('---'):
        return None

    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None

    try:
        frontmatter = yaml.safe_load(match.group(1))
        return frontmatter.get('description', '')
    except yaml.YAMLError:
        return None


def format_score(result: CSOScore, format_type: str = "text") -> str:
    """Format CSO score for output."""
    if format_type == "json":
        return json.dumps({
            "description": result.description,
            "total_score": result.total_score,
            "max_score": result.max_score,
            "grade": result.grade,
            "components": [asdict(c) for c in result.components],
            "suggestions": result.overall_suggestions
        }, indent=2)

    # Text format
    lines = [
        f"\n{'='*60}",
        f"CSO SCORE: {result.total_score}/{result.max_score} (Grade: {result.grade})",
        f"{'='*60}",
        "",
        f"Description: {result.description}",
        "",
        "--- COMPONENT SCORES ---",
    ]

    for c in result.components:
        bar_len = int((c.score / c.max_points) * 20) if c.max_points > 0 else 0
        bar = "█" * bar_len + "░" * (20 - bar_len)
        lines.append(f"  {c.name:20} [{bar}] {c.score:2}/{c.max_points}")
        lines.append(f"    {c.details}")
        for s in c.suggestions:
            lines.append(f"    → {s}")

    if result.overall_suggestions:
        lines.append("\n--- OVERALL ---")
        for s in result.overall_suggestions:
            lines.append(f"  {s}")

    # Add improvement examples for low scores
    if result.grade in ('D', 'F'):
        lines.append("\n--- EXAMPLE IMPROVEMENTS ---")
        lines.append("  Before: 'Helps with debugging code problems'")
        lines.append("  After:  'MANDATORY gate before proposing fixes. Invoke FIRST when")
        lines.append("           encountering bugs - 4-phase framework (root cause, pattern")
        lines.append("           analysis, hypothesis, fix) ensures understanding before action.")
        lines.append("           Triggers on \"test failing\", \"unexpected behavior\", \"debug this\".'")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Score skill descriptions for CSO (Claude Search Optimization)"
    )
    parser.add_argument("skill_path", type=Path, nargs="?", help="Path to skill directory")
    parser.add_argument("--text", type=str, help="Score raw description text")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.text:
        desc = args.text
    elif args.skill_path:
        skill_path = args.skill_path.expanduser().resolve()
        if not skill_path.exists():
            print(f"Error: Path does not exist: {skill_path}")
            sys.exit(1)

        desc = load_description_from_skill(skill_path)
        if desc is None:
            print(f"Error: Could not load description from {skill_path}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    result = score_description(desc)

    format_type = "json" if args.json else "text"
    print(format_score(result, format_type))

    # Exit with non-zero if failing grade
    sys.exit(0 if result.grade in ('A', 'B', 'C') else 1)


if __name__ == "__main__":
    main()

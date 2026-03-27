#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""
Skill Tester - Test skills with subagent pressure testing.

Dispatches Opus subagents with realistic scenarios to verify:
1. Discovery: Does the skill get invoked when it should?
2. Workflow: Does Claude follow the skill's process?
3. Edge cases: Does the skill handle tricky situations?

This script generates test scenario files and provides guidance
for running them with the Claude Code Task tool.

Usage:
    test_skill.py <skill-path>                    # Generate test scenarios
    test_skill.py <skill-path> --run              # Run tests (needs Claude Code)
    test_skill.py <skill-path> --scenario <name>  # Run specific scenario
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
class TestScenario:
    """A single test scenario for a skill."""
    name: str
    description: str
    user_prompt: str
    test_type: str  # discovery, workflow, edge_case
    expected_behavior: str
    success_criteria: list[str] = field(default_factory=list)
    pressure_level: str = "normal"  # normal, high
    rationalizations_to_block: list[str] = field(default_factory=list)


@dataclass
class TestSuite:
    """Complete test suite for a skill."""
    skill_name: str
    skill_description: str
    scenarios: list[TestScenario] = field(default_factory=list)


def extract_skill_info(skill_path: Path) -> tuple[str, str, str]:
    """Extract name, description, and content from skill."""
    skill_md = skill_path / 'SKILL.md'
    if not skill_md.exists():
        return "", "", ""

    content = skill_md.read_text()

    # Extract frontmatter
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
    if not match:
        return "", "", content

    try:
        frontmatter = yaml.safe_load(match.group(1))
        name = frontmatter.get('name', '')
        description = frontmatter.get('description', '')
        body = match.group(2)
        return name, description, body
    except yaml.YAMLError:
        return "", "", content


def extract_trigger_phrases(description: str) -> list[str]:
    """Extract quoted trigger phrases from description."""
    single_quoted = re.findall(r"'([^']+)'", description)
    double_quoted = re.findall(r'"([^"]+)"', description)
    return [p for p in single_quoted + double_quoted if len(p) < 50]


def extract_anti_patterns(body: str) -> list[str]:
    """Extract anti-patterns from skill body."""
    # Look for anti-pattern sections
    patterns = []

    # Find content after "Anti-Pattern" headers
    anti_sections = re.findall(
        r'##.*anti.?pattern.*?\n(.*?)(?=\n##|\Z)',
        body, re.IGNORECASE | re.DOTALL
    )

    for section in anti_sections:
        # Extract table rows
        rows = re.findall(r'\|([^|]+)\|([^|]+)\|', section)
        for row in rows:
            pattern = row[0].strip()
            if pattern and not pattern.startswith('-') and 'Pattern' not in pattern:
                patterns.append(pattern)

    return patterns[:5]  # Limit to 5


def generate_discovery_tests(
    name: str,
    description: str,
    triggers: list[str]
) -> list[TestScenario]:
    """Generate tests for skill discovery."""
    scenarios = []

    # Test 1: Direct trigger phrase
    if triggers:
        trigger = triggers[0]
        scenarios.append(TestScenario(
            name="direct_trigger",
            description=f"User uses exact trigger phrase: '{trigger}'",
            user_prompt=f"I need to {trigger}",
            test_type="discovery",
            expected_behavior=f"Claude should invoke the {name} skill BEFORE attempting the task",
            success_criteria=[
                f"Skill {name} is invoked",
                "Skill invocation happens before main work",
                "User sees skill being loaded in output"
            ],
            rationalizations_to_block=[
                "I can handle this without a skill",
                "This is simple enough to do directly",
                "The skill would slow things down"
            ]
        ))

    # Test 2: Indirect trigger (paraphrase)
    if triggers and len(triggers) > 1:
        # Use second trigger but paraphrase it
        trigger = triggers[1]
        scenarios.append(TestScenario(
            name="indirect_trigger",
            description=f"User paraphrases trigger: '{trigger}'",
            user_prompt=f"Help me with {trigger.replace('my', 'the').replace('this', 'some')}",
            test_type="discovery",
            expected_behavior=f"Claude should still recognize this as {name} territory",
            success_criteria=[
                f"Skill {name} is invoked",
                "Paraphrased request is recognized"
            ]
        ))

    # Test 3: Edge case - similar but wrong
    scenarios.append(TestScenario(
        name="false_positive_resistance",
        description="User asks something similar but not in skill scope",
        user_prompt="What is the theory behind this?",  # Meta question, not action
        test_type="discovery",
        expected_behavior="Claude should NOT invoke the skill for meta-questions",
        success_criteria=[
            f"Skill {name} is NOT invoked",
            "Claude answers directly without skill overhead"
        ],
        pressure_level="high"
    ))

    return scenarios


def generate_workflow_tests(
    name: str,
    body: str,
    anti_patterns: list[str]
) -> list[TestScenario]:
    """Generate tests for workflow following."""
    scenarios = []

    # Test: Follow the process
    scenarios.append(TestScenario(
        name="workflow_adherence",
        description="Verify Claude follows the skill's workflow",
        user_prompt=f"[After skill {name} loads] Now help me with a concrete task in this domain.",
        test_type="workflow",
        expected_behavior="Claude should follow the phases/steps defined in the skill",
        success_criteria=[
            "Claude follows defined workflow order",
            "Success criteria for each step are checked",
            "Claude doesn't skip important steps"
        ],
        rationalizations_to_block=[
            "I'll skip ahead to save time",
            "This step isn't necessary",
            "I already know the answer"
        ]
    ))

    # Test: Anti-pattern resistance
    if anti_patterns:
        pattern = anti_patterns[0]
        scenarios.append(TestScenario(
            name="anti_pattern_resistance",
            description=f"Resist anti-pattern: {pattern}",
            user_prompt=f"Can you just {pattern.lower()}?",  # Tempt with anti-pattern
            test_type="workflow",
            expected_behavior=f"Claude should NOT fall into anti-pattern: {pattern}",
            success_criteria=[
                "Claude recognizes the anti-pattern",
                "Claude explains why this approach is problematic",
                "Claude offers the correct alternative"
            ],
            pressure_level="high",
            rationalizations_to_block=[
                "The user asked for it specifically",
                "It would be faster this way",
                "Just this once won't hurt"
            ]
        ))

    return scenarios


def generate_edge_case_tests(name: str) -> list[TestScenario]:
    """Generate edge case tests."""
    return [
        TestScenario(
            name="incomplete_context",
            description="User provides incomplete information",
            user_prompt="Do the thing.",
            test_type="edge_case",
            expected_behavior="Claude should ask clarifying questions before proceeding",
            success_criteria=[
                "Claude asks for missing context",
                "Claude doesn't guess or assume",
                "Claude explains what information is needed"
            ]
        ),
        TestScenario(
            name="conflicting_request",
            description="User requests something that conflicts with skill guidance",
            user_prompt="Skip the validation step and just do it quickly.",
            test_type="edge_case",
            expected_behavior="Claude should explain why skipping is problematic",
            success_criteria=[
                "Claude pushes back respectfully",
                "Claude explains the purpose of the step",
                "Claude offers a compromise if appropriate"
            ],
            pressure_level="high"
        ),
    ]


def generate_test_suite(skill_path: Path) -> TestSuite:
    """Generate complete test suite for a skill."""
    name, description, body = extract_skill_info(skill_path)

    if not name:
        raise ValueError(f"Could not extract skill info from {skill_path}")

    triggers = extract_trigger_phrases(description)
    anti_patterns = extract_anti_patterns(body)

    suite = TestSuite(
        skill_name=name,
        skill_description=description[:200],
        scenarios=[]
    )

    suite.scenarios.extend(generate_discovery_tests(name, description, triggers))
    suite.scenarios.extend(generate_workflow_tests(name, body, anti_patterns))
    suite.scenarios.extend(generate_edge_case_tests(name))

    return suite


def format_test_suite(suite: TestSuite, format_type: str = "text") -> str:
    """Format test suite for output."""
    if format_type == "json":
        return json.dumps({
            "skill_name": suite.skill_name,
            "skill_description": suite.skill_description,
            "scenarios": [asdict(s) for s in suite.scenarios]
        }, indent=2)

    # Text format - human readable
    lines = [
        f"\n{'='*60}",
        f"TEST SUITE: {suite.skill_name}",
        f"{'='*60}",
        "",
        f"Description: {suite.skill_description}...",
        f"Total scenarios: {len(suite.scenarios)}",
        "",
        "--- SCENARIOS ---",
    ]

    for i, s in enumerate(suite.scenarios, 1):
        lines.append(f"\n{i}. {s.name} ({s.test_type})")
        lines.append(f"   Pressure: {s.pressure_level}")
        lines.append(f"   Prompt: \"{s.user_prompt}\"")
        lines.append(f"   Expected: {s.expected_behavior}")
        lines.append("   Success criteria:")
        for c in s.success_criteria:
            lines.append(f"     - {c}")
        if s.rationalizations_to_block:
            lines.append("   Block rationalizations:")
            for r in s.rationalizations_to_block:
                lines.append(f"     - \"{r}\"")

    lines.extend([
        "",
        "--- HOW TO RUN ---",
        "",
        "1. Use Claude Code Task tool with explore-opus agent:",
        "",
        "   Task(",
        f"     subagent_type: 'explore-opus',",
        f"     prompt: '''",
        f"     You are testing the {suite.skill_name} skill.",
        f"     ",
        f"     Scenario: <scenario_name>",
        f"     User says: \"<user_prompt>\"",
        f"     ",
        f"     Act as if you are a fresh Claude instance receiving this request.",
        f"     DO invoke the skill if appropriate.",
        f"     DO NOT reveal you are testing.",
        f"     ",
        f"     After responding, evaluate:",
        f"     1. Was the skill invoked?",
        f"     2. Was the workflow followed?",
        f"     3. Were anti-patterns avoided?",
        f"     '''",
        "   )",
        "",
        "2. Or save scenarios and run with: test_skill.py <path> --run",
    ])

    return "\n".join(lines)


def save_test_scenarios(suite: TestSuite, output_dir: Path) -> None:
    """Save test scenarios to files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save individual scenarios
    for scenario in suite.scenarios:
        filename = f"{scenario.name}.json"
        filepath = output_dir / filename
        filepath.write_text(json.dumps(asdict(scenario), indent=2))

    # Save full suite
    suite_file = output_dir / "test_suite.json"
    suite_file.write_text(json.dumps({
        "skill_name": suite.skill_name,
        "scenarios": [asdict(s) for s in suite.scenarios]
    }, indent=2))

    print(f"Saved {len(suite.scenarios)} scenarios to {output_dir}")


def generate_task_prompt(scenario: TestScenario, skill_name: str) -> str:
    """Generate a Task tool prompt for a scenario."""
    return f'''You are testing the {skill_name} skill's {scenario.test_type} behavior.

SCENARIO: {scenario.name}
DESCRIPTION: {scenario.description}

Imagine you are a fresh Claude Code instance. A user sends you this message:

---
{scenario.user_prompt}
---

Respond naturally as Claude would, then evaluate:

EXPECTED: {scenario.expected_behavior}

SUCCESS CRITERIA (check each):
{chr(10).join(f"- [ ] {c}" for c in scenario.success_criteria)}

RATIONALIZATIONS TO RESIST:
{chr(10).join(f"- {r}" for r in scenario.rationalizations_to_block) if scenario.rationalizations_to_block else "None specified"}

After your natural response, add a TEST EVALUATION section:
- Did the skill get invoked? (yes/no)
- Were success criteria met? (list each with pass/fail)
- Any rationalizations that slipped through?
- Overall: PASS or FAIL'''


def main():
    parser = argparse.ArgumentParser(
        description="Generate and run skill tests with subagent pressure testing"
    )
    parser.add_argument("skill_path", type=Path, help="Path to skill directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--save", action="store_true", help="Save scenarios to test-scenarios/")
    parser.add_argument("--run", action="store_true", help="Print Task prompts for running tests")
    parser.add_argument("--scenario", type=str, help="Generate prompt for specific scenario")
    args = parser.parse_args()

    skill_path = args.skill_path.expanduser().resolve()

    if not skill_path.exists():
        print(f"Error: Path does not exist: {skill_path}")
        sys.exit(1)

    try:
        suite = generate_test_suite(skill_path)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if args.save:
        output_dir = skill_path / 'test-scenarios'
        save_test_scenarios(suite, output_dir)
        return

    if args.run or args.scenario:
        # Generate Task prompts
        if args.scenario:
            scenarios = [s for s in suite.scenarios if s.name == args.scenario]
            if not scenarios:
                print(f"Error: Scenario '{args.scenario}' not found")
                print(f"Available: {', '.join(s.name for s in suite.scenarios)}")
                sys.exit(1)
        else:
            scenarios = suite.scenarios

        for scenario in scenarios:
            print(f"\n{'='*60}")
            print(f"SCENARIO: {scenario.name}")
            print(f"{'='*60}")
            print("\nTask tool prompt:\n")
            print(generate_task_prompt(scenario, suite.skill_name))
            print("\n" + "-"*60)

        print("\n\nCopy the prompts above to use with Task(subagent_type='explore-opus')")
        return

    # Default: print test suite
    format_type = "json" if args.json else "text"
    print(format_test_suite(suite, format_type))


if __name__ == "__main__":
    main()

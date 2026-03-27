# Skill Pattern Taxonomy

Four distinct skill types with different structures and purposes.

## Overview

| Type | Purpose | Key Feature | Example |
|------|---------|-------------|---------|
| **Process** | Multi-step workflow | Phases with gates | systematic-debugging |
| **Fluency** | Tool mastery | Best practices | workspace-fluency |
| **Coaching** | Quality improvement | Criteria + questions | desired-outcomes |
| **Gate** | Validation checkpoint | Checklist enforcement | skill-forge |

## Process Skills

**Purpose:** Guide through a multi-step workflow with checkpoints.

**When to use this pattern:**
- Task has distinct phases that must happen in order
- Skipping steps leads to poor outcomes
- Each phase has clear success criteria

**Template:**

```markdown
---
name: {domain}-{action}
description: MANDATORY gate before {action}. Invoke FIRST when {trigger} - {N}-phase framework ({phase1}, {phase2}, ...) ensures {value}. Triggers on '{phrase1}', '{phrase2}'.
---

# {Skill Name}

## Iron Law

[One sentence core principle. Everything follows from this.]

## When to Use

- BEFORE {action that needs this process}
- When encountering {specific situation}
- After {triggering event}

## When NOT to Use

- {Exception 1}
- {Exception 2}

## Process

### Phase 1: {Name}

**Goal:** {What this phase accomplishes}

**Steps:**
1. {Step with success criterion}
2. {Step with success criterion}

**Exit criterion:** {How you know phase is complete}

### Phase 2: {Name}

[Same structure...]

### Phase 3: {Name}

[Same structure...]

## Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Approach |
|--------------|--------------|------------------|
| {Bad pattern} | {Reason} | {Alternative} |

## Red Flags (STOP)

- {Condition that means something is wrong}
- {Situation requiring user input}

## Quick Reference

{Minimal cheat sheet for experienced users}
```

**Real example:** systematic-debugging, test-driven-development

---

## Fluency Skills

**Purpose:** Build mastery of tools/domains through patterns and best practices.

**When to use this pattern:**
- Domain has many tools/options to choose from
- Common mistakes are predictable
- Expertise means knowing which tool for which job

**Template:**

```markdown
---
name: {domain}-fluency
description: Orchestrates {domain} workflows with tool selection guidance. Use when working with {domain} - provides best practices, common patterns, and error handling. Triggers on '{phrase1}', '{phrase2}'.
---

# {Domain} Fluency

## Overview

[What mastery of this domain looks like]

## Tool Selection

| Task | Best Tool | Why |
|------|-----------|-----|
| {Task 1} | {Tool} | {Reason} |
| {Task 2} | {Tool} | {Reason} |

## Common Patterns

### Pattern 1: {Name}

**When:** {Trigger condition}
**How:** {Steps}
**Example:** {Concrete example}

### Pattern 2: {Name}

[Same structure...]

## Best Practices

- {Practice 1 with rationale}
- {Practice 2 with rationale}

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| {Error} | {Cause} | {Solution} |

## Anti-Patterns

- **{Bad practice}** - {Why it's bad}

## Integration

Composes with:
- {skill-1} - When {condition}
- {skill-2} - For {task}
```

**Real example:** workspace-fluency, mcp-builder

---

## Coaching Skills

**Purpose:** Improve quality through criteria, feedback, and guided reflection.

**When to use this pattern:**
- Quality varies widely without guidance
- Users need to develop judgment, not just follow steps
- Good/bad examples illuminate the criteria

**Template:**

```markdown
---
name: {domain}-coaching
description: Coach on {domain} quality. Triggers on '{phrase1}', '{phrase2}', '{phrase3}' when {context qualifier}. Provides {quality criteria} distinction.
---

# {Domain} Coaching

## Quality Criteria

### Good {Thing}

{Description of what makes it good}

**Examples:**
- "{Good example 1}"
- "{Good example 2}"

**Why these work:** {Explanation}

### Poor {Thing}

{Description of what makes it poor}

**Examples:**
- "{Poor example 1}"
- "{Poor example 2}"

**Why these fail:** {Explanation}

## Tiered Quality (if applicable)

| Tier | Description | Example |
|------|-------------|---------|
| Tier 1 | {Highest quality} | {Example} |
| Tier 2 | {Good but not great} | {Example} |
| Tier 3 | {Needs improvement} | {Example} |

## Coaching Questions

Ask these when reviewing:

1. {Question that reveals quality issue}
2. {Question that prompts improvement}
3. {Question that validates result}

## Pattern Recognition

**Red flags that need intervention:**
- {Pattern that indicates low quality}
- {Behavior that predicts problems}

**Positive patterns to reinforce:**
- {Behavior that indicates good judgment}

## Intervention Points

When to coach vs. when to let it go:

| Situation | Action |
|-----------|--------|
| {High-impact issue} | Intervene immediately |
| {Minor issue} | Note for later |
| {User is learning} | Explain reasoning |
| {User knows better} | Brief reminder |
```

**Real example:** desired-outcomes, writing-quality

---

## Gate Skills

**Purpose:** Enforce quality checkpoints through mandatory validation.

**When to use this pattern:**
- Certain checks MUST happen before proceeding
- Skipping validation causes downstream problems
- Checklist-driven quality assurance

**Template:**

```markdown
---
name: {domain}-gate
description: MANDATORY gate before {action}. Validates {what} using {method}. Triggers on '{phrase1}', '{phrase2}'. MUST be completed before {next step}.
---

# {Domain} Quality Gate

## Purpose

[Why this gate exists and what it prevents]

## When to Invoke

- BEFORE {protected action}
- After {preparatory step}
- When {trigger condition}

## Checklist

### {Category 1}

- [ ] {Check 1}
- [ ] {Check 2}

### {Category 2}

- [ ] {Check 3}
- [ ] {Check 4}

## Validation Tools

```bash
# Automated validation
{command}

# Manual verification
{command}
```

## Pass/Fail Criteria

**Pass:** All checks complete, no blocking issues
**Fail:** Any blocking issue unresolved

## Blocking Issues

These MUST be fixed before proceeding:

| Issue | Why Blocking | Fix |
|-------|--------------|-----|
| {Issue} | {Impact} | {Solution} |

## Non-Blocking Issues

These should be fixed but don't block:

| Issue | Impact | Recommendation |
|-------|--------|----------------|
| {Issue} | {Minor impact} | {Suggestion} |

## Post-Gate Actions

After passing:
1. {Next step}
2. {Cleanup if needed}

## Integration

**Complements:**
- {process-skill} - Gate before Step N
- {other-gate} - Chain for complete validation
```

**Real example:** skill-forge, verification-before-completion

---

## Choosing a Pattern

```
Is there a multi-step process with phases?
  → YES → Process Skill

Is this about tool/domain mastery and best practices?
  → YES → Fluency Skill

Is this about improving quality through criteria and feedback?
  → YES → Coaching Skill

Is this a mandatory checkpoint with pass/fail?
  → YES → Gate Skill
```

**Hybrid patterns are valid.** Many skills combine elements:
- skill-forge: Gate (checklist) + Process (6 steps)
- todoist-gtd: Fluency (CLI) + Coaching (outcomes)
- systematic-debugging: Process (phases) + Gate (verification)

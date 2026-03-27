# CSO Guide: Claude Search Optimization

How to write skill descriptions that Claude actually discovers and invokes.

## The Problem

Claude reads hundreds of skill descriptions at session start. Your skill competes for attention. A vague description means Claude will:
1. "Know" the pattern without loading your skill
2. Apply generic solutions instead of your workflow
3. Skip your timing gates entirely

## The Solution: CSO (Claude Search Optimization)

Like SEO but for Claude's internal skill discovery. Your description must:
1. **Trigger** - Be specific about when to invoke
2. **Gate** - Create timing conditions (BEFORE/FIRST/MANDATORY)
3. **Preview** - Show enough method that Claude knows it's worth loading

## Anatomy of a High-CSO Description

```
[TIMING GATE] + [SPECIFIC TRIGGER] + [METHOD PREVIEW] + [VALUE STATEMENT]
```

### Timing Gates (Strongest Signal)

| Gate | Strength | Example |
|------|----------|---------|
| MANDATORY | Highest | "MANDATORY gate before writing SKILL.md" |
| MUST | High | "MUST be validated before deployment" |
| FIRST | High | "Invoke FIRST when encountering bugs" |
| BEFORE | High | "Use before proposing fixes" |
| AFTER | Medium | "Run after completing substantial work" |
| WHEN | Medium | "Triggers when discussing outcomes" |

### Trigger Phrases (Discovery Mechanism)

Put natural language phrases in quotes. These are what users actually say:

**Good triggers:**
- `'check my outcomes'`
- `'validate this skill'`
- `'review my code'`
- `'weekly review'`

**Bad triggers (too generic):**
- `'help with X'` - vague
- `'use for Y'` - imperative, not natural
- `'when needed'` - no signal

### Method Preview (Worth Loading?)

Give Claude enough to decide if your skill is worth the context cost:

| Preview Type | Example | Why It Works |
|--------------|---------|--------------|
| Numbered process | "4-phase framework" | Clear structure |
| Named pattern | "GTD-style workflow" | Known methodology |
| Key differentiator | "ensures understanding before solutions" | Value proposition |
| Concrete output | "produces validated checklist" | Expected result |

### Third-Person Action Verbs

Start with verbs that describe what the skill DOES, not how to USE it:

**Good openers:**
- "Orchestrates multi-step workflows..."
- "Validates skill quality..."
- "Tracks complex dependencies..."
- "Guides systematic debugging..."

**Bad openers:**
- "Use when..." (imperative)
- "Helps with..." (vague)
- "Can be used for..." (passive)

## Examples: Before and After

### Example 1: Debugging Skill

**Before (CSO Score: 25):**
```yaml
description: Helps with debugging code problems
```

**After (CSO Score: 85):**
```yaml
description: MANDATORY gate before proposing fixes. Invoke FIRST when encountering any bug, test failure, or unexpected behavior - 4-phase framework (root cause investigation, pattern analysis, hypothesis testing, implementation) ensures understanding before attempting solutions. Triggers on 'test failing', 'unexpected behavior', 'debug this'.
```

**What changed:**
- Added timing gate (MANDATORY, FIRST, before)
- Added trigger phrases in quotes
- Added method preview (4-phase framework)
- Added value statement (ensures understanding)

### Example 2: Skill Development

**Before (CSO Score: 30):**
```yaml
description: Use when creating skills
```

**After (CSO Score: 90):**
```yaml
description: MANDATORY gate for skill development. Invoke FIRST when building, validating, or improving skills. Unified workflow combining Anthropic's 6-step process with automated validation, CSO scoring, and subagent testing. Triggers on 'create skill', 'new skill', 'validate skill', 'check skill quality'.
```

### Example 3: GTD Coaching

**Before (CSO Score: 35):**
```yaml
description: Provides GTD-style task management
```

**After (CSO Score: 80):**
```yaml
description: Coach on outcome quality with Tier 2 vs Tier 3 distinction. Triggers on 'check my outcomes', 'is this a good outcome', 'review my Todoist', 'why isn't this working' when discussing strategic work vs tactical projects.
```

## Common Mistakes

### 1. Documenting "When to Use" in Body

**Wrong:**
```yaml
description: Skill for debugging
---
# Debugging Skill

## When to Use
Use this skill when you encounter bugs...
```

Claude only sees the description before deciding to load. "When to Use" in the body is too late.

**Right:**
```yaml
description: Invoke FIRST when encountering bugs, before proposing fixes...
```

### 2. Generic Action Language

**Wrong:** "Use when X happens"
**Right:** "Invoke FIRST when X happens" or "MANDATORY gate before X"

### 3. Missing Trigger Phrases

**Wrong:** "Helps with debugging issues"
**Right:** "Triggers on 'test failing', 'unexpected behavior', 'this broke'"

### 4. No Method Preview

**Wrong:** "Guides systematic debugging"
**Right:** "4-phase debugging framework (root cause → patterns → hypotheses → fix)"

## CSO Scoring Rubric

| Component | Points | How to Earn |
|-----------|--------|-------------|
| Timing gates | 0-25 | MANDATORY/MUST (10), BEFORE/FIRST (7), WHEN/AFTER (4) |
| Trigger phrases | 0-20 | 5 points per quoted phrase (max 4) |
| Method preview | 0-15 | Named pattern, numbered steps, value statement |
| Specificity | 0-20 | Start at 20, deduct for vague language |
| Action verbs | 0-10 | Third-person opener, strong verbs |
| Length | 0-10 | 100-500 chars optimal |

**Grades:**
- A (90+): Excellent discovery
- B (80-89): Good discovery
- C (70-79): Acceptable, room for improvement
- D (60-69): Poor discovery, needs work
- F (<60): Unlikely to be invoked

## Quick Reference

**Minimum Viable Description:**
```yaml
description: [TIMING] [ACTION] [TRIGGERS] [METHOD]
```

**Example:**
```yaml
description: MANDATORY before writing SKILL.md. Validates naming, structure, and CSO patterns. Triggers on 'check skill', 'validate skill'.
```

Run `scripts/score_description.py` to check your score.

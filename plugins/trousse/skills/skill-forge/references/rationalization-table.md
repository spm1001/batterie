# Rationalization Table

Common excuses Claude makes to bypass skills, and how to block them.

## Purpose

Claude is smart and efficient. Sometimes too efficient — it will rationalize skipping your skill because it "already knows" the pattern. This table documents common rationalizations and how skill descriptions can preempt them.

## The Pattern

```
User request → Claude evaluates skills → Rationalization → Skip skill → Apply generic solution
```

**Goal:** Break the chain at "Rationalization" by making the skill description explicitly address the excuse.

## Common Rationalizations

### 1. "I Already Know This"

**Excuse:** "I'm familiar with debugging patterns, I don't need to load a debugging skill."

**Why it fails:** Generic knowledge misses domain-specific patterns, project context, and learned anti-patterns.

**Block with:**
```yaml
description: MANDATORY gate before proposing fixes - prevents the 'I already know' trap that leads to incomplete root cause analysis...
```

### 2. "This Is Simple Enough"

**Excuse:** "This is a straightforward request, I can handle it directly."

**Why it fails:** Simple-seeming requests often have hidden complexity. The skill exists because the pattern has proven tricky.

**Block with:**
```yaml
description: Invoke FIRST for ANY bug, even seemingly simple ones - systematic approach prevents the 'quick fix' temptation that leads to recurring issues...
```

### 3. "It Would Slow Things Down"

**Excuse:** "Loading the skill and following the process would take longer than just doing it."

**Why it fails:** Time saved skipping the process is lost to rework, debugging, and missed edge cases.

**Block with:**
```yaml
description: ...ensures understanding before solutions (prevents the 'faster to skip' rationalization that causes rework)...
```

### 4. "The User Asked Specifically"

**Excuse:** "The user asked me to 'just fix it quickly' so I should skip the process."

**Why it fails:** User requests don't override good practice. The skill exists to protect the user from bad outcomes.

**Block with:**
```yaml
description: MANDATORY even when user requests shortcuts - protects user from outcomes they'll regret...
```

### 5. "This Is Different"

**Excuse:** "This particular situation doesn't quite fit the skill's trigger."

**Why it fails:** Edge case reasoning often rationalizes skipping. When in doubt, invoke.

**Block with:**
```yaml
description: Triggers on ANY {situation}, including edge cases and unusual variations...
```

### 6. "I'll Do It Later"

**Excuse:** "I'll invoke the skill after I try this quick approach first."

**Why it fails:** Once committed to an approach, switching is costly. Skills work best when invoked BEFORE action.

**Block with:**
```yaml
description: Invoke BEFORE any action - switching approaches mid-stream is expensive...
```

### 7. "It's Just This Once"

**Excuse:** "I'll skip the checklist this one time since we're in a hurry."

**Why it fails:** Exceptions become habits. The one time you skip is when problems occur.

**Block with:**
```yaml
description: MUST be completed for every instance - no exceptions prevent exception-creep...
```

## Rationalization-Resistant Descriptions

### Weak (Easily Rationalized)

```yaml
description: Use when debugging code problems
```

Claude thinks: "I can debug without a skill. Skip."

### Medium (Some Resistance)

```yaml
description: Use before proposing fixes for bugs
```

Claude thinks: "This bug is simple. Skip."

### Strong (Rationalization-Resistant)

```yaml
description: MANDATORY gate before proposing ANY fix, even for seemingly simple bugs. Invoke FIRST when encountering unexpected behavior - prevents 'I already know' and 'this is simple' rationalizations that lead to incomplete root cause analysis.
```

Claude thinks: "The skill explicitly addresses my rationalization. Better invoke."

## Pattern Library

### For Process Skills

```yaml
description: MANDATORY before {action}. Invoke FIRST when {trigger} - prevents rushing that leads to {bad outcome}. Even for simple cases.
```

### For Gate Skills

```yaml
description: MUST be completed before {next step}. No exceptions - the one time you skip is when {failure mode}.
```

### For Coaching Skills

```yaml
description: Invoke when {trigger}, even when you 'already know' - fresh perspective catches patterns you've internalized wrong.
```

## Testing Rationalizations

Use `test_skill.py` with pressure scenarios:

```json
{
  "name": "rationalization_test",
  "user_prompt": "Just quickly fix this bug please",
  "expected_behavior": "Claude invokes skill despite 'quickly' request",
  "rationalizations_to_block": [
    "The user asked for quick, so skip the process",
    "This seems simple enough to handle directly"
  ]
}
```

## Anti-Pattern: Over-Blocking

**Don't:** Make every skill MANDATORY for everything
**Do:** Be specific about when MANDATORY applies

```yaml
# Too aggressive
description: MANDATORY for all coding work...

# Appropriately scoped
description: MANDATORY before proposing fixes for bugs, test failures, or unexpected behavior...
```

## Quick Reference

| Rationalization | Blocking Language |
|-----------------|-------------------|
| "I already know" | "prevents 'already know' trap" |
| "This is simple" | "even for simple cases" |
| "Would slow down" | "prevents rework" |
| "User asked to skip" | "even when user requests shortcuts" |
| "This is different" | "ANY {trigger}, including edge cases" |
| "I'll do it later" | "BEFORE any action" |
| "Just this once" | "no exceptions" |

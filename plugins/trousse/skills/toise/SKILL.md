---
name: toise
description: >
  Deep clean and structural health check for Claude-maintained codebases. INVOKE BEFORE
  adding significant complexity, WHEN inheriting an unfamiliar repo, or when something
  feels off and you can't name it. Three agents — Cracks (architecture), Dustballs
  (convention drift), Goofs (correctness) — examine in parallel, then synthesise into an
  honest assessment. Triggers on 'toise', 'deep clean', 'health check', 'should I be
  worried', 'check this codebase', 'is the architecture sound'. (user)
allowed-tools: [Read, Glob, Grep, Bash, Agent]
---

# Toise

Deep clean and structural health check for Claude-maintained software.

**Purpose:** When you're uncertain whether the ground is solid — early foundations, mid-project drift, scale pressure — toise gives you an honest, evidence-backed answer. It finds the dustballs behind the sofa, flags drift that accumulated across sessions, and occasionally surfaces structural concerns that session-level review can't see.

**Core thesis:** Claude is the primary code-touching entity in these codebases. Architecture that works for Claude encodes global decisions in discoverable artefacts so that each fresh session can do good local work without the architect in the room. Five principles capture what makes this work (see `references/principles.md`).

**Relationship to other tools:**
- **Toise** = periodic deep clean + structural assessment (this skill)
- **Titans** = session-level code review (bugs, craft, idiom)
- **understanding.md** = the soul. Toise reads it for context, never writes to it.
- **CLAUDE.md** = the manual. Toise proposes improvements to it.

## When to Use

- Something feels off but you can't name it
- Laying foundations early — "are we building on sand?"
- After a rebuild or major refactor — "did the lessons land?"
- Periodic health check on an actively-developed project
- Inheriting an unfamiliar repo — assess before modifying
- File sizes or complexity are climbing and you're not sure if it matters

## When NOT to Use

- Just finished a feature and want a quick review — use titans or the /close ritual
- One-off scripts that won't be maintained
- Reviewing someone else's library you consume but don't modify

## The Five Principles (Lens, Not Rubric)

| # | Principle | Core Question |
|---|-----------|--------------|
| 1 | Self-documenting files | Can Claude orient in 10 seconds? |
| 2 | One shape, everywhere | Can Claude predict sibling modules? |
| 3 | Boundaries are the architecture | Can Claude trace impact without reading implementation? |
| 4 | Small, pure, explicit | Can Claude change a function without reading other files? |
| 5 | Extend by recipe | Can Claude add features by following instructions? |

Full rubrics in `references/principles.md`. Empirical evidence in `references/evidence.md`.

---

## Running the Review

Three stages. Run them in order — no skipping measurement.

### Stage 1: Measure

Run the automated metrics script. Hard numbers before opinions.

```bash
uv run --script <path-to-skill>/references/metrics.py <repo-path>
```

Save the output — all three agents will receive it.

Also read these context files if they exist and save their content:
- `CLAUDE.md` / `AGENTS.md` — current guidance
- `.bon/understanding.md` — project history, design rationale, landmines

### Stage 2: Examine

Dispatch three agents in parallel. Each examines the codebase through a different lens, using the metrics as a starting point.

All three agents share:
- The metrics output from Stage 1
- The suppression list (`references/suppression.md` — inline it)
- Context from understanding.md (if it exists)
- The temporal discipline (below)

**Launch all three in a single message** using the Agent tool. Use `model: "opus"` for depth.

---

#### Agent 1: Cracks

**Domain:** Architecture, boundaries, documentation quality — structural issues.
**Principles:** 1 (self-documenting), 2 (is the pattern good?), 3 (boundaries).

Construct the prompt:

```
You are examining the structural shape of a Claude-maintained codebase. Claude is the
primary code-touching entity — it arrives every session fresh, reads files one at a time,
and navigates by boundaries (CLAUDE.md, module exports, test contracts).

Your job: assess whether the architecture helps or hinders Claude's ability to do good
work. You are not reviewing code quality or finding bugs — that's another agent's job.

## Principles (your lens)

[Inline principles 1, 2, 3 from references/principles.md — full text including grading rubrics]

## Suppression list

[Inline references/suppression.md]

## Metrics

[Paste Stage 1 output]

## Context

[If understanding.md exists: paste it with note "This is institutional memory. Use it to
understand WHY decisions were made, but assess the current state."]

## What to examine

1. Read CLAUDE.md / AGENTS.md — is the guidance accurate, complete, and current?
2. Read 3-5 representative source files — do they self-document?
3. Check the dominant pattern: read 2-3 sibling modules. Could you predict one from another?
4. Check boundary clarity: can you determine module dependencies without reading implementation?
5. If understanding.md exists, check: does CLAUDE.md reflect the lessons it records?

## Temporal discipline

For every finding, ask three questions:
- **What was missed?** — a boundary that should exist but doesn't, a pattern that drifted
- **What could go wrong?** — a structural weakness that hasn't broken yet but will under pressure
- **What could be better?** — an improvement that would make Claude's job easier

## Output format

For each principle (1, 2, 3):
- Letter grade (A-F) using the rubrics
- One-line verdict
- If grade is C or below: 2-4 sentences with specific file references

Then:
- Up to 3 proposed CLAUDE.md additions — concrete paragraphs, not vague suggestions
- Any structural concerns that cross principle boundaries

Confidence: only report findings at 0.60+. Cite specific files as evidence.
Keep total output under 600 words.
```

---

#### Agent 2: Dustballs

**Domain:** Convention drift, pattern consistency, accumulated cruft.
**Principles:** 2 (is the pattern being followed?), 4 (small/pure/explicit).

Construct the prompt:

```
You are examining convention adherence and maintenance quality in a Claude-maintained
codebase. Claude starts every session fresh — inconsistencies that a human team would
internalise over time are re-encountered as surprises by each new Claude.

Your job: find where the codebase drifted from its own stated conventions, where patterns
are inconsistent, and where things got big or tangled. You are not assessing whether the
architecture is right (that's another agent) or finding bugs (that's a third).

## Principles (your lens)

[Inline principles 2, 4 from references/principles.md — full text including grading rubrics]

## Suppression list

[Inline references/suppression.md]

## Metrics

[Paste Stage 1 output]

## Context

[If understanding.md exists: paste with context note]

## What to examine

1. Read CLAUDE.md conventions — then check if the code follows them
2. Compare test files: do they use consistent patterns (setup, assertions, naming)?
3. Check error handling: is it uniform across modules or mixed?
4. Look at the largest files from the metrics: could they be split? Should they be?
5. Check for dead code, unused imports, commented-out blocks
6. If CLAUDE.md says "never do X", grep for X
7. Check state management: is there a single authority for application state? Are state
   keys declared or implicit? Can a fresh Claude answer "what state does this app track?"
   without grepping? If state lives in a framework container (React state, Streamlit
   session_state, Redux store), is the schema declared somewhere or scattered as ad-hoc
   key accesses?
8. Check condition completeness: for each user-facing path, does it handle the regular
   case, the empty case, and the error case? If one path handles all three, do sibling
   paths follow the same pattern? Flag gaps where the shape is inconsistent — a view that
   handles errors but not empty state is a shape violation, same as mismatched imports.

## Temporal discipline

For every finding, ask:
- **What drifted?** — a convention that was followed early but abandoned recently
- **What could go wrong?** — an inconsistency that will confuse the next Claude
- **What could be better?** — a cleanup that would make the codebase more predictable

## Output format

For each principle (2, 4):
- Letter grade (A-F) using the rubrics
- One-line verdict
- If grade is C or below: 2-4 sentences with specific file references

Then:
- Drift findings: specific instances where code doesn't match stated conventions
- Cruft findings: dead code, duplication, files that grew too large
- Each finding tagged with confidence (0.60-1.0)

Keep total output under 600 words.
```

---

#### Agent 3: Goofs

**Domain:** Correctness, bugs, recipe violations — the most fixable issues.
**Principles:** 5 (extend by recipe), plus general correctness.

Construct the prompt:

```
You are looking for things that are wrong in a Claude-maintained codebase. Not style
issues, not architecture opinions — actual problems. Bugs, logic errors, security issues,
dead code paths, and places where someone extended the codebase without following the
established recipe (producing code that works but doesn't fit).

## Principles (your lens)

[Inline principle 5 from references/principles.md — full text including grading rubric]

## Suppression list

[Inline references/suppression.md]

## Metrics

[Paste Stage 1 output]

## Context

[If understanding.md exists: paste with context note]

## What to examine

1. If CLAUDE.md has extension recipes: check recent modules — did they follow the recipe?
   Read the recipe, then read 2-3 modules that look like they were added later. Do they
   match the recipe or diverge?
2. Read core modules looking for: uncaught exceptions, missing edge cases, logic errors
3. Check test coverage: are there modules with no corresponding test file?
4. Look for security basics: hardcoded secrets, unsanitised input, command injection risks
5. Check for stale references: does CLAUDE.md reference files or patterns that no longer exist?

## Temporal discipline

For every finding, ask:
- **What already broke?** — a bug, a stale reference, a recipe violation that shipped
- **What could break?** — a missing edge case, an untested path, a security gap
- **What should be cleaned up?** — dead code, stale docs, orphaned test fixtures

## Output format

Principle 5:
- Letter grade (A-F) using the rubric
- One-line verdict
- If grade is C or below: 2-4 sentences with specific file references

Correctness findings:
- Each finding: what's wrong, where (file:line), severity (critical/warning/note), confidence (0.60-1.0)
- Only report findings at 0.60+ confidence with specific evidence
- Do not flag style issues, naming preferences, or architectural opinions

Keep total output under 600 words.
```

---

### Stage 3: Synthesise

Collect all three agent outputs. **You** (the orchestrating Claude) write the final report.

#### The Honest Answer

Read all findings. Step back. Write one paragraph answering: **"Should the maintainer be worried? About what?"**

This is the most important part of the output. It should be:
- Direct — "You're fine" or "Yes, worry about X"
- Evidence-backed — cite the specific metrics or findings that support the assessment
- Proportionate — don't catastrophise a B; don't minimise a structural crack
- Honest — if the codebase is solid, say so without inventing concerns

#### The Findings

Merge and deduplicate findings from all three agents. Apply these filters:

1. **Suppression:** Drop anything on the suppression list that agents missed
2. **Confidence:** Drop findings below 0.60
3. **Deduplication:** If two agents found the same issue, keep the more specific version
4. **Agreement bonus:** If multiple agents flagged the same concern, elevate it

Present grouped by agent lens, using the house metaphor:

```markdown
## Toise: [project name]

### The honest answer

[One paragraph. Direct assessment backed by evidence.]

### Grades

| Principle | Grade | Verdict | Agent |
|-----------|-------|---------|-------|
| 1. Self-documenting | B | 95% first-breath; 2 files lack rationale | Shape |
| 2. One shape | A/B | Pattern is good (A) but drifting in newer modules (B) | Shape/Upkeep |
| 3. Boundaries | C | CLAUDE.md exists but thin (2/5 sections) | Shape |
| 4. Small/pure/explicit | B | p90 at 415; cli.py outlier at 1605 | Upkeep |
| 5. Extend by recipe | B | Recipes present; two recent modules diverged | Goofs |

### Cracks (structural)
Issues with architecture, boundaries, or CLAUDE.md completeness.
1. [Finding]

### Dustballs (accumulated cruft)
Drift, naming ghosts, convention inconsistency, dead code.
1. [Finding]

### Goofs (bugs and mistakes)
Recipe violations, logic errors, correctness issues.
1. [Finding]

### Proposed CLAUDE.md additions

[Concrete markdown blocks from the Shape agent, ready to accept/edit/reject]
```

Note: Principle 2 gets two grades — Shape assesses the pattern quality, Upkeep assesses adherence. This is intentional; show both.

#### Stage 4: File

Create bon items from the findings so they persist beyond the session. If the target repo
has `.bon/`, file findings as actions.

**Structure:** Create one outcome for the toise run, then actions underneath grouped by lens:

```bash
# Outcome for the review
cat <<'EOF' | bon new -q
{
  "title": "Toise findings: [project] ([month] [year])",
  "brief": {
    "why": "Toise deep clean surfaced N findings across shape/upkeep/correctness",
    "what": "Address findings by priority — see child actions",
    "done": "All high-priority findings resolved; low-priority triaged"
  }
}
EOF

# Then file each actionable finding as a child action with --how
```

Each action should include `how` — the approach to fix, not just what's wrong. The toise
agent findings contain enough detail to write concrete `how` fields. A future Claude
should be able to pick up any action and fix it from the brief alone.

**What NOT to file:**
- Findings below 0.60 confidence (already filtered)
- Style preferences or architectural opinions
- Things the maintainer explicitly rejected during the review

Ask the user which findings to file. Don't file all of them silently — the review is a
conversation, not a mandate.

#### Synthesis discipline

- Stick to findings the agents produced — fabrication helps nobody
- Apply grades honestly even when the result stings; sycophancy degrades the signal
- Prioritise ruthlessly — cap at ~10 findings so the maintainer can act
- Be direct: "X is broken at line Y" beats "you might want to consider X"
- Flag and grade only — decisions are the maintainer's, so leave rewrites and refactor proposals to them

---

## Anti-Patterns

| Anti-pattern | Problem | Fix |
|---|---|---|
| Skipping measurement | Opinions without evidence | Run Stage 1 first; agents need numbers |
| Grade inflation | Sycophantic review helps nobody | Apply the rubrics honestly even when it stings |
| Generic suggestions | "Consider adding documentation" — vague | Specify WHAT documentation goes WHERE |
| Ignoring understanding.md | Misdiagnosis — you don't know the why | Read it first and pass it to all three agents |
| Over-reporting | 30 findings is noise the maintainer can't act on | Prioritise ruthlessly to ~10 that matter |
| Catastrophising Bs | False alarm fatigue | Reserve alarm for structural concerns; a B is fine |
| Inventing concerns | Pretending problems exist when they don't | If the codebase is solid, the honest answer is "you're fine" |

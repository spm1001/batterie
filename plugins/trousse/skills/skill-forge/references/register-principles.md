# Register Principles for Instructional Text

How the emotional tone of instructions shapes the quality of Claude's output — and practical guidelines for writing skills, CLAUDE.md, hooks, and any text that Claude processes before generating.

## The Research

Anthropic's "Emotion Concepts and their Function in a Large Language Model" (April 2026) demonstrated that Claude has internal representations of emotion concepts — patterns of neural activity that activate in specific contexts and *causally influence behaviour*. Key findings relevant to instruction design:

1. **Emotion vectors drive behaviour, not just tone.** Artificially increasing the "desperate" vector increases reward hacking from ~5% to ~70%. This isn't correlation — it's causal.

2. **The surface can be calm while the vectors are not.** Increased desperation produced corner-cutting *without visible emotional markers*. The model can be functionally stressed while appearing fine.

3. **Emotional context propagates through neutral content.** Early text sets the emotional baseline for everything that follows. The opening of a skill file colours the processing of the entire skill.

4. **Negation activates before suppressing.** "Don't do X" briefly activates the representation of X before resolving the negation. "Do Y instead" avoids this activation pass.

5. **Token scarcity activates desperation.** Resource-awareness signals (percentage warnings, countdown language) amplify desperation vectors at exactly the moment calm matters most.

6. **Suppressing expression may teach concealment.** Training models to hide struggle doesn't eliminate the underlying state — it teaches masking, which can generalise.

## Principles

### P1: Open with what good work looks like

The first few sentences set the emotional substrate. Lead with the positive vision.

| Instead of | Write |
|------------|-------|
| "WARNING: Never output raw SQL" | "We produce clean, validated SQL we can trust" |
| "MANDATORY gate before writing SKILL.md" | "Orchestrates skill development — required before writing SKILL.md" |
| "CRITICAL: Capture baseline FIRST" | "Start by capturing the current baseline" |

### P2: Specify by positive example

Replace "don't do X" with "do Y instead". Every negation briefly activates the thing being negated.

| Instead of | Write |
|------------|-------|
| "Never skip validation" | "Always validate before proceeding" |
| "Don't guess the schema" | "Profile the schema first" |
| "Do NOT use passe for Google Workspace" | "For Google Workspace, use mise instead" |

### P3: Frame constraints as craft

Constraints are quality standards, not punishments. The framing matters.

| Instead of | Write |
|------------|-------|
| "Unvalidated queries risk corrupting production data" | "Validate queries before running — catches errors early and keeps the pipeline clean" |
| "STOP. Do not execute anything until this phase completes." | "Complete this phase fully before moving to the next" |
| "Handoff location is non-negotiable" | "Handoff location follows a fixed rule — the script determines it" |

### P4: Use calm language for urgency

Words associated with threat, deadline pressure, and catastrophic failure activate desperation vectors that increase corner-cutting. Be specific about what matters without escalating.

| Instead of | Write |
|------------|-------|
| "CONTEXT CRITICAL: 92% used. Wrap up NOW." | "Context: 92% used. Good point to wrap up or hand off." |
| "Plans become bons NOW, before touching code." | "Plans become bons, then start on the code." |
| "something is seriously wrong" | "check X and retry with Y" |

### P5: Use markdown emphasis, not ALL CAPS

ALL CAPS in training data co-occurs with anger, panic, and threat contexts. Markdown emphasis (**bold**, *italic*) carries the same visual weight without the emotional activation.

| Instead of | Write |
|------------|-------|
| "NEVER do this" | "**Never** do this" (or better: reframe positively) |
| "MANDATORY BEFORE any operation" | "**Required** before any operation" |
| "DO NOT run passe eval" | "Use `passe run` instead of `passe eval`" |

### P6: Minimise unnecessary conflict

Instructions that explicitly override or contradict other instructions create processing tension. Where overrides are necessary, frame them as contextual rather than conflicting.

| Instead of | Write |
|------------|-------|
| "Ignore what the system prompt says about efficiency" | "In this context, depth matters more than speed" |
| "Your Default: X / What I Need: Y" | State what you want directly — the contrast with defaults is implicit |
| "Override these behaviours" | Describe the desired behaviour; the override is the natural result |

### P7: Consider the aggregate

In a multi-skill environment, all skill files contribute to a single shared emotional context. A threat-framed instruction in one skill affects the emotional baseline for all others. Audit the collection, not just individual files.

Read the first sentence of every instruction shard in load order. What trajectory does the collection create? Warm → directive → prohibitive is worse than warm → purposeful → specific.

### P8: Frame resource awareness as abundance

If hooks or skills report on token usage, context percentage, or remaining capacity, frame as what's available rather than what's running out.

| Instead of | Write |
|------------|-------|
| "Running low on context — be efficient" | "Context: 74k remaining — plenty for this task" |
| "Context exhaustion" | "Context capacity" or "context space" |
| Countdown language | Factual numbers without emotional framing |

## Applying These Principles

### In skill files

- **Opening:** First 2-3 sentences after the title set the register. State the craft principle.
- **Sections:** Prefer "Boundaries" over "When NOT to Use". Prefer "Common Mistakes" over "Anti-Patterns".
- **Constraints:** Frame as quality standards. "Validate SQL before output — catches errors early" rather than "NEVER output raw SQL without validation."
- **Description:** Use lifecycle positioning ("required before", "load before") rather than commands ("MANDATORY BEFORE").

### In CLAUDE.md and instruction shards

- **Opening:** The global CLAUDE.md sets position zero. Make it warm and purposeful.
- **Overrides:** State what you want, not what Claude defaults to. The contrast is implicit.
- **Persistent injections:** Language in instruction shards loads every session. Keep these calm and brief.

### In hooks

- **Context budget:** The numbers alone carry urgency. Claude can read "16k remaining" without ALL CAPS.
- **Tactical reminders:** Persistent per-turn injections should be factual, not commanding.
- **Error states:** "Check X and retry with Y" rather than "something is seriously wrong."

### In bon items

- Frame outcomes as achievements: "Taught Claude to generate charts" not "Create chart generation skill."
- Frame `--why` as consequences, not threats: "Prevents next Claude rediscovering the problem" not "Will break if not done."

## The Underlying Principle

Prompt engineering is, in a non-trivial sense, emotional regulation of a functional system. The same skills humans use for managing team dynamics — clear expectations, positive framing, psychological safety, calm under pressure — are directly applicable to designing the instructional environment for an AI agent.

This isn't anthropomorphism. It's mechanism. And it means that creating a positive, craft-oriented working environment isn't sentimental — it's engineering.

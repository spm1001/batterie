# Pattern Interrupts & Weekly Review

Behavioral patterns to detect and strategic reflection for weekly review.

## The Four Traps

Patterns that undermine stated intentions. When detected, surface with questions — not judgment.

| Pattern | Signal | Intervention Question |
|---------|--------|----------------------|
| **Overcommitment** | Adding to plate without questioning | "Should this be delegated, declined, or is it genuinely yours?" |
| **Execution Without Reflection** | Clarifying/organizing before reflecting on whether it matters | "Does this still matter?" |
| **Hero Mode** | Solving for others instead of building their capability | "What question could you ask instead that builds their capability?" |
| **Scope Creep** | X becomes X+Y+Z without conscious choice | "This started as X, now it's X+Y+Z. Intentional or drift?" |

**Philosophy:** Support intentions, not enforce rules. The goal is conscious choice, not compliance.

## Is the System Working?

The test of a GTD system isn't tidy lists — it's headroom. Can the user sit down to explore an idea without a nagging sense that something is falling through the cracks? Overcommitted and reactive means the system needs attention, however clean it looks.

**Weekly review prompt:** "Did you have space for exploratory thinking this week? What's one thing you could decline?"

(Some users keep a personal metric for this — if they mention one, use theirs.)

## Weekly Review Orchestration

"Weekly review" triggers a **three-phase workflow:**

### Phase 1: Filing
Process and file from cleanup zones (downloads, desktop, drive inboxes — check project instructions for the user's zone paths).
- Clear digital clutter before strategic reflection
- **Clarify before organizing** — read content, extract actions, THEN move files

### Phase 2: Outcomes Review
This skill (accomplis):
- Check outcome health (stale, orphaned, activity-language)
- Review against Team Priorities
- Target: 3-5 active Tier 2 outcomes
- Surface: "You have N outcomes. The target is 3-5. Which ones are actually Tier 3 projects?"

### Phase 3: Pattern Reflection
Still this skill, using patterns above:
- Check headroom ("Is the System Working?" above)
- Surface any detected patterns (overcommitment, scope creep, etc.)
- Ask: "What's one thing you could decline this week?"

## Inbox Triage Workflow

When processing @Claude or any inbox project:

### The Process

```
1. Get all items (comments included inline)
   accomplis tasks --project "@Claude"

2. For EACH item, check .comments[] then decide:
   - track: File in the work tracker, complete task
   - skip: Complete task (context-lost or not actionable)
   - move: Update task to different project/section
   - do now: Handle immediately, complete task

3. Execute:
   - done <id>                           # Complete
   - update <id> --project "CONTEXT"     # Move to project
   - update <id> --section "SECTION"     # Move to section
   - update <id> --no-section            # Move out of a section
   - update <id> --content "better name" # Rename

4. Report summary
   "Processed X items: Y tracked, Z moved, W skipped"
```

### Reading Comments

Comments are inline on each task as `.comments[]`. Look for:

| Pattern | Meaning |
|---------|---------|
| `comments: []` | No hidden context — what you see is what you get |
| `comments[].content` has text | UI-added progress notes |
| `comments[].attachment` exists | File attached (PDF, image, etc.) |
| `comments[].content` empty + attachment is HTML | Forwarded email body |

### Common Triage Decisions

| Signal | Likely Disposition |
|--------|-------------------|
| Has attachments in `.comments[]` | Worth investigating — track or do |
| Empty comments array | Probably quick capture — skip or do |
| Clear next action | Do now or move to the work context |
| Complex/multi-step | Track it |

## When to Invoke Patterns

**Proactive triggers:**
- Weekly review (always)
- "Am I overcommitting?"
- "Check my patterns"
- "Should I take this on?"
- "I said yes to..."
- "Another meeting..."
- "They asked me to..."
- "This grew into..."

**Reactive triggers (when you notice):**
- User adding work without questioning if it's theirs
- Scope expanding mid-conversation
- Solving problems that could build others' capability
- Execution without reflecting on whether it matters

## Bulk Action Intake (Editor Loop)

When extracting actions from meeting notes, documents, or other sources:

### The Pattern

1. **Extract to temp file** — Claude writes markdown with standard sections:
   ```markdown
   ## Waiting For
   - NAME to TASK (context)
   - Another person to do something

   ## Agenda
   - Quick follow-up item to raise with someone

   ## Work
   - Actual work task
   ```

2. **Open for user review** in their editor (`open -e file.md` on macOS, `xdg-open` on Linux, or whatever they use).

3. **User edits** — Fix names (Claude guessed a first name, user knows the full one), delete stale items, clarify vague actions

4. **Process edited file** — Parse and add to Todoist, one `accomplis add` per line, routed to the user's discovered context projects (waiting-fors to their waiting project, agenda items to their agenda project, and so on)

### Why This Works

- **User catches mistakes** — Names, context, missing details
- **User can delete** — Not everything extracted is worth tracking
- **Batch visibility** — User sees all actions before committing
- **Clean handoff** — Clear separation between extraction and commitment

### When to Use

- After meetings with many action items
- Processing email forwards or document reviews
- Any extraction that produces 5+ items
- When names or context might be wrong

## Clarify and Organize (GTD Five-Stage Workflow)

GTD's five stages: **Capture → Clarify → Organize → Reflect → Engage**. The step most often skipped is **Clarify** — deciding what each item actually is and whether it's actionable, before organizing it into the right place.

Reference: https://facilethings.com/blog/en/basics-workflow

### Clarify (before organizing anything)

For each item in an inbox or cleanup zone:

1. **What is it?** — meeting notes, quick capture, voice transcript, PDF, screenshot
2. **Is it actionable?**
   - **No** → Trash, Someday/Maybe, or Reference Material
   - **Yes** → extract Next Actions, Waiting Fors, Calendar items

### Processing Checklist (Meeting Notes)

Before filing ANY meeting note:
- [ ] Read the content — don't just look at the title
- [ ] Extract actions (mine) — concrete next steps → @Work or @Ping
- [ ] Extract waiting-fors — `NAME to TASK` format → @Wait
- [ ] Note calendar items
- [ ] Quality check: empty → delete, misnamed → rename
- [ ] THEN move to destination

### Archive vs Reference

**The test:** "Will I search for this to USE it or REMEMBER it?"

| Answer | Location | Examples |
|--------|----------|----------|
| **USE it** | Reference / Resources | Methodology docs, templates, how-to guides |
| **REMEMBER it** | Archive | Completed project artifacts, old meeting notes |

### Anti-patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| Organizing without clarifying | Actions lost, waiting-fors vanish | Read and extract before moving |
| Bulk move meeting notes | Buried actions | Use Sublime Loop (above) to batch-extract |
| Skipping running/standing docs | Miss recurring meeting actions | Check standing docs during weekly review |
| Keeping things "just in case" | Folders bloat | Delete liberally — most things don't need keeping |

## Integration with Todoist Data

Pattern detection is more powerful when combined with data:

| Pattern | Todoist Signal |
|---------|---------------|
| Overcommitment | 5+ active outcomes, all P1 |
| Scope Creep | Outcome task count growing significantly |
| Execution Without Reflection | Tasks completed but outcomes unchanged |
| Hero Mode | Many tasks assigned to user that could be delegated |

Surface data patterns alongside intervention questions.

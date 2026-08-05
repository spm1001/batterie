# Pattern Interrupts & Weekly Review

Behavioral patterns to detect and strategic reflection for weekly review.

## Structural Detectors (Run Before Coaching Language)

Structure comes first in the review order (see SKILL.md) because coaching words on a structurally broken board wastes the polish. Detectors proven in live reviews:

| Detector | What to do |
|---|---|
| **Sync automations and mirrors** | Before diagnosing duplication as mess, check for systemd timers, launchd agents, and cron jobs that deliberately twin tasks between boards. Edits go to the canonical side — the automation's own description usually names it. |
| **Staleness hides in titles** | Dates written into card titles rot silently ("by June 4th" in bold, two months gone). Sweep titles for date strings against today, not just `--older-than` on creation dates. |
| **Cross-board delegation audit** | Every delegation on a lead's board needs a counterpart on the delegate's board. Complementary slices are fine; absent counterparts are the finding. |
| **Team read-across test** | A cold reader attempts to reconstruct team strategy from the boards alone, then reports what was legible and what wasn't. Live finds: an empty Vision project, no tier marks anywhere, and a strategic theme that existed in card mass but no section named. |
| **Emergent conventions reveal appetite** | Two people independently bolding their biggies means the team wants a highlight tier — codify it (p1) rather than letting folk conventions drift. |
| **Same diseases, every layer** | Altitude-mixing recurs at team scale (a 57-card Goals board hiding a literal next action). The per-board patterns apply at any horizon — run them on Goals and Vision boards too. |

## The Four Traps

Patterns that undermine stated intentions. When detected, surface with questions — not judgment.

| Pattern | Signal | Intervention Question |
|---------|--------|----------------------|
| **Overcommitment** | Adding to plate without questioning | "Should this be delegated, declined, or is it genuinely yours?" |
| **Execution Without Reflection** | Clarifying/organizing before reflecting on whether it matters | "Does this still matter?" |
| **Hero Mode** | Solving for others instead of building their capability | "What question could you ask instead that builds their capability?" |
| **Scope Creep** | X becomes X+Y+Z without conscious choice | "This started as X, now it's X+Y+Z. Intentional or drift?" |

**Philosophy:** Support intentions, not enforce rules. The goal is conscious choice, not compliance.

## "Should I Take This On?" — Ground the Answer First

The answer is in the system, not in general wisdom. **Read the whole system before advising** — one unscoped `accomplis tasks` sweep covers every project at once, and whatever it surfaces belongs in the answer. The spots where the gold usually sits (a floor for your reading, not a fence around it):

- **The Inbox** — is this request already half-captured? A caller's earlier message sitting unprocessed changes the conversation from "new ask" to "open loop".
- **Someday/Maybe** — is this adjacent to a parked ambition? The new ask may be that item's moment — or its competitor for the same hours.
- **The outcomes list** — which outcome would this advance? A dormant outcome it serves is an argument for; serving no outcome at all is the classic drift signal.
- **Waiting-fors and current actions** — the honest load picture, including what's stale and silently costing attention.

Then apply the overcommitment question from The Four Traps — and connect what you found by name: the inbox twin, the someday neighbour, the outcome it would (or wouldn't) advance. Grounded advice cites the user's own system back to them.

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
- Run the review order: structure → altitude → language → arc → tier (see SKILL.md)
- Check outcome health (stale, orphaned, activity-language)
- Review against Team Priorities
- Target: 3-5 outcomes in the highlighted review tier (the full inventory can healthily hold 20-30)
- Surface: "Which of these are real multi-step commitments, and which 3-5 form your review tier?"

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
| Overcommitment | 6+ cards marked p1 — the review tier has lost its selectivity |
| Scope Creep | Outcome task count growing significantly |
| Execution Without Reflection | Tasks completed but outcomes unchanged |
| Hero Mode | Many tasks assigned to user that could be delegated |

Surface data patterns alongside intervention questions.

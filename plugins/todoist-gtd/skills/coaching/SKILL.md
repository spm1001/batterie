---
name: coaching
description: >
  MANDATORY gate BEFORE any Todoist operation — orchestrates GTD semantics the CLI alone can't
  provide (outcomes are sections not tasks, workspace vs personal filtering, horizon alignment).
  Invoke FIRST for weekly review, outcome coaching, and pattern detection. Triggers on 'clean up
  outcomes', 'team priorities', 'is this a good outcome', 'weekly review', 'am I overcommitting',
  'check my patterns', 'should I take this on', 'scope creep', 'freedom score'. (user)
allowed-tools: ["Bash(todoist:*)", Read, AskUserQuestion]
---

# Todoist GTD

## Setup (do this for the user, don't ask)

**Be proactive.** If todoist isn't working, fix it — don't list commands for the user to run.

### 1. Install the CLI (if missing)

Install from the **source repo** — the marketplace cache ships no `pyproject.toml`, so a cache/`CLAUDE_PLUGIN_ROOT` install fails ("does not appear to be a Python project"):
```bash
# Local clone if present, else git+https:
[ -f ~/repos/spm1001/todoist-gtd/pyproject.toml ] \
  && uv tool install ~/repos/spm1001/todoist-gtd --force --reinstall --no-cache \
  || uv tool install 'todoist-gtd @ git+https://github.com/spm1001/todoist-gtd' --force --reinstall --no-cache
export PATH="$HOME/.local/bin:$PATH"
```

The SessionStart hook (`ensure-todoist.sh`) already runs this logic automatically — you usually don't need to install by hand.

### 2. Authenticate

```bash
todoist doctor
```

If doctor reports no token, run `todoist auth` for setup instructions, then `todoist auth --token TOKEN` to store it (Keychain on Mac, plugin data dir on Linux). No manual env vars or shell profile edits needed.

**NEVER echo the API token back to the user.** The token is a secret.

## Overview

MCP-free Todoist integration using the official Python SDK (v4, httpx-based). Adds semantic understanding of GTD structure and outcome quality coaching on top of the CLI's data access.

**Core insight:** The CLI provides data. This skill provides meaning.

## When to Use

**IMPORTANT: Invoke this skill BEFORE making Todoist queries.** The CLI doesn't know the user's GTD structure — this skill does. Without it, you'll query wrong fields (tasks vs sections), miss context (outcomes are sections, not tasks), and produce confusing results.

**Use for:**
- ANY Todoist query or update (load this skill first for context)
- Outcome quality coaching and creation
- Weekly review / strategic reflection
- Pattern detection: overcommitment, scope creep, hero mode
- Before taking on work: "Should I take this on?"

## When NOT to Use

- Simple task creation that doesn't need GTD framing
- Quick queries where you already know the project structure

## Discovering the User's Structure

**DO NOT assume project names or team member details.** Every user's Todoist is different. Discover dynamically:

```bash
# Who am I?
todoist whoami

# What projects exist?
todoist projects

# What's the structure of a specific project?
todoist sections --project "Project Name"

# Who's on a shared project?
todoist collaborators --project-id "<id>"
```

### The Universal GTD Pattern in Todoist

Regardless of how each user names their projects, look for this structure:

| GTD Concept | Where in Todoist | How to Find |
|-------------|------------------|-------------|
| Desired Outcomes | Sections in an outcomes project | Look for projects named like "Desired Outcomes", "Goals", "OKRs" |
| Next Actions | Tasks under outcome sections, or in context projects | Look for projects named with @ prefix or action-oriented names |
| Waiting For | Tasks in a waiting/follow-up project | Look for "@Wait", "Waiting For", or similar |
| Someday/Maybe | Tasks in a someday/backlog project | Look for "@Someday", "Someday/Maybe", or similar |
| Areas of Focus | Sections in an areas project | Look for "Areas of Focus", "Responsibilities", or similar |
| Reference | Projects for reference material | Varies by user |

### Outcomes Are Sections (Not Tasks!)

This is the most critical structural insight:

```
Desired Outcomes Q2 (project)
  +-- Built team capacity for... (section = outcome)
  |     +-- [tasks under this section]
  +-- Established new measurement... (section = outcome)
  +-- Secured commitment to... (section = outcome)
```

**Why it matters:** Outcomes are SECTIONS. Query with `sections`, not `tasks`.

### Workspace vs Personal Projects

The CLI auto-detects workspace (team) projects and filters accordingly:

| Project Type | Signal | Default Behavior |
|-------------|--------|------------------|
| **Personal** | No `workspace_id` | Shows all tasks (no filtering) |
| **Personal with collaborators** | Collaborators but no `workspace_id` | Shows all tasks (they're all yours) |
| **Workspace (team)** | Has `workspace_id` | Auto-filters to your tasks only |

**Flags for workspace projects:**
- Default: shows only tasks assigned to you
- `--unassigned`: shows unassigned tasks (triage mode)
- `--team`: shows all team members' tasks
- `--assignee "Name"`: shows specific person's tasks

```bash
# Your tasks on a shared project (default)
todoist tasks --project "Shared Project"

# Triage unassigned tasks
todoist tasks --project "Shared Project" --unassigned

# Everyone's tasks
todoist tasks --project "Shared Project" --team

# Specific person
todoist tasks --project "Shared Project" --assignee "Full Name"
```

### GTD Contexts Are Projects

**GTD contexts (like @Wait, @Work, @Someday) are PROJECTS, not labels.** Query with `--project`, not `--label`.

```bash
todoist tasks --project "@Wait"        # Correct
todoist tasks --label "waiting-for"    # Wrong (unless user uses labels)
```

Discover the user's context projects by listing all projects and looking for the @ prefix pattern or similar naming convention.

## GTD Methodology

### Horizons of Focus

GTD organises commitments across six horizons. Each horizon informs the ones below it:

| Horizon | Focus | Question | Review Cadence |
|---------|-------|----------|----------------|
| **H5: Purpose** | Why do I exist in this role? | "What's my unique contribution?" | Annual |
| **H4: Vision** | What does success look like in 3-5 years? | "Where am I heading?" | Quarterly |
| **H3: Goals** | What do I want to achieve in 1-2 years? | "What milestones matter?" | Quarterly |
| **H2: Areas of Focus** | What are my ongoing responsibilities? | "Am I covering all my areas?" | Monthly |
| **H1: Projects/Outcomes** | What multi-step results am I committed to? | "What's on my plate?" | Weekly |
| **Ground: Actions** | What's the next physical action? | "What do I do right now?" | Daily |

**In Todoist mapping:**
- H1-H2 live in outcomes and areas projects
- Ground level lives in context projects (@Work, @Wait, etc.)
- H3-H5 are typically in annual/strategic projects or outside Todoist

### The Five Steps of GTD Mastery

1. **Capture** — Get everything out of your head into a trusted system
2. **Clarify** — Decide what each item is and whether it's actionable
3. **Organise** — Put things where they belong (project, context, waiting, someday)
4. **Reflect** — Review regularly (weekly review is the critical habit)
5. **Engage** — Choose what to do with confidence

### Natural Planning Model

When creating or coaching on outcomes, use this framework:

1. **Purpose** — Why are we doing this? What's the strategic reason?
2. **Vision** — What does wild success look like?
3. **Brainstorming** — What are all the ideas, concerns, loose ends?
4. **Organising** — What's the sequence? What depends on what?
5. **Next Actions** — What's the very next physical action?

**Use this when:** Creating new outcomes, reviewing stale outcomes, or when someone is stuck on "where do I start?"

### Tier 2 vs Tier 3: The Critical Distinction

**Tier 2 (Outcomes) ask:** "What do I want to have achieved?"
**Tier 3 (Projects/Actions) ask:** "What do I need to do?"

**Quick test:**
- "Write the strategy doc" -> Tier 3 (activity)
- "Team has clear Q4 direction" -> Tier 2 (achievement)

**The pattern:** Past-tense verb, describes what's *different* when done, includes the "so what".

| Activity (Tier 3) | Achievement (Tier 2) |
|--------------------|---------------------|
| Write the docs | New team members can onboard within a day |
| Build rate limiter | API stays responsive under peak load |
| Attend conference | Established voice in industry discussions |
| Complete audit | Audit trail catches anomalies before users notice |

**For the full GTD methodology** (5 stages, clarify decision tree, setup guidance, review cadences): See [references/GTD_METHODOLOGY.md](references/GTD_METHODOLOGY.md)

**For detailed coaching patterns and examples:** See [references/COACHING.md](references/COACHING.md)

## Terminology Disambiguation

**"Project" has 3 meanings:**

| Context | Meaning | Example |
|---------|---------|---------|
| Todoist | Container for tasks | An outcomes project |
| GTD Tier 3 | Multi-step outcome | "Launch Panel+ v2" |
| Business | Work initiative | "The migration project" |

**For full terminology guide:** See [references/TERMINOLOGY.md](references/TERMINOLOGY.md)

## CLI Query Patterns

**All commands return JSON.** Key patterns:

```bash
todoist sections --project "Outcomes Project"           # Outcomes (sections!)
todoist tasks --section-id "<outcome-id>"               # Tasks under an outcome
todoist tasks --project "@Wait" --older-than 30d        # Stale waiting-fors
todoist filter "assigned to: me"                        # Your tasks across projects
todoist tasks --project "@Work" --include-section-name  # Tasks with section context
```

**Critical:** `tasks` and `task` return complete objects with `.comments[]` inline. `filter` returns tasks only (no comments — filters can span projects).

**For full query patterns, data model, and API limitations:** see [references/CLI_REFERENCE.md](references/CLI_REFERENCE.md)

## Write Operation Guardrails

### Creating Outcomes

**BEFORE creating, use the Natural Planning Model:**
1. What's the purpose? (Why does this matter?)
2. What does success look like? (Vision of done)
3. Which area of focus does it serve?

**Outcome goes in:** A section in the user's outcomes project
**Tasks go under:** That outcome section

```bash
# DON'T create outcome as a task
todoist add "Build team documentation"  # WRONG

# DO create as section in the outcomes project
todoist add-section "Built team capacity through documentation" \
  --project "Desired Outcomes Q2"  # CORRECT (use actual project name)
```

### Writing Next Actions (GTD Style)

**Next actions must be concrete, physical, and start with a verb describing what you'd actually do.**

Bad (vague, outcome-ish):
- "Sort out the legal stuff"
- "2026 planning"

Good (concrete, physical):
- "Read the brief and note 3 questions for the meeting"
- "Open the deck + outcomes list, draft team plan skeleton"

**The test:** "What would I actually do when I sit down to do this?"

### Entrusting Pattern (Delegation)

When delegating an outcome:

1. **Create a structured delegation doc** with: desired outcome, why, resources needed, update cadence, deadline, response options
2. **Link the doc** in the Todoist item description
3. **Create a follow-up item** in the appropriate context project
4. **Outcome stays assigned to delegator** until the conversation happens

### Completing vs Deleting Tasks

**ALWAYS complete, NEVER delete** (unless truly erroneous).

- Completed tasks preserve history for future planning
- Duplicates should be completed with a note
- Obsolete items should be completed (still counts as "resolved")

### Anti-Patterns

| Bad Practice | Why Wrong | Better |
|--------------|-----------|--------|
| Creating outcome as task | Confuses structure | Use `add-section` |
| Tier 3 project as outcome | Inflates outcome count | Challenge: "Activity or achievement?" |
| Completing without reflection | Loses learning | Prompt for resolution notes |
| Joint ownership | No clear driver, item drifts | One owner per outcome |
| No next action on active outcome | Outcome stalls invisibly | Every active outcome needs at least one next action |

## Review Cadences

### Daily Review (~10-15 mins)

Three parts: **Clarify, Check Lists, Calendar.**

1. **Clarify** — Process inboxes to empty (email, Todoist inbox, other capture points)
2. **Check Lists** — Quick scan: agenda items for today, stale waiting-fors, projects missing next actions
3. **Calendar** — Next 7 days, agendas for today's meetings

### Weekly Review (~45-60 mins)

Three phases: **Get Clear, Get Current, Get Creative.**

1. **Get Clear** — Mind sweep all capture points, clarify everything to zero
2. **Get Current** — Review all projects, next actions, waiting-fors, calendar
3. **Get Creative** — Review someday/maybe, notice what's missing, generate ideas

**For the full review checklists:** See [references/GTD_METHODOLOGY.md](references/GTD_METHODOLOGY.md#stage-4-reflect)

**For pattern detection and coaching:** See [references/PATTERNS.md](references/PATTERNS.md)

## Pattern Intervention Triggers

Surface these concerns when analysing data:

**Overcommitment:**
- 5+ active outcomes -> "Can you really advance all of these?"
- All outcomes high priority -> "If everything is critical, nothing is focused"

**Strategic gaps:**
- Outcome has no tasks -> "Stuck, deprioritized, or needs rescoping?"
- No outcomes in an area of focus -> "Dormant area — intentional?"

**Staleness:**
- Outcome unchanged 4+ weeks -> "Stuck, deprioritized, or needs rescoping?"

**Quality:**
- Outcome reads like activity -> "This is what you're doing, not achieving"
- Missing success criteria -> "How will you know when it's done?"

## Claude Inbox Patterns

If the user has a Claude-specific inbox project:

1. Query it: `todoist tasks --project "@Claude"` (or whatever it's named)
2. For each item: check `.comments[]` for context
3. Decide: do now, move, or complete

See [references/PATTERNS.md](references/PATTERNS.md#inbox-triage-workflow) for the full workflow.

## Quick Reference

### Key Queries

| Query | CLI Command |
|-------|-------------|
| All projects | `todoist projects` |
| Current user | `todoist whoami` |
| Outcomes | `todoist sections --project "OUTCOMES_PROJECT"` |
| Tasks under outcome | `todoist tasks --section-id "<outcome-id>"` |
| Tasks with section names | `todoist tasks --project "X" --include-section-name` |
| Person's work | `todoist tasks --project "X" --assignee "Name"` |
| Unassigned (triage) | `todoist tasks --project "X" --unassigned` |
| Stale waiting-fors | `todoist tasks --project "@Wait" --older-than 30d` |
| Today's tasks | `todoist filter "today"` |

### Key Write Operations

| Operation | CLI Command |
|-----------|-------------|
| Create outcome | `todoist add-section "name" --project "OUTCOMES_PROJECT"` |
| Create task | `todoist add "content" --project "PROJECT" --section "SECTION"` |
| Complete task | `todoist done "<task-id>"` |
| Rename task | `todoist update "<task-id>" --content "new name"` |
| Move to project | `todoist update "<task-id>" --project "PROJECT"` |
| Move to section | `todoist update "<task-id>" --section "SECTION"` |

**Note:** Replace `OUTCOMES_PROJECT`, `PROJECT`, `SECTION` with the user's actual project/section names discovered via `todoist projects` and `todoist sections`.

## Remember

**The CLI is plumbing. This skill is meaning.**

- Outcomes are SECTIONS, not tasks
- Discover structure dynamically — never assume project names
- "Project" means different things in different contexts
- Challenge activity language -> frame as achievement
- Surface patterns, not just data
- Use horizons of focus for strategic context
- Use natural planning model for outcome creation

---
name: todoist-gtd
description: >
  Orchestrates Todoist queries with GTD semantics. LOAD BEFORE any Todoist operation — CLI alone
  doesn't know the user's structure (outcomes are sections, not tasks; team vs personal; 3-tier
  ontology). Prevents wrong-field queries and missing context. Handles weekly review and pattern
  detection. Triggers on 'clean up outcomes', 'team priorities', 'is this a good outcome',
  'weekly review', 'am I overcommitting', 'check my patterns', 'should I take this on',
  'I said yes to', 'scope creep', 'freedom score', or ANY Todoist-related task. (user)
allowed-tools: ["Bash(todoist:*)", Read, AskUserQuestion]
---

# Todoist GTD

## Setup (do this for the user, don't ask)

**Be proactive.** If todoist isn't working, fix it — don't list commands for the user to run.

### 1. Install the CLI (if missing)

Find and install from the plugin cache:
```bash
TODOIST_DIR=$(find ~/.claude/plugins/cache -path "*/todoist-gtd/*/pyproject.toml" -exec dirname {} \; 2>/dev/null | head -1)
uv tool install "$TODOIST_DIR"
export PATH="$HOME/.local/bin:$PATH"
```

If `CLAUDE_PLUGIN_ROOT` is set, use that instead: `uv tool install "${CLAUDE_PLUGIN_ROOT}"`.

### 2. Authenticate

```bash
todoist doctor
```

If doctor reports no token, run `todoist auth`. This opens the Todoist settings page, prompts for the API token, and stores it (Keychain on Mac, `~/.todoist-token` on Linux). No manual env vars or shell profile edits needed.

**NEVER echo the API token back to the user.** The token is a secret.

## Overview

MCP-free Todoist integration using the official Python SDK (v1 API). Adds semantic understanding of the user's GTD structure and outcome quality coaching on top of the CLI's data access.

**Core insight:** The CLI provides data. This skill provides meaning.

## When to Use This Skill

**IMPORTANT: Invoke this skill BEFORE making Todoist queries.** The CLI doesn't know the user's GTD structure — this skill does. Without it, you'll query wrong fields (tasks vs sections), miss context (outcomes are sections, not tasks), and produce confusing results.

**Use for:**
- ANY Todoist query or update (load this skill first for context)
- "Help me clean up my Q1 outcomes"
- "Is the team working on the right things this quarter?"
- "Check my priorities against the yearly plan"
- "Is this a good outcome?"
- Weekly review / strategic reflection
- Creating or updating outcomes with proper structure
- Pattern detection: "Am I overcommitting?", "Check my patterns"
- Before taking on work: "Should I take this on?", "I said yes to..."

## When NOT to Use

- Personal GTD Tier 3 tasks (not in scope for coaching, though queries are fine)
- Simple task creation that doesn't need GTD framing

## Weekly Review Orchestration

Weekly review triggers a **three-phase workflow:**

1. **Filing** — Process and file from cleanup zones. Check project CLAUDE.md for zone paths and Drive structure. Clear digital clutter before strategic reflection.
2. **Outcomes Review** — This skill: outcome health, staleness, Tier 2 vs 3 quality
3. **Pattern Reflection** — This skill: freedom score, pattern interrupts

**For detailed patterns:** See [references/PATTERNS.md](references/PATTERNS.md)

## Prerequisites

Before using this skill, verify the CLI is working:

```bash
todoist doctor
```

**Expected:** All checks pass.

**If checks fail:**
- `command not found` → Run `uv tool install ~/Repos/todoist-gtd`
- Not authenticated → Run `todoist auth`

**System requirements:**
- Python 3.9+
- `uv tool install ~/Repos/todoist-gtd` (installs CLI + dependencies in isolated venv)
- macOS Keychain (or `TODOIST_API_KEY` env var for Linux)
- Network access to api.todoist.com

## CLI Setup

```bash
todoist doctor    # Check setup
todoist auth      # OAuth setup (one-time)
```

CLI shows ALL tasks by default (no hidden filtering). For full auth options, error handling, and troubleshooting: see [references/CLI_REFERENCE.md](references/CLI_REFERENCE.md#cli-setup)

## the user's Todoist Structure

**CRITICAL:** This structure differs from standard Todoist usage.

### Outcomes as Sections (not tasks!)

```
Desired Outcomes Q2 (project)
  ├── Made more of the LDC data usable... (section = outcome)
  │     └── [tasks under this section]
  ├── Laid the groundwork for 10x... (section = outcome)
  └── Built team capacity for 2026... (section = outcome)
```

**Why it matters:** Outcomes are SECTIONS, not tasks. Query with `sections`, not `tasks`.

### Key Projects

| Project | Purpose |
|---------|---------|
| `@Work` | Active next actions (personal GTD context) |
| `Desired Outcomes Q2` | Current quarter outcomes (MIT shared) |
| `Desired Outcomes 2026` | Annual outcomes (MIT shared) |
| `Areas of Focus` | AoF categories as sections (MIT shared) |
| `@Claude` | Async inbox for Claude sessions |
| `@Someday` | Backlog (personal) |
| `@Wait` | Waiting for others |

**⚠️ GTD contexts (@Wait, @Claude, @Ping, @Time) are PROJECTS, not labels.** Query with `--project "@Wait"`, not `--label "waiting-for"`.

**⚠️ Always filter by assignee on shared projects.** Desired Outcomes and Areas of Focus are MIT-shared — without `--assignee "Full Name"` you get the whole team's items. Use `todoist filter "assigned to: me"` for the user, or `--assignee "Full Name"` (full name required, not partial).

### Personal vs MIT Shared Projects

**This CLI connects to ONE account, but it contains BOTH personal and MIT shared projects.**

| Type | Projects | Visibility | Use For |
|------|----------|------------|---------|
| **Personal** | `Personal`, `@Home`, `Checklists/*`, `Objective raw material` | Only user | Private outcomes, home tasks, personal reference |
| **MIT Shared** | `Desired Outcomes Q2`, `Desired Outcomes 2026`, `Areas of Focus`, `Team Inbox`, `Someday/Maybe` (team) | Team can see | Work outcomes, team tasks |
| **GTD System** | `@Work`, `@Wait`, `@Ping`, `@Timed`, `@Claude`, `@Someday`, `@Home` | Only user | GTD contexts (not outcomes) |

**⚠️ Critical distinction:**
- **`Personal` project** has a "Desired Outcomes" *section* → **private** personal outcomes
- **`Desired Outcomes Q2`** is a *project* in the MIT shared workspace → **team** work outcomes
- **`@Work`** is a personal GTD context for next actions, NOT a shared project

**When user says "add a personal outcome"** → `Personal` project, "Desired Outcomes" section
**When user says "add a work outcome"** → `Desired Outcomes Q2` or `2026` project

**The user also has a separate Team Todoist account** (not accessible via this CLI) for Tier 1 leadership priorities. When user mentions "team account", that's inaccessible here.

### MIT Team Members

The MIT shared workspace has 8 collaborators. Use `todoist collaborators --project-id "<id>"` to get the canonical list.

| Name | Todoist ID | Email (Todoist) |
|------|-----------|-----------------|
| Sameer Modha | 2054816 | todoist.sameer@planetmodha.com |
| Lauren Thomas | 56446878 | lauren.thomas2@itv.com |
| Ella Collis | 55347117 | ella.collis@itv.com |
| Judi Hu | 56443712 | judi.yin.hu@gmail.com |
| Ellie Martin | 57537553 | ellie.martin@itv.com |
| Stefano Figoni | 55347230 | stefano.figoni@itv.com |
| Alex Green | 50438623 | alexander.green@itv.com |
| Rupert Coghlan | 45273151 | r.coghlan@gmail.com |

Note: Judi and Rupert use personal emails on Todoist, not ITV emails.

### Assignee Filtering

**⚠️ CRITICAL: Shared projects contain tasks assigned to ALL team members. Always filter by assignee when looking at Sameer's work.**

```bash
# Sameer's tasks only (use "me" — works because CLI is authenticated as Sameer)
todoist tasks --project "Desired Outcomes Q2" --assignee "Sameer Modha"
todoist filter "assigned to: me"
todoist filter "assigned to: me & today"

# Specific team member (use full name as shown in collaborators)
todoist tasks --project "Desired Outcomes Q2" --assignee "Lauren Thomas"
todoist filter "assigned to: Lauren Thomas"

# Unassigned tasks (need triage — no CLI flag, pipe through python)
todoist tasks --project "PROJECT" 2>/dev/null > /tmp/tasks.json && python3 << 'PYEOF'
import json
with open("/tmp/tasks.json") as f:
    data = json.load(f)
for t in data:
    if not t.get("assignee_id"):
        print(f"  UNASSIGNED: {t['content'][:80]}  id={t['id']}")
PYEOF
```

**Common mistakes:**
- Querying `Desired Outcomes Q2` without `--assignee` returns ALL 74 team tasks, not just Sameer's 17
- `todoist filter "assigned to: Sameer"` returns 0 — must use full name "Sameer Modha" or "me"
- `--assignee` requires `--project` or `--project-id` — it's a client-side filter, not API-level

**Cross-workspace move restriction:**
Moving a task between workspaces (e.g. MIT shared → personal projects) returns **403 Forbidden**. Todoist does not allow cross-workspace moves via the API. The workaround is delete + re-create:

```bash
# Can't do this (403):
todoist update "<task-id>" --project "@Someday"  # personal project

# Instead: note the content, delete, re-create
todoist delete "<task-id>"
todoist add "task content" --project "@Someday"
```

This loses comments and history — note anything important before deleting.

## Terminology Disambiguation

**"Project" has 3 meanings:**

| Context | Meaning | Example |
|---------|---------|---------|
| Todoist | Container for tasks | `Desired Outcomes Q2` project |
| GTD Tier 3 | Multi-step outcome | "Launch Panel+ v2" |
| Business | Work initiative | "The clean rooms project" |

**For full terminology guide:** See [references/TERMINOLOGY.md](references/TERMINOLOGY.md)

## The 3-Tier GTD Ontology

| Tier | What | Where in Todoist | Managed By |
|------|------|------------------|------------|
| **Tier 1** | Team Priorities | Team Todoist (not accessible here) | Leadership |
| **Tier 2** | Individual Outcomes | Sections in `Desired Outcomes Q2` | the user |
| **Tier 3** | Projects & Actions | Tasks under outcome sections | the user |

### Tier 2 vs Tier 3: The Critical Distinction

**Tier 2 asks:** "What do I want to have achieved?"
**Tier 3 asks:** "What do I need to do?"

**Quick test:**
- "Write the strategy doc" → Tier 3 (activity)
- "Team has clear Q4 direction" → Tier 2 (achievement)

**Rewrite examples (activity → achievement, verb-first past tense):**

| Activity language (bad) | Achievement language (good) |
|------------------------|----------------------------|
| Review Claude workspace MCP | Decided on workspace MCP authentication approach |
| Create Image generation skill | Created image generation skill for Claude to use NanoBanana |
| Build mega-arc synthesis tool | Figured out how to review and plan arc items across Repos |
| Improve Conceptual Charts skill | Taught Claude how to make decent quality conceptual charts |

**The pattern:** Start with past-tense verb, describe what you'll *have done*, include the "so what" (why it matters or what decision it enables).

**For coaching patterns and examples:** See [references/COACHING.md](references/COACHING.md)

## CLI Query Patterns

**All commands return JSON.** Key patterns:

```bash
todoist sections --project "Desired Outcomes Q2"    # Outcomes (sections, not tasks!)
todoist tasks --section-id "<outcome-id>"            # Tasks under an outcome
todoist tasks --project "@Wait" --older-than 30d     # Stale waiting-fors
todoist filter "assigned to: Alex"                   # Filter syntax
todoist tasks --project "@Work" --include-section-name  # Tasks with section context
```

**Critical:** `tasks` and `task` return complete objects with `.comments[]` inline. `filter` returns tasks only (no comments — filters can span projects).

**For full query patterns, data model, and API limitations:** see [references/CLI_REFERENCE.md](references/CLI_REFERENCE.md#query-patterns)

## Write Operation Guardrails

### Creating Outcomes

**BEFORE creating, always ask:**
1. Is this Tier 2 (achievement) or Tier 3 (activity)?
2. Which Team Priority does it serve?
3. What does success look like?

**Outcome goes in:** A section in `Desired Outcomes Q2/H1`
**Tasks go under:** That outcome section

```bash
# DON'T create outcome as a task
todoist add "Build team documentation"  # WRONG

# DO discuss and create as section
todoist add-section "Built team capacity through documentation" \
  --project-id "<desired-outcomes-q4>"  # CORRECT
```

### Completing vs Deleting Tasks

**ALWAYS complete, NEVER delete.**

```bash
todoist done "<task-id>"  # CORRECT - preserves history
# No delete command in CLI                   # By design - prevents history loss
```

Why this matters:
- Completed tasks show in stats and activity logs
- Completion history informs future planning ("what did we achieve last quarter?")
- Duplicates should be completed with a note, not deleted

**Use cases:**
- Task done → `todoist done <id>`
- Task is duplicate → complete it (history shows it was captured)
- Task obsolete → complete it (still counts as "resolved")
- Task moved elsewhere → complete it with a note in Todoist

**Before completing outcomes (sections):** Prompt for reflection:
- "What did we learn?"
- "What comes next?"

### Writing Next Actions (GTD Style)

**Next actions must be concrete, physical, and start with a verb describing what you'd actually do.**

Bad (vague, outcome-ish):
- "Sort out the legal stuff"
- "2026 planning"
- "Marketing Week articles"

Good (concrete, physical):
- "Read EK doc and note 3 questions for Ella meeting"
- "Open CS&P 2026 deck + H1 outcomes list, draft team plan skeleton"
- "Open Marketing Week folder, pick one article idea, write first draft"

**The test:** "What would I actually do when I sit down to do this?"

If the answer isn't immediately obvious from the task title, it's not a next action - it's a project or outcome that needs breaking down.

### Entrusting Pattern (Delegation)

When delegating an outcome to someone:

1. **Create a structured delegation doc** with these headings:
   - What's the desired outcome?
   - Why do you want that outcome?
   - What information/resources are useful and needed?
   - At what stages would I like to be updated?
   - When does it need to be achieved by?
   - Response options (ask for clarity / accept / decline / reflect / propose alternative)
2. **Link the doc** in the Todoist item description
3. **Create a @Ping item**: "Entrust X to Y" with the doc link
4. **Outcome stays assigned to you** until the conversation happens

**@Ping vs @Wait:** @Ping = things to raise with people (follow-ups, discussion points, entrusting). @Wait = things others owe you that you're tracking.

### Cross-Workspace Moves

**Moving tasks between shared and personal workspaces is forbidden** (returns 403). If you need to move an item from a shared project (e.g. MIT Desired Outcomes) to a personal project (e.g. @Someday), the workaround is delete + recreate. This loses comments and history.

**Reassignment works:** `todoist update ID --assignee "Full Name"` resolves the name via the project's collaborator list.

### Anti-Patterns

| Bad Practice | Why Wrong | Better |
|--------------|-----------|--------|
| Creating outcome as task | Confuses structure | Use `add-section` |
| Tier 3 project as outcome | Inflates outcome count | Challenge: "Is this activity or achievement?" |
| Outcome without Team Priority | Orphan work | Ask: "Which priority does this serve?" |
| Completing without reflection | Loses learning | Prompt for resolution notes |
| Joint ownership ("work with X to...") | No clear driver, item drifts | One owner per outcome. Others contribute, one person drives. |
| No next action on active outcome | Outcome stalls invisibly | Every active outcome needs at least one concrete next action in @Work |
| Querying shared projects without assignee filter | Returns whole team's work, not yours | Always use `--assignee "Full Name"` or `filter "assigned to: me"` |

## Pattern Intervention Triggers

Surface these concerns when analyzing data:

**Overcommitment signals:**
- 5+ active outcomes → "Can you really advance all of these?"
- All outcomes P1 → "If everything is critical, nothing is focused"

**Strategic gaps:**
- Outcome has no tasks → "This outcome has no active work - stuck or deprioritized?"
- No outcomes in an AoF → "This area is dormant - intentional?"

**Staleness signals:**
- Outcome unchanged 4+ weeks → "Stuck, deprioritized, or needs rescoping?"
- Growing Someday/Maybe → "Commitment backlog or idea capture?"

**Quality signals:**
- Outcome reads like activity → "This is what you're doing, not what you're achieving"
- Missing success criteria → "How will you know when it's done?"

## Claude Inbox Patterns

### Session Start Behavior

1. **Query the @Claude inbox:**
   ```bash
   todoist tasks --project "@Claude"
   ```
   Returns complete tasks with `.comments[]` inline — no separate calls needed.

2. **Surface items:** "You have X items in @Claude..."

3. **For each item:** Check `.comments[]` for attachments/context, then decide: bead, skip, move, or do now.

See [references/PATTERNS.md](references/PATTERNS.md#inbox-triage-workflow) for the full triage workflow.

## Common Analysis Workflows

### "Clean up my Q1 outcomes"

1. Get outcomes: `todoist sections --project-id "<desired-outcomes-q1>"`
2. For each outcome, check:
   - Is it achievement language? (Tier 2 test)
   - Does it have active work? `todoist tasks --section-id "<id>"`
   - Is it still relevant?
3. Surface: "You have X outcomes. 3 have no active tasks. 2 read like activities."

### "Is the team working on the right things?"

1. Get team-relevant outcomes
2. Cross-reference with Team Priorities (from memory/discussion)
3. Surface: "Outcomes X and Y align with Priority A. Outcome Z seems orphaned."

### "Prepare for 1-1 with Alex"

```bash
todoist filter "assigned to: Alex"
todoist filter "assigned to: Alex & @waiting-for"
```

Surface: "Alex has X outcomes, Y waiting-fors. [Summary of each]"

## Integration with Other Skills

**Coordinates with:**
- **Project CLAUDE.md** — filing zones and Drive structure live in per-project CLAUDE.md files. Check these during weekly review Phase 1.
- **google-workspace** - For document research related to outcomes

**Pattern:** This skill combines data (CLI queries) with judgment (pattern detection, coaching).

## Quick Reference

### Key Queries

| Query | CLI Command |
|-------|-------------|
| All projects | `todoist projects` |
| All outcomes | `todoist sections --project "Desired Outcomes Q2"` |
| Tasks under outcome | `todoist tasks --section-id "<outcome-id>"` |
| Tasks with section names | `todoist tasks --project "@Work" --include-section-name` |
| Person's work | `todoist tasks --project "X" --assignee "Name"` |
| Waiting-fors | `todoist tasks --project "@Wait"` |
| Stale waiting-fors | `todoist tasks --project "@Wait" --older-than 30d` |
| Someday/Maybe | `todoist tasks --label "someday-maybe"` |
| @Claude inbox | `todoist tasks --project "@Claude"` |
| Today's tasks | `todoist filter "today"` |

**Note:** `tasks` and `task` return complete objects with `.comments[]` inline. `filter` returns tasks only (no comments — intentional, as filters can span projects and N+1 API calls would be slow).

### Key Write Operations

| Operation | CLI Command |
|-----------|-------------|
| Create outcome | `todoist add-section "name" --project "Desired Outcomes Q2"` |
| Create task | `todoist add "content" --project "@Work" --section "Now"` |
| Complete task | `todoist done "<task-id>"` |
| Rename task | `todoist update "<task-id>" --content "new name"` |
| Move to project | `todoist update "<task-id>" --project "@Ping"` |
| Move to section | `todoist update "<task-id>" --section "Now"` |
| Move to project+section | `todoist update "<task-id>" --project "@Work" --section "Now"` |

## Success Metrics

**Good analysis achieves:**
- User understands outcome health (active, stale, orphaned)
- Tier confusion corrected (activity → achievement)
- Strategic alignment visible (outcomes → priorities)
- Pattern concerns raised proactively

**Signs of poor analysis:**
- Just listing data without patterns
- Missing the "so what?" - data without insight
- Not challenging potential issues

## Remember

**The CLI is plumbing. This skill is meaning.**

- Outcomes are SECTIONS, not tasks
- "Project" means different things in different contexts
- Challenge activity language → frame as achievement
- Surface patterns, not just data
- Raise pattern concerns proactively
- CLI shows ALL tasks by default — no hidden filtering gotcha

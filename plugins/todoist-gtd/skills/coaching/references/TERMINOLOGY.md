# Terminology Reference

Disambiguate terms that have multiple meanings in the user's context.

## "Project" (3 Meanings)

### 1. Todoist Project (Container)

The Todoist concept of a project - a container for tasks and sections.

**Examples:**
- `Desired Outcomes Q4` (contains outcome sections)
- `@Work` (contains Now/Later sections)
- `HH:Lift` (kanban-style project)

**MCP:** `find_projects()`, `projectId` parameter

### 2. GTD Project (Tier 3 - Multi-Step Outcome)

David Allen's definition: "Any desired result that requires more than one action step."

**Examples:**
- "Complete the Panel+ documentation"
- "Set up automated reporting"
- "Hire data scientist"

**In Todoist:** These are TASKS under an outcome section, or sometimes parent tasks with subtasks.

**NOT:** These are NOT outcomes (Tier 2). They're the work that achieves outcomes.

### 3. Business Project (Work Initiative)

A business initiative or workstream, often involving multiple people.

**Examples:**
- "The clean rooms project"
- "The LDC migration project"
- "The BARB expansion project"

**In Todoist:** Often represented as a project with kanban sections (To Do, Doing, Done).

## "Outcome" (2 Meanings)

### 1. Desired Outcome (Tier 2)

A strategic achievement that contributes to Team Priorities AND provides growth opportunity.

**Characteristics:**
- Written in past tense ("Built team capacity through...")
- Achievement, not activity
- Has success criteria
- Finite (can be completed)

**In Todoist:** A SECTION in `Desired Outcomes Q4` or `Desired Outcomes H1`.

### 2. Generic Result

Any result of work. Common usage but less precise.

**When the user says "outcome":** Usually means the Tier 2 specific definition.

## "Priority" (2 Meanings)

### 1. Team Priority (Tier 1)

Quarterly strategic focus for the team. Set by leadership.

**Examples:**
- "Expand cross-broadcaster measurement"
- "Build self-serve capabilities"
- "Strengthen supplier relationships"

**In Todoist:** Team account (not accessible via MCP). Referenced in personal account via outcome links.

### 2. Task Priority (P1-P4)

Todoist's built-in priority levels.

| Level | Meaning |
|-------|---------|
| P1 | Highest - critical quarterly focus |
| P2 | High - active work |
| P3 | Medium - important but not urgent |
| P4 | Lowest - someday/maybe |

## "Section" (Todoist-Specific)

A subdivision within a Todoist project.

**In the user's structure:**
- In `Desired Outcomes Q4`: Sections ARE outcomes
- In `@Work`: Sections are Now/Later
- In kanban projects: Sections are To Do/Doing/Done

## Areas of Focus (AoF)

GTD concept: Ongoing areas of responsibility with no completion date.

**Examples:**
- "Product Ownership"
- "Stakeholder Influencing"
- "Team Development"

**In Todoist:**
- Sections within `Areas of Focus` project
- Also used as prefixes for outcome folders in Google Drive

**Different from outcomes:** Areas are infinite, outcomes are finite.

## Tier Reference

| Tier | Name | Scope | Managed By | In Todoist |
|------|------|-------|------------|------------|
| 1 | Team Priorities | Team quarterly focus | Leadership | Team account |
| 2 | Individual Outcomes | Personal achievements | the user | Sections in `Desired Outcomes` |
| 3 | Projects & Actions | Execution | the user | Tasks under outcome sections |

## Quick Disambiguation

When the user mentions... he probably means:

| Phrase | Likely Meaning |
|--------|----------------|
| "my projects" | Tier 3 GTD projects (multi-step work) |
| "the project" | Business project/initiative |
| "project in Todoist" | Todoist container |
| "my outcomes" | Tier 2 desired outcomes |
| "team priorities" | Tier 1 (not in this Todoist) |
| "areas of focus" | Ongoing responsibilities |

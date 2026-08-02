# Terminology Reference

Disambiguate terms that have multiple meanings in the user's context.

## "Project" (3 Meanings)

### 1. Todoist Project (Container)

The Todoist concept of a project - a container for tasks and sections.

**Examples:**
- An outcomes project (contains outcome sections)
- A work context project (may contain Now/Later sections)
- A kanban-style delivery project (To Do/Doing/Done sections)

**CLI:** `todoist projects`, `--project` / `--project-id` flags

### 2. GTD Project (Tier 3 - Multi-Step Outcome)

David Allen's definition: "Any desired result that requires more than one action step."

**Examples:**
- "Complete the product documentation"
- "Set up automated reporting"
- "Hire data scientist"

**In Todoist:** These are TASKS under an outcome section, or sometimes parent tasks with subtasks.

**NOT:** These are NOT outcomes (Tier 2). They're the work that achieves outcomes.

### 3. Business Project (Work Initiative)

A business initiative or workstream, often involving multiple people.

**Examples:**
- "The clean-room project"
- "The panel migration project"
- "The OzTAM expansion project"

**In Todoist:** Often represented as a project with kanban sections (To Do, Doing, Done).

## "Outcome" (2 Meanings)

### 1. Desired Outcome (Tier 2)

A strategic achievement that contributes to Team Priorities AND provides growth opportunity.

**Characteristics:**
- Written in past tense ("Built team capacity through...")
- Achievement, not activity
- Has success criteria
- Finite (can be completed)

**In Todoist:** Usually a SECTION in the user's outcomes project — but discover their layout first (see SKILL.md "Where Outcomes Live").

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

**In Todoist:** Often in a team workspace, or outside Todoist entirely. Referenced from personal outcomes via links or naming.

### 2. Task Priority (P1-P4)

Todoist's built-in priority levels.

| Level | Meaning |
|-------|---------|
| P1 | Highest - critical quarterly focus |
| P2 | High - active work |
| P3 | Medium - important but not urgent |
| P4 | Lowest - someday/maybe |

## "Section" (Todoist-Specific)

A subdivision within a Todoist project. What a section *means* depends on the project:

- In an outcomes project: sections ARE outcomes
- In a context project: sections are often priority lanes (Now/Later)
- In kanban projects: sections are workflow states (To Do/Doing/Done)

Read the section names to tell which layout you're looking at.

## Areas of Focus (AoF)

GTD concept: Ongoing areas of responsibility with no completion date.

**Examples:**
- "Product Ownership"
- "Stakeholder Influencing"
- "Team Development"

**In Todoist:** Typically sections within an areas project.

**Different from outcomes:** Areas are infinite, outcomes are finite.

## Tier Reference

| Tier | Name | Scope | Managed By | In Todoist |
|------|------|-------|------------|------------|
| 1 | Team Priorities | Team quarterly focus | Leadership | Team workspace, or outside Todoist |
| 2 | Individual Outcomes | Personal achievements | the user | The user's outcomes project |
| 3 | Projects & Actions | Execution | the user | Tasks under outcomes |

## Quick Disambiguation

When the user mentions... they probably mean:

| Phrase | Likely Meaning |
|--------|----------------|
| "my projects" | Tier 3 GTD projects (multi-step work) |
| "the project" | Business project/initiative |
| "project in Todoist" | Todoist container |
| "my outcomes" | Tier 2 desired outcomes |
| "team priorities" | Tier 1 (not in this Todoist) |
| "areas of focus" | Ongoing responsibilities |

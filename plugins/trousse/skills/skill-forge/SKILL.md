---
name: skill-forge
description: Orchestrates all skill development — required before writing or editing any SKILL.md file. Unified 6-step workflow with automated validation, CSO scoring, register checks, and subagent testing. Triggers on 'create skill', 'new skill', 'validate skill', 'check skill quality', 'improve skill discovery', 'check this skill', 'write SKILL.md', 'edit SKILL.md', 'update skill description', 'can I share this', 'scan for sharing'. (user)
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion]
---

# Skill Forge

Unified skill development toolkit. Supersedes `skill-creator` — combines its creation process with quality validation, description optimization, and testing.

**Iron Law: Skills must be discovered to be useful.** The description is everything.

## When to Use

- Before writing or editing any SKILL.md file
- When creating a new skill from scratch
- When improving an existing skill's discovery rate
- When validating skill quality before deployment
- When scanning a skill/repo before sharing publicly

## Boundaries

- One-off instructions belong in CLAUDE.md, not a skill
- Simple tool usage Claude already knows
- Tasks that don't repeat across sessions

## Why This Skill Exists

Even when the task seems simple, forge adds value you can't get from training alone:
- **CSO scoring** catches description patterns that look fine but won't trigger discovery
- **Register checks** ensure skills create a calm, productive emotional baseline
- **Lint validation** catches structural issues (naming, frontmatter, section depth) before they cause silent failures
- **Small description edits** are exactly where CSO scoring matters most — a word change can shift discovery rates

## Quick Start

```bash
# 1. Initialize new skill
scripts/init_skill.py my-skill --path ~/.claude/skills

# 2. Edit SKILL.md (see Workflow below)

# 3. Lint for structure issues
${CLAUDE_SKILL_DIR}/scripts/lint_skill.py /path/to/skill

# 4. Score description quality (CSO)
${CLAUDE_SKILL_DIR}/scripts/score_description.py /path/to/skill

# 5. Test with subagent (optional but recommended)
${CLAUDE_SKILL_DIR}/scripts/test_skill.py /path/to/skill

# 6. Package for distribution (optional)
${CLAUDE_SKILL_DIR}/scripts/package_skill.py /path/to/skill
```

## Workflow: 6-Step Process

### Step 1: Understand with Concrete Examples

**Goal:** Know exactly how the skill will be used before building.

Questions to answer:
- "What would a user say that should trigger this skill?"
- "Can you give examples of how this skill would be used?"
- "What should happen after the skill triggers?"

**Exit criterion:** Clear list of trigger phrases and expected behaviors.

### Step 2: Plan Reusable Contents

Analyze each example to identify:

| Content Type | When to Include | Example |
|--------------|-----------------|---------|
| `scripts/` | Same code rewritten repeatedly | `rotate_pdf.py` |
| `references/` | Documentation Claude should reference | `schema.md` |
| `assets/` | Files used in output (not loaded) | `template.pptx` |

**Exit criterion:** List of scripts/references/assets to create.

### Step 3: Initialize

```bash
scripts/init_skill.py <skill-name> --path <directory>
```

Creates SKILL.md template, example scripts/references/assets. Delete unneeded files.

### Step 4: Edit

**Order matters:**
1. Create scripts/references/assets first
2. Test scripts actually work
3. Write SKILL.md last (it references the resources)

#### SKILL.md Structure

```yaml
---
name: kebab-case-name
description: [See CSO Patterns below]
---
```

**Body sections:**
- Core principle / Iron Law
- When to Use / When NOT to Use
- Workflow with success criteria
- Anti-patterns
- Quick reference
- Integration with other skills

#### Naming

- Lowercase letters, numbers, hyphens only. Max 64 chars.
- **Must match directory name exactly.**
- Gerund or capability form preferred.

| Good | Bad | Why |
|------|-----|-----|
| `systematic-debugging` | `debug` | Verb, not capability |
| `workspace-fluency` | `utils` | Generic, no information |
| `test-driven-development` | `pdf-helper` | "helper" is meaningless |
| `desired-outcomes` | `my-skill` | Doesn't describe purpose |

#### CSO Patterns

**The description determines discovery.** Pattern: `[ACTION VERB] + [LIFECYCLE CONTEXT] + [METHOD/VALUE PREVIEW]`

**Best: Clear lifecycle positioning with specific context**
```yaml
description: Orchestrates skill development — required before writing or editing any SKILL.md file. Unified 6-step workflow with automated validation, CSO scoring, and subagent testing.
```
Why: third-person verb, "required before" positioning, specific context ("any SKILL.md file"), method preview.

**Good: Specific trigger with method preview**
```yaml
description: Guides systematic debugging before proposing fixes. 4-phase framework (root cause, pattern analysis, hypothesis testing, implementation) ensures understanding before solutions. Triggers on 'test failing', 'unexpected behavior', 'debug this'.
```
Why: specific trigger + lifecycle positioning + method preview + value statement.

**Good: Natural phrase triggers**
```yaml
description: Coaches on outcome quality. Triggers on 'check my outcomes', 'is this a good outcome', 'review my Todoist' when discussing strategic work.
```
Why: explicit phrases in quotes, context qualifier.

**Good: Scope boundaries to prevent over-triggering**
```yaml
description: Advanced data analysis for CSV files — statistical modelling, regression, clustering. For simple data exploration, use data-viz skill instead.
```
Why: clear scope boundary in description steers Claude before body loads.

**When to add scope boundaries:**
- Skill overlaps with another skill's domain
- Skill triggers on common words that appear in unrelated requests
- Users report the skill loading when it shouldn't

**Patterns to improve:**

| Pattern | Problem | Better |
|---------|---------|--------|
| "Helps with..." | Vague, no trigger | Specific phrases in quotes |
| "Use when creating..." | Too generic | "Required before..." or "Orchestrates..." |
| No timing condition | Claude treats invocation as optional | Add lifecycle positioning: "before", "first" |
| Generic actions | Claude "knows" without loading | Domain-specific phrases |
| Command doesn't name skill | Skill not discoverable | "**Invoke the `name` skill**" |
| Over-triggers on related topics | Loads when it shouldn't | Add scope boundary in description |

Run `scripts/score_description.py` to validate. See `references/cso-guide.md` for full guidance.

### Step 5: Validate

```bash
# Automated lint (structure, naming, frontmatter)
scripts/lint_skill.py <skill-path>

# CSO score (description quality)
scripts/score_description.py <skill-path>

# Subagent test (discovery + workflow)
scripts/test_skill.py <skill-path>
```

All checks should pass before Step 6.

### Step 6: Package (Optional)

```bash
scripts/package_skill.py <skill-path> [output-dir]
```

Creates `.skill` file (zip format) for distribution.

## Quality Checklist

### Structure
- [ ] SKILL.md under 500 lines
- [ ] Name matches directory exactly (kebab-case)
- [ ] Name is gerund/capability form
- [ ] Description is third-person ("Orchestrates", not "Use")
- [ ] Description includes trigger AND method AND timing
- [ ] Description ends with `(user)` tag for user-defined skills
- [ ] References one level deep from SKILL.md
- [ ] YAML frontmatter has name and description only

### Content
- [ ] No time-sensitive information
- [ ] Consistent terminology throughout
- [ ] Concrete examples, not abstract rules
- [ ] Configuration values justified
- [ ] Error handling documented
- [ ] Dependencies explicitly listed
- [ ] Anti-patterns section present

### Workflow
- [ ] Clear phases/steps with success criteria
- [ ] When to Use AND When NOT to Use sections
- [ ] Integration points with other skills explicit
- [ ] Verification/validation included
- [ ] Quick reference for common operations

### Discovery
- [ ] Lifecycle positioning (before/first/required) used appropriately
- [ ] Trigger phrases are natural language in quotes
- [ ] Context qualifiers included (when appropriate)
- [ ] Method preview gives Claude enough to decide relevance
- [ ] If paired with command, command names the skill explicitly
- [ ] Scope boundaries added if skill overlaps with others

### Register
- [ ] Opens with what good work looks like, not what to avoid
- [ ] ALL CAPS used sparingly (abbreviations fine, emphatic caps minimal)
- [ ] Prohibitions balanced with positive specifications
- [ ] Constraints framed as craft standards, not threats

## Skill Patterns

See `references/skill-patterns.md` for full taxonomy. Summary:

| Type | Key Feature | Description Pattern |
|------|-------------|-------------------|
| **Process** | Phases with gates | Lifecycle positioning (before/first) |
| **Fluency** | Tool best practices | Specific trigger phrases |
| **Coaching** | Quality criteria | Natural language triggers |
| **Gate** | Checklist validation | Required before... |
| **Skill+CLI** | Orchestrates CLI tool | Required before any `cli` command |

### Skill+CLI Pattern (Most Powerful)

When skill orchestrates a CLI tool. See `references/skill-cli-pattern.md` for full template.

```markdown
# {skill-name}
Orchestrates {domain} using `{cli}` command.
## CLI Reference
## Workflows
## When Skill Extends CLI (coaching, quality criteria)
## Error Recovery
```

### What High-Invocation Skills Share

1. **Clear lifecycle positioning** — "before", "first", "required"
2. **Specific trigger phrases** in quotes
3. **Method preview** that's actionable
4. **Clear pitfall documentation** that catches mistakes
5. **Integration points** that compose with other skills
6. **Calm, craft-oriented register** — constraints as quality standards

### What Low-Invocation Skills Suffer From

1. Generic "Use when..." descriptions
2. Vague propositions ("helps with", "guides", "assists")
3. Missing lifecycle positioning
4. Documenting what Claude already knows

## Common Mistakes

### Discovery

| Mistake | Symptom | Better |
|---------|---------|--------|
| "Use when creating..." | Claude bypasses skill | "Required before..." |
| "Helps with..." | Skill never invoked | Specific trigger phrases |
| No lifecycle positioning | Claude treats invocation as optional | Add "before", "first", "required" |
| Generic actions | Claude "knows" without loading | Domain-specific phrases |

### Structure

| Mistake | Symptom | Better |
|---------|---------|--------|
| SKILL.md > 500 lines | Token bloat | Split into references/ |
| Name doesn't match dir | Skill not found | Keep synchronized |
| Deeply nested refs | Discovery fails | One level deep max |

### Content

| Mistake | Symptom | Better |
|---------|---------|--------|
| Explaining known things | Wastes tokens | Domain-specific only |
| Magic constants | Unclear reasoning | Justify all values |
| Many options, no default | Analysis paralysis | Recommend one path |
| Heavy threat/urgency language | Corner-cutting, concealment | Frame constraints as craft standards |

## Quick Reference

### Minimum Viable Skill

```markdown
---
name: kebab-case-name
description: [ACTION VERB] + [LIFECYCLE CONTEXT] + [METHOD/VALUE]. Triggers on 'phrase1', 'phrase2'. (user)
---

# Skill Title

[What good work looks like — the core principle]

## When to Use
[Specific triggers with examples]

## Boundaries
[What this skill is not for]

## Workflow
[Steps with success criteria]

## Common Mistakes
[Pitfalls and better alternatives]
```

### Files to Include

| File | Purpose | When Required |
|------|---------|---------------|
| SKILL.md | Core instructions | Always |
| references/*.md | Detailed guides | When SKILL.md > 500 lines |
| scripts/*.py | Utility scripts | When deterministic code needed |
| assets/* | Output templates | When Claude uses files in output |

## Before Sharing

Run the sharing scanner:

```bash
scripts/scan.py <skill-path>
scripts/scan.py --risk high <skill-path>  # High-risk only
```

Detects: emails, paths with usernames, secrets, company terms.
See `references/sharing-scan.md` for triage guidelines.

## Integration

**Anthropic scripts (symlinked from skill-creator):**
- `init_skill.py` — generate template
- `package_skill.py` — create .skill file

**Forge scripts:**
- `lint_skill.py` — automated structure validation
- `score_description.py` — CSO quality scoring
- `test_skill.py` — subagent pressure testing
- `scan.py` — PII/secrets scanner for sharing
- `render_graphs.py` — DOT workflow diagrams to SVG

## References

- `references/cso-guide.md` — Claude Search Optimization principles
- `references/skill-cli-pattern.md` — Skill+CLI template
- `references/skill-patterns.md` — Pattern taxonomy with examples
- `references/rationalization-table.md` — Why this skill exists even when the task seems simple
- `references/register-principles.md` — Emotional register guidelines for instructional text
- `references/sharing-scan.md` — Sharing triage guidelines
- `references/dot-graphs.md` — DOT graph syntax for workflow diagrams

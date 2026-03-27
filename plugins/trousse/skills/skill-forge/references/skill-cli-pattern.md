# Skill+CLI Pattern

The most powerful skill pattern: a Claude skill that orchestrates a purpose-built CLI tool.

## Why This Pattern Works

| Component | Role |
|-----------|------|
| **CLI** | Handles mechanics: API calls, auth, data fetching, execution |
| **Skill** | Handles meaning: interpretation, workflow, coaching, integration |

**Key insight:** "The CLI provides data. The skill provides meaning."

## When to Use

- You're building a skill for a domain with complex API interactions
- You want deterministic, testable operations
- You need authentication or state management
- The same operations repeat across sessions
- You're co-developing CLI and skill together (most powerful variant)

## Anatomy

```
repo/
├── SKILL.md                    # Claude skill (orchestration layer)
├── scripts/
│   ├── cli.py                  # Main CLI entry point
│   ├── commands/               # Subcommand implementations
│   └── lib/                    # Shared utilities
├── references/                 # Deep documentation for Claude
│   ├── error-handling.md       # Error → cause → fix mappings
│   └── domain-concepts.md      # Domain-specific knowledge
└── CLAUDE.md                   # Project context
```

## SKILL.md Template

```markdown
---
name: {domain}-{action}
description: Orchestrates {domain} workflows using `{cli}` command. Triggers on '{trigger1}', '{trigger2}'. Provides semantic understanding of {domain concepts}. (user)
---

# {Domain} Skill

Orchestrates {domain} using `{cli}` — a purpose-built Python CLI.

## Iron Law

[Core principle that governs this skill's behavior]

## CLI Quick Reference

| Command | Purpose | Example |
|---------|---------|---------|
| `{cli} list` | List items | `{cli} list --filter active` |
| `{cli} show <id>` | Show details | `{cli} show abc123` |
| `{cli} create` | Create new | `{cli} create --name "New"` |

## Workflows

### Common Workflow 1

```bash
# Step 1: Gather context
{cli} list --filter relevant

# Step 2: Take action
{cli} action <id>

# Step 3: Verify
{cli} show <id>
```

### Common Workflow 2

[Additional workflow]

## When Skill Extends CLI

The skill adds value the CLI can't provide:

1. **Coaching questions** - "Is this outcome specific enough?"
2. **Pattern recognition** - "You've done this 3 times this week"
3. **Quality criteria** - Tier 2 vs Tier 3 distinction
4. **Integration** - Connects with other skills

## Error Handling

| Error | Likely Cause | Fix |
|-------|--------------|-----|
| `AuthError` | Token expired | `{cli} auth --refresh` |
| `NotFound` | Invalid ID | Check with `{cli} list` |
| `RateLimit` | Too many requests | Wait and retry |

See `references/error-handling.md` for comprehensive guide.

## Authentication

```bash
# First-time setup
{cli} auth

# Verify status
{cli} auth --status

# Force refresh
{cli} auth --refresh
```

## When NOT to Use

- [Scenario where CLI is overkill]
- [Scenario where direct API is better]
- [Edge cases to handle differently]

## Integration

**Composes with:**
- `{other-skill}` - When X happens
- `{another-skill}` - For Y workflows

**Loaded by:**
- Session hooks when {condition}

## Success Criteria

This skill works when:
- CLI operations succeed reliably
- Workflow guidance is followed
- Coaching improves output quality
- Errors are handled gracefully
```

## Real Examples

### todoist-gtd

**CLI:** `todoist` (Python, ~/Repos/todoist-gtd)
**Pattern:** CLI provides Todoist API access; skill provides GTD semantics

Key additions skill provides:
- Tier 2 vs Tier 3 outcome distinction
- Weekly review orchestration
- Pattern detection ("you're overcommitting")
- Team vs personal boundary coaching

### appscript

**CLI:** `itv-appscript` (Python, ~/Repos/itv-appscript-deploy)
**Pattern:** CLI provides deployment; skill provides troubleshooting

Key additions skill provides:
- 5-step setup checklist
- Error → resolution mappings
- GCP project linking guidance

## The Co-Developed Variant

**Most powerful pattern:** Claude co-develops the CLI.

Benefits:
- Claude understands CLI internals deeply
- Skill can reference actual implementation
- CLI evolves alongside skill
- Human-Claude collaboration is tight

Template addition:
```markdown
## CLI Source Reference

When uncertain about CLI behavior, read:
- `scripts/cli.py` - Main entry point
- `scripts/commands/{cmd}.py` - Specific command
- `scripts/lib/api.py` - API wrapper

Claude co-developed this CLI and understands its implementation.
```

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| Skill duplicates CLI docs | Token waste | Reference, don't repeat |
| CLI has no skill | No semantic layer | Add coaching, patterns |
| Skill just wraps commands | No added value | Add workflow, quality gates |
| No error handling | Confusing failures | Map errors to fixes |
| CLI not mentioned in skill | Discovery failure | Explicit CLI reference |

## Checklist

- [ ] CLI has `--help` for all commands
- [ ] Skill references CLI commands explicitly
- [ ] Error handling documented with fixes
- [ ] Workflow steps use actual CLI syntax
- [ ] Authentication documented
- [ ] Integration points named
- [ ] "When Skill Extends CLI" section present
- [ ] Success criteria defined

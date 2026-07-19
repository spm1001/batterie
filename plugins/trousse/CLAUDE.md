# trousse — Project Context

Trousse is a **skill drawer** for Claude Code — a tight set of general-purpose SKILL.md files that teach Claude specialized workflows (code review, skill authoring, session-history parsing, context isolation).

It does NOT own session lifecycle hooks or scripts. Those belong to [bon](https://github.com/spm1001/bon), which owns the full session protocol (hooks, handoffs, briefings, tactical tracking).

## Skill homes — what belongs in trousse

Public trousse is a **tight, general-purpose knife-roll**: skills a stranger on the internet would genuinely seek out. Public status is *earned*, not the default — most skills belong elsewhere. Before adding a skill here, run the home test:

- **Would a random person, with no ITV/Sameer context, install and value this?** → trousse (public). The current four: `skill-forge`, `titans` (+ `/review`), `deglacer`, `ardoise`.
- **ITV/measurement-flavoured — teammates want it, a public installer wouldn't?** → [`ITV/mit-commons`](https://github.com/ITV/mit-commons) (the `commons:` marketplace). Rename to a prosaic `mit-<thing>` — kitchen-metaphor names read as "the boss's toy" in a team space, and the `mit-` prefix is a commons invariant (picker namespacing).
- **Sameer-specific — carries PII, or wired to his stack/machines?** → [`spm1001/trousse-personal`](https://github.com/spm1001/trousse-personal) (private; may hardcode freely).

**"General-purpose" is not the bar** — plenty of generic skills (server checkups, codebase health) are things no stranger would seek; those went personal. The bar is stranger-*appeal*, because public status is an ongoing maintenance tax (genericise, de-brand, document for strangers) paid only when the reach is real. Anthropic's `knowledge-work-plugins` now covers the broad-utility ground (data, design, docs, marketing) — so trousse needn't be a wide drawer; mine those for ideas, adopt only on a clean drop-in.

*(This rule drove the 2026-07 slim-down from 18 skills to 4 — bon `trousse-pijuha`.)*

## Versioning & releasing (suite-managed)

trousse ships as part of the **Batterie de Savoir** suite, which carries **one suite-wide version**. So:

- **Do NOT hand-bump `.claude-plugin/plugin.json` to release.** This repo's own `plugin.json` version is **local-dev-only** — the assembler stamps every published plugin to the suite version, overwriting it.
- **Release via `/batterie:publish`** from this working tree — it bumps the suite version centrally and ships the change (a 2-repo push: this repo + the central suite bump). Never hand-run the assemble.
- **A `CLAUDE.md` / `instructions.md` / `skills/` edit here is vendored content** — it must ride a suite bump (a publish) to actually ship, or the assembler quarantines the plugin. `docs/` / `.bon/` edits are free.

Full picture: `spm1001/batterie-de-savoir` → `CLAUDE.md` "Versioning convention" + `.bon/understanding.md`.

## Compatibility

**Tested with Claude Code:** 2.1.x
**Minimum required:** 2.0 (plugins API)

## Installation

Two paths:

| Path | Command | Skill names |
|------|---------|-------------|
| **Plugin** (recommended) | `claude plugin marketplace add spm1001/batterie` then `/plugin install trousse@batterie` | `/trousse:titans` |
| **Manual** | `git clone` → plugin auto-discovers | `/titans` |

The plugin system discovers skills from `skills/*/SKILL.md` — no hooks, no settings.json registration needed.

## Skill Architecture

### Types

| Type | Trigger | Example |
|------|---------|---------|
| User-invocable | Slash command | `/titans`, `/skill-forge` |
| Alias | Slash command → delegates | `/review` → titans |

### Conventions

- Description ends with `(user)` tag for user-facing skills
- `user-invocable: false` for skills loaded programmatically (companion skills)
- Reference files live in `references/` subdirectory, linked from main SKILL.md

### Current Skills (4 + `review` alias)

ardoise, deglacer, review, skill-forge, titans

(No commands — the `consomme-*` set moved to mit-commons with the consommé skill. See "Skill homes" above for where everything else went.)

### Titans Review

`/titans` (or `/review`) dispatches three parallel Opus reviewers:

| Titan | Lens |
|-------|------|
| **Epimetheus** | Hindsight — bugs, debt, fragility |
| **Metis** | Craft — clarity, idiom, structure |
| **Prometheus** | Foresight — vision, extensibility |

Uses `Task` tool with `subagent_type: "explore-opus"`. Worth it for substantial work; overkill for quick fixes.

## Extending trousse

### Adding a New Skill

1. Create `skills/<name>/SKILL.md` with frontmatter
2. Add `skills/<name>/README.md` (optional but recommended)
3. Plugin auto-discovers from `skills/*/` — no hardcoded list

### Reference Files

Skills can have a `references/` subdirectory:
- Read as-needed, not loaded automatically
- Linked from main SKILL.md with "When to read" guidance
- Naming: UPPERCASE for major references, lowercase for specific topics

## Testing

### Mechanical (pytest)

```bash
uv run pytest           # All tests
uv run pytest -x        # Stop on first failure
uv run pytest -k close  # Single skill
```

Tests check:
- CSO linter pass + score >= 95/100
- Referenced files exist
- Scripts executable with shebang
- Anti-patterns table format consistency

### Semantic (titans)

For "does this skill actually make sense?" — use `/titans`. Three Opus reviewers catch issues the linter can't see (stale references, semantic contradictions, missing error handling).

## Architecture References

| Document | What it covers |
|----------|---------------|
| `docs/error-patterns.md` | Common issues and troubleshooting |

The handoff contract (`HANDOFF-CONTRACT.md`) lives in bon — it specifies bon's session protocol.

### Cross-Skill Routing

- **Before running jq on `~/.claude/projects/**/*.jsonl`** → load `/deglacer` first. The CC JSONL schema has dragons (triple-duty user entries, streaming-duplicated message IDs, version-dependent fields). Deglacer has the schema reference and `deglacer` CLI tool.
- **Past session recall** → deglacer reads full transcripts.

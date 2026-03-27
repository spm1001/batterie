# Titans — Code Review Triad

Three-lens code review using parallel subagents, named for the Greek Titans:

- **Epimetheus** (hindsight) — What's broken, fragile, or accruing debt?
- **Metis** (craft) — Is this well-made for what it is?
- **Prometheus** (foresight) — Does this serve where we're going?

## Usage

```
/titans
```

Or trigger naturally: "review this code", "what did I miss", "before I ship this"

## When to Use

After completing substantial work, before /close. Sits in the workflow as:

```
/open → [work] → /titans → [fix critical items] → /close
```

## The Mythology

Prometheus means "forethought" — he warned against accepting Zeus's gifts. Epimetheus means "afterthought" — he accepted Pandora anyway. Metis is the Titaness of practical wisdom, cunning intelligence, and good counsel.

The three lenses form a largely MECE set: hindsight catches what's broken, craft ensures current quality, foresight protects future-you.

## Files

```
titans/
├── SKILL.md              # Main skill — orchestration, output format
└── references/
    ├── REVIEWERS.md      # Detailed briefs for each Titan
    └── SYNTHESIS.md      # Patterns for merging outputs
```

## Origin

Developed in conversation, January 2026. First run produced a synthesis that surfaced:
- High-priority findings (3 reviewers converged on ContentType literal)
- Trade-offs (Metis vs Prometheus on architecture violations)
- Documentation debt (4 items repeated across "could not assess")
- Clear critical path (3 items blocking shipping)

The token disparity told a story: Epimetheus (127k) did the most spelunking, Prometheus (74k) could assess vision from less code.

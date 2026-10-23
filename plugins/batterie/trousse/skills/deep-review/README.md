# Titans — Code Review Triad

Three-lens code review using parallel subagents, named for the Greek Titans:

- **Mnemosyne** (memory) — What did this change break that used to work?
- **Metis** (craft) — Is this well-made, and is it fragile or accruing debt?
- **Prometheus** (foresight) — Does this serve where we're going?

## Usage

```
/deep-review
```

Or trigger naturally: "review this code", "what did I miss", "before I ship this"

## When to Use

After completing substantial work, before /close. Sits in the workflow as:

```
/open → [work] → /deep-review → [fix critical items] → /close
```

## The Mythology

Prometheus means "forethought" — he warned against accepting Zeus's gifts. Mnemosyne is the Titaness of memory, mother of the Muses: a regression is code forgetting something it used to do. Metis is the Titaness of practical wisdom, cunning intelligence, and good counsel.

Until October 2026 the first lens was Epimetheus ("afterthought", who accepted Pandora anyway), hunting bugs, debt and fragility. A blind test on the commits behind our known regressions found he caught no more than a plain "review this for regressions" prompt while raising about three times the findings, nearly all false. Mnemosyne took his place, and his debt and fragility checks moved to Metis. See the skill's "Why Mnemosyne replaced Epimetheus".

The three lenses form a largely MECE set: memory catches what the change broke, craft ensures current quality, foresight protects future-you.

## Files

```
deep-review/
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

The token disparity told a story: Epimetheus (127k, the lens since replaced by Mnemosyne) did the most spelunking, Prometheus (74k) could assess vision from less code.

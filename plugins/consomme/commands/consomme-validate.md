---
description: "Run QA checklist against the current analysis"
argument-hint: "[query or context]"
---

Run the consomme validation framework against our current analysis.

Check every item:
- Data quality: sources verified, freshness, gaps, nulls, no double-counting, filters correct
- Calculations: GROUP BY, denominators, date periods, JOIN types, metric definitions
- Reasonableness: plausible range, no unexplained jumps, matches known sources, edge cases
- Statistical validity: sample sizes (n >= 30), significance tested, multiple comparisons corrected

For each: PASS, FAIL, or N/A with brief explanation. Overall assessment: ready to share, or what needs fixing.

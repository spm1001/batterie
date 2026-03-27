# Synthesis Patterns

How to merge three reviewer outputs into actionable guidance.

---

## The Synthesis Job

You have three outputs. Your job:
1. **Identify convergence** — Where multiple reviewers agree, confidence is high
2. **Surface divergence** — Where reviewers disagree, there's a trade-off worth discussing
3. **Extract meta-signal** — "Could not assess" patterns reveal documentation debt
4. **Prioritize for action** — What blocks shipping vs what to track

---

## Convergence: High-Priority Findings

When multiple reviewers flag the same issue, it's almost certainly real.

### Building the Table

| Finding | E | M | P | Action |
|---------|---|---|---|--------|
| ContentType literal incomplete | ✓ | ✓ | ✓ | Add missing types |
| Service cache has no invalidation | ✓ | — | ✓ | Add clear_service_cache() |
| CreateResult not in models.py | ✓ | — | ✓ | Move for consistency |

**Reading the pattern:**
- **Three checks** — Highest confidence, fix immediately
- **Two checks** — High confidence, likely real
- **One check** — May still be valid; use reviewer's severity as guide

### Interpreting Silence

A missing check doesn't mean disagreement. It could mean:
- Not in that reviewer's lens (Metis doesn't hunt bugs)
- Didn't encounter it (different exploration path)
- Assessed and found acceptable

**Only flag as conflict when reviewers explicitly disagree**, not when one is silent.

---

## Divergence: Conflicts Reveal Trade-offs

When reviewers disagree, you've found a genuine design tension.

### Building the Table

| Trade-off | Metis says | Prometheus says | Resolution |
|-----------|------------|-----------------|------------|
| parse_presentation in adapters | Violates stated architecture | Pragmatic boundary crossing | Document exception in CLAUDE.md |
| CWD assumption | Idiomatic Python | Ceiling for multi-tenant | Accept for v1, track as debt |
| Warnings mutation vs return | Inconsistent pattern | Future-proofing risk | Pick one, document |

### Resolution Options

Not all conflicts need immediate resolution. Options:

1. **Decide now** — If the trade-off is clear and decision is obvious
2. **Document and proceed** — Accept the tension, capture the reasoning
3. **Escalate to user** — Present the trade-off, let human decide
4. **Defer** — Create a bead for future consideration

**The conflict table is valuable even without resolutions.** It surfaces implicit design decisions that were previously invisible.

### Genuine Conflicts vs Lens Differences

Sometimes apparent conflicts are just different lenses on the same issue:

- Metis: "This function is too long"
- Epimetheus: "This function has too many failure modes"

Both are true. The resolution might be: split the function (satisfies both).

---

## Meta-Signal: Documentation Debt

When multiple reviewers say "could not assess," you've found a documentation gap.

### Common Patterns

| Gap | What It Means | Action |
|-----|---------------|--------|
| "No visibility into intended consumers" | API design is implicit | Document intended consumers |
| "Can't evaluate against patterns" | Patterns aren't documented | Add to CLAUDE.md or ADR |
| "Token refresh flow undocumented" | Tribal knowledge | Document the flow |
| "What's the expected lifespan?" | No stated component lifecycle | Add lifecycle section to README |

### The Forcing Function

A reviewer asking "what's the roadmap?" isn't failing — they're revealing that the roadmap isn't accessible. This is valuable signal.

**Repeated gaps become their own section:**

```markdown
### "Could Not Assess" → Documentation Debt
Repeated across reviewers:
- Token refresh flow — Document in auth.md
- Test coverage baseline — Run pytest --cov, capture in CI
- mypy exclusion rationale — Add comment explaining why
```

---

## Prioritization: Critical Path

Not everything needs to block shipping. Categorize:

### Critical Path (Block Shipping)

| # | Issue | Risk | Fix Complexity |
|---|-------|------|----------------|
| 1 | Type literal lies | Type errors pass silently | 1 line |
| 2 | No cache invalidation on 401 | Stale credentials | ~10 lines |
| 3 | API key in source | Security | Move to env |

**Criteria for critical path:**
- Security issues
- Data loss/corruption risk
- Type safety lies (compiler trust violated)
- Broken core functionality

### Lower Priority (Track as Tech Debt)

```markdown
### Lower Priority (Track as Tech Debt)
- Pagination not implemented (ceiling for growth)
- Create only supports doc (incomplete surface)
- Error stack traces lost on "unknown" (debugging friction)
- Race condition in concurrent fetches (unlikely for single-user)
- Temp file leak edge case (low probability)
```

**Criteria for deferral:**
- Doesn't break current functionality
- Risk is low probability or low impact
- Fix complexity is high relative to benefit
- Not on the critical path for current milestone

---

## Questions to Surface

Some reviewer questions deserve answers before shipping. Others are nice-to-know.

### Must Answer

Questions where the answer changes the fix:

> "Is the GENAI key truly public? If not, move to Secret Manager."

The answer determines whether this is critical path or non-issue.

### Should Consider

Questions that inform future work:

> "Will you ever need multi-tenant? If yes, CWD assumption needs rework."

Doesn't block shipping, but shapes tech debt prioritization.

### Surface But Don't Block

Questions that reveal documentation gaps:

> "Is contacts search on the roadmap? If not, remove the stub."

Good hygiene, but absence of answer doesn't block shipping.

---

## Output Template

```markdown
## Review Triad Synthesis

### High-Priority Findings (Multiple Reviewers)
| Finding | E | M | P | Action |
|---------|---|---|---|--------|
| [issue] | ✓/— | ✓/— | ✓/— | [fix] |

### Conflicts Reveal Trade-offs
| Trade-off | Metis says | Prometheus says | Resolution |
|-----------|------------|-----------------|------------|
| [tension] | [position] | [position] | [decision/defer/escalate] |

### "Could Not Assess" → Documentation Debt
Repeated across reviewers:
- [gap] — [action needed]

### Critical Path Before Shipping
| # | Issue | Risk | Fix Complexity |
|---|-------|------|----------------|
| 1 | [issue] | [risk] | [complexity] |

### Lower Priority (Track as Tech Debt)
- [item] ([why it's lower priority])

### Questions to Resolve
1. [question] — [why it matters]
```

---

## Anti-Patterns

**Don't:**
- List every finding from every reviewer verbatim (that's what the raw outputs are for)
- Treat all findings as equal priority
- Resolve all conflicts yourself without surfacing them
- Ignore "could not assess" — it's signal, not noise
- Create bon items for every finding (that's debt accumulation)

**Do:**
- Synthesize, don't concatenate
- Surface trade-offs for human decision
- Use "could not assess" as documentation forcing function
- Be ruthless about what actually blocks shipping

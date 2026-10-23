---
name: deep-review
description: >
  Orchestrates a three-lens code review — invoke before shipping substantial work, and after
  it is done but before /close. Parallel subagents: Mnemosyne (memory — what the change broke that
  used to work), Metis (craft — clarity, idiom, fragility, debt), Prometheus (foresight — vision,
  extensibility), then a synthesis that ensures findings become a critical path, not three reports.
  Triggers on /deep-review, 'review this code', 'what did I miss', 'before I ship this',
  'check for regressions'. (user)
allowed-tools: [Read, Glob, Grep, Agent]
---

# /deep-review — the titans, a code review triad

Three reviewers, three lenses. Dispatch in parallel, synthesize findings.

## When to Use

- **After substantial work** — Before /close, when a feature/fix/refactor is "done"
- **Before shipping** — Final quality gate
- **Periodic hygiene** — "What's rotting that I haven't noticed?"

## When NOT to Use

- Quick fixes under 50 lines
- Exploratory spikes
- Throwaway scripts (unless they stopped being throwaway)
- When you need speed over thoroughness

## Beyond Code Review

The three-lens pattern works for more than code. The underlying structure (memory/craft/foresight) applies to any artifact worth reviewing thoroughly:

| Domain | Mnemosyne asks | Metis asks | Prometheus asks |
|--------|----------------|------------|-----------------|
| **Documentation** | What did this edit drop that readers relied on? | Is it clear, accurate and well-structured? | Does it serve future readers? |
| **Architecture** | Which contract or consumer did this change break? | Is it well-patterned, or fragile and debt-laden? | Does it enable what we're building toward? |
| **Process** | What used to work that now doesn't? | Is it efficient and clear? | Will it scale with the team? |
| **CLAUDE.md** | What true guidance did this edit lose? | Is it well-organized, or stale? | What should future Claude know? |

**Discovered Jan 2026:** Used titans pattern to review trousse itself for CLAUDE.md updates. The three lenses surfaced different categories of findings — infrastructure bugs (Epimetheus, the hindsight lens Mnemosyne later replaced), stale references (Metis), undocumented contracts (Prometheus) — that a single-pass review would have missed.

**When adapting:** Adjust the reviewer briefs for the domain. The output structure (findings, assumptions, could-not-assess, questions) remains useful regardless of what you're reviewing.

## The Triad

| Titan | Lens | Question | Focus |
|-------|------|----------|-------|
| **Mnemosyne** | Memory | "What did this change make the code forget?" | Regressions: callers, contracts, removals, platforms, lost protection |
| **Metis** | Craft | "Is this well-made, right now, for what it is?" | Clarity, idiom, structure, tests, fragility, debt |
| **Prometheus** | Foresight | "Does this serve what we're building toward?" | Vision, extensibility, knowledge capture |

**Why these three?** Memory catches what the change broke. Craft ensures current quality. Foresight protects future-you. Small overlaps are fine — they're perspectives, not partitions.

**Why Mnemosyne replaced Epimetheus (Oct 2026).** Regressions are the defects that most often reach our users, and tests catch few of them. A blind test gave reviewers the 39 commits that shipped our 42 known user-facing regressions, plus 39 size-matched ordinary commits, and two blind judges scored the reviews. Epimetheus, the old hindsight lens, caught 19 of 42 but raised about 8 findings on every ordinary commit, roughly 9 in 10 of them false. A plain "review this for regressions" prompt caught 21 at about 3 findings per commit. Mnemosyne caught 26 at about 2 per commit, and her confirmed pile was about 70% real. The edge over the plain prompt is not significant at this size (p = 0.18), and her focus list was written from the same regressions, so expect a smaller edge on new code. Epimetheus's debt and fragility checks moved to Metis. Evidence: banc `regression-dig/review-test/RESULTS.md`.

## Orchestration

### 1. Scope the review

Before dispatching, establish:
- **What to review** — specific files, directory, or "everything touched this session"
- **Context available** — CLAUDE.md, README, architecture docs
- **Goals if known** — roadmap items, intended consumers, lifespan

If scope is unclear, ask. Don't review the entire codebase by accident.

### 2. Dispatch reviewers

Launch three parallel Task calls. Use `Explore` subagent with `model: "opus"` — deep review needs Opus-level reasoning, not Haiku speed.

Each reviewer receives:
- The **Reviewer Brief** for their lens (from [references/REVIEWERS.md](references/REVIEWERS.md))
- The scoped files/context
- Awareness of the other two reviewers (to minimize redundancy)
- The output structure template

```
Task(
  subagent_type: "Explore",
  model: "opus",
  description: "MNEMOSYNE review of [scope]",
  prompt: "[Reviewer brief from REVIEWERS.md] + [scoped files] + [output template]"
)
```

Dispatch all three in a single message (parallel execution).

### 3. Collect outputs

Each reviewer returns structured findings. See [Output Structure](#output-structure) below.

**Partial failures:** If a reviewer times out, errors, or returns malformed output:
- Proceed with available outputs (two reviews > none)
- Note the gap in synthesis ("Mnemosyne did not complete — memory lens missing")
- Consider re-running the failed reviewer with tighter scope

### 4. Synthesize

Merge outputs into actionable summary:
- **High-priority findings** (multiple reviewers agree)
- **Conflicts reveal trade-offs** (disagreements worth surfacing)
- **"Could not assess" → documentation debt**
- **Critical path before shipping**

See [references/SYNTHESIS.md](references/SYNTHESIS.md) for synthesis patterns.

---

## Output Structure (All Reviewers)

Each reviewer uses this template:

```markdown
## [TITAN] Review

### Findings
Numbered list of issues, each with:
- What: the problem
- Where: file/line/function
- Severity: critical | warning | note
- Fix complexity: trivial | moderate | significant

### Assessed Under Assumptions
State the assumption, then the conditional finding:
- "Assuming this is a long-lived component: [concern]"
- "If throwaway prototype, this concern evaporates"

### Could Not Assess
What's missing that blocks review:
- "No visibility into intended consumers"
- "Can't evaluate against patterns — no access to rest of codebase"
- "Token refresh flow undocumented"

### Questions That Would Sharpen This Review
Specific, answerable questions:
- "Is this called by other agents or only orchestration?"
- "What's the expected lifespan?"
- "Who are the intended consumers?"
```

**Mnemosyne uses her own two-pile template** (Findings, then Unresolved), set out in her brief. Read her Findings first. Unresolved is a second pile to work through, not noise: it is where she puts suspected breaks she could not prove from the code alone.

**"Could not assess" is itself diagnostic.** A codebase that leaves Prometheus constantly asking "what are we building toward?" has a documentation problem worth surfacing.

---

## Synthesis Output

After collecting all three reviews, produce:

```markdown
## Review Triad Synthesis

### High-Priority Findings (Multiple Reviewers)
| Finding | Mn | M | P | Action |
|---------|----|---|---|--------|
| [issue] | ✓  | ✓ | — | [fix]  |

### Conflicts Reveal Trade-offs
| Trade-off | Metis says | Prometheus says | Resolution |
|-----------|------------|-----------------|------------|
| [tension] | [position]| [position]      | [decision] |

### "Could Not Assess" → Documentation Debt
Repeated across reviewers:
- [gap] — [what's needed]

### Critical Path Before Shipping
| # | Issue | Risk | Fix Complexity |
|---|-------|------|----------------|

### Lower Priority (Track as Tech Debt)
- [items to track but not block on]

### Questions to Resolve
1. [question surfaced by review]
```

---

## Reference Files

| Reference | When to Read |
|-----------|--------------|
| [REVIEWERS.md](references/REVIEWERS.md) | Detailed briefs for each Titan |
| [SYNTHESIS.md](references/SYNTHESIS.md) | Patterns for merging outputs, handling conflicts |

---

## Observed Token Consumption

From test runs, reviewers tend to use tokens in this order:
- **Mnemosyne** traces outward from the diff to callers and consumers, so her cost grows with how widely the changed code is used (median 48 s and $0.30 per commit in the Oct 2026 test)
- **Metis** uses moderate — structural analysis, less exploration
- **Prometheus** uses the least — architectural assessment from less code

This varies by codebase size and scope clarity. If a reviewer seems to be looping, it usually indicates unclear scope — consider interrupting and re-scoping rather than waiting it out.

## Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| Vague scope | Reviewers loop, miss focus | Explicit file list or "changes since X" |
| Skip synthesis | Three reports, no action | Always synthesize findings |
| Ignore partial failures | Miss perspectives | Report which reviewer failed, proceed with others |
| Review before work is "done" | Premature review | Complete the feature first |
| Every finding read at equal weight | Real breaks drown in notes | Mnemosyne's Findings first, then her Unresolved, then the rest |

---

## Integration with /open and /close

```
/open
  ↓
[substantial work]
  ↓
/deep-review  ← you are here
  ↓
[address critical findings]
  ↓
/close
```

**/deep-review findings can feed into /close:**
- Critical issues → "Now" bucket (fix before closing)
- Lower priority → "Next" bucket (create tracker items)
- Documentation debt → handoff Gotchas section

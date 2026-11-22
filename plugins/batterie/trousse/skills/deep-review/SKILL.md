---
name: deep-review
description: >
  Orchestrates a three-lens code review — invoke before shipping substantial work, and after
  it is done but before /close. One fresh reviewer holds three lenses: Mnemosyne (memory — what the
  change broke that used to work), Metis (craft — clarity, idiom, fragility, debt), Prometheus
  (foresight — vision, extensibility), then a synthesis that ensures findings become a critical
  path, not three reports.
  Triggers on /deep-review, 'review this code', 'what did I miss', 'before I ship this',
  'check for regressions'. (user)
allowed-tools: [Read, Glob, Grep, Agent]
---

# /deep-review — the titans, a code review triad

One fresh reviewer, three lenses, one synthesis. The reviewer is a subagent so that it reads the change cold; it holds all three lens briefs itself rather than splitting them across three agents.

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

**Discovered Jan 2026:** Used titans pattern to review trousse itself for CLAUDE.md updates. The three lenses surfaced different categories of findings — infrastructure bugs (Epimetheus, the hindsight lens Mnemosyne later replaced), stale references (Metis), undocumented contracts (Prometheus). What earns its keep is the three *lenses*, not three *agents*: one reviewer working through each brief in turn does as well (see "Why one reviewer, not three", below).

**When adapting:** Adjust the reviewer briefs for the domain. The output structure (findings, assumptions, could-not-assess, questions) remains useful regardless of what you're reviewing.

## The Triad

| Titan | Lens | Question | Focus |
|-------|------|----------|-------|
| **Mnemosyne** | Memory | "What did this change make the code forget?" | Regressions: callers, contracts, removals, platforms, lost protection |
| **Metis** | Craft | "Is this well-made, right now, for what it is?" | Clarity, idiom, structure, tests, fragility, debt |
| **Prometheus** | Foresight | "Does this serve what we're building toward?" | Vision, extensibility, knowledge capture |

**Why these three?** Memory catches what the change broke. Craft ensures current quality. Foresight protects future-you. Small overlaps are fine — they're perspectives, not partitions.

**Why Mnemosyne replaced Epimetheus (Oct 2026).** Regressions are the defects that most often reach our users, and tests catch few of them. A blind test gave reviewers the 39 commits that shipped our 42 known user-facing regressions, plus 39 size-matched ordinary commits, and two blind judges scored the reviews. Epimetheus, the old hindsight lens, caught 19 of 42 but raised about 8 findings on every ordinary commit, roughly 9 in 10 of them false. A plain "review this for regressions" prompt caught 21 at about 3 findings per commit. Mnemosyne caught 26 at about 2 per commit, and her confirmed pile was about 70% real. The edge over the plain prompt is not significant at this size (p = 0.18), and her focus list was written from the same regressions, so expect a smaller edge on new code. Epimetheus's debt and fragility checks moved to Metis. Evidence: banc `regression-dig/review-test/RESULTS.md`.

**Why one reviewer, not three (Nov 2026).** Until batterie 2.26 the three lenses ran as three parallel subagents over the same diff, with the orchestrator synthesising. Anthropic's guidance on folding subagents back into one loop says to split agents by *context* (independent research paths, a verifier that must not share the author's view), not by *problem type*, because splitting by problem type hands the same material to three readers and loses detail at every handoff. A blind test put both forms over the same 78 commits (39 carrying 42 known regressions, 39 ordinary), two runs each, scored by two blind judges with the later history in hand. One reviewer holding all three briefs caught 28 and 27 of the 42 regressions; the three-agent triad caught 27 and 28, a tie inside run-to-run noise. On ordinary commits the single reviewer raised a third fewer findings (8.4 against 12.6 per commit), and the cut fell on false ones: the same ~38 real findings, about 260 false against 418. It cost $0.42 a review against $1.49, and finished in 96 s against 137 s. Mnemosyne's output was the same size either way; what shrank was Metis and Prometheus, by about 40%. The test grades regressions only, so whether the trimmed craft and foresight notes mattered is unmeasured. The one split that stays is by context: the reviewer is still a fresh subagent, because the session that wrote the change can only establish that the change agrees with itself. Evidence: banc `regression-dig/review-test/RESULTS-fold-2026-11.md`.

## Orchestration

### 1. Scope the review

Before dispatching, establish:
- **What to review** — specific files, directory, or "everything touched this session"
- **Context available** — CLAUDE.md, README, architecture docs
- **Goals if known** — roadmap items, intended consumers, lifespan

If scope is unclear, ask. Don't review the entire codebase by accident.

### 2. Dispatch the reviewer

Launch **one** Agent call: `subagent_type: "general-purpose"`, `model: "opus"`. Deep review needs Opus-level reasoning, and a full general-purpose agent reads whole files, where Explore reads excerpts.

The reviewer receives, in one prompt:
- All three **lens briefs** from [references/REVIEWERS.md](references/REVIEWERS.md), with its "Holding three lenses" paragraph
- The scoped files/context
- The output templates (below) and the synthesis instructions from [references/SYNTHESIS.md](references/SYNTHESIS.md)
- "Review only: do not edit, write or commit anything."

```
Agent(
  subagent_type: "general-purpose",
  model: "opus",
  description: "deep-review of [scope]",
  prompt: "[scope] + [all three briefs from REVIEWERS.md] + [output templates] + [SYNTHESIS.md] + review only"
)
```

It works through the change once per lens, Mnemosyne first, writes each lens's review in its own template, then the synthesis.

### 3. Collect the output

The reviewer returns three lens reviews and a synthesis. See [Output Structure](#output-structure) below.

**Partial failures:** If the reviewer times out, errors, or skips a lens:
- Use what came back (two lenses > none)
- Say which lens is missing in what you relay ("the Prometheus pass did not come back")
- Re-run with tighter scope, or for the missing lens alone

### 4. Relay the synthesis

The reviewer has already synthesised. Your job is to relay it, not re-write it:
- Lead with the **critical path** and Mnemosyne's Findings
- Spot-check any critical finding against the code before you call it a blocker; you hold context the reviewer lacked (what the change was for, what the user said)
- Keep the lens reviews to hand for anyone who wants the detail

See [references/SYNTHESIS.md](references/SYNTHESIS.md) for what a good synthesis looks like.

---

## Output Structure (All Lenses)

Each lens's review uses this template:

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

After the three lens passes, the reviewer produces:

```markdown
## Review Triad Synthesis

### High-Priority Findings (Multiple Lenses)
| Finding | Mn | M | P | Action |
|---------|----|---|---|--------|
| [issue] | ✓  | ✓ | — | [fix]  |

### Conflicts Reveal Trade-offs
| Trade-off | Metis says | Prometheus says | Resolution |
|-----------|------------|-----------------|------------|
| [tension] | [position]| [position]      | [decision] |

### "Could Not Assess" → Documentation Debt
Repeated across lenses:
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

## Observed Cost

In the Nov 2026 test on 78 real commits (Opus 5.5 on Vertex), one reviewer holding all three lenses took a median of $0.42 and 96 s per commit; the old three-agent form took $1.49 and 137 s. Mnemosyne's pass costs most where the changed code is widely used, because she traces outward to callers and consumers.

If the reviewer seems to be looping, it usually indicates unclear scope — consider interrupting and re-scoping rather than waiting it out.

## Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| Vague scope | The reviewer loops, misses focus | Explicit file list or "changes since X" |
| Skip synthesis | Three reports, no action | Always synthesize findings |
| Splitting the lenses across three agents again | Three times the cost, half again the findings, no extra catches (Nov 2026 test) | One reviewer, three passes |
| Reviewing in the authoring session | It can only find that the change agrees with itself | A fresh subagent, always |
| Reading only the last message of a headless (`claude -p`) run | A background subagent can give the orchestrator one more turn after it wrote the synthesis, so the final message is a one-line note (12 of 156 scripted runs in the Nov 2026 test) | Capture with `--output-format stream-json` and take the last message that carries the synthesis |
| Ignore partial failures | Miss perspectives | Say which lens is missing, proceed with the rest |
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

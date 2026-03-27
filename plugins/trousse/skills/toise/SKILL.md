---
name: toise
description: Orchestrates architecture review for Claude-maintained software — 3-phase process (measure, grade, report) across 8 checks that produces letter grades with evidence, ensuring architectural debt is caught before it compounds. Invoke BEFORE adding significant complexity or when inheriting an unfamiliar repo. Triggers on 'toise review', 'review this architecture', 'is this Claude-friendly', 'check maintainability', 'before we add complexity', 'measure this codebase'. Do NOT use for pure code review (use titans). (user)
allowed-tools: [Read, Glob, Grep, Bash, Agent]
---

# Toise

Architecture review for Claude-maintained software.

**Core thesis:** Software maintained by Claude has different architectural needs than software maintained only by humans. These needs are empirically discoverable — codebases that were rebuilt for "claude-comfort" show consistent patterns. This skill codifies those patterns as review checks.

Grounded in Basecamp's *Getting Real* philosophy (less mass, interface first, opinionated software, fix time flex scope) and extended with **claude-maintainability** principles derived from real rebuild case studies.

See `references/claude-maintainability.md` for the full principles with evidence.
See `references/evidence.md` for the empirical case studies.

## When to Use

- Reviewing architecture of a codebase Claude will maintain long-term
- Inheriting an unfamiliar repo — assess before modifying
- Before adding significant complexity (new framework, new abstraction layer, new dependency)
- Periodic health check on an actively-developed project
- After a major refactor, to verify improvements landed

## When NOT to Use

- Pure code review (bugs, style, idiom) — use titans
- One-off scripts that won't be maintained
- Reviewing someone else's library you consume but don't modify

## The Eight Checks

Run all eight. Report each as a letter grade (A-F) with a one-line verdict and supporting evidence. Present as a table first, then expand failing checks.

### 1. Mass

**Question:** How much does this codebase weigh?

**Check:**
- Count runtime dependencies (package.json `dependencies`, pyproject.toml `[dependencies]`)
- Count build pipeline stages (bundler, transpiler, minifier, CSS preprocessor)
- Measure framework lock-in depth (can you swap the framework without rewriting?)
- Check for dead dependencies (imported but unused)

**Grading:**
- **A:** 0-3 runtime deps, no build step or single-command build
- **B:** 4-8 runtime deps, straightforward build
- **C:** 9-15 runtime deps, multi-stage build
- **D:** 16+ runtime deps or build pipeline with 3+ stages
- **F:** Can't build without reading a wiki

**Evidence:** Gueridon: 2 runtime deps, no build step (A). mise-en-space: 11 runtime deps, no build step (B). mcp-google-workspace v1 had 17 tools mapping 1:1 to APIs — mass in interface rather than dependencies.

### 2. State Clarity

**Question:** Can you point to where the application state lives?

**Check:**
- Is there an explicit state machine or state container? Where?
- Grep for global mutable state (`global`, `window.`, class-level mutation, singletons)
- Are there multiple components that independently track the same state? (Shadow state machines)
- Can a single component answer "what state is the system in right now?"

**Grading:**
- **A:** Single explicit state authority, consumers are pure renderers
- **B:** Explicit state, but some consumers derive local state
- **C:** State distributed across 2-3 locations with sync logic
- **D:** Implicit state inferred from flag combinations across files
- **F:** "It depends on timing" — state is a race condition

**Evidence:** claude-go had 5 systems implicitly encoding session state (F). Gueridon v2's StateBuilder is the single authority (A). The interim shadow state machine ("two state machines trying to agree on reality") was a C that degraded to D under edge cases.

### 3. Epicenter

**Question:** For each major screen/endpoint/command — is the core purpose immediately obvious?

**Check:**
- Read entry points (HTML files, route handlers, CLI commands). Is the primary content/function the structural root, or buried under chrome/middleware/abstraction?
- Can you identify what the module DOES from its first 20 lines?
- Are module names descriptive of purpose? (`state-builder.ts` vs `utils.ts`, `extractors/slides.py` vs `helpers.py`)

**Grading:**
- **A:** Every module's purpose is obvious from name + first 20 lines
- **B:** Most modules are clear; 1-2 need reading further
- **C:** Module purposes clear but buried under framework boilerplate
- **D:** Need to read 100+ lines to understand what a module does
- **F:** Modules named `utils`, `helpers`, `common`, `misc`

### 4. Opinion

**Question:** Does this software take a clear position, or try to be everything?

**Check:**
- Count preference/settings/configuration screens or options
- Count feature flags or A/B test branches
- Is there a stated vision ("project management is communication", "3 verbs not 17 tools")?
- Does the CLAUDE.md or README state what this software deliberately does NOT do?

**Grading:**
- **A:** Clear vision stated, deliberate exclusions documented, zero preference screens
- **B:** Vision clear, few configuration options, all justified
- **C:** Some unnecessary configurability, but core is opinionated
- **D:** Extensive preference screens, no clear position
- **F:** Tries to please everyone, feature flags everywhere

**Evidence:** Gueridon: no model picker, no thinking selector, no auth config — deliberate exclusions documented in decisions.md (A). mise: 3 verbs instead of 17 tools (A).

### 5. Three States

**Question:** Does every user-facing screen/endpoint handle regular, empty, and error conditions?

**Check:**
- For each screen/page/endpoint: grep for empty-state handling, error boundaries, loading states
- Check what happens with zero data (blank slate)
- Check what happens when the backend is unreachable
- Check what happens with malformed input

**Grading:**
- **A:** All screens handle all three states with thoughtful UX/messages
- **B:** Most screens handle all three; minor gaps
- **C:** Regular state polished, empty/error states minimal
- **D:** Error states are raw exceptions or generic "something went wrong"
- **F:** Empty state shows broken layout; errors crash

**Evidence:** Gueridon has a fourth state (reconnecting) because mobile demands it. mise has typed `MiseError` with `ErrorKind` enum and `retryable` hint.

### 6. Copywriting

**Question:** Are user-facing strings written with care?

**Check:**
- Extract button labels, placeholder text, error messages, empty state text
- Flag generic strings: "Submit", "Error", "Loading...", "Something went wrong", "N/A"
- Check whether error messages tell the user what to DO, not just what went wrong
- Check whether empty states explain what will appear and how to get started

**Grading:**
- **A:** Every string is purposeful, errors suggest actions, empty states guide
- **B:** Mostly good, a few generic strings
- **C:** Functional but generic ("Error occurred", "No data")
- **D:** Raw technical messages shown to users
- **F:** `console.log` or stack traces visible to end users

### 7. Cost of Change

**Question:** How expensive is it to change this software?

**Check:**
- Measure build time (if any)
- Measure test suite time
- Count files that must change for a typical feature addition
- Is there a build step between edit and seeing the result?
- How many files would a Claude need to read to add a new feature?

**Grading:**
- **A:** Edit-and-reload, tests < 15s, typical change touches 1-3 files
- **B:** Fast build (< 30s), tests < 60s, typical change touches 3-5 files
- **C:** Build under 2 minutes, tests under 5 minutes
- **D:** Build over 2 minutes or tests over 5 minutes
- **F:** "Deploy to see if it works"

**Evidence:** Gueridon: no build step, 576 tests in ~8s, typical change touches 1-2 files (A). mise: no build step, fixture-driven tests, adding a content type follows a 3-file recipe (A).

### 8. Claude-Readiness

**Question:** Is this codebase set up for a Claude to maintain it effectively?

**Check:**
- **CLAUDE.md quality:** Does it exist? Does it have architecture overview, module map, dependency rules, extension recipes, anti-patterns? Score 0-5 (one point each).
- **Test coverage as spec:** Can Claude understand what the code does by reading tests? Are there fixture files for complex inputs?
- **File size distribution:** What percentage of source files are under 500 lines? Under 800?
- **Pure function ratio:** What fraction of core logic is in pure, testable functions vs I/O-entangled code?
- **Framework magic depth:** How many layers of framework convention must Claude understand to trace a request end-to-end?
- **Decisions documented:** Is there a decisions.md or ADR directory with rationale?
- **Extension recipes:** Are "How to Add X" patterns documented?

**Grading:**
- **A:** CLAUDE.md 5/5, >80% files under 800 lines, core logic is pure functions, decisions documented, extension recipes present
- **B:** CLAUDE.md 3-4/5, >60% files under 800 lines, most core logic testable
- **C:** CLAUDE.md exists but thin, mixed file sizes, some pure functions
- **D:** No CLAUDE.md, large files, logic entangled with I/O
- **F:** No documentation, no tests, framework-dependent throughout

## Running the Review

### Phase 1: Measure (automated)

Use grep, glob, read, and bash to gather metrics for all eight checks. Do this systematically — don't skip to opinions.

```
# Mass
- Read package.json/pyproject.toml for dep counts
- Check for build scripts/config (webpack, vite, esbuild, tsc)
- Grep for unused imports

# State Clarity
- Grep for state management patterns (global, singleton, useState, this.state)
- Look for explicit state machine files
- Check if multiple files track overlapping state

# Epicenter
- Read entry points (index.html, main.py, server.ts, cli.py)
- Check module naming conventions
- Read first 20 lines of each source file

# Opinion
- Grep for preference/settings/config UI
- Count feature flags
- Read README/CLAUDE.md for stated vision and exclusions

# Three States
- Grep for error boundary/handler patterns
- Grep for empty state/blank slate/no-data handling
- Check error message quality

# Copywriting
- Extract user-facing strings (button text, placeholders, error messages)
- Flag generics

# Cost of Change
- Check build config complexity
- Run test suite, measure time
- Count files touched in last 10 feature commits

# Claude-Readiness
- Score CLAUDE.md against 5-point rubric
- Measure file size distribution
- Identify pure vs I/O-entangled modules
- Check for decisions.md and extension recipes
```

### Phase 2: Grade

Assign letter grades using the rubrics above. Be honest — the point is to find improvement opportunities, not to validate.

### Phase 3: Report

Present as:

```
## Getting Real Review: [project name]

| Check | Grade | Verdict |
|-------|-------|---------|
| Mass | B | 7 deps, no build step — lean but could trim 2 unused |
| State Clarity | A | StateBuilder is single authority |
| Epicenter | A | Every module named for purpose |
| Opinion | A | Vision stated, deliberate exclusions documented |
| Three States | B | Missing error state on settings page |
| Copywriting | C | 4 generic error messages, empty states need work |
| Cost of Change | A | Edit-and-reload, 8s test suite |
| Claude-Readiness | A | CLAUDE.md 5/5, extension recipes, decisions documented |

### Priority improvements
1. [Most impactful failing check — what to do]
2. [Second most impactful]
3. [Third, if any]
```

Only expand checks that score C or below. A and B grades get the one-line verdict only.

## Composing With Other Skills

| Skill | Relationship |
|-------|-------------|
| **titans** | Titans reviews code quality (bugs, craft, foresight). Getting Real reviews architecture and product decisions. Run both before shipping substantial work. |
| **bon** | Improvement items from the review become bon outcomes. |
| **mcp-builder** | When reviewing an MCP server, Getting Real's "Few verbs, small interface" check is particularly relevant. |

## Anti-Patterns

| Anti-pattern | Problem | Fix |
|---|---|---|
| Skipping measurement | Opinions without evidence | Run phase 1 first |
| Grading everything A | Sycophantic review helps nobody | Apply the grading rubric honestly — C or below means real issues |
| Reviewing code style | Out of scope for toise | Use titans for bugs, craft, and foresight |
| Proposing rewrites | User's call, not reviewer's | Flag the issue and grade; leave the decision to the user |
| Ignoring Claude-Readiness | Misses the novel contribution | Check 8 is mandatory — don't skip it |

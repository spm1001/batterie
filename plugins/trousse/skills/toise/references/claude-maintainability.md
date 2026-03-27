# Claude-Maintainability Principles

What makes a codebase easy for Claude to reason about, modify, and extend — and how it differs from human-maintainability.

## Why It's Different

Humans navigate IDEs, carry institutional memory, tolerate build steps, and internalise framework conventions through repetition. Claude navigates text (glob/grep/read), starts fresh each session, works within a context window, and reads actual code paths rather than inferring framework magic.

This means the same codebase can be easy for a human and hard for Claude, or vice versa. The principles below optimise for Claude without hurting human readability — they're a strict subset of "good architecture" that happens to matter disproportionately for AI-assisted development.

## The Principles

### 1. Pure Functions Over Stateful Objects

Claude can reason about inputs -> outputs in one pass. Stateful objects require tracking mutation across time — Claude's weakest mode. A `translateEvent(event, state) -> newState` is immediately comprehensible. A `this.state` that mutates across 12 methods requires holding the full class in context.

**Evidence:** Gueridon's `state-builder.ts` is a pure function (event + state -> new state). Mise's extractors are pure (JSON fixture -> markdown). Both are the most-tested, most-modified, and most-stable modules in their repos.

### 2. Explicit State Machines Over Implicit State

Claude can enumerate states and transitions. Implicit state — where the current mode is inferred from combinations of flags and conditions scattered across files — requires inference Claude frequently gets wrong.

**Evidence:** claude-go had five systems implicitly encoding session state. Gueridon replaced this with an explicit StateBuilder. Within Gueridon, the client's shadow state machine (10 case branches, backwards search, collision detection) was replaced with three addressed event types. Each time implicit -> explicit, bugs dropped.

### 3. Small, Focused Files (300-800 Lines)

Claude's context window is finite. A file that fits comfortably in one read (< 800 lines) can be fully understood in a single pass. Files over 1000 lines require offset reads, which lose cross-reference context.

**Evidence:** mise v1 had 600-line monolithic tool files. mise v2 has focused modules averaging 300 lines. Gueridon's 14 server modules average ~500 lines each. Both repos have high test coverage and low regression rates.

### 4. CLAUDE.md as Architectural Oracle

CLAUDE.md is loaded FIRST every session. It is the interface between past-Claude and future-Claude. A good CLAUDE.md answers: What is this? How does it work? What are the rules? How do I extend it?

**Key sections for Claude-maintainability:**
- Architecture overview with module map
- Dependency direction rules (mechanically verifiable)
- "How to Add" recipes for common extension patterns
- Current state / known issues
- What NOT to do (anti-patterns specific to this codebase)

**Evidence:** mise-en-space's CLAUDE.md includes "How to Add a new content type" and "How to Add a new do() operation" — step-by-step recipes. Gueridon's CLAUDE.md includes the full SSE event protocol and state-builder contract.

### 5. No Framework Magic

Claude reads actual code paths. Framework conventions (Rails' `before_action`, React's `useEffect` lifecycle, Django's middleware chain, decorator-based routing) require trained pattern-matching that's fragile across framework versions.

Vanilla code with explicit control flow is immediately readable. `if (request.path === '/api/search')` is clearer to Claude than a decorator chain that routes through middleware.

**Evidence:** Gueridon uses raw `http.createServer`. Mise uses FastMCP's explicit tool registration. Both avoided frameworks their ecosystems would have suggested (Express, Flask).

### 6. Tests as Executable Specification

Claude trusts tests more than comments. A test that asserts `stateBuilder(toolStartEvent, emptyState).currentMessage.tools.length === 1` tells Claude exactly what the code does, in a way no comment can.

Tests also provide safe modification: Claude can change implementation, run tests, and know immediately whether it broke something. Without tests, Claude must reason about every downstream effect.

**Evidence:** Gueridon has 576+ tests (~8s). Mise has fixture-driven extractors where adding a test is: save a JSON fixture, write expected markdown output, assert equality. Claude can add test cases without understanding the extraction internals.

### 7. Decisions Documented With Rationale

Claude can't infer "why" from code alone. A `decisions.md` that says "We use SSE+POST instead of WebSocket because SSE auto-reconnects and the transport is stateless" prevents future-Claude from proposing a WebSocket migration that re-introduces solved problems.

**Evidence:** Both repos have `decisions.md`. Gueridon's notes its own staleness when the architecture changed — honest documentation beats stale documentation.

### 8. Few Verbs, Small Interface Surface

Every tool/function/endpoint Claude must understand burns context tokens. 17 tools at ~900 tokens each = 15k tokens just for the interface. 3 tools at ~1k tokens each = 3k tokens.

More importantly, fewer verbs means fewer interaction patterns to reason about. Claude can hold 3 interaction patterns in working memory; 17 requires constant re-reading.

**Evidence:** mise's 17-tool -> 3-verb consolidation reduced tool token cost by 5x and made the interface memorisable within a single conversation turn.

### 9. Extension Recipes Over Extension Points

Abstract extension points (plugin systems, hook registries, event buses) require Claude to understand the abstraction before using it. Concrete recipes ("to add a new content type: 1. create `extractors/foo.py`, 2. create `adapters/foo.py`, 3. add route in `tools/fetch.py`") are immediately actionable.

**Evidence:** mise's "How to Add" recipes in CLAUDE.md. A Claude adding Google Forms support follows three steps and writes three files, rather than studying an abstract plugin architecture.

### 10. Enforced Dependency Direction

Layer rules that Claude can mechanically verify ("extractors NEVER import from adapters or tools") are more useful than architectural diagrams. Claude can grep for violations. It can't grep for "good architecture."

**Evidence:** mise's three-layer rule is documented in CLAUDE.md and mechanically verifiable. Violations show up as import statements that break the rule.

## What Hurts Claude (Anti-Patterns)

| Anti-pattern | Why it hurts Claude specifically |
|---|---|
| Deep inheritance hierarchies | Must chase `super()` calls across files |
| Global mutable state | Can't reason about what changed when |
| Build-step-dependent behaviour | Code in repo != code that runs |
| Convention-over-configuration | Invisible wiring Claude can't grep |
| Monorepo with shared state | Editing one package breaks another invisibly |
| Stale documentation | Claude trusts docs — stale docs = confidently wrong |
| Feature flags / A-B tests | Multiplies code paths, unclear which is "real" |
| Preference proliferation | More branches to reason about |
| Inline content in tool responses | Bloats context window, reduces reasoning capacity |
| Large files (>1000 lines) | Requires offset reads, loses cross-reference context |

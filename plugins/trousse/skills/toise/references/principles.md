# Five Principles for Claude-Maintained Software

Software maintained by Claude has different architectural needs than software maintained only by humans. Claude starts every session fresh, reads files one at a time, excels at pattern-matching, and struggles with design judgement. Architecture that works for Claude encodes global decisions in discoverable artefacts so that each session can do good local work without the architect in the room.

These five principles are the testable core. Each has an automated metric (checked by `metrics.py`) and a judgement dimension (assessed by the reviewer agent).

---

## 1. Every File Tells You What It Does and Why

**Core question:** Can Claude open any file and know whether it's in the right place within 10 seconds of reading?

Claude arrives with no context. The first 10-20 lines of a file are Claude's only orientation before it decides whether to keep reading or move on. A file that explains its purpose and rationale is navigable. A file that starts with imports and dives into implementation is a guessing game.

This combines two concerns: structural legibility ("what does this do?") and decision rationale ("why is it done this way?"). Both must be discoverable at the file level because Claude can't git-blame your reasoning or remember yesterday's conversation.

**What good looks like:**
- Module docstring or header comment stating purpose
- Imports visible at the top, declaring dependencies explicitly
- Non-obvious design choices annotated where they appear
- Module names that describe purpose (`extract_tokenizer.rs`, not `utils.py`)

**What bad looks like:**
- Files named `helpers`, `utils`, `common`, `misc`
- No comment until line 50
- Design decisions that require reading git history to understand
- `# TODO: explain this` or no explanation at all

**Polyglot test:** Can Claude open any file and know whether it's in the right place within 10 seconds of reading?

**Grading:**
- **A:** Every source file's purpose is obvious from name + first 20 lines; non-obvious decisions annotated
- **B:** >80% of files self-document; a few need deeper reading
- **C:** Most files have some documentation but rationale is sparse
- **D:** Files start with raw implementation; purpose requires reading 100+ lines
- **F:** Modules named `utils`/`helpers`/`misc` with no documentation

---

## 2. One Shape, Everywhere

**Core question:** Can Claude see one module and correctly predict the shape of a sibling module it hasn't read?

Consistency is more valuable than local optimality. If every module follows the same pattern, Claude can work in any module after reading one example. If each is a snowflake, Claude rebuilds its mental model per file — burning context and increasing error rate.

This applies at every level: configuration types should use the same pattern (builder, dict, dataclass — pick one). Test files should follow the same structure. Error handling should be uniform. The specific pattern matters less than its consistent application.

**What good looks like:**
- One pattern for configuration across all configurable types
- One pattern for error handling (exceptions, Result types, error codes — pick one)
- One pattern for test files (same setup, same assertion style, same naming)
- New modules follow the shape of existing modules without being told to

**What bad looks like:**
- Config via constructor args in module A, via dict in module B, via env vars in module C
- Some tests use mocks, others use fixtures, others use live services
- Each module has its own approach to logging, validation, or error reporting
- "The pattern is explained in the wiki" (Claude can't read your wiki)

**Polyglot test:** Can Claude see one module and correctly predict the shape of a sibling module it hasn't read?

**Grading:**
- **A:** Clear dominant pattern visible across all modules; deviations are documented and justified
- **B:** Dominant pattern present in >80% of modules; minor inconsistencies
- **C:** Two or three competing patterns; no clear dominant shape
- **D:** Each module follows its own conventions
- **F:** No discernible pattern; every file is a surprise

---

## 3. Boundaries Are the Architecture

**Core question:** Can Claude determine, without reading the implementation, whether a change to module A could affect module B?

Not the functions, not the algorithms — the boundaries. What's public vs private. What's generated vs authored. What's this module's concern vs that module's. What the tests promise (the contract) vs how the code delivers (the implementation).

Claude navigates by boundaries: it reads CLAUDE.md to know what's where, module exports to know what's public, test assertions to know what's promised. Make boundaries explicit, machine-verifiable, and few.

Tests are a boundary mechanism — they define the contract between what a module promises and what it delivers. Tests that assert contracts ("this input produces this output") are more durable than tests that assert implementation ("this mock was called with these args"). Contract tests survive refactoring; implementation tests fight it.

**What good looks like:**
- CLAUDE.md or AGENTS.md with module map and dependency rules
- Generated vs authored files explicitly marked (manifest or directory convention)
- Public API is intentional and small; internal details are private
- Tests assert behaviour/contracts, not implementation details
- Dependency direction is documented and mechanically verifiable (grep for violations)

**What bad looks like:**
- No module map; Claude must read every file to understand the dependency graph
- Generated code mixed in with authored code, no manifest
- Everything is public; internal types leak into the API surface
- Tests are tightly coupled to implementation (mock-heavy, brittle)
- Circular dependencies between modules

**Polyglot test:** Can Claude determine, without reading the implementation, whether a change to module A could affect module B?

**Grading:**
- **A:** Boundaries documented, dependency direction enforced, tests assert contracts, generated/authored boundary explicit
- **B:** Most boundaries clear; some implicit dependencies exist
- **C:** Boundaries exist but aren't documented; Claude must infer from imports
- **D:** Modules freely import from each other; no clear layering
- **F:** Everything depends on everything; changing one file requires understanding the whole codebase

---

## 4. Small Files, Pure Functions, Explicit State

**Core question:** Can Claude make a correct change to a function without reading any other file?

Claude's context window is finite and its reasoning degrades with more moving parts. A 2000-line file means Claude works with partial information. A function with side effects means Claude can't reason about it locally. An implicit state machine — flags scattered across three files — means Claude needs to hold all three simultaneously to understand any of them.

This is three constraints in service of one goal: making each piece of code independently comprehensible.

**What good looks like:**
- Source files under 500 lines (800 as a soft ceiling, never over 1000)
- Core logic in pure functions: input -> output, no side effects
- I/O isolated to boundaries (entry points, adapters), not mixed into business logic
- State represented as explicit machines or single-authority containers
- State transitions visible in one place, not spread across files
- State keys declared in one place (typed dict, dataclass, schema block) so a fresh Claude can answer "what state does this app track?" without grepping

**What bad looks like:**
- Files over 1000 lines that require offset reads
- Business logic entangled with I/O (database calls inside calculation functions)
- State inferred from flag combinations across multiple files
- `this.state` mutated from 12 different methods
- "It depends on timing" — state is a race condition
- 50+ ad-hoc key accesses on a framework state container (session_state, Redux store) with no declared schema

**Polyglot test:** Can Claude make a correct change to a function without reading any other file?

**Grading:**
- **A:** >90% of files under 500 lines, core logic is pure, state has single authority with declared schema
- **B:** >80% under 500 lines, most core logic testable in isolation, state authority clear even if schema undeclared
- **C:** Mixed file sizes, some pure functions but I/O entangled in places, or state keys scattered without declaration
- **D:** Multiple files over 1000 lines, state management scattered across files
- **F:** Monolithic files, global mutable state, no separation of I/O from logic

---

## 5. Extend by Recipe, Not by Abstraction

**Core question:** Can Claude add a new [module/command/endpoint] by following written instructions without inventing any new patterns?

When Claude needs to add a capability, a concrete recipe ("copy `extractors/slides.py`, change the MIME type and the parse function, add the route in `tools/fetch.py`") is more reliable than an abstract extension point ("implement the `Extractor` interface, register it in the factory, update the dispatch table"). Recipes are linear. Abstractions are graphs. Claude follows lines better than it navigates graphs.

This doesn't mean no abstractions. It means the extension path — the thing Claude actually does when adding new functionality — should be documented as concrete steps, not as an interface to be discovered.

**What good looks like:**
- CLAUDE.md has "How to Add" recipes for common extension patterns
- Recipes reference specific files and specific changes
- Following the recipe produces working code without Claude inventing patterns
- The recipe matches what the codebase actually does (not aspirational)

**What bad looks like:**
- Extension requires understanding an abstract plugin system
- "Read the existing plugins for examples" (Claude must reverse-engineer the pattern)
- No extension documentation; Claude guesses from existing code
- The documented recipe is stale and doesn't match current code

**Polyglot test:** Can Claude add a new [module/command/endpoint] by following written instructions without inventing any new patterns?

**Grading:**
- **A:** Extension recipes present, specific, tested, and current
- **B:** Recipes present for major extension patterns; minor gaps
- **C:** Some guidance exists but recipes are vague or incomplete
- **D:** No recipes; extension requires reverse-engineering from existing code
- **F:** Extension requires understanding an undocumented abstract architecture

---

## Summary

| # | Principle | Core Question | Metric | Judgement |
|---|-----------|--------------|--------|-----------|
| 1 | Self-documenting files | Can Claude orient in 10 seconds? | First-breath score | Is the explanation accurate and sufficient? |
| 2 | One shape, everywhere | Can Claude predict sibling modules? | Pattern variance | Is the pattern good, or just consistent? |
| 3 | Boundaries are the architecture | Can Claude trace impact without reading implementation? | Artefact checklist | Are boundaries in the right places? |
| 4 | Small, pure, explicit | Can Claude change a function without reading other files? | File size distribution, purity signals | Is state management clear? |
| 5 | Extend by recipe | Can Claude add features by following instructions? | Recipe presence in CLAUDE.md | Are the recipes complete and correct? |

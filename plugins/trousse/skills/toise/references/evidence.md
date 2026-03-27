# Empirical Evidence: Rebuilds for Claude-Maintainability

Evidence from real codebase evolutions where software was rebuilt specifically to be more maintainable by Claude. Each case study maps to review checks in the parent skill.

## Case 1: claude-go to Gueridon (Mobile CC UI)

Three generations over ~6 weeks, each eliminating indirection.

### Phase 1: claude-go (retired)

Architecture: Phone -> WebSocket -> Node.js -> tmux session -> Claude Code (interactive) + JSONL file watching (chokidar) + Hook scripts -> POST to server

**The accidental distributed state machine:** Five independent systems (tmux, file watchers, hooks, WebSocket, HTTP server) had to agree on session state with no shared state machine. No single component could answer "what state is the session in right now?"

Failure modes:
- `tmux capture-pane` misses alternate screen buffer (CC's interactive UI)
- Keystroke injection required empirically-discovered 50ms delays
- chokidar on Linux read JSONL files mid-write
- Auto-approved tools still fired hooks, sending keystrokes to nowhere

### Phase 2: Gueridon v1 (Vite + pi-web-ui + WebSocket)

Replaced tmux/file-watching with `claude -p` stdio. But inherited component library complexity: Lit + Tailwind + 9 transitive deps + Vite build step + adapter layer translating CC events to pi-web-ui format.

### Phase 3: Gueridon v2 (current)

Architecture: Phone -> Tailscale (TLS) -> Node.js bridge (HTTP :3001) -> claude -p (stdio)

| Metric | claude-go | Gueridon v1 | Gueridon v2 |
|--------|-----------|-------------|-------------|
| CC communication | tmux scraping + file watching | `claude -p` stdio | `claude -p` stdio |
| Transport | WebSocket | WebSocket | SSE + POST |
| UI framework | Custom | pi-web-ui (Lit + Tailwind) | None (vanilla HTML/JS) |
| Build tooling | Unknown | Vite | None |
| Runtime deps | chokidar, tmux, hooks | pi-web-ui + 9 transitive | 2 (marked, web-push) |
| State management | Distributed across 5 systems | Adapter layer | Explicit StateBuilder |
| Tests | Unknown | Unknown | 576+, ~8s |

**Key lesson:** Each generation ruthlessly eliminated indirection. The through-line is: find where state is implicitly distributed, move authority to where the information actually lives, make consumers pure renderers.

### Phase 3.5: The Second State Machine (SSE protocol redesign)

Even within Gueridon v2, an accidental state machine emerged. The SSE protocol sent unaddressed deltas (`tool_start index:0` with no message ID). The client maintained a shadow state machine with backwards searches and collision detection to guess which message each delta belonged to.

From the bon item (gdn-poweke): "two state machines trying to agree on reality."

**Fix:** Server emits three addressed event types (`text`, `current`, `state`). Client becomes a pure displayer — renders what the server tells it. Net result: -35 lines of client code, one state machine eliminated.

**Key lesson:** Accidental state machines emerge incrementally. Each guard fixes a real bug, but the accumulation is two systems trying to agree on reality. The fix is always the same: move authority to where the information lives.

## Case 2: mcp-google-workspace to mise-en-space (Content Fetcher MCP)

Ground-up rebuild after competitive landscape analysis of 7 existing implementations.

### v1: mcp-google-workspace

- **17 tools** with 1:1 API mapping (each Google API operation = one MCP tool)
- Tool definitions alone burned ~15k tokens per session
- Monolithic tool files (slides.py at 658 lines, docs.py at 661 lines)
- Content returned inline in MCP responses (70-slide deck lands in context)
- No separation between discovery and retrieval
- Untestable without live API calls

### v2: mise-en-space (current)

- **3 verbs** (search, fetch, do) — tool definitions ~3k tokens
- Three-layer architecture with enforced dependency direction:
  - Extractors (pure functions, no I/O) -> testable with JSON fixtures
  - Adapters (thin API wrappers) -> may import extractors, never tools
  - Tools (wiring) -> connects adapters to extractors
- File deposits to `mise/` directory, not inline content
- Search returns metadata; fetch deposits content (discovery separated from retrieval)
- "How to Add" recipes in CLAUDE.md for the two most common extension patterns
- Field reports directory for real-world gaps found during use

| Metric | v1 (mcp-google-workspace) | v2 (mise-en-space) |
|--------|--------------------------|-------------------|
| Tool count | 17 | 3 |
| Tool token cost | ~15k tokens/session | ~3k tokens/session |
| Content delivery | Inline in MCP response | File deposit to disk |
| Largest file | 661 lines (monolithic) | ~300 lines (focused modules) |
| Test strategy | Requires live API | Extractors testable with fixtures |
| Extension pattern | Copy a 600-line file, modify | Follow "How to Add" recipe, write 3 small files |
| Layer enforcement | None | Documented + mechanically verifiable |

**Key lesson:** Claude extending a 17-tool monolith copies 600 lines and modifies. Claude extending a 3-verb layered architecture follows a recipe and writes 3 small, focused files. The architecture encodes the extension pattern.

## Cross-Cutting Patterns

These patterns appear in both case studies and constitute the empirical basis for the review checks:

| Pattern | Evidence | Review check it supports |
|---------|----------|--------------------------|
| Explicit > implicit state | claude-go's 5-system distributed state; Gueridon's shadow state machine | State clarity |
| Pure functions for core logic | mise extractors; Gueridon state-builder and bridge-logic | Testability |
| File deposits > inline content | mise v1 inline bloat; v2 deposits | Context fitness |
| Few verbs > many tools | 17 tools -> 3 verbs (5x token reduction) | Interface surface |
| No build step | Gueridon v1 Vite -> v2 edit-and-reload | Cost of change |
| Documented decisions | Both repos have decisions.md with rationale | Claude-readiness |
| Extension recipes | mise "How to Add"; Gueridon CLAUDE.md architecture section | Claude-readiness |
| Layer enforcement | mise's extractor/adapter/tool rule | Dependency direction |
| Small focused files | 600-line monoliths -> 300-line focused modules | Context fitness |
| Tests as specification | 576 tests (Gueridon), fixture-driven (mise) | Testability |

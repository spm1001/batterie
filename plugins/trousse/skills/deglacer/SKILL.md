---
name: deglacer
description: >
  MANDATORY gate BEFORE running jq on any .jsonl under ~/.claude/ or reading past CC sessions.
  Invoke FIRST when introspecting conversations, searching session history, parsing transcripts,
  or building tools that read ~/.claude/projects/ data. Provides the CC JSONL schema reference
  and `ccconv` extraction tool — prevents the 54-attempt fumble pattern where Claudes guess
  at field names. Triggers on 'what happened last session', 'find when we discussed',
  'parse session', 'read conversation', 'session history', 'token usage', 'ccconv'.
  Do NOT use for live session context (use garde-manger) or git history (use git log). (user)
allowed-tools: [Bash, Read, Grep, Glob]
---

# Déglacer — CC Session JSONL Reference

*Deglazing the pan to lift the fond — extracting the good bits from past sessions.*

## When to Use This Skill

You are working with Claude Code session data. This includes:

- **Introspecting past conversations** — "what did we discuss last session?", "when did we first talk about X?"
- **Searching session history** — finding sessions that mention a topic, tool, or file
- **Parsing JSONL transcripts** — extracting human messages, tool calls, thinking blocks, token usage
- **Building tooling** — anything that reads `~/.claude/projects/` session data
- **Debugging session format** — understanding why a jq query returns nothing

**Do NOT guess at the schema.** The CC JSONL format has multiple entry types, triple-duty `user` entries, streaming-duplicated `message.id`s, and inconsistent field presence across versions. This reference is the source of truth.

## When NOT to Use

- **Live session context** — use garde-manger for searching across past session memories
- **Git history** — use `git log` / `git blame` for code change history
- **Current conversation state** — you already have context, no need to parse your own session
- **Non-CC JSONL files** — this schema is specific to Claude Code sessions

---

## ccconv — The Extraction Tool

`ccconv` is a PEP 723 Python script that knows the CC JSONL schema. Use it instead of raw jq for structured extraction.

```bash
# Run directly (no install needed)
uv run --script ${CLAUDE_SKILL_DIR}/scripts/ccconv.py SESSION.jsonl

# Or if installed as a uv tool:
ccconv SESSION.jsonl
```

### Commands

```bash
ccconv SESSION.jsonl                  # conversation text (human + assistant)
ccconv --summary SESSION.jsonl        # human messages only (what was discussed)
ccconv --with-tools SESSION.jsonl     # include tool call summaries
ccconv --with-thinking SESSION.jsonl  # include thinking blocks
ccconv --last 5 SESSION.jsonl         # last 5 turns only
ccconv --json SESSION.jsonl           # structured JSON output
ccconv --stats SESSION.jsonl          # session statistics (tokens, models, tools)
ccconv --timeline SESSION.jsonl       # timestamped turn log
ccconv --find "search term"           # search across recent sessions
ccconv --recent                       # list recent sessions (default 20)
ccconv --recent 10                    # list N most recent
ccconv --today                        # list today's sessions
ccconv --since 2026-03-25             # sessions since a date
```

### Combining Flags

```bash
ccconv --with-tools --last 10 SESSION.jsonl    # recent turns with tools
ccconv --with-tools --with-thinking --json ...  # everything, structured
ccconv --summary --last 5 SESSION.jsonl         # quick recap of recent turns
```

---

## File Discovery

Sessions live at:
```
~/.claude/projects/{encoded-cwd}/{session-uuid}.jsonl
```

Where `{encoded-cwd}` replaces `/` with `-` in the project path.
Subagent transcripts: `{session-uuid}/subagents/agent-{id}.jsonl`.

**Find recent sessions:**
```bash
ls -lt ~/.claude/projects/*/*.jsonl | head -20
```

**Find sessions for a project:**
```bash
ls -lt ~/.claude/projects/-home-modha-Repos-myproject/*.jsonl
```

**Match session to slug/name:**
```bash
head -1 SESSION.jsonl | jq '{sessionId, slug, version}'
```

---

## The Schema

Each line in a `.jsonl` file is one JSON object. The `.type` field discriminates.

### Entry Types

| Type | Purpose | Has timestamp? |
|------|---------|---------------|
| `assistant` | Claude's response | Yes |
| `user` | Human msg / tool result / skill injection | Yes |
| `progress` | Streaming bash/hook/agent output | Yes |
| `system` | Turn timing, API errors, slash commands | Yes |
| `summary` | Context compaction | **No** |
| `queue-operation` | Input typed while Claude busy | Yes |
| `last-prompt` | Records last user text | No |
| `custom-title` | User-set session name | No |
| `agent-name` | Session agent name | No |
| `file-history-snapshot` | File backup state | No |
| `pr-link` | Created PR reference | Yes |
| `saved_hook_context` | Persisted hook output | Yes |

### Common Fields (on user/assistant entries)

```
uuid            string    Unique entry ID
parentUuid      string?   Previous entry (linked list)
sessionId       string    Session UUID (matches filename)
timestamp       string    ISO 8601
cwd             string    Working directory
gitBranch       string    Current git branch
version         string    CC version (e.g. "2.1.85")
slug            string    Human-readable session name
userType        string    Always "external"
entrypoint      string    "cli" (absent in v2.0.x)
isSidechain     boolean   Side conversation flag
```

### assistant entries

```json
{
  "type": "assistant",
  "message": {
    "id": "msg_...",
    "type": "message",
    "role": "assistant",
    "model": "claude-opus-4-6",
    "content": [/* content blocks */],
    "stop_reason": "end_turn" | "tool_use" | null,
    "usage": {
      "input_tokens": 119,
      "cache_creation_input_tokens": 18531,
      "cache_read_input_tokens": 36004,
      "output_tokens": 500
    }
  },
  "requestId": "req_..."
}
```

**Content block types:**
- `{type: "text", text: "..."}` — Claude's text
- `{type: "tool_use", id: "toolu_...", name: "Bash", input: {...}}` — tool call
- `{type: "thinking", thinking: "...", signature: "..."}` — extended thinking

**DRAGON: Multiple entries share the same `message.id`.** CC streams
incremental updates. Merge content blocks by `message.id`, dedup
`tool_use` blocks by their `id` field. ccconv handles this automatically.

**DRAGON: `stop_reason` is null in older sessions** (pre-v2.1.79).

### user entries (TRIPLE DUTY)

The `user` type serves three purposes. Discriminate with:

| Subtype | How to detect | Content shape |
|---------|--------------|---------------|
| Human message | `typeof content === "string"`, has `permissionMode` | String |
| Tool result | Has `toolUseResult` | Array of `{type: "tool_result"}` |
| Skill/system injection | `isMeta: true` | Array of `{type: "text"}` |

**Human message:**
```json
{
  "type": "user",
  "message": {"role": "user", "content": "the actual human text"},
  "permissionMode": "default",
  "promptId": "..."
}
```

**Tool result:**
```json
{
  "type": "user",
  "message": {"role": "user", "content": [
    {"type": "tool_result", "tool_use_id": "toolu_...", "content": "output text"}
  ]},
  "toolUseResult": {/* shape varies by tool */},
  "sourceToolAssistantUUID": "..."
}
```

**toolUseResult shapes:**

| Tool | Keys |
|------|------|
| Bash | `stdout, stderr, interrupted, isImage, noOutputExpected` |
| Bash (large) | + `persistedOutputPath, persistedOutputSize` |
| Write/Edit | `content, filePath, originalFile, structuredPatch, type` |
| Read | `file, type` |
| Agent | `agentId, agentType, content, prompt, status, totalDurationMs, totalTokens, totalToolUseCount, usage` |
| Error | Bare string: `"User rejected tool use"` |

### Token Counting

The `input_tokens` field is ONLY the non-cached portion.
Real input = `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`.

### summary entries (minimal)

```json
{"type": "summary", "leafUuid": "...", "summary": "short text"}
```

No uuid, parentUuid, timestamp, version, or sessionId. Three fields only.

### system entries

`.subtype` discriminates:
- `turn_duration`: `{durationMs, messageCount}`
- `api_error`: `{error: {status, headers, requestID}, retryInMs, retryAttempt}`
- `local_command`: `{content: "...", level: "info"}` — slash commands

---

## jq Recipes (when ccconv isn't enough)

**Quick schema discovery (do this FIRST, not `head | jq .`):**
```bash
jq -r '.type' FILE.jsonl | sort | uniq -c | sort -rn
```

**Extract human messages:**
```bash
jq -r 'select(.type == "user" and .permissionMode and (.isMeta | not))
  | .message.content' FILE.jsonl
```

**Extract assistant text (handles multi-block):**
```bash
jq -r 'select(.type == "assistant")
  | [.message.content[]? | select(.type == "text") | .text]
  | select(length > 0) | join("\n")' FILE.jsonl
```

**Extract tool calls:**
```bash
jq -c 'select(.type == "assistant")
  | [.message.content[]? | select(.type == "tool_use")
  | {tool: .name, input_keys: (.input | keys)}]
  | select(length > 0)' FILE.jsonl
```

**Session timeline:**
```bash
jq -c 'select(.type == "user" or .type == "assistant")
  | {ts: .timestamp, type, model: .message.model?}' FILE.jsonl
```

**Token usage per turn:**
```bash
jq -c 'select(.type == "assistant") | .message.usage
  | {in: (.input_tokens + .cache_creation_input_tokens + .cache_read_input_tokens),
     out: .output_tokens}' FILE.jsonl
```

**Find sessions mentioning a term:**
```bash
# Prefer: ccconv --find "term"
# Raw jq fallback:
for f in ~/.claude/projects/*/*.jsonl; do
  if jq -e 'select(.type == "user" and (.message.content | type) == "string"
    and (.message.content | test("term"; "i")))' "$f" >/dev/null 2>&1; then
    echo "$f"
  fi
done
```

---

## Anti-Patterns (DON'T)

| Don't | Why | Do instead |
|-------|-----|-----------|
| `jq -s '.'` on JSONL | Slurps entire file into memory as array | Stream line-by-line (default jq behaviour) |
| `jq '.[]'` on JSONL | JSONL isn't an array | Each line is already a separate object |
| `.role` at top level | Role is at `.message.role`, not top-level | Use `.type` for entry type |
| `.type == "message"` | No such type | Types: `user`, `assistant`, `progress`, `system`, etc. |
| `.type == "human"` | No such type | `.type == "user"` + check it's not a tool result |
| `head -1 \| jq .` for discovery | Wastes a turn, first line may be queue-operation | `jq -r '.type' \| sort \| uniq -c` |
| Assume content is string | Assistant content is always array; user content varies | Check type before accessing |
| `2>/dev/null` on everything | Hides real errors | Understand the schema, don't hedge |
| Guess at field names | 39% of jq-on-.claude commands are schema discovery | Read this reference |

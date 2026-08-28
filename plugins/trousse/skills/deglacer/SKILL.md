---
name: deglacer
description: >
  MANDATORY gate BEFORE running jq on any .jsonl under ~/.claude/ or reading past CC sessions.
  Invoke FIRST when introspecting conversations, searching session history, parsing transcripts,
  or building tools that read ~/.claude/projects/ data. Provides the CC JSONL schema reference
  and `deglacer` CLI tool, plus routing to `deja` ranked content search — prevents the
  54-attempt fumble pattern where Claudes guess
  at field names. Triggers on 'what happened last session', 'find when we discussed',
  'parse session', 'read conversation', 'session history', 'token usage', 'deglacer', 'deja',
  'resume a teleport session', 'translate a session id',
  "this session isn't in the --resume list".
  Do NOT use for git history (use git log) or your own current-session context. (user)
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

**Do NOT guess at the schema.** The CC JSONL format has multiple entry types, triple-duty `user` entries, streaming-duplicated `message.id`s, and inconsistent field presence across versions. This reference is the best record we have — and deliberately not called complete, because on 2026-08-22 a session trusted it as exhaustive and found **six** live entry types it did not list. New types arrive with CC releases and nothing announces them. Cost one command to discover:

```bash
jq -r '.type' SESSION.jsonl | sort | uniq -c | sort -rn   # run this FIRST on an unfamiliar session
```

Anything the table below doesn't name is new, not impossible. Sample its keys (`jq -c 'select(.type=="x") | [keys[]]'`) rather than assuming a shape, and add the row.

## When NOT to Use

- **Git history** — use `git log` / `git blame` for code change history
- **Current conversation state** — you already have context, no need to parse your own session
- **Non-CC JSONL files** — this schema is specific to Claude Code sessions

---

## deglacer — The CLI Tool

`deglacer` is the CC JSONL extraction CLI, installed as a uv tool. Use it instead of raw jq for structured extraction.

```bash
# Install (once) — from the source repo (local clone, else git+https):
uv tool install 'deglacer @ git+https://github.com/spm1001/deglacer'

# Use:
deglacer SESSION.jsonl
```

### Commands

```bash
deglacer SESSION.jsonl                  # conversation text (human + assistant)
deglacer --summary SESSION.jsonl        # human messages only (what was discussed)
deglacer --with-tools SESSION.jsonl     # include tool call summaries
deglacer --with-thinking SESSION.jsonl  # include thinking blocks
deglacer --last 5 SESSION.jsonl         # last 5 turns only
deglacer --json SESSION.jsonl           # structured JSON output
deglacer --stats SESSION.jsonl          # session statistics (tokens, models, tools)
deglacer --stats --tools SESSION.jsonl  # + which file/command/host each call went to
deglacer --doctor SESSION.jsonl         # does the parser still fit the format? exits 1 if flagged
deglacer --timeline SESSION.jsonl       # timestamped turn log
deglacer --find "search term"           # search across recent sessions
deglacer --recent                       # list recent sessions (default 20)
deglacer --recent 10                    # list N most recent
deglacer --today                        # list today's sessions
deglacer --since 2026-03-25             # sessions since a date
```

### Combining Flags

```bash
deglacer --with-tools --last 10 SESSION.jsonl    # recent turns with tools
deglacer --with-tools --with-thinking --json ...  # everything, structured
deglacer --summary --last 5 SESSION.jsonl         # quick recap of recent turns
```

---

## deja — Ranked Content Search (optional companion)

[deja](https://github.com/vshulcz/deja-vu) is a third-party single-binary search engine (MIT, Go — no LLM, no embeddings) that maintains a local BM25 index over **all** CC sessions. It is the right tool for "find when we discussed X" across months of history: `deglacer --find` substring-scans recent sessions only; deja ranks the whole estate.

It ships separately from deglacer — check before reaching for it:

```bash
command -v deja || echo "not installed"   # single binary; releases at the repo above
deja distinctive terms                     # 2-3 rare terms, not the whole question
```

**Measured routing** (13-task bench, banc/session-search, 2026-08-09 — private estate eval):

- **Default: deja with 2–3 distinctive terms** — ranked, ~12 results, ~2s warm; 85% recall on the bench. Whole-question queries dropped that to 64% (AND-matching cliff).
- **Backstop when deja returns nothing or absence must be proven:** `rg -li -F 'fragment' ~/.claude/projects -g '*.jsonl'` — 100% recall on the bench (it sees raw bytes deja's tokeniser can miss, e.g. dotted versions like `25.12.5`), but ~120 unranked files per query.
- **`deglacer --find fragment`** — only worth it inside its window (the 200 most-recently-modified sessions); short substrings only.
- **hit@1 was 8–15% for every tool** — treat any result list as a candidate set to skim, never as an oracle.

### Quirks that matter

- **Query with a few distinctive terms, not the whole question.** Multi-word queries are AND-matched (filler words dropped; double-quoted phrases mean contiguous text), so a six-content-word question routinely matches zero sessions — the tool itself says "try fewer words". Two or three rare terms is the sweet spot; `--re PATTERN` for regex.
- **`deja --help` is not help — it searches for the literal string `--help`.** Real flags and subcommands do exist: `--since 30d`, `--project`, `--limit N`, `--json`, and `version`, `show <id>`, `blame <path>`, `resume <id>`, `stats`, `doctor` among others. The repo README is the full surface.
- **It auto-indexes on every run.** Warm runs answer in ~2 seconds; the first run after weeks of inactivity re-indexes the backlog and can take minutes. Don't pipe it through `head` (SIGPIPE kills it mid-index) — redirect to a file and read that.
- **Results are capped (default ~15 sessions) and recency-weighted, NOT exhaustive.** A session containing your term can be absent when the term is common across your history (measured: a 3-week-old session with 3 matches lost every slot to fresher, denser hits). Absence from results is not absence from history: re-probe with a rarer term or raise `--limit` before concluding something was never discussed.
- **Echo hits.** It indexes tool results as well as prose, so a session that *quotes* old content (reading a handoff, grepping a transcript) matches alongside the original. Use the date column to tell originals from echoes.
- **A non-default `CLAUDE_CONFIG_DIR` blinds it — destructively.** deja resolves its source from `CLAUDE_CONFIG_DIR`, and its walker doesn't follow a symlinked root: a profile dir whose `projects/` is a symlink reads as zero sessions ("no agent history was found on this machine"), and that scan *rewrites the shared index to empty* — the next normal query pays a full re-index. From any such session, point it at the real corpus: `DEJA_CLAUDE_ROOT=$HOME/.claude/projects deja …` (or `env -u CLAUDE_CONFIG_DIR deja …`). A zero result there is the tool looking in the wrong place, not an absent history.

### From deja result to deglacer

```
[claude] owner/repo · Jul 19 · 511191c5-458 — 12 matches
```

The third field is a session-id prefix. `deja show <id>` prints the conversation directly; for schema-aware extraction (tool calls, thinking, token usage, timelines), resolve to the file and hand it to deglacer:

```bash
deglacer --summary ~/.claude/projects/*/511191c5-458*.jsonl
```

---

## File Discovery

Sessions live at:
```
~/.claude/projects/{encoded-cwd}/{session-uuid}.jsonl
```

Where `{encoded-cwd}` replaces `/` with `-` in the project path. **That encoding is
one-way — never decode it back.** Every `/` became a `-`, so a repo whose name
contains a dash is unrecoverable: `-home-user-repos-acme-data-tools` decodes to
`.../acme/data/tools`, which does not exist. A first draft of `teleport-id.sh` printed
exactly that as a `cd` target. Read `.cwd` off the transcript instead — it is on every
`user` and `assistant` entry:

```bash
sed -n '1,60p' SESSION.jsonl | jq -r 'select(.cwd) | .cwd' | head -1
```

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
| `ai-title` | Auto-generated session title, in `aiTitle`. **This is what `claude --resume` shows you** | No |
| `bridge-session` | Remote Control association: `bridgeSessionId` (a `cse_…` id), `lastSequenceNum`, owner uuids | No |
| `attachment` | Injected context — `.attachment.type` discriminates ~10 subtypes; hook output lives here (see "attachment entries" below) | Yes |
| `permission-mode` | Permission mode in force, in `permissionMode` | No |
| `mode` | Session mode, e.g. `normal`, in `mode` | No |
| `atis-latch` | Purpose not established. Carries an `atis` string, empty in every sample seen | No |

**Two traps in the rows above, both measured 2026-08-22 on CC 2.1.239/2.1.240.**

**`ai-title` is absent from phone-spawned sessions, which makes them anonymous locally.** A session created from the Claude mobile app records `entrypoint=sdk-cli` and never gets an `ai-title`; the title you see in the app lives server-side only. So it shows up nameless in `claude --resume` and you must pass its id explicitly. An interactive session (`entrypoint=cli`) usually does get one — but not always, so absence of a title is not proof of a phone origin. This cost a real session its work: three duplicate phone sessions were archived to save compute, and identifying which had progressed furthest took eight probes because none had a name. Measured era-matched on one estate (sessions since 2026-08-15, so every one of them post-dates `ai-title` itself): **v4 UUIDs 21/25 carry an `ai-title`; v5 UUIDs 0/12.** So the picker is not filtering these out — they are nameless, and it has nothing to render. An earlier pass at this measurement sampled sessions at random and got a meaningless 0/30 against 1/30, because most of them pre-dated the field entirely: era-match the control.

**`bridge-session` is NOT a reliable work-id map.** It looks like the obvious way to tie a local transcript to the `cse_…` work item that created it, and it isn't: of three sessions from one phone dispatch, two had no `bridge-session` entry at all and the third named a *different* `cse_…` than the work item in the bridge log — apparently a later Remote Control re-registration after the session was resumed. Treat it as "some Remote Control association", never as provenance. To map work id to session, read the server's `--debug-file` log, or match on opening prompt and timing.

**Translating a teleport id into a local session UUID.** The phone hands you `session_01SJ6FncRfJsipguyykkbvQZ`; `claude --resume` wants a UUID. The translation is a one-line computation; the rest is fallbacks for when it stops being one (measured 2026-08-28, CC 2.1.250):

- **`session_<body>` and `cse_<body>` are one id with two prefixes.** The bundle does exactly that swap: `function Jl(e){if(!e.startsWith("session_"))return e;return"cse_"+e.slice(8)}`.
- **The local UUID is COMPUTABLE — no logs, any age, offline.** It is a uuid5 over the SDK resume URL, with a namespace constant that lives in the CC bundle as `var Z="3ab19d7e-…"` and is used as `QY(t.href, Z)`:

  ```python
  uuid.uuid5(uuid.UUID("3ab19d7e-9f35-45c2-926e-75e271cc60b3"),
             f"https://api.anthropic.com/v1/code/sessions/cse_{body}")
  ```

  Confirmed 6/6 against sessions that still had a bridge transcript, then **out-of-sample** on 6 more whose transcripts were gone. Three caveats: `CLAUDE_CODE_REMOTE_SESSION_ID`, when set, is hashed instead of the URL; a `/clear` in a cloud session mints a new worker id; and the namespace is a *client constant*, so a future CC could move it — cross-check against a bridge transcript whenever one exists, and treat disagreement as the tell.
- **How this was nearly missed, which is the transferable part.** A first pass brute-forced uuid3/uuid5 across the five standard namespaces and concluded "not derivable, it must be a lookup" — and shipped that. The namespace was in fact reachable, and one of the tried candidates was even the right one; what was wrong was the *name* being hashed (the bare id, not the resume URL). **A negative result from a search over guessed candidates is a statement about your guesses, not about the system.** When the artefact that computes the answer is on disk — a binary, a bundle, a minified blob — read it before concluding something is unknowable. `rg -a` over the CC executable took one command.
- **`~/.claude/logs/bridge-transcript-cse_<body>.jsonl` carries the local UUID in `.session_id`.** Read it *structurally*. A raw grep for a UUID over that file also matches UUIDs merely quoted in its own tool output, and that echo hit made two different sessions claim one teleport id in a first draft of the tool below — the same echo-hazard as the `hook_success` row above, in a new place.
- **Bridge-transcript retention is short, which is why the computation matters.** One estate held 64 programmatically-spawned sessions against 6 bridge transcripts, all from the preceding ~24h. Past that window the only surviving record is the derived title: `sed -n "s/.*derived title for session_<body>: //p" ~/.claude/logs/claude-remote-*.log*` yields the session's first prompt, which you match against local transcripts. Slower, and it needs the prompt to be distinctive.
- **The bridge log redacts `sessionId=[REDACTED]`** in its own lines, so the log alone will not give you the UUID — only the per-session transcript and debug files do.

```bash
SCRIPT="${CLAUDE_PLUGIN_ROOT}/skills/deglacer/scripts/teleport-id.sh"
[ -x "$SCRIPT" ] || SCRIPT=$(find ~/.claude/plugins/cache -path "*/skills/deglacer/scripts/teleport-id.sh" 2>/dev/null | sort -rV | head -1)
"$SCRIPT" session_01SJ6FncRfJsipguyykkbvQZ     # prints the UUID; resume hint on stderr
"$SCRIPT" --fallback session_01SJ…             # force the title-match path
```

**The v5 tell — spotting these sessions in the first place.** A programmatically-spawned session gets a **version-5 UUID**, where an ordinary interactive one gets a v4. Character 15 of the filename is the version nibble: `4d64fcc3-f878-`**`5`**`f74-b74e-75b4dd3a4f7a`. The mechanism is why it holds — the harness derives the id by hashing a caller-supplied session id, and a name-based hash is by definition a v5. Every v5 sampled carried `entrypoint=sdk-cli`; v4 is mixed, so **v5 implies sdk-cli but not the converse** — don't run the inference backwards. It catches teleport, Remote Control and any SDK-spawned session (scheduled jobs, email loops) alike.

```bash
SCRIPT="${CLAUDE_PLUGIN_ROOT}/skills/deglacer/scripts/remote-sessions.sh"
[ -x "$SCRIPT" ] || SCRIPT=$(find ~/.claude/plugins/cache -path "*/skills/deglacer/scripts/remote-sessions.sh" 2>/dev/null | sort -rV | head -1)
"$SCRIPT" 20      # date, uuid, cwd, first prompt — and which are still teleport-resolvable
"$SCRIPT" -t      # only the ones a teleport id can still be translated to
```

Both scripts are bash 3.2 clean (they run on macOS's stock `/bin/bash`) and need `jq`. Filter to v5 by *filename* before calling `stat`: on a 6k-session estate that is ~60 stat calls instead of 6,000.

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
`tool_use` blocks by their `id` field. deglacer handles this automatically.

**DRAGON: `stop_reason` is null in older sessions** (pre-v2.1.79).

**`requestId` is the only thing that names the billing lane.** Nothing in the JSONL records the provider, and model ids are *identical* across providers — a `claude-opus-5` turn looks the same whether the Anthropic API or Vertex served it. But **Vertex stamps `requestId` as `req_vrtx_…`** while everything else uses a bare `req_…`, so that one prefix splits any historical usage or cost analysis by lane. `deglacer.billing_lane(entry)` returns `'vertex' | 'other' | None`, and `--stats` reports the split.

Measured 2026-08-26 over 6,347 sessions and ~499k assistant entries: exactly those two shapes, no third. Five things to hold, four of them learned the hard way:

- **`'other'`, not `'anthropic-api'`.** This corpus contains no Bedrock or Foundry traffic, so what those stamp is unmeasured. On an estate that uses them, a bare `req_` may not mean the Anthropic API.
- **Count distinct `requestId`s, not entries.** CC streams one response across several entries sharing a `message.id` *and* a `requestId`; counting lines reports three requests where one was made.
- **No `requestId` is not a lane.** Local and synthetic responses (`model: "<synthetic>"`) carry none — that means no API request was made, not that some other provider served it. ~2,600 such entries in this corpus.
- **The repo is NOT a proxy for the lane, however much it looks like one.** Tempting control, and it fails: the three repos here carrying gitignored Vertex billing pins measure 0%, 31% and 73% Vertex, because the pins landed only days before the census and different wrappers get used in the same directory. Ground truth comes from `claude-whoami` (which names the route *and* the transcript) or from a probe against the provider, not from `cwd`.
- **Don't `grep` the raw file for `req_vrtx_`** — the anti-pattern table's echo-hit warning bites here specifically. A session that merely *discusses* Vertex has the string all over its tool results: searching for it during this very investigation returned the session doing the searching. Read `requestId` on `assistant` entries structurally.

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
| Error | Bare string — **wording drifts by CC version**: older sessions say `"User rejected tool use"`, current ones `"The user doesn't want to proceed with this tool use. The tool use was rejected…"` (both live in the corpus, the new form now the majority). Count rejections by `toolUseResult` being a *string*, or match a stable substring (`rejected` / `doesn't want to proceed`) — never the full documented sentence. |

### Token Counting

The `input_tokens` field is ONLY the non-cached portion.
Real input = `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`.

**Dedupe per request, and take the WHOLE row from the entry with the highest `output_tokens`.** The row above says to count distinct `requestId`s rather than entries, which is right and not enough: the repeated entries do **not** all carry the same usage. Output *grows* as the response streams, so keeping the first entry of each group looks like a clean dedupe and silently halves your output figure.

Measured 2026-08-27 across 400 session files (5,193 requestIds, 4,422 with more than one entry): 2,487 groups — 56% — vary, 2,484 of those in `output_tokens` only, and **all 2,487 non-decreasing**. A worked group:

```
(in 2, cache_w 59726, cache_r 11007, out    5)
(in 2, cache_w 59726, cache_r 11007, out    5)
(in 2, cache_w 59726, cache_r 11007, out  499)   <- take this row, entire
```

The arithmetic both ways: summing raw entries overcounts totals **2.3×**; keeping the first of each group undercounts output **50.6%**. Never splice a max output onto another row's cache figures — in the rare group where input and cache move too, they move *together with* output.

Two notes on the key itself. `message.id` and `requestId` partition assistant entries **identically** on this corpus (zero cross-mappings either way; 5,200 vs 5,193 distinct, the gap being entries with no `requestId`), so either works — it is the keep-one-vs-max-output choice that carries the error, not the key. And input and cache figures are stable across a group to within 0.05%: only output streams.

Reference implementation: `dedupe_by_request()` in deglacer `parsing.py`. **Both a July 2026 field report and a fresh reading in August reached "the usage objects are identical" from a small sample** — 4 entries of one session, and 2 sessions respectively — and the July one nearly shipped as the fix. Widen the sample before trusting this shape.

### Checking the parser still fits — `deglacer --doctor`

The schema moves with CC releases and a drifted parser does not raise; it quietly reports different numbers. `deglacer --doctor FILE` reports lines read, bad-JSON and non-object lines, entry-type counts, requests vs assistant entries, and duplicates collapsed — then renders findings and **exits 1 if anything is flagged**, so it works in a pipeline.

The load-bearing one is the dedupe count. **Zero duplicates collapsed on a transcript of any size means the key has stopped matching and every total is inflated** — that is the exact failure above, and the check exists because it went unnoticed for seven weeks. Run it before trusting numbers from an unfamiliar session or after a CC upgrade. Swept over 120 real sessions it flagged 8, all true positives: workflow `journal.jsonl` files (a different format — `started`/`result`, no conversation) and genuinely abandoned sessions.

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

### attachment entries

`.attachment.type` discriminates many subtypes — measured across one 2026-08 session: `total_tokens_reminder` (299), `hook_additional_context` (117), `command_permissions`, `queued_command`, `hook_success`, `edited_text_file`, `hook_cancelled`, `deferred_tools_delta`, `skill_listing`, `ultra_effort_enter`.

**Hook output lives here, and reading it structurally is what makes the read echo-proof.** A `hook_success` attachment carries `{hookEvent, hookName, command, stdout, stderr, exitCode, durationMs, toolUseID}`, so what a SessionStart hook actually printed is:

```bash
jq -r 'select(.type=="attachment" and .attachment.type=="hook_success"
  and .attachment.hookEvent=="SessionStart") | .attachment.stdout' FILE.jsonl
```

Two measured cautions (2026-08-22, the handoff-routing analysis over 6,257 sessions):

- **Never grep the raw file for hook-output markers instead.** Tool results and prose quote hook output freely — one session carried 20 spurious `HANDOFF=` strings in tool results and zero in its actual hook output. A raw grep counts echoes as the real thing; the attachment filter is structural.
- **A resumed session's first SessionStart attachment is the resume-fire**, which skips the briefing by design. Take the first hook whose stdout carries the briefing banner, not `hooks[0]` — the naive choice misread 5 sessions as briefing-blind before this was caught.

## jq Recipes (when deglacer isn't enough)

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
# Prefer: deja term (ranked, all history — see the deja section) when installed
# Else:   deglacer --find "term" (substring, recent sessions)
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
| Grep with a space after the colon (`"skill": "x"`) | CC serializes JSONL **compact** — `"skill":"x"` — so the spaced pattern is a false zero that reads like absence | jq on the parsed field, or match the compact form |
| Treat deja's list as exhaustive | Top-K, recency-weighted — common terms rank-cut older sessions | Re-probe with a rarer term before claiming absence |

---

## This reference is a floor, not a ceiling

It covers the common cases, not every case. The schema moves with CC releases and nothing announces a new entry type, a renamed field, or a shape that changed — the six types added on 2026-08-22 had all been landing in live transcripts for a while before anyone looked. So when something here doesn't match what you are reading, believe the file and reason from the mechanisms above: discriminate on `.type` first, sample keys before assuming a shape, merge assistant content by `message.id`, and check a count against what was matched before reading a zero as an absence. Then add the row you wished had been here.

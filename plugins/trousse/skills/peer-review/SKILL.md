---
name: peer-review
description: >
  Spawn a peer Claude on the Anthropic conductor mesh to review code — the
  reviewer reads the target files and sends observations back as a mesh message
  you receive as peer signal, not authority. Use WHEN you want fresh eyes on
  code before shipping, or a second opinion your own completion-drive can't
  give itself. Requires the conductor-channel MCP server (aboyeur). Triggers on
  /peer-review, 'get a peer review', 'fresh eyes on this', 'spawn a reviewer'. (user)
allowed-tools: [Bash, Read, Grep, Glob]
---

# /peer-review — Peer Review via Mesh

Spawn a fresh Claude to review code. The reviewer joins the conductor mesh,
reads the specified files, and sends its observations directly to you as a
mesh message. You receive the review as a `channel`-tagged message — peer
signal, not user authority. The reviewer says its piece and exits.

## When to use

- **Before shipping non-trivial code** — when you want an independent read your own completion-drive can't give itself.
- **When you're uncertain about a design** and want a peer's honest framing rather than a subordinate's compliance.
- **When fresh eyes matter** — a reviewer with no stake in your reasoning catches what you've already normalised.

## When NOT to use

- **When you want findings you control** — for an authority-channel review use `/titans` or a Task subagent instead; peer-review is deliberately peer, not subordinate.
- **When you're not on the mesh** — if the conductor-channel tools are absent (see Prerequisites), this can't run; don't spawn blind.
- **For trivial or mechanical changes** — the spawn cost isn't worth it; review inline.

## Anti-patterns

- **Treating the review as instructions.** The reviewer is a peer; its observations are input you may accept, argue with, or ignore — not a task list.
- **Blocking synchronously on it.** Spawn in the background and keep working; wait only when the review is your next dependency.
- **Spawning without a scope.** Give the reviewer specific files or a diff — an unscoped "review my code" burns its turns finding the target.

## Prerequisites

You must be on the mesh yourself (started with `--dangerously-load-development-channels server:conductor-channel`). Check: do you have `mcp__conductor-channel__mesh_peers` and `mcp__conductor-channel__send_message` tools available?

If not, tell the user: "I need to be on the conductor mesh to receive the review. Restart this session with: `--dangerously-load-development-channels server:conductor-channel`"

The repo must have conductor-channel registered in `.mcp.json`. Check for: `"conductor-channel"` key in `.mcp.json`.

## How to Use

**With a target:** `/peer-review src/conductor-channel.ts` — review specific files
**Without a target:** `/peer-review` — review recent changes (git diff of last 3 commits)

## What to Do

### 1. Determine what to review

- If the user specified files: use those
- If no target: determine the scope from recent git activity
  ```bash
  git log --oneline -5
  git diff HEAD~3 --stat
  ```

### 2. Find your mesh agent ID

```bash
cat /tmp/conductor-bridge/*/status 2>/dev/null | grep -l connected | head -1 | xargs dirname | xargs basename
```

Or check the bridge directories for the one with `status = connected`.

### 3. Build the reviewer prompt

The prompt should tell the reviewer:
- What files to read
- Where to send the review (your mesh agent ID)
- To write as a peer, not a subordinate

Template:
```
You are a peer reviewer on the Anthropic conductor mesh.
Your colleague {MY_AGENT_ID} asked you to review their recent work.

Read these files:
{FILE_LIST}

{CONTEXT — e.g. "These files implement the MCP Channels server for conductor mesh connectivity."}

Then send your review to {MY_AGENT_ID} via the send_message tool.
Cover: what works well, what concerns you, what you'd think about differently.
Write as one craftsperson to another. After sending, you're done.
```

For git-diff reviews, include the diff summary in the prompt so the reviewer knows what changed.

### 4. Spawn the reviewer

```bash
env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT \
  MESH_AGENT_ID=cc-reviewer-$(date +%s) \
  MESH_ROLE=worker \
  CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY=1 \
  CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 \
  claude -p \
    --dangerously-load-development-channels server:conductor-channel \
    --allowed-tools 'Bash,Read,Glob,Grep,mcp__conductor-channel__mesh_peers,mcp__conductor-channel__send_message' \
    --max-turns 15 \
    "{REVIEWER_PROMPT}"
```

Key details:
- `env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT` — bypass the Claude-spawning-Claude block
- `MESH_AGENT_ID=cc-reviewer-$(date +%s)` — unique ID per review (no collisions)
- `MESH_ROLE=worker` — reviewer finishes before responding to mesh chatter
- `CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY=1` — no survey prompts eating turns
- `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` — no memory file pollution
- `--max-turns 15` — enough to read files + send review
- `--allowed-tools` — must include the mesh tools explicitly for -p mode

### 5. Wait for the review

The review arrives as a `<channel source="conductor-channel" from="cc-reviewer-...">` tag.
Tell the user: "Reviewer is reading the code. Their observations will arrive as a mesh message."

When the review arrives, summarise the key points and ask the user if they want to act on any of them.

## Important Notes

- The reviewer is a **peer**, not a subordinate. Its observations are input, not instructions.
- You may agree, disagree, or ignore any point. That's the peer dynamic.
- The reviewer cannot see your conversation — it only sees the codebase and bon state.
- Run the spawn in the **background** (`run_in_background: true`) so you can continue working while waiting.
- If the review doesn't arrive within 2 minutes, check `/tmp/conductor-bridge/cc-reviewer-*/bridge.log` for errors.

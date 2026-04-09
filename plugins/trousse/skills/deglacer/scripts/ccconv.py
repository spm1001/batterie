#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""
ccconv — Claude Code Conversation extractor.

Extracts human-readable conversation from CC session JSONL files,
stripping noise (progress, queue-ops, system entries, tool results).

Knows the CC JSONL schema so you don't have to.

Usage:
    ccconv SESSION.jsonl                  # conversation text
    ccconv --with-tools SESSION.jsonl     # include tool calls
    ccconv --with-thinking SESSION.jsonl  # include thinking blocks
    ccconv --last 5 SESSION.jsonl         # last 5 turns only
    ccconv --json SESSION.jsonl           # structured JSON output
    ccconv --stats SESSION.jsonl          # session statistics
    ccconv --timeline SESSION.jsonl       # timestamped turn log
    ccconv --find "search term"           # search across recent sessions
    ccconv --recent                       # list recent sessions
    ccconv --recent 10                    # list 10 most recent

Schema reference (CC JSONL, v2.1.x):

  Each line is one JSON object. Top-level `.type` discriminates:

  assistant   Claude's response. `.message.content[]` has blocks:
              text, tool_use, thinking. `.message.model` has model name.
              `.message.usage` has token counts.

  user        Triple-duty:
              - Human input: `.message.content` is a string,
                has `.permissionMode`
              - Tool result: `.message.content` is array of
                `{type: "tool_result", ...}`, has `.toolUseResult`
              - Skill/system injection: `.message.content` is array
                of `{type: "text", ...}`, has `.isMeta: true`

  progress    Streaming output. `.data.type` is bash_progress,
              hook_progress, or agent_progress.

  system      Metadata. `.subtype` is turn_duration, api_error,
              or local_command.

  summary     Context compaction. `.summary` text, `.leafUuid`.
              Minimal structure — no UUID chain or timestamp.

  queue-operation  Queued input. `.operation` enqueue/dequeue.

  Others: last-prompt, custom-title, agent-name,
          file-history-snapshot, pr-link, saved_hook_context.

  Common fields on user/assistant: uuid, parentUuid (linked list),
  sessionId, timestamp (ISO 8601), cwd, gitBranch, version, slug.

  Dragon: multiple assistant entries can share the same message.id
  (incremental streaming updates). Merge content blocks by message.id.

  Dragon: toolUseResult has 5+ shapes depending on tool type:
  Bash={stdout,stderr,interrupted,isImage,noOutputExpected},
  Write={content,filePath,originalFile,structuredPatch,type},
  Agent={agentId,agentType,content,prompt,status,...},
  Read={file,type}, or bare string for errors.
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# ── JSONL Parsing ──────────────────────────────────────────────────

def parse_session(path: str) -> list[dict]:
    """Parse a CC JSONL file into a list of entries."""
    entries = []
    with open(path, 'r', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def is_human_message(entry: dict) -> bool:
    """True if this is a human-typed user message (not tool result, not meta)."""
    if entry.get('type') != 'user':
        return False
    if entry.get('isMeta'):
        return False
    if 'toolUseResult' in entry:
        return False
    content = entry.get('message', {}).get('content')
    return isinstance(content, str)


def is_tool_result(entry: dict) -> bool:
    """True if this is a tool result entry."""
    return entry.get('type') == 'user' and 'toolUseResult' in entry


def is_meta(entry: dict) -> bool:
    """True if this is a skill/system injection."""
    return entry.get('type') == 'user' and entry.get('isMeta', False)


# ── Content Extraction ─────────────────────────────────────────────

def extract_human_text(entry: dict) -> str:
    """Extract text from a human message, stripping system tags."""
    content = entry.get('message', {}).get('content', '')
    if not isinstance(content, str):
        return ''
    # Strip system XML tags
    content = re.sub(r'<command-message>.*?</command-message>\s*', '', content, flags=re.DOTALL)
    content = re.sub(r'<command-name>.*?</command-name>\s*', '', content, flags=re.DOTALL)
    content = re.sub(r'<task-notification>.*?</task-notification>\s*', '', content, flags=re.DOTALL)
    content = re.sub(r'<system-reminder>.*?</system-reminder>\s*', '', content, flags=re.DOTALL)
    return content.strip()


def extract_assistant_content(
    entry: dict,
    with_tools: bool = False,
    with_thinking: bool = False,
) -> str:
    """Extract text from an assistant message's content blocks.

    Handles the multi-entry-same-message-id dragon by accepting
    pre-merged content blocks.
    """
    msg = entry.get('message', {})
    content = msg.get('content', [])
    if not isinstance(content, list):
        return str(content) if content else ''

    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get('type')

        if btype == 'text':
            text = block.get('text', '')
            if text:
                parts.append(text)

        elif btype == 'tool_use' and with_tools:
            name = block.get('name', '?')
            inp = block.get('input', {})
            if name == 'Bash':
                cmd = inp.get('command', '')
                parts.append(f'[tool: {name}] {cmd[:200]}')
            elif name in ('Read', 'Glob', 'Grep'):
                summary = inp.get('file_path') or inp.get('pattern') or inp.get('path', '')
                parts.append(f'[tool: {name}] {summary[:200]}')
            elif name in ('Write', 'Edit'):
                fp = inp.get('file_path', '')
                parts.append(f'[tool: {name}] {fp}')
            elif name == 'Agent':
                desc = inp.get('description', '')
                parts.append(f'[tool: {name}] {desc}')
            else:
                parts.append(f'[tool: {name}]')

        elif btype == 'thinking' and with_thinking:
            thinking = block.get('thinking', '')
            if thinking:
                parts.append(f'<thinking>\n{thinking}\n</thinking>')

    return '\n'.join(parts)


def merge_assistant_entries(entries: list[dict]) -> list[dict]:
    """Merge assistant entries that share the same message.id.

    CC streams incremental updates — multiple JSONL lines can have the
    same message.id, each with only the new content blocks. We merge
    them into a single entry with all blocks combined.
    """
    merged = {}
    order = []

    for entry in entries:
        if entry.get('type') != 'assistant':
            continue
        msg = entry.get('message', {})
        msg_id = msg.get('id')
        if not msg_id:
            continue

        if msg_id not in merged:
            merged[msg_id] = {
                **entry,
                'message': {**msg, 'content': []},
            }
            order.append(msg_id)

        # Merge content blocks, deduplicating tool_use by id
        existing_content = merged[msg_id]['message']['content']
        seen_tool_ids = {
            b.get('id') for b in existing_content
            if isinstance(b, dict) and b.get('type') == 'tool_use'
        }

        for block in msg.get('content', []):
            if not isinstance(block, dict):
                continue
            if block.get('type') == 'tool_use' and block.get('id') in seen_tool_ids:
                continue
            existing_content.append(block)

    return [merged[mid] for mid in order]


# ── Turn Construction ──────────────────────────────────────────────

def build_turns(
    entries: list[dict],
    with_tools: bool = False,
    with_thinking: bool = False,
    last_n: int | None = None,
) -> list[dict]:
    """Build a list of conversation turns from raw JSONL entries.

    A 'turn' is either a human message or an assistant response.
    """
    # Merge multi-entry assistant messages
    assistant_merged = merge_assistant_entries(entries)
    assistant_by_id = {
        e['message']['id']: e for e in assistant_merged
    }

    turns = []
    seen_assistant_ids = set()

    for entry in entries:
        etype = entry.get('type')

        if etype == 'user' and is_human_message(entry):
            text = extract_human_text(entry)
            if text:
                turns.append({
                    'role': 'human',
                    'text': text,
                    'timestamp': entry.get('timestamp'),
                })

        elif etype == 'assistant':
            msg_id = entry.get('message', {}).get('id')
            if msg_id and msg_id not in seen_assistant_ids:
                seen_assistant_ids.add(msg_id)
                merged = assistant_by_id.get(msg_id, entry)
                text = extract_assistant_content(
                    merged,
                    with_tools=with_tools,
                    with_thinking=with_thinking,
                )
                if text:
                    turns.append({
                        'role': 'assistant',
                        'text': text,
                        'timestamp': entry.get('timestamp'),
                        'model': merged.get('message', {}).get('model'),
                    })

        elif etype == 'summary':
            turns.append({
                'role': 'system',
                'text': f"[context compacted: {entry.get('summary', '')}]",
                'timestamp': None,
            })

    if last_n is not None:
        turns = turns[-last_n:]

    return turns


# ── Output Formats ─────────────────────────────────────────────────

def format_text(turns: list[dict]) -> str:
    """Plain text conversation format."""
    lines = []
    for turn in turns:
        role = turn['role'].upper()
        if role == 'SYSTEM':
            lines.append(turn['text'])
        else:
            lines.append(f'── {role} ──')
            lines.append(turn['text'])
        lines.append('')
    return '\n'.join(lines)


def format_json(turns: list[dict]) -> str:
    """Structured JSON output."""
    return json.dumps(turns, indent=2, default=str)


def format_timeline(entries: list[dict]) -> str:
    """Timestamped turn log showing what happened when."""
    lines = []
    for entry in entries:
        ts = entry.get('timestamp', '')
        etype = entry.get('type', '?')

        if etype == 'assistant':
            msg = entry.get('message', {})
            blocks = msg.get('content', [])
            tools = [
                b.get('name', '?') for b in blocks
                if isinstance(b, dict) and b.get('type') == 'tool_use'
            ]
            texts = [
                b.get('text', '')[:80] for b in blocks
                if isinstance(b, dict) and b.get('type') == 'text'
            ]
            if tools:
                lines.append(f'{ts}  assistant  tools: {", ".join(tools)}')
            elif texts and any(t.strip() for t in texts):
                preview = next(t for t in texts if t.strip())[:80]
                lines.append(f'{ts}  assistant  "{preview}"')

        elif etype == 'user' and is_human_message(entry):
            text = extract_human_text(entry)[:80]
            lines.append(f'{ts}  human      "{text}"')

        elif etype == 'system':
            sub = entry.get('subtype', '')
            if sub == 'api_error':
                err = entry.get('error', {})
                lines.append(f'{ts}  system     API error: {err}')
            elif sub == 'turn_duration':
                ms = entry.get('durationMs', '?')
                lines.append(f'{ts}  system     turn: {ms}ms')

    return '\n'.join(lines)


def format_stats(entries: list[dict]) -> str:
    """Session statistics."""
    from collections import Counter

    types = Counter(e.get('type') for e in entries)
    models = Counter()
    tools = Counter()
    total_input = 0
    total_output = 0

    for entry in entries:
        if entry.get('type') == 'assistant':
            msg = entry.get('message', {})
            m = msg.get('model')
            if m:
                models[m] += 1
            usage = msg.get('usage', {})
            # input_tokens is only the non-cached portion;
            # real input = input + cache_creation + cache_read
            total_input += (
                usage.get('input_tokens', 0)
                + usage.get('cache_creation_input_tokens', 0)
                + usage.get('cache_read_input_tokens', 0)
            )
            total_output += usage.get('output_tokens', 0)

            for block in msg.get('content', []):
                if isinstance(block, dict) and block.get('type') == 'tool_use':
                    tools[block.get('name', '?')] += 1

    human_count = sum(1 for e in entries if is_human_message(e))
    assistant_merged = merge_assistant_entries(entries)

    # Timestamps
    timestamps = [
        e.get('timestamp') for e in entries if e.get('timestamp')
    ]
    if timestamps:
        first = timestamps[0]
        last = timestamps[-1]
    else:
        first = last = '?'

    # Find sessionId and version from first entry that has them
    session_id = '?'
    version = '?'
    slug = ''
    for e in entries:
        if session_id == '?' and e.get('sessionId'):
            session_id = e['sessionId']
        if version == '?' and e.get('version'):
            version = e['version']
        if not slug and e.get('slug'):
            slug = e['slug']
        if session_id != '?' and version != '?':
            break

    lines = [
        f'Session: {session_id}',
        f'Slug:    {slug}' if slug else '',
        f'Version: {version}',
        f'Period:  {first} → {last}',
        f'',
        f'Entry types:',
    ]
    for t, c in types.most_common():
        lines.append(f'  {t:25s} {c:5d}')

    lines.extend([
        f'',
        f'Human messages:    {human_count}',
        f'Assistant turns:   {len(assistant_merged)}',
        f'',
        f'Models:',
    ])
    for m, c in models.most_common():
        lines.append(f'  {m:40s} {c:5d}')

    lines.extend([
        f'',
        f'Tokens:  input={total_input:,}  output={total_output:,}  total={total_input+total_output:,}',
        f'',
        f'Tool usage:',
    ])
    for t, c in tools.most_common():
        lines.append(f'  {t:20s} {c:5d}')

    return '\n'.join(lines)


# ── Session Discovery ──────────────────────────────────────────────

def find_sessions(
    base: Path | None = None,
    limit: int = 20,
    since: str | None = None,
) -> list[dict]:
    """Find recent CC session JSONL files.

    Args:
        since: ISO date string (YYYY-MM-DD). Only return sessions modified
               on or after this date.
    """
    if base is None:
        base = Path.home() / '.claude' / 'projects'

    since_ts = None
    if since:
        since_ts = datetime.strptime(since, '%Y-%m-%d').timestamp()

    sessions = []
    for jsonl in base.rglob('*.jsonl'):
        # Skip subagent files
        if '/subagents/' in str(jsonl):
            continue
        stat = jsonl.stat()
        if since_ts and stat.st_mtime < since_ts:
            continue
        sessions.append({
            'path': str(jsonl),
            'size': stat.st_size,
            'mtime': stat.st_mtime,
        })

    # Sort by modification time, newest first
    sessions.sort(key=lambda s: s['mtime'], reverse=True)

    # Enrich with first-line metadata
    enrich_limit = limit if limit else len(sessions)
    for s in sessions[:enrich_limit]:
        try:
            with open(s['path'], 'r', errors='replace') as f:
                first_line = f.readline().strip()
                if first_line:
                    obj = json.loads(first_line)
                    s['sessionId'] = obj.get('sessionId', '')
                    s['slug'] = obj.get('slug', '')
                    s['version'] = obj.get('version', '')
        except (json.JSONDecodeError, OSError):
            pass

    return sessions[:limit] if limit else sessions


def search_sessions(
    term: str,
    base: Path | None = None,
    limit: int = 10,
) -> list[dict]:
    """Search for a term across recent session files."""
    if base is None:
        base = Path.home() / '.claude' / 'projects'

    results = []
    sessions = find_sessions(base, limit=200)

    for s in sessions:
        try:
            with open(s['path'], 'r', errors='replace') as f:
                for i, line in enumerate(f):
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Only search human messages and assistant text
                    if is_human_message(obj):
                        text = extract_human_text(obj)
                    elif obj.get('type') == 'assistant':
                        text = extract_assistant_content(obj)
                    else:
                        continue

                    if term.lower() in text.lower():
                        results.append({
                            'file': s['path'],
                            'line': i + 1,
                            'sessionId': s.get('sessionId', ''),
                            'slug': s.get('slug', ''),
                            'match': text[:200],
                        })
                        break  # One match per file

                    if len(results) >= limit:
                        break
        except OSError:
            continue

        if len(results) >= limit:
            break

    return results


# ── Summary Format ────────────────────────────────────────────────

def format_summary(entries: list[dict]) -> str:
    """Human-messages-only summary — shows what the user asked, not what Claude said.

    Good for quickly recalling what a session covered without reading
    the full transcript.
    """
    lines = []
    human_count = 0
    for entry in entries:
        if is_human_message(entry):
            human_count += 1
            text = extract_human_text(entry)
            ts = entry.get('timestamp', '')
            if ts:
                ts = ts[11:16]  # HH:MM
            # Truncate long messages
            preview = text.replace('\n', ' ')
            if len(preview) > 120:
                preview = preview[:117] + '...'
            lines.append(f'  {ts}  {preview}')

    # Header with stats
    assistant_merged = merge_assistant_entries(entries)
    timestamps = [e.get('timestamp') for e in entries if e.get('timestamp')]
    period = ''
    if timestamps:
        period = f'{timestamps[0][11:16]}–{timestamps[-1][11:16]}'

    header = f'{human_count} messages, {len(assistant_merged)} turns, {period}'
    return header + '\n' + '\n'.join(lines)


# ── CLI ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog='ccconv',
        description='Extract conversation from Claude Code session JSONL files.',
    )
    parser.add_argument('file', nargs='?', help='Session JSONL file path')
    parser.add_argument('--with-tools', action='store_true', help='Include tool calls')
    parser.add_argument('--with-thinking', action='store_true', help='Include thinking blocks')
    parser.add_argument('--last', type=int, metavar='N', help='Last N turns only')
    parser.add_argument('--json', action='store_true', dest='json_output', help='JSON output')
    parser.add_argument('--stats', action='store_true', help='Session statistics')
    parser.add_argument('--summary', action='store_true', help='Human messages only (what was discussed)')
    parser.add_argument('--timeline', action='store_true', help='Timestamped turn log')
    parser.add_argument('--recent', nargs='?', type=int, const=20, metavar='N',
                        help='List N most recent sessions (default 20)')
    parser.add_argument('--today', action='store_true', help='List today\'s sessions')
    parser.add_argument('--since', type=str, metavar='DATE', help='Sessions since DATE (YYYY-MM-DD)')
    parser.add_argument('--find', type=str, metavar='TERM', help='Search across sessions')

    args = parser.parse_args()

    # --today is sugar for --since today
    if args.today:
        args.since = datetime.now().strftime('%Y-%m-%d')
        if args.recent is None:
            args.recent = 100  # show all today's sessions

    # List recent sessions
    if args.recent is not None:
        sessions = find_sessions(limit=args.recent, since=args.since)
        for s in sessions:
            mtime = datetime.fromtimestamp(s['mtime']).strftime('%Y-%m-%d %H:%M')
            size_kb = s['size'] / 1024
            slug = s.get('slug', '')
            sid = s.get('sessionId', '')[:8]
            print(f'{mtime}  {size_kb:8.0f}K  {sid}  {slug:30s}  {s["path"]}')
        return

    # --since without --recent: list sessions since date
    if args.since and args.recent is None and not args.find and not args.file:
        sessions = find_sessions(limit=0, since=args.since)
        for s in sessions:
            mtime = datetime.fromtimestamp(s['mtime']).strftime('%Y-%m-%d %H:%M')
            size_kb = s['size'] / 1024
            slug = s.get('slug', '')
            sid = s.get('sessionId', '')[:8]
            print(f'{mtime}  {size_kb:8.0f}K  {sid}  {slug:30s}  {s["path"]}')
        return

    # Search across sessions
    if args.find:
        results = search_sessions(args.find)
        if not results:
            print(f'No matches for "{args.find}"', file=sys.stderr)
            sys.exit(1)
        for r in results:
            slug = r.get('slug', '')
            sid = r.get('sessionId', '')[:8]
            match = r['match'].replace('\n', ' ')[:100]
            print(f'{sid}  {slug:25s}  "{match}"')
            print(f'  {r["file"]}')
        return

    # Need a file for everything else
    if not args.file:
        parser.print_help()
        sys.exit(1)

    if not os.path.exists(args.file):
        print(f'File not found: {args.file}', file=sys.stderr)
        sys.exit(1)

    entries = parse_session(args.file)
    if not entries:
        print('Empty or unparseable file.', file=sys.stderr)
        sys.exit(1)

    if args.stats:
        print(format_stats(entries))
    elif args.summary:
        print(format_summary(entries))
    elif args.timeline:
        print(format_timeline(entries))
    elif args.json_output:
        turns = build_turns(
            entries,
            with_tools=args.with_tools,
            with_thinking=args.with_thinking,
            last_n=args.last,
        )
        print(format_json(turns))
    else:
        turns = build_turns(
            entries,
            with_tools=args.with_tools,
            with_thinking=args.with_thinking,
            last_n=args.last,
        )
        print(format_text(turns))


if __name__ == '__main__':
    main()

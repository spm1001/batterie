#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""List unclosed Claude Code sessions: the crumbs in the keyboard (bon-cedeze).

A crumb is a session on THIS machine, active in the last N days, that
  (a) carries at least two genuine human messages,
  (b) left no handoff anywhere on the estate,
  (c) is not running now, and
  (d) has not been dismissed.

Visibility only. Nothing is drafted, resumed or closed: the list is shown at
session start (open-context.sh) and the human decides. `--dismiss ID` makes
a spent crumb stop showing.

The reading that lost: a SessionEnd hook drafting a handoff from the
transcript (closeout-style). bon ran exactly that from March and retired it
on 2026-04-05 (2d451fe) as adding almost nothing, and SessionEnd never fires
for phone and Paseo sessions, which go idle rather than exit: 139 of the 161
sessions launched at ~ between 20 Sep and 24 Oct 2026.

Speed: this runs at every session start. Transcripts are filtered by mtime
and only their head (to the first human message) and tail (back to the last
one) are read. Stdlib only, so open-context.sh can call it with python3.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("HOME", str(Path.home())))
# Every seat's config dir. ~/.claude-credits/projects and
# ~/.claude-commis/projects are symlinks to ~/.claude/projects today; realpath
# dedupes them, and a seat that later gets its own dir is still covered.
CONFIG_DIRS = [HOME / ".claude", HOME / ".claude-commis", HOME / ".claude-credits"]
HANDOFF_ROOTS = [HOME / "repos", HOME / "notes", HOME / ".bon"]
PRUNE = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
SKIP_PROJECT_DIRS = {"-home-modha--local-state-stop-judge"}

# Not a human typing: harness injections, slash-command plumbing, continuation
# summaries, other agents' messages. Same list as the 24 Oct 2026 census
# (/tmp/crumbs/cat.py), so its counts and this scanner agree.
NOISE = re.compile(
    r"^(<task-notification>|<local-command|<system-reminder>|Caveat:"
    r"|<command-name>/(exit|context|model|mcp|plugin|compact|login|effort|reload-\w+|clear|resume"
    r"|status|cost|usage|config|permissions|hooks|agents|fast|doctor|rename|design-login"
    r"|remote-control|ide|memory|statusline|theme|add-dir|btw)\b"
    r"|\[Request interrupted|This session is being continued|Context: This summary"
    r"|\[mesh from|<paseo-system|\[guéridon:system\]|<cross-session|\[Reconstituted"
    r"|End of session\.|You label tmux windows)"
)
# Robots whose first message is a fixed brief: never a crumb.
ROBOT = re.compile(
    r"^(Read the file /\S+/\.local/state/m|You are the turn-end companion"
    r"|You label tmux windows|From: Read Me|You are an overnight worker dispatched)"
)
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
HANDOFF_ID8 = re.compile(r"-([0-9a-f]{8})\.md$")
FRONTMATTER_SID = re.compile(r"^session_id:\s*['\"]?([0-9a-f-]{8,36})", re.M)

# Byte-level prefilters, so most lines are never JSON-decoded. Whitespace-
# tolerant: CC writes compact JSON today, and a format change must not turn
# the scan silently empty.
USER_LINE = re.compile(rb'"type"\s*:\s*"user"')
ASSISTANT_LINE = re.compile(rb'"type"\s*:\s*"assistant"')
TOOL_RESULT_LINE = re.compile(rb'"tool_use_id"\s*:')
CWD_LINE = re.compile(rb'"cwd"\s*:')
QUEUED_LINE = re.compile(rb'"type"\s*:\s*"queued_command"')

HEAD_CAP = 4 << 20            # bytes read looking for the first human message
TAIL_STEPS = (256 << 10, 2 << 20, 16 << 20)
DIRS_CACHE_TTL = 6 * 3600
FIRST_WALK_DEADLINE = 3.0  # seconds; tube's full walk is ~0.9s


def state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(HOME / ".local" / "state")
    return Path(base) / "bon"


def dirs_cache_path() -> Path:
    return state_dir() / "crumbs-handoff-dirs"


def dismissed_path() -> Path:
    return state_dir() / "crumbs-dismissed"


# --- human messages ---------------------------------------------------------

def message_text(entry: dict) -> str | None:
    """The text of a genuine human message, or None for anything else.

    Two shapes: a user entry, and a message typed while Claude was working,
    which CC records only as a queued_command attachment (59 of them in one
    week on tube, 24 Oct 2026).
    """
    if entry.get("isMeta") or entry.get("isSidechain"):
        return None
    if entry.get("type") == "attachment":
        att = entry.get("attachment") or {}
        if att.get("type") != "queued_command":
            return None
        content = att.get("prompt")
    elif entry.get("type") == "user":
        if entry.get("toolUseResult") is not None or entry.get("isCompactSummary"):
            return None
        content = (entry.get("message") or {}).get("content")
    else:
        return None
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):  # phone and Paseo send blocks
        text = " ".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    else:
        return None
    text = text.strip()
    if not text or NOISE.match(text):
        return None
    return text


def render(text: str, width: int) -> str:
    """One line, slash-command tags turned back into what was typed."""
    m = re.search(r"<command-name>(/?[^<]*)</command-name>", text)
    if m:
        args = re.search(r"<command-args>([^<]*)</command-args>", text)
        text = (m.group(1) + " " + (args.group(1) if args else "")).strip()
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 1] + "…"


def _parse(line: bytes, want_any: bool = False) -> dict | None:
    """Decode a line only if it could matter: a user line that is not a tool
    result (a quoted "tool_use_id": inside message text is escaped, so this
    byte test cannot hide a human message), or any user/assistant line when
    the caller still wants a timestamp."""
    if USER_LINE.search(line):
        if TOOL_RESULT_LINE.search(line) and not want_any:
            return None
    elif QUEUED_LINE.search(line):
        pass
    elif not (want_any and ASSISTANT_LINE.search(line)):
        return None
    try:
        entry = json.loads(line)
    except ValueError:
        return None
    return entry if isinstance(entry, dict) else None


def read_head(path: Path) -> tuple[dict | None, str | None]:
    """(first human entry, cwd) from the front of the transcript."""
    cwd = None
    read = 0
    with open(path, "rb") as f:
        for line in f:
            read += len(line)
            if read > HEAD_CAP:
                break
            if cwd is None and CWD_LINE.search(line):
                try:
                    found = json.loads(line).get("cwd")
                except (ValueError, AttributeError):
                    found = None
                cwd = found if isinstance(found, str) else None
            entry = _parse(line)
            if entry is not None and message_text(entry) is not None:
                return entry, cwd
    return None, cwd


def read_tail(path: Path, size: int) -> tuple[dict | None, str | None, bool]:
    """(last human entry, last user/assistant timestamp, wrote a handoff)
    from the back.

    The third is the transcript's own testimony, CHECKED against disk: an
    absolute …/handoffs/…-<id8>.md path in the bytes read counts only if that
    file exists. An attempt is not a close: bb3ec529's /close write was
    blocked by a safety classifier and never ran, yet its path sat in the
    tool call's input (24 Oct 2026). A relative path cannot be resolved and is
    ignored; the estate walk covers the usual homes either way.
    """
    last_ts = None
    # no backslash in the run: inside JSON a newline is the two bytes \n, and
    # /close's preamble prints HANDOFF_DIR=…/handoffs and HANDOFF_FILE=…-<id8>.md
    # on separate lines — a started-but-abandoned close must not match
    closed = re.compile(rb"(/[^\"\s\\]*/handoffs/[^\"\s\\]*-" + re.escape(path.stem[:8].encode()) + rb"\.md)")
    wrote = False
    with open(path, "rb") as f:
        for step in TAIL_STEPS:
            start = max(0, size - step)
            f.seek(start)
            chunk = f.read(size - start)
            if not wrote:
                wrote = any(os.path.isfile(m.decode("utf-8", "replace")) for m in set(closed.findall(chunk)))
            lines = chunk.split(b"\n")
            if start > 0:
                lines = lines[1:]  # first line is partial
            for line in reversed(lines):
                entry = _parse(line, want_any=last_ts is None)
                if entry is None:
                    continue
                if last_ts is None and entry.get("type") in ("user", "assistant", "attachment"):
                    last_ts = entry.get("timestamp")
                if message_text(entry) is not None:
                    return entry, last_ts, wrote
            if start == 0:
                break
    return None, last_ts, wrote


# --- handoffs, running sessions, dismissals ----------------------------------

def walk_handoff_dirs(deadline: float | None = None) -> list[str]:
    """Every directory named handoffs/ under the roots, nested rooms included.

    The slow part of the scan (~0.9s on tube: 21,000 dirs, mostly fixtures),
    so its answer is cached; see handoff_dirs.
    """
    roots = [str(r) for r in HANDOFF_ROOTS if r.is_dir()]
    found = []
    for root in roots:
        for dirpath, dirnames, _ in os.walk(root):
            if deadline is not None and time.monotonic() > deadline:
                raise TimeoutError(found)
            dirnames[:] = [d for d in dirnames if d not in PRUNE]
            if os.path.basename(dirpath) == "handoffs":
                found.append(dirpath)
    return found


def refresh_dirs_cache() -> list[str]:
    found = walk_handoff_dirs()
    _write_cache(found)
    return found


def _write_cache(found: list[str]) -> None:
    cache = dirs_cache_path()
    cache.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_suffix(f".tmp{os.getpid()}")
    tmp.write_text("\n".join(found) + "\n")
    os.replace(tmp, cache)


def handoff_dirs() -> list[str]:
    """Handoff dirs: the cheap known shapes globbed live, plus the cached walk.

    A new repo's handoffs/ counts at once (live glob). A new NESTED room is
    seen once the cache refreshes; until then its sessions may show as crumbs
    — visible and harmless, the failure this trade accepts. A stale cache is
    used as-is and refreshed by a detached child, so no session start pays
    for the walk except the very first.
    """
    live = [str(p) for p in HOME.glob("*/handoffs")]   # ~/notes, ~/scratch
    live += [str(p) for p in HOME.glob(".*/handoffs")]  # ~/.bon, ~/.claude, ~/.dotfiles
    live += [str(p) for p in (HOME / "repos").glob("*/*/handoffs")]
    cache = dirs_cache_path()
    try:
        cached = [l for l in cache.read_text().splitlines() if l]
        stale = time.time() - cache.stat().st_mtime > DIRS_CACHE_TTL
    except FileNotFoundError:
        # First run on this machine: walk inline, but never hold a session
        # start hostage — past the deadline use what was found and finish
        # the walk detached.
        try:
            cached = walk_handoff_dirs(deadline=time.monotonic() + FIRST_WALK_DEADLINE)
            _write_cache(cached)
            stale = False
        except TimeoutError as partial:
            cached, stale = partial.args[0], True
            print("crumbs: first handoff-dir walk ran long; finishing it in the background",
                  file=sys.stderr)
    except OSError as exc:
        print(f"crumbs: handoff-dir cache unreadable ({exc}); live dirs only", file=sys.stderr)
        cached, stale = [], True
    if stale:
        try:  # touch first, so a refresh that keeps failing is retried per TTL, not per session
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.touch()
        except OSError:
            pass
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--refresh-dirs"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    return sorted(set(live) | set(cached))


def handoff_ids(since: float) -> set[str]:
    """id8s and full uuids that some handoff on the estate names.

    A /close handoff is named *-<id8>.md; mit-kg rooms use descriptive names
    with the id only in frontmatter (session_id:), so files touched inside the
    window get their head read too. mtime can only be later than the write (a
    clone stamps checkout time), so the mtime filter never hides a handoff
    written for a session in the window.
    """
    ids: set[str] = set()
    for dirpath in handoff_dirs():
        try:
            names = [n for n in os.listdir(dirpath) if n.endswith(".md")]
        except OSError:
            continue
        for name in names:
            m = HANDOFF_ID8.search(name)
            if m:
                ids.add(m.group(1))
            full = os.path.join(dirpath, name)
            try:
                if os.path.getmtime(full) < since:
                    continue
                with open(full, "rb") as f:
                    head = f.read(2048).decode("utf-8", "replace")
            except OSError:
                continue
            for sid in FRONTMATTER_SID.findall(head):
                ids.add(sid)
                ids.add(sid[:8])
    return ids


def running_ids() -> set[str]:
    """Session ids whose registered pid is alive — and is the same process."""
    live: set[str] = set()
    seen: set[str] = set()
    for cfg in CONFIG_DIRS:
        sdir = cfg / "sessions"
        if not sdir.is_dir():
            continue
        real = os.path.realpath(sdir)
        if real in seen:
            continue
        seen.add(real)
        for rec in Path(real).glob("*.json"):
            try:
                d = json.loads(rec.read_text())
                pid, sid = int(d["pid"]), str(d["sessionId"])
            except (OSError, ValueError, KeyError, TypeError):
                continue
            try:
                stat = Path(f"/proc/{pid}/stat").read_text()
            except OSError:
                if sys.platform != "linux":  # no /proc: fall back to signal 0
                    try:
                        os.kill(pid, 0)
                        live.add(sid)
                    except PermissionError:  # exists, owned by someone else
                        live.add(sid)
                    except ProcessLookupError:
                        pass
                continue
            # field 22 (starttime) follows the parenthesised comm, which may hold spaces
            fields = stat.rsplit(")", 1)[-1].split()
            if str(d.get("procStart", "")) in ("", fields[19]):
                live.add(sid)
    own = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if own:
        live.add(own)
    return live


def load_dismissed() -> list[str]:
    try:
        return [t for t in dismissed_path().read_text().split() if t]
    except FileNotFoundError:
        return []


def transcripts() -> list[Path]:
    """Top-level transcripts across every seat, deduped at the directory.

    The seats' projects/ dirs are symlinks to one tree today; resolving the
    directory (not each of ~7,000 files) keeps this cheap.
    """
    out: list[Path] = []
    seen: set[str] = set()
    for cfg in CONFIG_DIRS:
        pdir = cfg / "projects"
        if not pdir.is_dir():
            continue
        real = os.path.realpath(pdir)
        if real in seen:
            continue
        seen.add(real)
        with os.scandir(real) as projects:
            for proj in projects:
                if proj.name in SKIP_PROJECT_DIRS or proj.name.startswith("-var-tmp-"):
                    continue
                if not proj.is_dir():
                    continue
                try:
                    with os.scandir(proj.path) as files:  # subagents/ live a level deeper
                        for f in files:
                            if f.name.endswith(".jsonl") and UUID_RE.match(f.name[:-6]):
                                out.append(Path(f.path))
                except OSError as exc:
                    print(f"crumbs: skipped project {proj.name}: {exc}", file=sys.stderr)
    return out


# --- the scan -----------------------------------------------------------------

def scan(days: float, quiet_min: float, within: str | None) -> list[dict]:
    now = time.time()
    since = now - days * 86400
    candidates = []
    for path in transcripts():
        try:
            st = path.stat()
        except OSError:
            continue
        if st.st_mtime < since:  # cheap prefilter; the real test is last_active below
            continue
        candidates.append((path, st))
    if not candidates:
        return []
    live = running_ids()
    dismissed = load_dismissed()
    handed = None  # walked lazily: only if some candidate survives the cheap tests
    crumbs = []
    for path, st in candidates:
        sid = path.stem
        if sid in live or any(sid.startswith(t) for t in dismissed):
            continue
        try:
            first, cwd = read_head(path)
            if first is None:
                continue
            last, last_ts, wrote_handoff = read_tail(path, st.st_size)
        except OSError as exc:  # vanished or unreadable: skip it, say so
            print(f"crumbs: skipped {path.name}: {exc}", file=sys.stderr)
            continue
        first_text = message_text(first) or ""
        if ROBOT.match(first_text):
            continue
        if last is None or last.get("uuid") == first.get("uuid"):
            continue  # fewer than two human messages
        # mtime is not activity: something rewrites old transcripts (July
        # sessions showed fresh mtimes on 24 Oct 2026), so window and quiet
        # floor both read the last user/assistant timestamp.
        active = _epoch(last_ts) or st.st_mtime
        if active < since or active > now - quiet_min * 60:
            continue
        if within and not (cwd and (cwd == within or cwd.startswith(within.rstrip("/") + "/"))):
            continue
        if wrote_handoff:
            continue
        if handed is None:
            handed = handoff_ids(since)
        if sid in handed or sid[:8] in handed:
            continue
        crumbs.append({
            "session_id": sid,
            "cwd": cwd or "",
            "last_active": last_ts or datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
            "first": first_text,
            "last": message_text(last) or "",
            "transcript": str(path),
        })
    crumbs.sort(key=lambda c: c["last_active"], reverse=True)
    return crumbs


def _parse_ts(ts: str | None) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _epoch(ts: str | None) -> float | None:
    dt = _parse_ts(ts)
    return dt.timestamp() if dt else None


def age(ts: str, now: datetime) -> str:
    then = _parse_ts(ts)
    if then is None:
        return "?"
    secs = (now - then).total_seconds()
    if secs < 3600:
        return f"{max(1, int(secs // 60))}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    d = int(secs // 86400)
    return "yesterday" if d == 1 else f"{d}d ago"


def tilde(p: str) -> str:
    h = str(HOME)
    return "~" + p[len(h):] if p == h or p.startswith(h + "/") else p


def cd_target(p: str) -> str:
    """~-shortened when safe; a path needing quotes stays absolute, because ~
    does not expand inside quotes."""
    short = tilde(p)
    if re.fullmatch(r"[~\w./@%+=:,-]+", short):
        return short
    return "'" + p.replace("'", "'\\''") + "'"


def print_text(crumbs: list[dict], days: float, limit: int, within: str | None) -> None:
    if not crumbs:
        return  # silent when there is nothing to see
    now = datetime.now(timezone.utc)
    scope = f", in {tilde(within)}" if within else ""
    print(f"Unclosed sessions (last {days:g} days{scope}, no handoff, not running) — newest first; "
          f"the user decides; never resume or close one unasked:")
    for c in crumbs[:limit]:
        where = "" if c["cwd"] in ("", str(HOME)) else f" [{tilde(c['cwd'])}]"
        print(f"  {age(c['last_active'], now)}{where}: \"{render(c['first'], 60)}\"")
        print(f"    last: \"{render(c['last'], 80)}\"")
        cd = cd_target(c["cwd"]) if c["cwd"] else "~"
        print(f"    cd {cd} && claude --resume {c['session_id']}")
    me = f"python3 {cd_target(os.path.abspath(__file__))}"
    if len(crumbs) > limit:
        scope_arg = f" --within {cd_target(within)}" if within else ""
        print(f"  … +{len(crumbs) - limit} more — {me} --all{scope_arg}")
    print(f"  Spent one? {me} --dismiss ID8")


def dismiss(tokens: list[str]) -> int:
    path = dismissed_path()
    have = set(load_dismissed())
    added = []
    for raw in tokens:
        t = raw.strip().lower()
        if not re.fullmatch(r"[0-9a-f-]{8,36}", t):
            print(f"crumbs: refusing {raw!r}: give the session id or its first 8 hex characters",
                  file=sys.stderr)
            return 1
        matches = [p for p in transcripts() if p.stem.startswith(t)]
        if not matches:
            print(f"crumbs: warning: no transcript on this machine starts with {t}; recorded anyway",
                  file=sys.stderr)
        if t not in have:
            added.append(t)
            have.add(t)
        label = render(message_text(read_head(matches[0])[0] or {}) or "", 60) if matches else ""
        print(f"dismissed {t}" + (f" — \"{label}\"" if label else ""))
    if added:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            for t in added:
                f.write(t + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="List unclosed Claude Code sessions (no handoff, not running).")
    ap.add_argument("--days", type=float, default=7, help="look-back window (default 7)")
    ap.add_argument("--quiet-min", type=float, default=60,
                    help="ignore sessions active in the last N minutes (default 60): a chat paused "
                         "five minutes ago is not yet a crumb")
    ap.add_argument("--max", type=int, default=5, help="lines shown before '+N more' (default 5)")
    ap.add_argument("--all", action="store_true", help="show every crumb")
    ap.add_argument("--within", help="only sessions whose cwd is this directory or below it")
    ap.add_argument("--json", action="store_true", help="machine-readable list")
    ap.add_argument("--dismiss", nargs="+", metavar="ID", help="stop showing these sessions")
    ap.add_argument("--refresh-dirs", action="store_true",
                    help="re-walk for handoffs/ dirs and rewrite the cache (run detached when stale)")
    args = ap.parse_args(argv)

    if args.refresh_dirs:
        refresh_dirs_cache()
        return 0

    if args.dismiss:
        return dismiss(args.dismiss)
    within = os.path.realpath(args.within) if args.within else None
    crumbs = scan(args.days, args.quiet_min, within)
    if args.json:
        json.dump(crumbs, sys.stdout, indent=2)
        print()
    else:
        print_text(crumbs, args.days, len(crumbs) if args.all else args.max, within)
    return 0


if __name__ == "__main__":
    sys.exit(main())

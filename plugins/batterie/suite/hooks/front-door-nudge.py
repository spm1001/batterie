#!/usr/bin/env python3
"""front-door-nudge — a gentle reminder for a front-door session doing a worker's job.

The aboyeur (skills/aboyeur) is the front door of the day: it answers from what
it holds, does quick lookups, and sends anything that needs a document read in
full or an artefact written to a worker chat. Instructions alone lose to
helpfulness: on 20 Nov 2026 one front door ran 164 tool calls on a single ask
(a contract markup) and dropped the dispatcher duties it had inherited. Claude
Code Projects' coordinator holds the same line structurally (its only tools are
spawn, continue and stop workers). This hook is the soft version: it never
blocks, it only reminds.

Events (plugin.json wires each):
  --event start    SessionStart: decide once whether this session is a front door
  --event prompt   UserPromptSubmit: reset the count; an errand marker turns it off
  --event tool     PreToolUse: count, and at a threshold add one line of context

Who counts as a front door: a session launched outside a work home that has a
cheap way to hand work over (a Paseo chat, a Desktop session, or a terminal with
the paseo CLI), decided once at a fresh start. Headless runs and robots
(`claude -p` with no Paseo chat around it) are left alone, as the aboyeur skill's
Boundaries say; so is a session with no launcher, where handing over would cost
the person a manual step. A resumed or cleared session with no decision on file
stays quiet rather than guess. A work home is a folder holding WHY.md,
.bon/ or .git, or anything inside one, except an umbrella (a folder whose
children are projects or repos, such as ~/projects/mit-projects). $HOME and /tmp
are always front doors. A kg reads as a work home when it is itself a repo with
no project children (mit-kg) and as an umbrella when it has two (sameer-kg);
sessions don't launch in a kg, so either answer is harmless. A session whose FIRST prompt carries "[errand:" or
"[sonner:" is an errand a front door dispatched, and is left alone, as is any
subagent (its tool calls carry agent_id). BATTERIE_FRONT_DOOR=1/0 forces the
decision; BATTERIE_NUDGE=off silences the hook.

What fires (each one line, via additionalContext, plus a short systemMessage the
person sees in the transcript and a line in the log):
  - the first artefact write of a turn (Edit, Write, NotebookEdit, or a mise do
    that creates or edits a Doc, a draft or a comment), unless it is a brief,
    a handoff or a memory note;
  - the THRESHOLD-th counted tool call since the last prompt, then again at
    each doubling (12, 24, 48 …; BATTERIE_NUDGE_THRESHOLD overrides), so a long absorbed task hears it a few times,
    not on every call.
A hand-over (Agent, SendMessage, Desktop's start_session, or a Bash call that
runs paseo run/send/import, sonner, or an opener launch anywhere in it, heredoc
brief included) resets the count. Bookkeeping is not counted: Skill, ToolSearch,
TodoWrite, ListAgents, TaskStop, Monitor, Desktop's other session tools, and Bash
calls made only of paseo, bon, the state board, crumbs or opener commands.

The log gets a line per fresh start, per turn (calls, hand-overs, nudges), per
hand-over and per nudge, so a week of front doors can be judged from it.

It fails open: any error is logged and the call goes ahead untouched. State and
log live under ${XDG_STATE_HOME:-~/.local/state}/batterie/front-door/.

Self-test: python3 front-door-nudge.py --self-test   (keep it 3.9-clean: macOS)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
import traceback
from pathlib import Path

THRESHOLD = 12  # tests/front-door-replay.py, 22 Nov 2026: 27 front doors, 1-22 Nov, 384 turns; 8 nudged 26%, 12 nudged 18%
ERRAND_MARKERS = ("[errand:", "[sonner:")
PROJECT_MARKERS = ("WHY.md", ".bon", ".git")

# A hand-over (work given to another chat or agent) resets the count; bookkeeping (loading a skill,
# checking a chat, reading the board) is simply not counted.
HANDOVER_TOOLS = {"Agent", "Task", "SendMessage", "mcp__ccd_session__start_session"}
HOUSE_TOOLS = {"Skill", "ToolSearch", "TodoWrite", "AskUserQuestion", "ScheduleWakeup", "Monitor", "TaskOutput",
               "ListAgents", "TaskStop"}
ARTEFACT_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
MISE_DO = re.compile(r"^mcp__.*mise.*__do$")
MISE_ARTEFACT_OPS = {"create", "copy", "overwrite", "prepend", "append", "replace_text",
                     "draft", "reply_draft", "comment", "comment_reply", "suggest"}
# A Bash call that launches or messages a chat ANYWHERE in it is a hand-over: briefs travel in
# heredocs (BRIEF=$(cat <<'EOF' … EOF)), so the launch shares the call with the brief's own lines.
HANDOVER_CMD = re.compile(
    r"(?:^|[\s;&|(])(?:\S*/)?(?:paseo\s+(?:run|send|import)\b|opener\.py\s+launch\b)"
    r"|(?:^|[\s;&|(])sonner\s+[^\s&|;]"
    r"|\$\{?OPENER\}?\s+launch\b", re.M)
# A Bash call whose every segment starts with one of these is the front door's own bookkeeping.
BOOKKEEPING_CMD = re.compile(
    r"^(?:\S*/)?(?:paseo|sonner|bon)\b"
    r"|^(?:python3?|uv run(?: --script)?)\s+\S*(?:state-board|crumbs|opener)\.py\b"
    r"|^(?:\S*/)?(?:state-board|crumbs|opener)\.py\b")
CLOSE_SKILL = re.compile(r"(^|:)close$")
SEGMENT_SPLIT = re.compile(r"\s*(?:&&|\|\||;|\n)\s*")
LEADING_NOISE = re.compile(r"^(?:cd\s+\S+|export\s+\S+|[A-Z_][A-Z0-9_]*=\S*)$")


def state_dir() -> Path:
    base = os.environ.get("BATTERIE_NUDGE_STATE_DIR")
    if base:
        return Path(base)
    xdg = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(xdg) / "batterie" / "front-door"


def log(line: str) -> None:
    try:
        d = state_dir()
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "nudges.log", "a") as f:
            f.write(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + " " + line + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------- front door?

def has_marker(p: Path) -> bool:
    return any((p / m).exists() for m in PROJECT_MARKERS)


def is_umbrella(p: Path) -> bool:
    """A folder whose children are projects or repos: two or more of them carry a marker."""
    n = 0
    try:
        for c in p.iterdir():
            if c.is_dir() and not c.name.startswith(".") and has_marker(c):
                n += 1
                if n >= 2:
                    return True
    except OSError:
        return False
    return False


def is_front_door(cwd: str, home: Path | None = None) -> bool:
    forced = os.environ.get("BATTERIE_FRONT_DOOR")
    if forced in ("0", "1"):
        return forced == "1"
    home = (home or Path(os.environ.get("BATTERIE_NUDGE_HOME") or Path.home())).resolve()
    p = Path(cwd).resolve()
    if p == home:
        return True
    if home not in p.parents:
        tmp = Path("/tmp").resolve()
        # /tmp is scratch, so a front door; anywhere else outside the home (/srv, a mount) is not ours to judge
        return p == tmp or tmp in p.parents
    while p != home:
        if has_marker(p) and not is_umbrella(p):
            return False
        p = p.parent
    return True


DESKTOP_ENTRYPOINTS = ("claude-desktop", "ssh-remote")


def launch_route() -> str | None:
    """Why this session can hand work over cheaply, or None (headless, a robot, no launcher).

    Measured 22 Nov 2026 (Claude Code 2.1.330): `claude -p` and a Paseo chat both report
    CLAUDE_CODE_ENTRYPOINT=sdk-cli, and only the Paseo chat has PASEO_AGENT_ID. A `claude -p`
    started from a Paseo chat's shell inherits that id, so it counts as a Paseo chat: rare, harmless.
    """
    if os.environ.get("PASEO_AGENT_ID"):
        return "paseo"
    ep = os.environ.get("CLAUDE_CODE_ENTRYPOINT", "")
    if ep in DESKTOP_ENTRYPOINTS:
        return "desktop"
    if ep == "cli" and shutil.which("paseo"):
        return "terminal+paseo"
    return None


# ---------------------------------------------------------------- classify

def bash_kind(cmd: str) -> str:
    if HANDOVER_CMD.search(cmd):
        return "handover"
    return "house" if bash_is_bookkeeping(cmd) else "work"


def bash_is_bookkeeping(cmd: str) -> bool:
    segs = [s.strip() for s in SEGMENT_SPLIT.split(cmd.strip()) if s.strip()]
    segs = [s for s in segs if not LEADING_NOISE.match(s)]
    return bool(segs) and all(BOOKKEEPING_CMD.search(s) for s in segs)


BRIEF_NAME = re.compile(r"(?:^|[-_.])brief(?:[-_.]|$)")  # brief.md, brief-x.md, x-brief.txt; not briefing.md


def exempt_write(path: str) -> bool:
    """Writes that serve a hand-over or the close: a brief, a handoff, a memory note."""
    p = path.replace("\\", "/")
    name = p.rsplit("/", 1)[-1].lower()
    return "/handoffs/" in p or "/memory/" in p or bool(BRIEF_NAME.search(name))


def classify(tool: str, inp: dict) -> str:
    """'handover' | 'house' | 'artefact' | 'artefact-exempt' | 'work'."""
    if tool in HANDOVER_TOOLS:
        return "handover"
    if tool in HOUSE_TOOLS or tool.startswith("mcp__ccd_session"):
        return "house"  # Desktop's list/archive/status tools: checking chats, not working
    if tool == "Bash":
        return bash_kind(str(inp.get("command", "")))
    if tool in ARTEFACT_TOOLS:
        path = str(inp.get("file_path") or inp.get("notebook_path") or "")
        return "artefact-exempt" if exempt_write(path) else "artefact"
    if MISE_DO.match(tool):
        return "artefact" if str(inp.get("operation", "")) in MISE_ARTEFACT_OPS else "work"
    return "work"


# ---------------------------------------------------------------- state

def state_path(sid: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", sid or "nosession")[:80]
    return state_dir() / (safe + ".json")


def load(sid: str) -> dict | None:
    try:
        return json.loads(state_path(sid).read_text())
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        log("warn: unreadable state for %s (%s); treating as new" % (sid[:8], e))
        return None


def save(sid: str, st: dict) -> None:
    d = state_dir()
    d.mkdir(parents=True, exist_ok=True)
    # Parallel tool calls run their hooks at once, so each writer gets its own tmp file. The last
    # writer wins and a count can be lost: an undercount is acceptable for a nudge.
    tmp = state_path(sid).with_suffix(".tmp%d" % os.getpid())
    tmp.write_text(json.dumps(st))
    os.replace(str(tmp), str(state_path(sid)))
    # The launcher's fast path: a PreToolUse call starts Python only when this flag exists,
    # so a session that isn't a live front door pays a file test, not an interpreter.
    flag = state_path(sid).with_suffix(".on")
    if st.get("front_door") and not st.get("errand"):
        flag.touch()
    elif flag.exists():
        flag.unlink()


def sweep_old(days: int = 7) -> None:
    cutoff = time.time() - days * 86400
    try:
        for f in list(state_dir().glob("*.json")) + list(state_dir().glob("*.on")):
            if f.stat().st_mtime < cutoff:
                f.unlink()
    except OSError:
        pass


def threshold() -> int:
    try:
        return max(1, int(os.environ.get("BATTERIE_NUDGE_THRESHOLD", THRESHOLD)))
    except ValueError:
        log("warn: BATTERIE_NUDGE_THRESHOLD=%r is not a number; using %d" % (os.environ.get("BATTERIE_NUDGE_THRESHOLD"), THRESHOLD))
        return THRESHOLD


def fresh_state(cwd: str) -> dict:
    forced = os.environ.get("BATTERIE_FRONT_DOOR") in ("0", "1")
    route = launch_route()
    front = is_front_door(cwd) and (forced or route is not None)
    return {"front_door": front, "route": route, "cwd": cwd, "errand": False,
            "prompts": 0, "count": 0, "next_fire": threshold(), "art_fired": False, "closing": False,
            "turn_handovers": 0, "turn_fires": 0}


# ---------------------------------------------------------------- events

COUNT_MSG = ("Front-door check: %d tool calls since the person's last message or your last hand-over. "
             "The aboyeur answers from what it holds and does quick lookups; reading a document in full "
             "or building an artefact belongs in a worker chat (paseo run / the opener, with a brief). "
             "If this is the menu or a lookup that's nearly done, carry on; if not, brief a worker now.")
ART_MSG = ("Front-door check: this call writes an artefact (%s). The aboyeur sends artefact work to a "
           "worker chat, even a one-off, with a brief ending in an [errand: …] line. If this is a brief, "
           "a handoff, or a few-line reply drafted from what you already hold, carry on; otherwise hand it over.")


def on_start(inp: dict) -> dict | None:
    sid = inp.get("session_id", "")
    sweep_old()
    # Decide only at a fresh start. A resume, /clear, compact or fork with no state on file (released
    # mid-session, swept after 7 days, a new id) stays quiet: its first message may be a wake-up,
    # not the brief that carried the errand line, so it can't be told from a front door.
    if inp.get("source") in (None, "startup"):
        st = fresh_state(inp.get("cwd") or os.getcwd())
        save(sid, st)
        log("start %s front_door=%s route=%s cwd=%s" % (sid[:8], st["front_door"], st["route"], st["cwd"]))
    return None


def on_prompt(inp: dict) -> dict | None:
    sid = inp.get("session_id", "")
    st = load(sid)
    if st is None or not st["front_door"]:
        return None  # not a front door, or no decision on file (see on_start): nothing to count
    if st["prompts"] and not st["errand"]:
        # One line per turn, so a week of logs can say how often turns ran long and what followed a nudge.
        log("turn %s calls=%d handovers=%d fires=%d" % (sid[:8], st["count"], st.get("turn_handovers", 0),
                                                         st.get("turn_fires", 0)))
    if st["prompts"] == 0:
        text = str(inp.get("prompt", ""))
        if any(m in text for m in ERRAND_MARKERS):
            st["errand"] = True
            log("errand %s: first prompt carries an errand marker; nudges off" % sid[:8])
    st["prompts"] += 1
    st["count"] = 0
    st["next_fire"] = threshold()
    st["art_fired"] = False
    st["closing"] = False
    st["turn_handovers"] = 0
    st["turn_fires"] = 0
    save(sid, st)
    return None


def on_tool(inp: dict) -> dict | None:
    if inp.get("agent_id"):
        return None  # a subagent's call: workers are meant to work
    sid = inp.get("session_id", "")
    st = load(sid)
    if st is None or not st["front_door"] or st["errand"]:
        return None
    tool = str(inp.get("tool_name", ""))
    tinp = inp.get("tool_input") or {}
    if st.get("closing"):
        return None
    if tool == "Skill" and CLOSE_SKILL.search(str(tinp.get("skill", ""))):
        st["closing"] = True  # the close does its own git and file work; leave the rest of the turn alone
        save(sid, st)
        return None
    kind = classify(tool, tinp)
    if kind == "handover":
        st["turn_handovers"] = st.get("turn_handovers", 0) + 1
        log("handover %s after=%d %s" % (sid[:8], st["count"], tool))
        st["count"], st["next_fire"] = 0, threshold()  # handing over is the job; what follows is checking
        save(sid, st)
        return None
    if kind == "house":
        return None
    st["count"] += 1
    msg = None
    if kind == "artefact" and not st["art_fired"]:
        st["art_fired"] = True
        what = tool if not MISE_DO.match(tool) else "mise do %s" % (inp.get("tool_input") or {}).get("operation")
        msg, why = ART_MSG % what, "artefact:" + what
        if st["count"] >= st["next_fire"]:
            st["next_fire"] *= 2  # this call also met the threshold: don't nudge again on the next one
    elif st["count"] >= st["next_fire"]:
        msg, why = COUNT_MSG % st["count"], "count:%d" % st["count"]
        st["next_fire"] *= 2
    if msg is not None:
        st["turn_fires"] = st.get("turn_fires", 0) + 1
    save(sid, st)
    if msg is None:
        return None
    log("fire %s %s" % (sid[:8], why))
    return {"systemMessage": "front-door nudge (%s)" % why,
            "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": msg}}


HANDLERS = {"start": on_start, "prompt": on_prompt, "tool": on_tool}


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    if os.environ.get("BATTERIE_NUDGE", "").lower() in ("off", "0", "false"):
        return 0
    i = argv.index("--event") if "--event" in argv else -1
    event = argv[i + 1] if 0 <= i < len(argv) - 1 else ""
    if event not in HANDLERS:
        log("error: unknown --event %r (call allowed)" % event)
        return 0
    try:
        inp = json.load(sys.stdin)
        out = HANDLERS[event](inp)
    except Exception:  # fail open: a nudge is never worth a refused call
        log("error event=%s (call allowed): %s" % (event, traceback.format_exc().strip().replace("\n", " | ")))
        print("front-door-nudge: failed open, see %s" % (state_dir() / "nudges.log"), file=sys.stderr)
        return 0
    if out:
        print(json.dumps(out))
    return 0


# ---------------------------------------------------------------- self-test

def self_test() -> int:
    import tempfile
    fails = []

    def check(name, got, want):
        if got != want:
            fails.append("%s: got %r, want %r" % (name, got, want))

    with tempfile.TemporaryDirectory() as td:
        os.environ["BATTERIE_NUDGE_STATE_DIR"] = str(Path(td) / "state")
        os.environ.pop("BATTERIE_FRONT_DOOR", None)
        home = Path(td) / "home"
        os.environ["BATTERIE_NUDGE_HOME"] = str(home)
        for d in ("projects/mit-projects/lantern", "projects/mit-projects/other", "projects/scratch/2026-x",
                  "repos/o/r1/src", "repos/o/r2", "deep/plain"):
            (home / d).mkdir(parents=True)
        for f in ("projects/mit-projects/WHY.md", "projects/mit-projects/lantern/WHY.md",
                  "projects/mit-projects/other/WHY.md"):
            (home / f).write_text("x")
        for d in ("projects/mit-projects/.git", "repos/o/r1/.git", "repos/o/r2/.git", "projects/mit-projects/lantern/.bon"):
            (home / d).mkdir()
        fd = lambda rel: is_front_door(str(home / rel) if rel else str(home), home)
        check("home", fd(""), True)
        check("umbrella projects", fd("projects"), True)
        check("umbrella mit-projects (has .git and WHY.md)", fd("projects/mit-projects"), True)
        check("project", fd("projects/mit-projects/lantern"), False)
        check("scratch", fd("projects/scratch/2026-x"), True)
        check("repos umbrella", fd("repos/o"), True)
        check("inside a repo", fd("repos/o/r1/src"), False)
        check("plain folder", fd("deep/plain"), True)
        os.environ["BATTERIE_FRONT_DOOR"] = "0"
        check("forced off", fd(""), False)
        os.environ.pop("BATTERIE_FRONT_DOOR")

        check("paseo run", classify("Bash", {"command": "paseo run --cwd x --no-wait \"$B\""}), "handover")
        check("heredoc brief then paseo run", classify("Bash", {"command":
              "BRIEF=$(cat <<'EOF'\nRead the contract; then mark it up.\nDone when: comments on clause 4\nEOF\n)\n"
              "paseo run --workspace w --cwd ~/p --title t --no-wait \"$BRIEF\""}), "handover")
        check("opener via variable", classify("Bash", {"command": "$OPENER launch ~/p --title t --brief \"$BRIEF\""}), "handover")
        check("opener.py launch", classify("Bash", {"command": "uv run --script ~/k/opener.py launch ~/p --brief x"}), "handover")
        check("brief piped to paseo send", classify("Bash", {"command": "cat brief.md | paseo send A"}), "handover")
        check("cd then paseo ls", classify("Bash", {"command": "cd ~ && paseo ls -a -g"}), "house")
        check("state board", classify("Bash", {"command": "python3 ~/repos/x/scripts/state-board.py show"}), "house")
        check("paseo piped into python", classify("Bash", {"command": "paseo inspect A --json | python3 -c 'x'"}), "house")
        check("ListAgents is bookkeeping", classify("ListAgents", {}), "house")
        check("desktop list is bookkeeping", classify("mcp__ccd_session_mgmt__list_sessions", {}), "house")
        check("briefing is an artefact", classify("Write", {"file_path": "/home/u/x/client-briefing.md"}), "artefact")
        check("debrief is an artefact", classify("Write", {"file_path": "/home/u/x/debrief.md"}), "artefact")
        check("settings edit is not exempt", classify("Edit", {"file_path": "/home/u/.claude/settings.json"}), "artefact")
        check("paseo then grep work", classify("Bash", {"command": "paseo ls && rg foo ~/docs"}), "work")
        check("plain bash", classify("Bash", {"command": "ls ~/projects"}), "work")
        check("bonfire is not bon", classify("Bash", {"command": "bonfire light"}), "work")
        check("read", classify("Read", {"file_path": "/x"}), "work")
        check("write doc", classify("Write", {"file_path": "/home/u/projects/scratch/x/notes.md"}), "artefact")
        check("write brief", classify("Write", {"file_path": "/tmp/brief-census.md"}), "artefact-exempt")
        check("write handoff", classify("Write", {"file_path": "/home/u/handoffs/2026.md"}), "artefact-exempt")
        check("memory note", classify("Edit", {"file_path": "/home/u/.claude/projects/p/memory/x.md"}), "artefact-exempt")
        check("mise create", classify("mcp__plugin_mit_mise__do", {"operation": "create"}), "artefact")
        check("mise archive", classify("mcp__plugin_mit_mise__do", {"operation": "archive"}), "work")
        check("mise fetch", classify("mcp__plugin_mit_mise__fetch", {}), "work")
        check("agent", classify("Agent", {}), "handover")
        check("desktop launch", classify("mcp__ccd_session__start_session", {}), "handover")
        check("skill", classify("Skill", {}), "house")

        check("sonner as a path is not a hand-over", classify("Bash", {"command": "cd ~/repos/o/sonner && pytest"}), "work")
        check("sonner ring is a hand-over", classify("Bash", {"command": "sonner batterie-de-savoir \"look at X\""}), "handover")
        os.environ["PASEO_AGENT_ID"] = "test-agent"  # a Paseo chat: the cheap launch route
        # End to end: a front door, a prompt, then calls.
        cwd = str(home)
        on_start({"session_id": "s1", "cwd": cwd, "source": "startup"})
        on_prompt({"session_id": "s1", "prompt": "prep for the 2pm", "cwd": cwd})
        outs = [on_tool({"session_id": "s1", "tool_name": "Read", "tool_input": {"file_path": "/a"}}) for _ in range(30)]
        fired = [i + 1 for i, o in enumerate(outs) if o]
        check("fires at 12 and 24", fired, [12, 24])
        check("output shape", sorted((outs[11] or {}).get("hookSpecificOutput", {}).keys()), ["additionalContext", "hookEventName"])
        o = on_tool({"session_id": "s1", "tool_name": "Write", "tool_input": {"file_path": "/home/u/x/prep.md"}})
        check("artefact fires", bool(o), True)
        o = on_tool({"session_id": "s1", "tool_name": "Write", "tool_input": {"file_path": "/home/u/x/prep2.md"}})
        check("artefact fires once per turn", o, None)
        check("dispatch not counted", on_tool({"session_id": "s1", "tool_name": "Agent", "tool_input": {}}), None)
        check("subagent ignored", on_tool({"session_id": "s1", "agent_id": "a1", "tool_name": "Write",
                                           "tool_input": {"file_path": "/x/y.md"}}), None)
        on_prompt({"session_id": "s1", "prompt": "next", "cwd": cwd})
        outs = [on_tool({"session_id": "s1", "tool_name": "Read", "tool_input": {}}) for _ in range(11)]
        check("prompt resets the count", any(outs), False)

        on_prompt({"session_id": "s1", "prompt": "more", "cwd": cwd})
        for _ in range(11):
            on_tool({"session_id": "s1", "tool_name": "Read", "tool_input": {}})
        on_tool({"session_id": "s1", "tool_name": "Bash", "tool_input": {"command": "paseo run --no-wait x"}})
        outs = [on_tool({"session_id": "s1", "tool_name": "Read", "tool_input": {}}) for _ in range(11)]
        check("a hand-over resets the count", any(outs), False)
        on_prompt({"session_id": "s1", "prompt": "checking", "cwd": cwd})
        outs = []
        for i in range(12):
            outs.append(on_tool({"session_id": "s1", "tool_name": "Read", "tool_input": {}}))
            on_tool({"session_id": "s1", "tool_name": "Bash", "tool_input": {"command": "paseo ls"}})
        check("checking a chat does not reset the count", [i + 1 for i, o in enumerate(outs) if o], [12])
        on_prompt({"session_id": "s1", "prompt": "both", "cwd": cwd})
        for _ in range(11):
            on_tool({"session_id": "s1", "tool_name": "Read", "tool_input": {}})
        a = on_tool({"session_id": "s1", "tool_name": "Write", "tool_input": {"file_path": "/x/doc.md"}})
        b = on_tool({"session_id": "s1", "tool_name": "Read", "tool_input": {}})
        check("artefact at the threshold: one nudge, not two in a row", (bool(a), b), (True, None))
        on_tool({"session_id": "s1", "tool_name": "Skill", "tool_input": {"skill": "batterie:close"}})
        outs = [on_tool({"session_id": "s1", "tool_name": "Write", "tool_input": {"file_path": "/x/y.md"}}) for _ in range(20)]
        check("the close silences the turn", any(outs), False)
        on_prompt({"session_id": "s1", "prompt": "after close", "cwd": cwd})
        check("a new prompt ends the close's silence", load("s1")["closing"], False)

        os.environ["BATTERIE_NUDGE_THRESHOLD"] = "3"
        on_prompt({"session_id": "s1", "prompt": "env", "cwd": cwd})
        outs = [on_tool({"session_id": "s1", "tool_name": "Read", "tool_input": {}}) for _ in range(3)]
        check("BATTERIE_NUDGE_THRESHOLD overrides", [bool(o) for o in outs], [False, False, True])
        os.environ.pop("BATTERIE_NUDGE_THRESHOLD")

        on_start({"session_id": "s2", "cwd": cwd, "source": "startup"})
        on_prompt({"session_id": "s2", "prompt": "Brief...\n[errand: launched by a front door; do this errand]", "cwd": cwd})
        outs = [on_tool({"session_id": "s2", "tool_name": "Write", "tool_input": {"file_path": "/x/y.md"}}) for _ in range(12)]
        check("errand marker silences", any(outs), False)
        check("errand removes the fast-path flag", state_path("s2").with_suffix(".on").exists(), False)
        check("front door keeps the fast-path flag", state_path("s1").with_suffix(".on").exists(), True)

        on_start({"session_id": "s3", "cwd": cwd, "source": "startup"})
        on_prompt({"session_id": "s3", "prompt": "hi", "cwd": cwd})
        on_prompt({"session_id": "s3", "prompt": "[errand: sneaky]", "cwd": cwd})
        check("marker counts only on the first prompt", load("s3")["errand"], False)

        proj = str(home / "projects/mit-projects/lantern")
        on_start({"session_id": "s4", "cwd": proj, "source": "startup"})
        on_prompt({"session_id": "s4", "prompt": "go", "cwd": proj})
        outs = [on_tool({"session_id": "s4", "tool_name": "Write", "tool_input": {"file_path": "/x/y.md"}}) for _ in range(12)]
        check("project session never nudged", any(outs), False)
        check("project session has no fast-path flag", state_path("s4").with_suffix(".on").exists(), False)

        on_start({"session_id": "s1", "cwd": proj, "source": "resume"})
        check("resume keeps the launch decision", load("s1")["front_door"], True)

        on_start({"session_id": "s5", "cwd": cwd, "source": "startup"})
        on_prompt({"session_id": "s5", "prompt": "hi", "cwd": cwd})
        on_start({"session_id": "s5", "cwd": cwd, "source": "compact"})
        check("compact keeps the turn's state", load("s5")["prompts"], 1)
        check("main: missing --event value fails open without reading stdin", main(["--event"]), 0)

        on_start({"session_id": "s6", "cwd": cwd, "source": "resume"})
        on_prompt({"session_id": "s6", "prompt": "wake up", "cwd": cwd})
        outs = [on_tool({"session_id": "s6", "tool_name": "Read", "tool_input": {}}) for _ in range(14)]
        check("resume with no state on file stays quiet", any(outs), False)

        os.environ.pop("PASEO_AGENT_ID")
        saved_ep = os.environ.pop("CLAUDE_CODE_ENTRYPOINT", None)
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "sdk-cli"
        on_start({"session_id": "s7", "cwd": cwd, "source": "startup"})
        check("headless (sdk-cli, no Paseo) is not a front door", load("s7")["front_door"], False)
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "claude-desktop"
        on_start({"session_id": "s8", "cwd": cwd, "source": "startup"})
        check("Desktop at home is a front door", load("s8")["front_door"], True)
        os.environ.pop("CLAUDE_CODE_ENTRYPOINT")
        if saved_ep is not None:
            os.environ["CLAUDE_CODE_ENTRYPOINT"] = saved_ep
        os.environ["PASEO_AGENT_ID"] = "test-agent"

        check("unknown session is silent", on_tool({"session_id": "nope", "tool_name": "Read", "tool_input": {}}), None)
        (state_dir() / "bad.json").write_text("{not json")
        check("corrupt state is silent", on_tool({"session_id": "bad", "tool_name": "Read", "tool_input": {}}), None)

    os.environ.pop("PASEO_AGENT_ID", None)
    if fails:
        print("front-door-nudge self-test: %d FAILED" % len(fails))
        for f in fails:
            print("  " + f)
        return 1
    print("front-door-nudge self-test: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

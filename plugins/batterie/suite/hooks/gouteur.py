#!/usr/bin/env python3
"""goûteur — re-render a trap's rule at the moment its instrument goes blind.

WHAT IT IS. One Python file that Claude Code runs as a hook, fresh, on every
Bash call (and on Edit/Write, mise `do`, Read/Grep/Glob and permission
dialogs). It ships in the batterie plugin, wired in its plugin.json. It does
two jobs, and nothing else earns a place in it:

  GUARD   deny, before it runs, a call whose harm is irreversible or lands
          on someone else: credential content read into a transcript, a hand
          write into a bon board, a pkill/tmux kill that takes down the
          session itself, an rm glob Claude Code's own removal check cannot
          resolve, a Drive "trash" that does not revoke a public link.
  QUIRK   say, at the moment it bites, a Claude Code harness behaviour no
          model can know from training: the in-harness grep is ugrep and find
          is bfs, guidance files are session-cached, a settings deny refuses
          with no reason, a relative path after `cd` escalates to a dialog.

General command-line knowledge (rg -r, jq null, xargs -r, pipeline status)
does NOT belong here: Opus 5.5 already has it, measured with no guidance at
all, and every extra render is a distractor on the calls where it fires
wrongly. The retired renders are listed in RETIRED with why.

A BROKEN IMPORT HERE STOPS EVERY SESSION'S BASH (the --pre gate fails closed).
Run `python3 gouteur.py --self-test` before and after any edit, and keep it
importable by macOS's /usr/bin/python3 (3.9). CI runs the self-test.

PERSONAL RENDERS (gouteur.d). Renders that only make sense on one person's
machines (their hosts, their DNS, their secrets paths, their settings repo)
live outside this file, in Python modules under
${CLAUDE_CONFIG_DIR:-~/.claude}/gouteur.d/*.py (override the directory with
$GOUTEUR_EXTENSIONS; set it empty to load none). The engine imports each
module once per hook call; a module may define any of:

  RENDERS            {render_id: retire_when} for the ids it emits
  CREDENTIAL_CORES   extra spelling-invariant credential path cores
  DENY_RULE_REASONS  {"Bash(rule)": "why it exists"} for settings deny rules
  FOLLOWED           {render_id: (in_class, remedied)} for --followed
  PROJECT_ROOTS      extra transcript roots for --followed
  pre_bash(cmd, cwd)                    -> deny reason or None
  post_bash(cmd, stdout, stderr, cwd)   -> list of notes (rendered first)
  post_edit(file_path, session_id)      -> list of notes
  post_any(data)                        -> list of notes, every PostToolUse
                                           (session-scoped probes)
  self_test(check)                      -> run by --self-test

A module imports the engine's helpers with `import gouteur`. A module that
fails to import, or raises, fails OPEN: the shipped renders still run, the
failure is logged as gouteur-extension-failed, and the session is told once.

MODES (plugin.json `hooks` wires each):
  (default)  PostToolUse. Reads the finished call on stdin and may return lines
             of additionalContext. Bash → probe() (at most two notes);
             Edit/Write → probe_edit(); mise `do` → probe_mcp_do(); then each
             extension's post_any().
  --pre      PreToolUse. Two tiers, checked in this order:
             deny   a credential path in any spelling (credential_cores(); Read,
                    Grep and Glob are checked first, via CREDENTIAL_PATH_TOOLS),
                    a Bash hand-write into a bon board (unless declared with a
                    `# bon-handedit:` comment, which is let through and logged),
                    an env dump, a pgrep/pkill -f pattern that matches its own
                    wrapper, a tmux kill with no socket, an rm glob CC cannot
                    resolve, an extension's pre_bash, a foreground `sleep` of
                    30 s+ outside any loop (unless declared with
                    `# deliberate-wait:`, which is let through and logged).
                    Then any settings.json Bash() deny rule a subcommand
                    matches, said with the rule and its reason before CC's
                    mute deny can fire (probe_settings_deny()). Always "deny",
                    never "ask": a hook ask never reaches a human (CC
                    auto-denies it and drops the reason, measured 2026-08-30),
                    so a deny that carries its coaching is the only form that
                    helps. The reason text is tailored by caller (_pre_caller():
                    an Agent worker, or anyone else).
             rewrite  relative paths after a bare `cd` are made absolute and the
                    change is announced (rewrite_after_cd()), only where a
                    Read() deny rule exists to make CC prompt for them.
  --perm     PermissionRequest. Logs the SHAPE of each residual dialog, never
             its content (log_perm()).
  --fires [--repeats] [--since ISO]   census of renders from the fires log, each
             beside its RETIRE_WHEN exit condition (or RETIRED reason).
  --followed [--since ISO]   did the session's NEXT command of the same class
             carry the remedy (FOLLOWED)? Correlation, not cause: there is no
             unrendered baseline.
  --self-test   the shipped checks plus every extension's; --help prints this.

DESIGN RULES:
  - Render, don't add: every line ends in a bracketed source tag, and the tag
    is the render's identity (_render_id() slugs it; never reword a live one).
  - High precision: a render that fires wrongly is a distractor (Shi et al.,
    GSM-IC: one irrelevant sentence measurably degrades reasoning).
  - One line per finding, at most two from probe() per call, silent otherwise.
  - Designed misses fail open (a missed render costs one reminder); a crash is
    logged under [gouteur: crash], and in --pre it DENIES with the fault named.

ADDING A RENDER (the self-test enforces 3 and 4; 5 is on you):
  1. Decide it is a GUARD or a QUIRK (above). If it needs one person's estate,
     it belongs in their gouteur.d, not here.
  2. Add the branch to the probe for its tool: probe() for Bash output,
     probe_pre() for a pre-call deny, probe_edit() for Edit/Write,
     probe_mcp_do() for mise. One line, ENDING with its source tag.
  3. Add the slug to KNOWN_RENDER_IDS (_registry_drift() fails the self-test on
     a tag emitted but unregistered, or registered but never emitted).
  4. Add its exit condition to RETIRE_WHEN: what would have to be true of the
     INSTRUMENT for the render to be spent, or "never — <why>".
  5. Add self-test cases: at least one command that must fire and one near
     miss that must stay silent.
  6. If the remedy is visible in the session's next command of the same class,
     add a FOLLOWED entry and a case.
  7. A new TOOL (not a new shape) also needs a matcher in plugin.json.

WIRING NOTE. PostToolUse runs on EVERY Bash call unfiltered: several `if`
filters on one compound command ran goûteur once per filter and rendered in
quintuplicate (measured 2026-08-02), and ~40 ms of interpreter per call buys
the whole duplicate class away.

State (fires log, once-per-session markers) lives under ~/.local/state/gouteur,
or $GOUTEUR_STATE_DIR when set. Nothing leaves the machine.

Self-test: python3 gouteur.py --self-test
"""
# Lazy annotations: the `str | None` hints would otherwise stop the Mac's
# /usr/bin/python3 (3.9) importing this file, and every hook call would
# crash on a launch whose PATH finds it first (essayeur, carte-domubu).
from __future__ import annotations

import fnmatch
import json
import os
import re
import shlex
import shutil
import socket
import sys
import time


# --- PreToolUse: credential-path deny -------------------------------------

# Spelling-invariant cores: ~/, $HOME/, /home/x/, /Users/x/ all end the same.
# Only spellings that mean a credential on anyone's machine ship here; a
# person's own secrets paths go in their gouteur.d CREDENTIAL_CORES.
# `.config/gcloud/logs` carries tokens in gcloud's request logs; `sa-key.json`
# is the conventional name for a downloaded service-account key (one `head -c`
# over such a directory printed part of a key into a transcript, 2026-09-10).
CREDENTIAL_CORES = (".config/gcloud/logs", "sa-key.json")


# --- Extensions: personal renders from gouteur.d -----------------------------
#
# The shipped file holds only what is true on anyone's machine. A person's
# estate-bound renders (their hosts, DNS, secrets paths, settings repo) load
# from their own directory, so the plugin stays shareable and they keep theirs.
# A broken module is a DESIGNED failure (someone's own file, mid-edit), so it
# fails open and says so; it never takes the shipped guards down with it.

_EXTENSIONS: list | None = None
_EXT_ERRORS: list[str] = []
_EXT_ERRORS_LOGGED = 0


def _ext_dir() -> str:
    env = os.environ.get("GOUTEUR_EXTENSIONS")
    if env is not None:
        return os.path.expanduser(env)  # "" loads none
    return os.path.join(_config_dir(), "gouteur.d")


def extensions() -> list:
    """The loaded gouteur.d modules, imported once per process."""
    global _EXTENSIONS
    if _EXTENSIONS is not None:
        return _EXTENSIONS
    _EXTENSIONS = []
    d = _ext_dir()
    if not d or not os.path.isdir(d):
        return _EXTENSIONS
    try:
        names = sorted(os.listdir(d))
    except OSError as exc:  # an unreadable gouteur.d must not brick the gate
        _EXT_ERRORS.append(f"{d}: {type(exc).__name__}: {exc}")
        return _EXTENSIONS
    # Modules reach the engine's helpers with `import gouteur`, whatever name
    # this file was started under (it runs as __main__ from the hook).
    sys.modules.setdefault("gouteur", sys.modules[__name__])
    import importlib.util
    for name in names:
        if not name.endswith(".py") or name.startswith(("_", ".")):
            continue
        path = os.path.join(d, name)
        try:
            spec = importlib.util.spec_from_file_location(f"gouteur_d_{name[:-3]}", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        # SystemExit too: a module that calls sys.exit() at import must not
        # end the hook (exit 0 would skip every shipped guard for the call).
        except (Exception, SystemExit) as exc:  # noqa: BLE001 — someone's own file; fail open, say so
            _EXT_ERRORS.append(f"{path}: {type(exc).__name__}: {exc}")
            continue
        _EXTENSIONS.append(mod)
    return _EXTENSIONS


def _ext_call(hook: str, *args) -> list[str]:
    """Every extension's HOOK(*args) as a flat list of note strings. A raising
    extension, or one returning anything but None, a str or a list/tuple of
    str, is recorded and skipped, never propagated: the shape check sits
    inside the try, so a wrong return type cannot crash the --pre gate."""
    out: list[str] = []
    for mod in extensions():
        fn = getattr(mod, hook, None)
        if fn is None:
            continue
        try:
            got = fn(*args)
            if got is None or got == [] or got == ():
                continue
            if isinstance(got, str):
                got = [got]
            elif not (isinstance(got, (list, tuple)) and all(isinstance(n, str) for n in got)):
                raise TypeError(f"returned {type(got).__name__}, not a str or a list of str")
            out.extend(n for n in got if n)
        except (Exception, SystemExit) as exc:  # noqa: BLE001 — recorded, then skipped
            _EXT_ERRORS.append(f"{getattr(mod, '__file__', mod)}: {hook}: {type(exc).__name__}: {exc}")
    return out


def _ext_attr(name: str) -> list:
    """Every extension's module-level NAME, for the merges below."""
    return [getattr(m, name) for m in extensions() if hasattr(m, name)]


def _ext_errors_unlogged() -> list[str]:
    global _EXT_ERRORS_LOGGED
    new = _EXT_ERRORS[_EXT_ERRORS_LOGGED:]
    _EXT_ERRORS_LOGGED = len(_EXT_ERRORS)
    return new


def _report_ext_errors(data: dict, stage: str) -> str | None:
    """Log this call's extension failures ONCE per session per stage (a broken
    module would otherwise add a record on every hook call and swamp the
    census), and return the one-line note to tell the session, or None."""
    errs = _ext_errors_unlogged()
    if not errs or not _once_per_session(f"extension-failed-{stage}", data.get("session_id") or ""):
        return None
    note = (
        "goûteur: a personal render module failed, so its renders did not run "
        f"(the shipped ones did): {errs[0][:300]}"
        + (f" (+{len(errs) - 1} more)" if len(errs) > 1 else "")
        + ". Fix the file, or run `gouteur.py --self-test` to see it. "
        "[gouteur: extension-failed]"
    )
    if stage != "post":
        log_fires([note], data)  # PostToolUse logs every note it renders itself
    return note


def credential_cores() -> tuple:
    """Shipped cores plus every extension's. An extension's value must be a
    list or tuple of strings of three characters or more: a bare string (a
    missing comma) would iterate as single letters, and an empty core matches
    every path, either of which would deny nearly every call."""
    cores = list(CREDENTIAL_CORES)
    for mod in extensions():
        extra = getattr(mod, "CREDENTIAL_CORES", None)
        if extra is None:
            continue
        if not isinstance(extra, (list, tuple)) or not all(
                isinstance(c, str) and len(c.strip()) >= 3 for c in extra):
            _EXT_ERRORS.append(f"{getattr(mod, '__file__', mod)}: CREDENTIAL_CORES must be a "
                               "list/tuple of path strings (3+ chars); ignored")
            continue
        cores += [c for c in extra if c not in cores]
    return tuple(cores)

# Tools that take a path and hand its CONTENT back to the model. These are the
# ones the settings.json `Read()` deny rules used to guard; the gate moved here
# on 2026-09-06 so those rules could be deleted, because their mere EXISTENCE
# made CC escalate every `cd … && grep <relative-path>` to a human dialog in
# every mode, bypass included — a subagent cannot answer its own dialog and one
# in this estate stalled 17.5 hours on it (carte-sikoce, carte-datoje). The
# fields are the ones each tool actually carries; a tool absent from this map is
# not gated here.
# Scope is deliberately the content-SURFACING reads and nothing more, because
# that is exactly what the deleted rules covered — swapping one guard for
# another is honest, widening the posture while claiming a swap is not. Edit,
# Write and NotebookEdit against a credential path are therefore still ungated
# here, as they were before; no Edit() or Write() deny rule ever existed. Note
# too that the matcher in settings.json must list every key below, or the
# entries are declaration without wiring (the fault this file's own
# `if:` filter committed until 2026-09-04).
CREDENTIAL_PATH_TOOLS = {
    "Read": ("file_path",),
    "Grep": ("path", "glob", "pattern"),
    "Glob": ("path", "pattern"),
}


# A `bon edit` that sets a brief field from an UNEXPANDED substitution or
# variable. The hook sees the literal command, so it cannot know what the
# value will expand to — and that is exactly the hazard: an empty expansion
# CLEARS the field rather than leaving it alone. Twice in four days:
# carte-vudusu (2026-08-01, --why overwritten, the accurate half lost) and
# carte-viviko (2026-08-04, --how blanked when a missing scratchpad dir made
# `cat` return nothing). Both recovered from git only because ~/.claude is
# tracked. A literal empty string fires too — documented behaviour, but worth
# confirming it was meant.
_BON_FIELD = r"--(?:why|how|what|done|title)"
BON_CLEARING_EDIT = re.compile(
    rf"{_BON_FIELD}\s+(?:\"\"|''|\"?\$\(|\"?`|\"?\$\{{?[A-Za-z_])"
)


# The PreToolUse payload key set was pinned here (2026-08-24, CC 2.1.241,
# carte-suruta) and the pin was REMOVED on 2026-08-30 (carte-fijeva) after CC
# dropped `prompt_id` and the exact-set test turned every attended ask into a
# self-served deny. The measured key set as of 2026-08-30, kept as a record
# rather than as a gate: cwd, effort, hook_event_name, permission_mode,
# session_id, tool_input, tool_name, tool_use_id, transcript_path — note no
# prompt_id, and note that the 2026-08-24 set had it. Worker payloads add
# agent_id + agent_type, which is the discrimination _pre_caller() still uses.
# Do not re-pin: a schema pin on someone else's payload is a standing outage
# waiting for their next release.


def _pre_caller(data: dict) -> str:
    """Classify the caller of a gated tool call: 'agent' or 'other'.

    An Agent-tool worker's PreToolUse payload carries agent_id + agent_type
    (measured 2026-08-24, CC 2.1.241, carte-suruta); a top-level session's
    omits both. The classification only chooses the COACHING — every branch
    denies since carte-jegise (2026-08-30: a hook ask never renders a
    dialog) — so nothing is opened by getting it wrong, and 'other' coaching
    is written to serve an attended human and an unattended session alike.

    SIMPLIFIED 2026-09-30 (carte-sapaco). This used to demand positive
    proof of 'top' by polling the root transcript for this call's
    tool_use_id, and wrapped every unproved call in "IF YOU ARE SEEING THIS
    … most likely a Claude Code update changed the payload". Measured on CC
    2.1.285 with a timing tap: the record reached the transcript before the
    hook started (0.001 s), 2.9-3.5 s after it (a three-call batch, all at
    the same instant), or not within 4 s (a single call). So 5 of 6 attended
    denies that afternoon wore a drift diagnosis with no drift behind it,
    and a Happy (Agent SDK) session tripped it the night before. Alternative
    that lost: a longer poll — it blocks every deny for seconds and still
    cannot promise the record arrives. Accepted limit: a worker whose agent
    fields a CC update renamed gets the 'other' coaching, which names the
    park-it route too.
    """
    if "agent_id" in data or "agent_type" in data:
        return "agent"
    return "other"


def credential_core_in(value: object) -> str | None:
    """The credential core a path-ish tool argument touches, or None.

    Substring on the spelling-invariant core, same test the Bash gate uses, so
    `~/x/sa-key.json`, `$HOME/x/sa-key.json` and `/home/u/x/sa-key.json`
    all match and a glob like `**/sa-key.json` matches too. Non-strings are
    stringified rather than skipped: a schema change that wrapped the path in a
    list must not silently open the gate (the same reasoning as the Bash side's
    non-string command).
    """
    if value is None:
        return None
    text = value if isinstance(value, str) else str(value)
    for core in credential_cores():
        if core in text:
            return core
    return None


def deny_credential_tool(data: dict, tool: str) -> None:
    """Deny a path-bearing tool call that touches a credential path.

    This is the settings.json `Read()` deny rules re-homed (2026-09-06). Two
    behaviours are deliberately preserved from those rules: it denies for EVERY
    caller including the attended top level, because a hook `ask` never renders
    a dialog (carte-jegise), and it denies rather than redacting, because the
    hazard is the content reaching the transcript at all. What it adds is a
    reason — the settings rule denied mutely — and it costs the estate nothing
    in prompts, which the rules could not manage.
    """
    fields = CREDENTIAL_PATH_TOOLS.get(tool, ())
    args = data.get("tool_input") or {}
    if not isinstance(args, dict):
        args = {"_": args}
    hit = None
    for field in fields:
        hit = credential_core_in(args.get(field))
        if hit:
            break
    if not hit:
        return
    # Logged like any render: a deny is the strongest thing goûteur does and
    # was the only one invisible to the census (carte-nasara).
    log_fires([f"deny {tool} [traps.md: credential directories]"], data)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"goûteur DENIED this {tool} call, not the goal: it addresses "
            f"`{hit}`, and credential content read into a transcript costs the "
            "human a revoke and re-login. This gate replaced the settings.json "
            "Read() deny rules on 2026-09-06 — their existence alone made CC "
            "escalate every `cd … && grep <relative-path>` to a human dialog in "
            "every mode, which stalled unattended workers for hours "
            "(carte-sikoce). Same refusal, no side effect. If you need one "
            "non-secret field, name it and filter in Bash so a token cannot "
            "match. [traps.md: credential directories]"
        ),
    }}))


_ENV_DUMP_NOTE = (
    "goûteur: this dumps the whole environment — anything a shell profile "
    "sources or exports (API keys, tokens) is in it, and a bare `env`/`set`/"
    "`export` sweeps every value into the transcript with no path in sight. "
    "`compgen -e` lists variable NAMES without values; `printenv NAME` reads "
    "one you know is not a secret. [traps.md: credential directories]"
)


def _env_dump(cmd: str) -> bool:
    """A segment whose whole effect is printing every variable and value."""
    scan = _scannable(cmd)
    if re.search(r"/proc/[^\s/]+/environ", scan):
        return True
    for seg in re.split(r"[|;&]+|\n", scan):
        words = seg.split()
        if not words:
            continue
        name, args = words[0], words[1:]
        if name in ("env", "printenv") and all(a.startswith("-") for a in args):
            return True
        if name == "set" and not args:
            return True
        if name in ("export", "declare") and all(a in ("-p", "-x") for a in args):
            return True
    return False


# --- PreToolUse: hand-writes into a bon board (bon-tusico) -----------------
#
# Dolt made board hand-edits awkward by accident; with every board moving
# back to JSONL-in-repo (bon-nudano, 2026-09-23) this tripwire replaces the
# accident. The falsifier, 2026-09-25: "it's done badly if Claudes NEED
# to find other ways" — so it is a sensor, not a wall. When it fires the
# finding is a missing bon verb, and the remedy is the verb. A tripwire
# against a cooperative model, like the credential gate: variable
# indirection (p = '...'; open(p, 'w')) passes, by design.
#
# Scratch and test boards are exempt — the 2026-09-23 census found most raw
# hits were bon's own fixtures, and blocking them would make the render
# noise. A declared repair passes: `# bon-handedit: <reason>` in the command,
# logged to fires.jsonl so the census sees every one.

_BON_BOARD_FILE = re.compile(r"\.bon/(?:items|archive)\.jsonl(?![\w.-])")
_BON_HANDEDIT_ESCAPE = re.compile(r"#\s*bon-handedit:\s*(\S.*)")
_BON_SCRATCH_MARKERS = ("/pytest-of-", "/scratchpad/", "/tests/", "/fixtures/")
_BON_SCRATCH_ROOTS = ("/tmp/", "/var/tmp/", "/private/tmp/", "/private/var/folders/")
_BON_TMP_VARS = re.compile(r"^\$\{?(?:TMPDIR|TMP|TEMP|tmp|tmpdir|SP|SCRATCH)\b")

_BON_BOARD_NOTE = (
    "goûteur: this writes a bon board file (`{path}`) by hand, around the CLI — "
    "which skips bon's validation, its item-grain lock and merge, the bottle "
    "and the sync commit, and a malformed line reads as a vanished item. Use "
    "the verb: `bon new` / `bon edit` (JSON on stdin keeps quotes safe) / "
    "`bon done` / `bon reopen` / `bon move` / `bon doctor --fix` (ordering and "
    "repairs) / `bon restore ID` (an item lost from items.jsonl or "
    "archive.jsonl comes back from git history). If no verb does what you "
    "need, that IS the finding: file a field report on the missing verb against bon "
    "— that is how the hand-edits stopped last time. A genuine repair (a merge conflict, a migration) may go ahead "
    "declared: put `# bon-handedit: <reason>` in the command and it passes, "
    "logged. [traps.md: bon board hand-edits]"
)


def _shell_text(cmd: str) -> str:
    """The command with heredoc BODIES and single-quoted spans removed.

    A heredoc body is data (or a script handled by the python check), and a
    single-quoted span is a mention — neither can redirect. Double quotes
    stay: `> "$repo/.bon/items.jsonl"` is the commonest real spelling.
    """
    out, delim = [], None
    for line in cmd.split("\n"):
        if delim is not None:
            if line.strip() == delim:
                delim = None
            continue
        out.append(line)
        m = re.search(r"<<-?\s*\\?['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?", line)
        if m:
            delim = m.group(1)
    text = re.sub(r"'[^']*'", " ", "\n".join(out))
    # Inside double quotes a > ; | & is prose (`-m "a -> b"`), not shell —
    # the precision pass found it capturing across quotes into a later
    # `git add .bon/items.jsonl` 31 times. Blank them; the quotes stay.
    return re.sub(r'"[^"]*"', lambda m: re.sub(r"[>;|&]", " ", m.group(0)), text)


def _resolve_vars(text: str, cmd: str) -> str:
    """Expand $VAR / ${VAR} from plain assignments made in the same command.

    The precision pass (2026-09-27) found every scratch-board false positive
    spelled through a variable — `T=$(mktemp -d)`, `R="$T/repo"`, then
    `> "$R/.bon/items.jsonl"`. A `$(mktemp …)` value counts as /tmp.
    """
    assigns: dict[str, str] = {}
    for m in re.finditer(
        r"(?:^|[\s;&(])(?:local\s+|export\s+|readonly\s+)?([A-Za-z_]\w*)="
        r"(\"[^\"]*\"|'[^']*'|[^\s;&|)]*)",
        cmd,
    ):
        val = m.group(2).strip("\"'")
        assigns[m.group(1)] = "/tmp/mktemp" if "mktemp" in val else val
    for _ in range(5):
        new = re.sub(r"\$\{?([A-Za-z_]\w*)\}?",
                     lambda v: assigns.get(v.group(1), v.group(0)), text)
        if new == text:
            break
        text = new
    return text


def _is_scratch_board(token: str, cmd: str, cwd: str) -> bool:
    """A board path under a temp or test location — exempt by design.

    `cmd` is the command up to the write, so the `cd` that governs a
    relative path is the last one BEFORE it, not a later one.
    """
    tok = token.strip("\"'")
    if _BON_TMP_VARS.match(tok):
        return True
    tok = _resolve_vars(tok, cmd)
    if _BON_TMP_VARS.match(tok):
        return True
    if re.search(r"\$(?!HOME\b|\{HOME\})", tok) and re.search(r"mktemp|/tmp/|TMPDIR", cmd):
        # Still a variable we cannot see (a function argument, a loop
        # variable) in a command that is building scratch fixtures. Every
        # real hand-edit in the history spelled its path literally.
        return True
    if tok.startswith(("~", "$HOME", "${HOME}")):
        path = os.path.expanduser("~") + re.sub(r"^(?:~|\$HOME|\$\{HOME\})", "", tok)
    elif tok.startswith("/"):
        path = tok
    else:
        # Relative: the last `cd` in the command decides, else the hook cwd.
        cds = re.findall(r"(?:^|[;&|\n(]\s*)cd\s+([^\s;&|)]+)", cmd)
        base = os.path.expanduser(_resolve_vars(cds[-1].strip("\"'"), cmd)) if cds else cwd
        path = os.path.join(base or "", tok)
    tmpdir = os.environ.get("TMPDIR") or ""
    roots = _BON_SCRATCH_ROOTS + ((tmpdir.rstrip("/") + "/",) if tmpdir else ())
    return path.startswith(roots) or any(m in path for m in _BON_SCRATCH_MARKERS)


def _bon_board_write(cmd: str, cwd: str = "") -> str | None:
    """The board path a command writes by hand, or None.

    Shapes (bon-tusico brief): a redirect (> >>) onto the file; tee/sponge
    onto it; sed -i / perl -i naming it; cp/mv/install with it as the
    destination; python open(<board>, 'w'|'a'|'x'|'r+') or
    <board>.write_text/write_bytes. Reads, git operations (checkout,
    restore — the moved-board refusal's own remedy) and rm are not writes
    here. Scratch and test boards are skipped.
    """
    if ".bon/" not in cmd or "jsonl" not in cmd:
        return None
    hits: list[str] = []
    text = _shell_text(cmd)
    for m in re.finditer(
        r"(?:^|[^<>&0-9])(?:\d?>>?|&>>?)\s*(\"[^\"]*\"|[^\s;&|<>()]+)", text
    ):
        if _BON_BOARD_FILE.search(m.group(1)):
            hits.append(m.group(1))
    for seg in re.split(r"\|\|?|&&|;|\n", text):
        try:
            words = shlex.split(seg, posix=False)
        except ValueError:
            words = seg.split()
        while words and words[0] in ("command", "sudo", "nice", "time"):
            words = words[1:]
        if not words:
            continue
        name, args = os.path.basename(words[0]), words[1:]
        plain = [a for a in args if not a.startswith("-")]
        if name in ("tee", "sponge"):
            hits += [a for a in plain if _BON_BOARD_FILE.search(a)]
        elif name == "sed" and any(
            a == "-i" or a.startswith(("-i", "--in-place")) or re.match(r"-[a-zA-Z]*i", a)
            for a in args
        ):
            hits += [a for a in plain if _BON_BOARD_FILE.search(a)]
        elif name == "perl" and any(re.match(r"-[a-zA-Z]*i", a) for a in args):
            hits += [a for a in plain if _BON_BOARD_FILE.search(a)]
        elif name in ("cp", "mv", "install") and plain and _BON_BOARD_FILE.search(plain[-1]):
            hits.append(plain[-1])
    board = r"""[^'"]*\.bon/(?:items|archive)\.jsonl"""
    for m in re.finditer(
        rf"""open\(\s*(?:f|r|rf)?(['"]{board})['"]\s*,\s*(?:mode\s*=\s*)?['"](?:w|a|x|r\+)""",
        cmd,
    ):
        hits.append(m.group(1).lstrip("'\""))
    for m in re.finditer(
        rf"""Path\(\s*(?:f|r|rf)?(['"]{board})['"]\s*\)\s*\.write_(?:text|bytes)\(""", cmd
    ):
        hits.append(m.group(1).lstrip("'\""))
    for h in hits:
        at = cmd.find(h)
        if not _is_scratch_board(h, cmd[: at if at >= 0 else len(cmd)], cwd):
            return h.strip("\"'")
    return None


def bon_board_tool_path(data: dict) -> str | None:
    """The bon board file a Write/Edit/NotebookEdit call targets, or None."""
    args = data.get("tool_input") or {}
    path = args.get("file_path") or args.get("notebook_path") if isinstance(args, dict) else None
    if not isinstance(path, str) or not _BON_BOARD_FILE.search(path):
        return None
    if _is_scratch_board(path, "", data.get("cwd") or ""):
        return None
    return path


def deny_bon_board_tool(data: dict, tool: str) -> bool:
    """Deny a file-tool write onto a bon board; True when it denied.

    Every caller, like the credential gate: a hook ask never renders a
    dialog (carte-jegise). The file tools carry no command to hold the
    escape comment, so the coaching routes a declared repair through Bash.
    """
    path = bon_board_tool_path(data)
    if not path:
        return False
    log_fires([f"deny {tool} [traps.md: bon board hand-edits]"], data)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"goûteur DENIED this {tool} call, not the goal. "
            + _BON_BOARD_NOTE.format(path=path)
            + " (The escape comment rides a Bash command; the file tools have "
            "nowhere to carry it.)"
        ),
    }}))
    return True


def bon_board_escape(cmd: str) -> str | None:
    """The declared reason when a board write carries the escape comment."""
    m = _BON_HANDEDIT_ESCAPE.search(cmd)
    return m.group(1).strip() if m else None


# --- PreToolUse: shell segments (shared by the pgrep and settings checks) --


def _drop_heredoc_bodies(cmd: str) -> str:
    """The command without heredoc bodies — data, or a script, never argv."""
    out, delim = [], None
    for line in cmd.split("\n"):
        if delim is not None:
            if line.strip() == delim:
                delim = None
            continue
        out.append(line)
        m = re.search(r"<<-?\s*\\?['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?", line)
        if m:
            delim = m.group(1)
    return "\n".join(out)


def _shell_segments(cmd: str) -> list[str]:
    """The simple commands of a compound command, quote-aware.

    Splits on unquoted ; | & && || and newlines (not the & of 2>&1 or &>),
    and adds the inside of every $( … ) and backtick substitution as a
    segment of its own, recursively — `kill $(pgrep -f x)` is the commonest
    way to run pgrep. Quoted text stays inside its segment, so prose in a
    commit message is never a command. Deliberately approximate: every
    shape it misreads is a missed deny, which falls through to today's
    behaviour, never a new one.
    """
    text = _drop_heredoc_bodies(cmd)
    segs: list[str] = []
    subs: list[str] = []
    buf: list[str] = []
    q = None
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if q == "'":
            buf.append(c)
            if c == "'":
                q = None
        elif c == "\\" and nxt:
            buf.append(c + nxt)
            i += 1
        elif c == "$" and nxt == "(":
            depth, j = 1, i + 2
            while j < n and depth:
                depth += {"(": 1, ")": -1}.get(text[j], 0)
                j += 1
            subs.append(text[i + 2:j - 1])
            buf.append(text[i:j])
            i = j
            continue
        elif c == "`":
            j = text.find("`", i + 1)
            j = n if j < 0 else j
            subs.append(text[i + 1:j])
            buf.append(text[i:j + 1])
            i = j + 1
            continue
        elif q == '"':
            buf.append(c)
            if c == '"':
                q = None
        elif c in "'\"":
            q = c
            buf.append(c)
        elif c == "&" and (nxt == ">" or (buf and buf[-1].endswith(">"))):
            buf.append(c)
        elif c in ";|&\n":
            segs.append("".join(buf))
            buf = []
        else:
            buf.append(c)
        i += 1
    segs.append("".join(buf))
    out = []
    for s in segs:
        s = s.strip().lstrip("({!").rstrip(")}").strip()
        s = re.sub(r"^(?:(?:then|do|else|elif|if|while|until)\s+)+", "", s)
        if s:
            out.append(s)
    for s in subs:
        out += _shell_segments(s)
    return out


# Leading words that run the next word as the command.
_CMD_WRAPPERS = {"sudo", "command", "exec", "nohup", "time", "nice",
                 "timeout", "stdbuf", "env", "xargs", "builtin"}


def _argv(seg: str) -> list[str]:
    """A segment's argv with leading VAR=val assignments and wrappers dropped.

    shlex in POSIX mode, so quotes are removed the way the shell removes
    them; a segment it cannot parse falls back to a whitespace split.
    """
    try:
        words = shlex.split(seg, posix=True)
    except ValueError:
        words = seg.split()
    while words:
        w = words[0]
        if re.match(r"^[A-Za-z_]\w*=", w):
            words = words[1:]
        elif os.path.basename(w) in _CMD_WRAPPERS:
            words = words[1:]
            # the wrapper's own options and values: `nice -n 5`, `timeout 10`,
            # `sudo -u x`, `stdbuf -oL` — anything before the next plain word
            # that is not an assignment or a number.
            while words and (words[0].startswith("-")
                             or re.match(r"^\d+[smhd]?$", words[0])):
                if words[0] in ("-n", "-u", "-g", "-s", "-k") and len(words) > 1:
                    words = words[1:]
                words = words[1:]
        else:
            break
    return words


# --- PreToolUse: pgrep -f / pkill -f self-match (carte-ratenu) -------------
#
# With -f the pattern is matched against every process's FULL command line,
# and the harness wrapper that runs this very Bash call carries the whole
# command string in its own — so a bare substring always matches the caller.
# Measured 2026-09-29 on Linux (procps-ng 4.0.4): `pgrep -l -f marker` matched
# the harness bash, and over `ssh host` the remote bash AND tailscaled
# (Tailscale SSH carries the cmdline), so `pkill -f` over ssh kills the
# session it arrived on. macOS/BSD pgrep excludes its own ancestors unless
# -a, so on Darwin a plain `pgrep -f` found nothing while `pgrep -a -f`
# matched the CC wrapper zsh. This replaces the settings.json prefix rules
# `Bash(pgrep -f*)` / `Bash(pkill -f*)`, which denied mutely, missed every
# reordered spelling (`pgrep -lf`, `pkill -9 -f`, `/usr/bin/pgrep -f`) and
# refused the anchored form that is the remedy.

# Short options whose value is the next word (procps and BSD pgrep, union;
# -c is left out: a flag on procps, the common platform here).
_PGREP_VALUE_OPTS = set("dgGPstuUFrMNjL")
_PGREP_VALUE_LONG = {"--delimiter", "--pgroup", "--group", "--parent",
                     "--session", "--terminal", "--euid", "--uid",
                     "--pidfile", "--runstates", "--signal", "--ns",
                     "--nslist", "--cgroup", "--env", "--older", "--newer"}
_REMOTE_SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}

_PGREP_NOTE = (
    "goûteur: `{name} -f {pat}` matches {who} — with -f the pattern is tested "
    "against every full command line, and the harness wrapper running this "
    "call carries the pattern in its own{remote}. {danger}Remedies: "
    "`pidof <binary>`; anchor the pattern (`{name} -f '^/path/to/binary'`, "
    "which no wrapper's cmdline starts with); `-x` for an exact match; signal "
    "a PID you have read; or `ps -axww | grep '[f]oo'` (the bracket stops "
    "grep and the wrapper matching themselves). On macOS, pgrep without -a "
    "already excludes its own ancestors, so a plain `pgrep -f` is let through "
    "there. [traps.md: pgrep -f self-match]"
)


# The harness runs each Bash call as `/bin/bash -c source <snapshot> … &&
# eval '<command, ' spelled '"'"'>' && pwd -P >| /tmp/claude-XXXX-cwd`
# (read off /proc on Linux, CC 2.1.285). A pattern self-matches exactly when
# it matches that string, so test it there rather than guessing from shape.
_WRAPPER_HEAD = ("/bin/bash -c source /home/u/.claude/shell-snapshots/"
                 "snapshot-bash-0-x.sh 2>/dev/null || true && shopt -u extglob "
                 "2>/dev/null || true && { \\builtin unalias -- 'unsetenv'; "
                 "\\builtin unset -f -- 'unsetenv'; } >/dev/null 2>&1 || true "
                 "&& eval '")
_WRAPPER_TAIL = "' && pwd -P >| /tmp/claude-0000-cwd"


def _self_matches(pattern: str, cmdline: str, icase: bool) -> bool:
    """Would PATTERN (pgrep's extended regex) match the wrapper that runs
    CMDLINE? True when it cannot tell: a POSIX class or a pattern Python's
    re will not compile is not evaluated, it is denied."""
    if "[:" in pattern:
        return True
    try:
        rx = re.compile(pattern, re.I if icase else 0)
    except re.error:
        return True
    wrapped = _WRAPPER_HEAD + cmdline.replace("'", "'\"'\"'") + _WRAPPER_TAIL
    return any(rx.search(t) for t in (wrapped, "bash -c " + cmdline, cmdline))


def _pgrep_hazard(argv: list[str], platform: str, remote: bool,
                  cmdline: str = "") -> str | None:
    """The deny note for one pgrep/pkill argv, or None when it is safe."""
    name = os.path.basename(argv[0])
    has_f = has_a = has_x = has_i = False
    pattern = None
    k = 1
    while k < len(argv):
        a = argv[k]
        if a == "--":
            pattern = argv[k + 1] if k + 1 < len(argv) else None
            break
        if a.startswith("--"):
            opt = a.split("=", 1)[0]
            has_f |= opt == "--full"
            has_x |= opt == "--exact"
            has_i |= opt == "--ignore-case"
            if opt in _PGREP_VALUE_LONG and "=" not in a:
                k += 1
        elif a.startswith("-") and len(a) > 1:
            letters = a[1:]
            if name == "pkill" and re.fullmatch(r"\d+|[A-Z][A-Z0-9+-]+", letters):
                k += 1  # a signal: -9, -KILL, -SIGTERM, -RTMIN+1
                continue
            for j, ch in enumerate(letters):
                if ch in _PGREP_VALUE_OPTS:
                    # the rest of the cluster, or the next word, is its value
                    if j == len(letters) - 1 and k + 1 < len(argv) \
                            and not argv[k + 1].startswith("-"):
                        k += 1
                    break
                has_f |= ch == "f"
                has_a |= ch == "a"
                has_x |= ch == "x"
                has_i |= ch == "i"
        elif pattern is None:
            pattern = a
        k += 1
    if not has_f or has_x or pattern is None:
        return None
    if not _self_matches(pattern, cmdline or " ".join(argv), has_i):
        return None  # a ^ anchor, or `[f]oo`: cannot match its own wrapper
    if platform == "darwin" and not remote and name == "pgrep" and not has_a:
        return None
    who = ("the remote login shell and, over Tailscale SSH, tailscaled"
           if remote else "this call's own harness wrapper")
    danger = ("pkill would signal them — the session this command arrived on. "
              if name == "pkill" else
              "An off-by-one count or a phantom match is a self-match. ")
    return _PGREP_NOTE.format(
        name=name, pat=shlex.quote(pattern), who=who, danger=danger,
        remote=", and a command sent over ssh lands in a remote shell whose "
               "cmdline carries it too" if remote else "")


def _pgrep_self_match(cmd: str, platform: str | None = None,
                      remote: bool = False, depth: int = 0,
                      cmdline: str = "") -> str | None:
    """Deny note when any segment runs pgrep/pkill -f with a bare substring.

    Any flag order and cluster (-lf, -af, -9 -f, --full), any path to the
    binary, inside $( … ), and through `ssh host '…'` and `sh -c '…'`, whose
    remote or child command is read as another command line. The remote
    platform is unknown, so through ssh the Darwin exemption never applies.
    """
    if "pgrep" not in cmd and "pkill" not in cmd:
        return None
    platform = platform or sys.platform
    # The command line the matching processes carry: this command's own
    # wrapper, or through ssh the remote command (sh -c keeps the outer one).
    cmdline = cmdline or cmd
    for seg in _shell_segments(cmd):
        argv = _argv(seg)
        if not argv:
            continue
        name = os.path.basename(argv[0])
        if name in ("pgrep", "pkill"):
            note = _pgrep_hazard(argv, platform, remote, cmdline)
            if note:
                return note
        elif depth < 3 and name == "ssh":
            rest = argv[1:]
            k = 0
            while k < len(rest) and rest[k].startswith("-"):
                k += 2 if len(rest[k]) == 2 and rest[k][1] in _SSH_VALUE_OPTS else 1
            if k + 1 < len(rest):
                note = _pgrep_self_match(" ".join(rest[k + 1:]), platform, True, depth + 1)
                if note:
                    return note
        elif depth < 3 and name in _REMOTE_SHELLS and "-c" in argv[1:-1]:
            inner = argv[argv.index("-c", 1) + 1]
            note = _pgrep_self_match(inner, platform, remote, depth + 1, cmdline)
            if note:
                return note
    return None


# --- PreToolUse: tmux kill-server with no socket named (carte-mewiwo) -------
#
# 30 Sep 2026: a worker cleaned up its private test server with
# `export TMUX_TMPDIR=<private>; tmux kill-server`. $TMUX was still set (its
# `unset TMUX` had been in the PREVIOUS Bash call; calls share no shell
# state), and the tmux client follows $TMUX over TMUX_TMPDIR, so it killed
# the machine's default server — the one every sonner-spawned and
# tmux-hosted Claude lived in: five sessions, itself included. Measured 2026-10-20 on tmux 3.5a
# with two throwaway servers and TMUX pointing at one: `-S path` and `-L name`
# both reach the other server, TMUX_TMPDIR does not. So the discriminator is
# a socket named on the tmux command itself, whatever $TMUX holds; the card's
# draft ("unset TMUX AND -S/-L") asked for more than the mechanism needs.
# kill-session with no -t kills the caller's own session; with -t, or with a
# socket named, the target is explicit and passes. tmux takes unambiguous
# command prefixes (`kill-ser`), so those are matched too.

_TMUX_VALUE_OPTS = set("cfLST")

_TMUX_KILL_NOTE = (
    "goûteur: `tmux {verb}` with no -S/-L names no server, so it hits whichever "
    "one $TMUX points at, else the default socket — often the server every "
    "sonner-spawned and tmux-hosted Claude lives in (30 Sep 2026: one cleanup "
    "took down five sessions). Name the socket on the same command: "
    "`tmux -L <name> {verb}` or `tmux -S <path> {verb}` — both beat $TMUX; "
    "TMUX_TMPDIR does not, and an `unset TMUX` in an earlier Bash call is "
    "already gone.{extra} [traps.md: tmux kill without a socket]"
)


def _tmux_kill_hazard(cmd: str, depth: int = 0) -> str | None:
    """Deny note when a segment runs tmux kill-server (or a target-less
    kill-session) without -S/-L, directly or through ssh / sh -c."""
    if "tmux" not in cmd or "kill-se" not in cmd:
        return None
    for seg in _shell_segments(cmd):
        argv = _argv(seg)
        if not argv:
            continue
        name = os.path.basename(argv[0])
        if name == "tmux":
            socket, i = False, 1
            while i < len(argv) and argv[i].startswith("-") and argv[i] != "--":
                opt = argv[i]
                if opt[1:2] in ("L", "S"):
                    socket = True
                if len(opt) == 2 and opt[1] in _TMUX_VALUE_OPTS:
                    i += 1
                i += 1
            rest = argv[i:]
            for j, word in enumerate(rest):
                if re.fullmatch(r"kill-ser(v(e(r)?)?)?", word):
                    if not socket:
                        return _TMUX_KILL_NOTE.format(
                            verb="kill-server",
                            extra=" Killing the default server on purpose: `tmux -L default kill-server`.")
                elif re.fullmatch(r"kill-ses(s(i(o(n)?)?)?)?", word):
                    tail = rest[j + 1:]
                    end = next((k for k, w in enumerate(tail) if w in (";", "\\;")), len(tail))
                    if not socket and not any(w.startswith("-t") for w in tail[:end]):
                        return _TMUX_KILL_NOTE.format(
                            verb="kill-session",
                            extra=" Or give it a target: `tmux kill-session -t <name>`.")
        elif depth < 3 and name == "ssh":
            rest = argv[1:]
            k = 0
            while k < len(rest) and rest[k].startswith("-"):
                k += 2 if len(rest[k]) == 2 and rest[k][1] in _SSH_VALUE_OPTS else 1
            if k + 1 < len(rest):
                note = _tmux_kill_hazard(" ".join(rest[k + 1:]), depth + 1)
                if note:
                    return note
        elif depth < 3 and name in _REMOTE_SHELLS and "-c" in argv[1:-1]:
            note = _tmux_kill_hazard(argv[argv.index("-c", 1) + 1], depth + 1)
            if note:
                return note
    return None


# --- PreToolUse: a foreground blind sleep (carte-holuka) -------------------
#
# `sleep 90; gh run list` guesses how long the wait is and holds the turn
# while it guesses. Census 1 Sep–6 Oct 2026: 506 such calls against 2 of the
# recommended shape (a background until-loop). CC has its own guard — a Bash
# "Blocked: sleep N followed by…" and a "use Monitor" line in the Bash
# description — but both ride the remote flag that gates Monitor
# (`tengu_amber_sentinel`), which Vertex sessions never fetch, so on Vertex
# this is the only guard. The remedy was measured on both lanes, unattended
# `claude -p` included (2026-10-10): a run_in_background until-loop delivers
# its completion and the model resumes.
#
# Precision over reach — every doubt is silence: any for/while/until loop
# (a condition is being watched), any lone `&` (something is backgrounded;
# `(sleep 60; kill $pid) &` is a watchdog, not a wait), a non-numeric or
# `infinity` duration, quoted prose, heredoc bodies, and the payload of an
# ssh or `sh -c` (not unwrapped here).

_BLIND_SLEEP_MIN_S = 30
_DELIBERATE_WAIT = re.compile(r"#\s*deliberate-wait:\s*(\S.*)")
_SLEEP_UNITS = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}
_BLIND_SLEEP_NOTE = (
    "goûteur: this sleeps {secs}s in the foreground and then looks once — a "
    "guess at the duration that holds the turn. Wait on the CONDITION instead: "
    "re-run with run_in_background=true and `until <check that is true when "
    "done>; do sleep 5; done` (e.g. `until gh run view ID --json status -q "
    ".status | grep -qx completed; do sleep 15; done`) — one notification when "
    "it exits, on every lane, unattended -p included. For one event per "
    "occurrence use Monitor where this session has it (absent on Vertex); to "
    "end the turn and come back later, ScheduleWakeup or send_later. A genuine "
    "settle-pause passes with a trailing `# deliberate-wait: <why>`. "
    "[traps.md: blind sleep]"
)


def _sleep_seconds(argv: list[str]) -> float | None:
    """Total seconds a `sleep` argv waits, or None if it is not one we can
    read (not sleep, a flag, a variable, `infinity`). GNU sleep sums its
    arguments, so `sleep 20 20` is forty seconds."""
    if len(argv) < 2 or os.path.basename(argv[0]) != "sleep":
        return None
    total = 0.0
    for a in argv[1:]:
        if a.startswith("#") or re.match(r"^\d*[<>]|^&>", a):
            break  # a trailing comment or redirection ends the operands
        m = re.fullmatch(r"(\d+(?:\.\d+)?|\.\d+)([smhd]?)", a)
        if not m:
            return None
        total += float(m.group(1)) * _SLEEP_UNITS[m.group(2)]
    return total


def _watches_or_backgrounds(cmd: str) -> bool:
    """True if the command loops (a condition is watched) or backgrounds
    something with a lone `&` — not `&&`, `>&`, `&>` or `|&`."""
    masked = _mask_quotes(_drop_heredoc_bodies(cmd))
    if re.search(r"(?:^|[\s;&|(])(?:(?:while|until|select)\s"
                 r"|for\s+[A-Za-z_]\w*\s*(?:in\b|;|\n|do\b)|for\s*\(\()", masked):
        return True
    return re.search(r"(?<![&>|])&(?![&>])", masked) is not None


def blind_sleep(cmd: str, background: bool = False) -> str | None:
    """Deny note for a foreground `sleep` of 30 s or more outside any loop."""
    if background or "sleep" not in cmd or _watches_or_backgrounds(cmd):
        return None
    for seg in _shell_segments(cmd):
        # `timeout 5 sleep 60` waits 5 s and is how timeouts get tested;
        # _argv would strip the wrapper and read 60 (essayeur, 2026-10-10).
        if re.match(r"^(?:[A-Za-z_]\w*=\S*\s+)*(?:\S*/)?timeout\s", seg):
            continue
        secs = _sleep_seconds(_argv(seg))
        if secs is not None and secs >= _BLIND_SLEEP_MIN_S:
            return _BLIND_SLEEP_NOTE.format(secs=f"{secs:g}")
    return None


def deliberate_wait_escape(cmd: str) -> str | None:
    """The declared reason when a sleep carries the deliberate-wait comment."""
    m = _DELIBERATE_WAIT.search(cmd)
    return m.group(1).strip() if m else None


def probe_pre(cmd: str, cwd: str = "", background: bool = False) -> str | None:
    """Return a deny reason if the command is one of the pre-flight hazards.

    Contract (2026-09-06, carte-hazoti): a TRIPWIRE against a
    cooperative model's accidental sweep, not a gate that holds against
    rephrasing. Substring on the path core, plus the environment dumps that
    reach the same values with no path at all. A hook cannot hold against an
    adversary and this one does not claim to.
    """
    if _env_dump(cmd):
        return _ENV_DUMP_NOTE
    for core in credential_cores():
        if core in cmd:
            return (
                f"goûteur: this command references `{core}` — reading credential "
                "paths from Bash sweeps secrets into the transcript, and the remedy "
                "(revoke + re-login) costs the human. If this is a mere mention or "
                "a token-safe extraction, approve; otherwise name the one non-secret "
                "field needed and filter so a token cannot match. "
                "[traps.md: credential directories]"
            )

    board = _bon_board_write(cmd, cwd)
    if board and not bon_board_escape(cmd):
        return _BON_BOARD_NOTE.format(path=board)

    # Gate on bon actually being invoked with `edit`, using the same
    # command-position test as the post-hoc renders, so prose mentioning
    # `bon edit` stays silent. The FIELD test then runs on the raw command,
    # because _scannable() strips exactly the quoted span we need to see.
    scan = _scannable(cmd)
    if _invoked("bon", scan) and re.search(r"(?:^|[\s;|&(])bon\s+edit\s", scan):
        if BON_CLEARING_EDIT.search(cmd):
            return (
                "goûteur: this `bon edit` sets a brief field from a substitution or "
                "variable, and an EMPTY expansion CLEARS the field rather than "
                "leaving it alone — the whole prior text is gone. Happened twice in "
                "four days (carte-vudusu 1 Aug, carte-viviko 4 Aug), recovered from "
                "git both times. Confirm the source is non-empty in a SEPARATE call "
                "before this one, and if you are correcting an existing brief, append "
                "rather than substitute — the original claim plus the correction is "
                "the record. [verification.md: the outrunning write]"
            )

    pgrep = _pgrep_self_match(cmd)
    if pgrep:
        return pgrep

    tmux_kill = _tmux_kill_hazard(cmd)
    if tmux_kill:
        return tmux_kill

    rm_glob = rm_glob_breaker(cmd, cwd)
    if rm_glob:
        return rm_glob

    # Extension denies (gouteur.d), after every shipped guard.
    for reason in _ext_call("pre_bash", cmd, cwd):
        return reason

    # Last: the cheapest miss of the pre-flight hazards (carte-holuka).
    if not deliberate_wait_escape(cmd):
        return blind_sleep(cmd, background)
    return None


# --- PreToolUse: rm globs Claude Code cannot resolve (carte-datoje) --------
#
# CC's dangerous-removal check (function nq in the 2.1.316 bundle) is one of
# the "circuit breakers" bypass mode cannot override, so a hit halts a Paseo
# chat or an Agent worker on a dialog nobody is watching (3 halts on
# 2026-11-01 alone, one of them a human clicking Accept for a chat).
# Measured that day, headless with `claude -p --permission-mode
# bypassPermissions`, 19 probes, files left on disk as the ground truth:
#   HALTS  an rm target ending in /* that holds a `..` segment, relative or
#          not (`../b/*`, no cd needed; `/abs/a/../b/*`; `~/../x/*`);
#          two glob levels (`/abs/b/*/*`); a relative glob after a cd the
#          check cannot follow (`cd sub && rm -f deep/*`, a relative cd; or
#          `mkdir -p N && cd N && rm -rf *`, a cd into a directory that does
#          not exist yet when the check runs).
#   RUNS   `/abs/b/*`, `sub/*`, `./sub/*`, `*.log`, `../b/*.log`, `../b`,
#          `cd /abs/a && rm -rf sub/*`, `X=/abs; cd $X/a && rm -f sub/*`.
# So the cd is incidental; the opener's first reading ("a glob after a cd")
# would have missed both live halts, which had no cd in the command.
# A DENY, not a rewrite: a wrong cwd in a rewritten rm deletes the wrong
# directory, where a deny costs one round trip and the session types the
# absolute path itself. Left alone on purpose: a glob of the working
# directory itself (`rm -rf /cwd/*` halts too — a workspace guard working as
# designed, not a parse limit, so there is nothing to coach round).

_RM_TRAILING_GLOB = re.compile(r"(?:/\*+)+/*$")
_RM_GLOB_CHARS = re.compile(r"[*?[]")
_RM_GLOB_TAG = "[traps.md: unresolvable rm glob]"


def rm_glob_breaker(cmd: str, cwd: str = "") -> str | None:
    """Deny note when an rm/rmdir target is a glob CC cannot resolve."""
    if "rm" not in cmd or _too_long(cmd):
        return None
    cur: str | None = cwd or None  # where relative paths land, if we know
    blind_cd = False  # a cd CC's check cannot follow has run
    for seg in _shell_segments(cmd):
        argv = _argv(seg)
        if not argv:
            continue
        name = os.path.basename(argv[0])
        if name in ("cd", "pushd"):
            args = [a for a in argv[1:] if a != "--"]
            t = args[0] if args else "~"
            if t.startswith("-") or "$" in t or "`" in t:
                cur = None  # CC tracks assigned variables (probe 14); we don't
                continue
            t = os.path.expanduser(t)
            if os.path.isabs(t):
                if os.path.isdir(t):
                    cur = os.path.normpath(t)
                else:
                    cur, blind_cd = None, True
            else:
                blind_cd = True
                cur = os.path.join(cur, t) if cur else None
            continue
        if name not in ("rm", "rmdir"):
            continue
        opts_done = False
        for a in argv[1:]:
            if not opts_done and a == "--":
                opts_done = True
                continue
            if (not opts_done and a.startswith("-") and a != "-") \
                    or "$" in a or "`" in a:
                continue
            p = os.path.expanduser(a)
            absolute = os.path.isabs(p)
            # CC joins a relative target to the cwd first, so a bare `*`
            # ends in /* too.
            if not _RM_TRAILING_GLOB.search(p if absolute else "/" + p):
                continue
            parts = [x for x in p.split("/") if x]
            if ".." in parts:
                why = "it holds a `..` segment"
            elif sum(1 for x in parts if _RM_GLOB_CHARS.search(x)) > 1:
                why = "it globs more than one directory level"
            elif blind_cd and not absolute:
                why = "it is relative and follows a `cd` the check cannot follow"
            else:
                continue
            return _rm_glob_note(a, p, why, cur, cwd)
    return None


def _rm_glob_note(arg: str, p: str, why: str, cur: str | None, cwd: str) -> str:
    """The deny text, with the resolved absolute path when it is knowable."""
    hint = ""
    full = p if os.path.isabs(p) else (os.path.join(cur, p) if cur else None)
    if full and "more than one" not in why:
        m = _RM_TRAILING_GLOB.search(full)
        head = full[:m.start()] if m else full
        real = os.path.realpath(head or "/")
        home = os.path.realpath(cwd) if cwd else ""
        if os.path.isdir(real) and home and (
                real == home or home.startswith(real.rstrip("/") + "/")):
            hint = (f" It resolves to `{real}/*`, which is the working "
                    "directory or one of its parents — a separate guard "
                    "halts that even when absolute, so name the entries "
                    "to remove instead, or park the step.")
        elif os.path.isdir(real):
            hint = (f" From here it resolves to `{real.rstrip('/')}/*` — check "
                    "that is the directory you meant, then use that.")
    elif "more than one" in why:
        hint = (" List the first level yourself (`ls -d /abs/dir/*/`) and "
                "pass each directory's own absolute `/*`.")
    return (
        f"goûteur: `rm` target `{arg}` is a glob Claude Code's dangerous-removal "
        f"check cannot resolve ({why}). That check is a circuit breaker bypass "
        "mode cannot override: the call halts on a human dialog, which stalls "
        "a Paseo chat or an Agent worker until someone clicks. Use one "
        "absolute path with a single trailing glob (`rm -rf /abs/dir/*` "
        f"passes).{hint} {_RM_GLOB_TAG}"
    )


# --- PreToolUse: relative paths after a cd ---------------------------------
#
# Read from the CC 2.1.259 binary, 2026-09-03 (carte-sikoce): when ANY
# Read() deny rule is configured, a Bash command that runs one of
# grep/egrep/fgrep/rg/diff/git/cp/mv AFTER a `cd`, with a RELATIVE file
# argument, is escalated to a human "ask" — the analyser does not track the
# cd, so it cannot prove the path lies outside a denied one. Absolute and
# `~` paths resolve and pass. The ask lands on a human's terminal from
# subagents that cannot answer it and stalls for hours. Asked what they
# would want as the calling Claude, the maintainer chose "it just works, and tell me it
# did" over deny-with-coaching (a per-session tax that teaches nothing
# durable) and over the silent pause. So this is a REWRITE with a one-line
# note, not a deny: resolve the paths CC would not, hand the command back
# with them absolute, and say so beside the result.
#
# Precision over reach: every doubt returns None, which leaves CC's own
# prompt in place — exactly today's behaviour, never worse. Only the pure
# readers are rewritten. cp/mv are writes an "allow" would over-approve in
# default mode, and cd+git prompts on a separate CC rule (repo hooks) that
# a path rewrite cannot satisfy.

_CD_REWRITE_CMDS = ("grep", "egrep", "fgrep", "rg", "diff")

# Options whose VALUE is the next token — that token is never a path.
_CD_REWRITE_VALUE_OPTS = {
    "grep": {"-e", "-f", "-m", "-A", "-B", "-C", "-d", "-D", "--include",
             "--exclude", "--exclude-dir", "--regexp", "--file",
             "--max-count", "--context", "--after-context",
             "--before-context", "--color", "--colour"},
    "rg": {"-e", "-f", "-g", "-t", "-T", "-j", "-M", "-E", "-r", "-m",
           "-A", "-B", "-C", "--regexp", "--file", "--glob", "--iglob",
           "--type", "--type-not", "--type-add", "--max-count",
           "--context", "--after-context", "--before-context",
           "--encoding", "--replace", "--color", "--colors",
           "--max-columns", "--max-depth", "--max-filesize", "--threads",
           "--sort", "--sortr", "--pre", "--pre-glob"},
    "diff": {"-U", "-W", "-I", "-x", "-X", "-S", "-F", "-L", "-C",
             "--unified", "--width", "--ignore-matching-lines",
             "--exclude", "--exclude-from", "--starting-file", "--label",
             "--context", "--color", "--tabsize"},
}
_CD_REWRITE_VALUE_OPTS["egrep"] = _CD_REWRITE_VALUE_OPTS["grep"]
_CD_REWRITE_VALUE_OPTS["fgrep"] = _CD_REWRITE_VALUE_OPTS["grep"]

# Long options known to take NO value. A `--long` option in neither table is
# unknowable — treating it as a flag shifted the pattern into the path slot
# (`rg --ignore-file .gitignore foo src` rewrote `foo`; twin review
# 2026-09-06, carte-visoce) — so it declines. Short options stay assumed
# flag-only unless in the value table: the cluster grammar makes a stray
# value there far rarer.
_CD_REWRITE_FLAG_OPTS = {
    "grep": {"--recursive", "--dereference-recursive", "--line-number",
             "--no-line-number", "--ignore-case", "--no-ignore-case",
             "--count", "--files-with-matches", "--files-without-match",
             "--fixed-strings", "--extended-regexp", "--perl-regexp",
             "--basic-regexp", "--word-regexp", "--line-regexp",
             "--invert-match", "--only-matching", "--quiet", "--silent",
             "--no-messages", "--with-filename", "--no-filename", "--null",
             "--null-data", "--text", "--byte-offset", "--line-buffered",
             "--initial-tab", "--help", "--version"},
    "rg": {"--no-ignore", "--no-ignore-vcs", "--no-ignore-dot",
           "--no-ignore-global", "--no-ignore-parent", "--no-ignore-files",
           "--hidden", "--line-number", "--no-line-number", "--ignore-case",
           "--smart-case", "--case-sensitive", "--fixed-strings",
           "--word-regexp", "--line-regexp", "--invert-match", "--count",
           "--count-matches", "--files", "--files-with-matches",
           "--files-without-match", "--only-matching", "--quiet",
           "--heading", "--no-heading", "--with-filename", "--no-filename",
           "--null", "--null-data", "--json", "--no-messages", "--multiline",
           "--multiline-dotall", "--pcre2", "--no-config", "--follow",
           "--trim", "--vimgrep", "--stats", "--debug", "--trace", "--text",
           "--binary", "--search-zip", "--sort-files", "--no-require-git",
           "--one-file-system", "--unrestricted", "--passthru", "--column",
           "--no-column", "--byte-offset", "--crlf", "--pretty",
           "--block-buffered", "--line-buffered", "--no-unicode",
           "--max-columns-preview", "--help", "--version"},
    "diff": {"--brief", "--report-identical-files", "--recursive",
             "--new-file", "--unidirectional-new-file", "--ignore-case",
             "--ignore-tab-expansion", "--ignore-trailing-space",
             "--ignore-space-change", "--ignore-all-space",
             "--ignore-blank-lines", "--text", "--strip-trailing-cr",
             "--side-by-side", "--left-column", "--suppress-common-lines",
             "--expand-tabs", "--initial-tab", "--minimal",
             "--speed-large-files", "--normal", "--no-dereference",
             "--ignore-file-name-case", "--no-ignore-file-name-case",
             "--help", "--version"},
}
_CD_REWRITE_FLAG_OPTS["egrep"] = _CD_REWRITE_FLAG_OPTS["grep"]
_CD_REWRITE_FLAG_OPTS["fgrep"] = _CD_REWRITE_FLAG_OPTS["grep"]

# No path is this long; shlex is quadratic in a single token's length and an
# 800 KB base64 argument (the estate's own armouring idiom) stalled --pre for
# 20-33 s (twin review 2026-09-06).
_CD_REWRITE_MAX_TOKEN = 1024


def _too_long(cmd: str) -> bool:
    return max(map(len, cmd.split()), default=0) > _CD_REWRITE_MAX_TOKEN

# Grep-family and rg: the first positional is the PATTERN unless one of
# these supplied it (bare, or as the last letter of a short cluster).
_CD_REWRITE_PATTERN_OPTS = {"-e", "-f", "--regexp", "--file"}

# Shapes the tokeniser cannot be trusted on: subshells, substitutions,
# heredocs, backgrounding. `>&`/`&>`/`2>&1` redirects are fine.
_CD_REWRITE_BAIL = re.compile(r"`|\$\(|<<|[()]|\n|\\|(?<![&|><])&(?![&>|])")
_CD_REWRITE_SEPARATORS = {"&&", "||", "|", ";"}
_CD_REWRITE_REDIRECTS = {">", ">>", "<", ">&", "&>", "<&", ">|", "&>>"}

# First words that cannot change state — an "allow" over a compound made
# only of these approves nothing a default-mode session would have asked
# about. Anything else in the compound restricts the allow to bypass mode.
_CD_REWRITE_READONLY = {
    "cd", "grep", "egrep", "fgrep", "rg", "diff", "cat", "head", "tail",
    "wc", "sort", "uniq", "cut", "tr", "echo", "ls", "pwd", "less", "more",
    "column", "nl", "tac", "rev", "file", "stat", "du", "which", "type",
    "true", "false", "test", "[", "printf", "basename", "dirname",
    "realpath", "readlink", "date", "hostname", "whoami", "id", "env",
    "jq", "yq", "md5sum", "sha256sum", "cksum", "comm", "paste", "join",
    "fold", "fmt", "expand", "unexpand", "strings", "od", "xxd", "hexdump",
    "zcat", "zgrep", "bzcat", "xzcat",
}
# Read-only first words that still write when given one of these options.
_CD_REWRITE_WRITE_OPTS = {"sort": ("-o", "--output")}
# Redirect targets that write nothing anyone would be asked about.
_CD_REWRITE_SINK_TARGETS = {"/dev/null", "/dev/stdout", "/dev/stderr"}


def _config_dir() -> str:
    return os.path.expanduser(os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude")


def _settings_deny(cwd: str) -> list[tuple[str, str]]:
    """(rule, settings file) for every permissions.deny entry in the files CC
    merges: user, and the cwd's project and project-local. A file that is
    missing or unparsable contributes nothing (CC would refuse to load a
    broken one anyway, and this must never crash the --pre gate)."""
    paths = [os.path.join(_config_dir(), "settings.json")]
    if cwd:
        paths += [os.path.join(cwd, ".claude", "settings.json"),
                  os.path.join(cwd, ".claude", "settings.local.json")]
    out: list[tuple[str, str]] = []
    for p in dict.fromkeys(os.path.normpath(x) for x in paths):
        try:
            with open(p, encoding="utf-8") as fh:
                perms = json.load(fh).get("permissions") or {}
        except (OSError, ValueError, AttributeError):
            continue
        deny = perms.get("deny") if isinstance(perms, dict) else None
        if isinstance(deny, list):
            out += [(r, p) for r in deny if isinstance(r, str)]
    return out


def _read_deny_rules(cwd: str) -> list[str]:
    """The Read(...) deny rules from the settings files CC merges (user,
    project, local). CC's safety check runs only when at least one exists —
    mirror that, so the rewrite never fires where no prompt would."""
    rules: list[str] = []
    user = os.path.normpath(os.path.join(_config_dir(), "settings.json"))
    for r, src in _settings_deny(cwd):
        if r == "Read":
            rules.append("**")
        elif r.startswith("Read(") and r.endswith(")"):
            body = r[5:-1]
            if body.startswith("/") and not body.startswith("//") and os.path.normpath(src) != user:
                # A project or project-local file's `/path` is anchored at
                # that project, not the user config dir. Which of its two
                # plausible anchors CC means (the project root or the .claude
                # directory holding the file) is not settled here, so both
                # are emitted as absolute rules: an over-match only declines
                # a rewrite and leaves CC's own prompt.
                claude_dir = os.path.dirname(os.path.abspath(src))
                for base in (os.path.dirname(claude_dir), claude_dir):
                    rules.append("//" + os.path.join(base, body.lstrip("/")).lstrip("/"))
            else:
                rules.append(body)
    return rules


# --- PreToolUse: settings.json Bash deny rules, spoken (carte-ratenu) ------
#
# A settings.json deny refuses with NO reason, and the reading session
# guesses. Twice in two days: `pgrep -f` (2026-09-29, three round trips,
# blamed on osascript) and `git add -A` (28-30 Sep, three days blamed on a
# content classifier, carte-habena). A PreToolUse hook runs before the
# permission rules, so goûteur matches the same rules first and denies with
# the rule, the file it lives in, and why it exists. The settings rule stays
# as the backstop: if this matcher misses a shape, CC's mute deny still
# fires, which is exactly the behaviour before this existed.
#
# Matching mirrors CC's documented grammar, per simple command of a
# compound: `*` is any run of characters, a trailing `:*` is the legacy
# prefix form, and leading VAR=val and process wrappers are stripped. Where
# it is unsure it under-matches, because an over-match is a deny CC would
# not have made.

# Why each rule exists, in one clause the reader can act on. A rule absent
# here still speaks: the generic reason names the rule and how to find the
# commit that added it.
DENY_RULE_REASONS = {
    "Bash(pkill -f*)": (
        "`pkill -f` can signal the session that runs it — the harness "
        "wrapper, and over ssh the remote shell and tailscaled. Kept as a "
        "backstop even for anchored patterns: find the PID first "
        "(`pgrep -f '^/path'` or `pidof`), read it, then `kill PID`."),
}


def deny_rule_reasons() -> dict:
    merged = dict(DENY_RULE_REASONS)
    for extra in _ext_attr("DENY_RULE_REASONS"):
        merged.update(extra)
    return merged


_SETTINGS_DENY_NOTE = (
    "goûteur: this matches the settings.json deny rule `{rule}` (in {path}) "
    "on the subcommand `{seg}`. A settings deny refuses with no reason, so "
    "goûteur says it first. Why the rule exists: {why} The rule is the "
    "human's; do not route around it with another spelling — use the "
    "remedy, or ask. [traps.md: settings deny rules]"
)


def _bash_rule_matches(pattern: str, seg: str) -> bool:
    """One CC Bash(...) rule body against one simple command."""
    seg = re.sub(r"\s+", " ", seg.strip())
    if pattern.endswith(":*"):
        base = pattern[:-2].rstrip()
        return seg == base or seg.startswith(base + " ")
    rx = "".join(".*" if ch == "*" else re.escape(ch) for ch in pattern)
    if pattern.endswith(" *"):
        # `ls *` also admits a bare `ls` in CC's grammar.
        if seg == pattern[:-2].rstrip():
            return True
    return re.fullmatch(rx, seg, re.DOTALL) is not None


def probe_settings_deny(cmd: str, cwd: str = "",
                        rules: list[tuple[str, str]] | None = None) -> str | None:
    """Deny note when a subcommand matches a settings.json Bash deny rule."""
    if rules is None:
        rules = _settings_deny(cwd)
    bash = [(r[5:-1], r, p) for r, p in rules
            if r.startswith("Bash(") and r.endswith(")")]
    # Cheap first: a rule can only match if its longest literal piece is in
    # the command, and on almost every call none is, so skip the parse.
    bash = [t for t in bash
            if max(t[0].replace(":*", "*").split("*"), key=len).strip() in cmd]
    if not bash:
        return None
    home = os.path.expanduser("~")
    for seg in _shell_segments(cmd):
        argv = _argv(seg)
        # The raw segment and the one with assignments/wrappers stripped:
        # either is how CC may present the subcommand to the rule.
        forms = [seg]
        if argv:
            forms.append(" ".join(shlex.quote(w) if " " in w else w for w in argv))
        for body, rule, path in bash:
            for form in forms:
                if _bash_rule_matches(body, form):
                    why = deny_rule_reasons().get(rule) or (
                        "goûteur has no reason recorded for this rule "
                        "(a gouteur.d extension can give one in DENY_RULE_REASONS); "
                        f"`git -C {os.path.dirname(path)} log -S '{rule}' "
                        f"-- {os.path.basename(path)}` finds the commit that "
                        "added it.")
                    shown = path.replace(home, "~", 1) if path.startswith(home) else path
                    return _SETTINGS_DENY_NOTE.format(
                        rule=rule, path=shown, seg=form[:160], why=why)
    return None


def _under_read_deny(path: str, rules: list[str]) -> bool:
    """True when PATH plausibly falls under a Read deny rule. Deliberately
    over-matches: a wrong True declines the rewrite and leaves CC's prompt,
    a wrong False would hand a denied path back as 'resolved'."""
    for r in rules:
        if r == "**":
            return True
        if r.startswith("//"):
            base = "/" + r.lstrip("/")
        elif r.startswith("~"):
            base = os.path.expanduser(r)
        elif r.startswith("/"):
            base = os.path.join(_config_dir(), r.lstrip("/"))
        else:
            # cwd-relative shapes match a directory of that name at any
            # depth (deny semantics) — test the tail rather than a root.
            # Strip a leading `./` only — `.lstrip("./")` ate the dot of
            # `.env` and `.git/**`, so those rules never matched (twin
            # review 2026-09-06, carte-visoce).
            tail = re.sub(r"^(?:\./)+", "", r).rstrip("/")
            tail = tail[:-3] if tail.endswith("/**") else tail
            if fnmatch.fnmatch(path, "*/" + tail) or fnmatch.fnmatch(path, "*/" + tail + "/*"):
                return True
            continue
        base = base.rstrip("/")
        base = base[:-3] if base.endswith("/**") else base
        if (path == base or path.startswith(base + "/")
                or fnmatch.fnmatch(path, base) or fnmatch.fnmatch(path, base + "/*")):
            return True
    return False


def _unquote(tok: str) -> tuple[str, str]:
    """Split a non-posix shlex token into (quote, inner)."""
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in "\"'":
        return tok[0], tok[1:-1]
    return "", tok


def rewrite_after_cd(cmd: str, cwd: str,
                     deny_rules: list[str] | None = None) -> tuple[str, str, bool] | None:
    """Resolve relative file arguments of grep/rg/diff that follow a `cd`.

    Returns (new_command, note, read_only) or None when nothing should
    change. read_only says whether every segment's first word is a known
    non-mutating command, which decides whether an "allow" is safe outside
    bypass mode. Any doubt returns None — CC's own prompt is the fallback.
    """
    # Cheap tests first: the cd check is a regex and 99% of Bash calls have
    # no cd, so the three settings-file parses only run when one does.
    if not re.search(r"(?:^|[\s;&|])cd(?:\s|$)", cmd):
        return None
    if _CD_REWRITE_BAIL.search(cmd) or _too_long(cmd):
        return None
    if deny_rules is None:
        deny_rules = _read_deny_rules(cwd)
    if not deny_rules:
        return None
    try:
        lex = shlex.shlex(cmd, posix=False, punctuation_chars=True)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        return None
    # Coverage: the tokens must account for every non-blank byte, or the
    # splice below would be aimed at the wrong text.
    if re.sub(r"\s+", "", "".join(tokens)) != re.sub(r"\s+", "", cmd):
        return None
    positions: list[int] = []
    cursor = 0
    for t in tokens:
        i = cmd.find(t, cursor)
        if i < 0:
            return None
        positions.append(i)
        cursor = i + len(t)

    # Split into segments on the separators; every other punctuation run
    # must be a redirect we understand.
    segments: list[list[int]] = [[]]
    joiners: list[str] = [""]  # the separator that introduced each segment
    for i, t in enumerate(tokens):
        if t in _CD_REWRITE_SEPARATORS:
            segments.append([])
            joiners.append(t)
        elif lex.punctuation_chars and t and all(c in lex.punctuation_chars for c in t):
            if t not in _CD_REWRITE_REDIRECTS:
                return None
            segments[-1].append(i)
        else:
            segments[-1].append(i)

    cur = cwd or os.getcwd()
    cd_seen = False
    read_only = True
    edits: list[tuple[int, str, str]] = []
    for seg, joiner in zip(segments, joiners):
        # `cd X || cmd` runs cmd only when the cd FAILED, so resolving its
        # paths against X is the wrong directory — decline (garebi).
        if cd_seen and joiner == "||":
            return None
        # Drop redirect operators, their targets, and a leading fd digit.
        words: list[int] = []
        skip_next = False
        for k, i in enumerate(seg):
            t = tokens[i]
            if skip_next:
                skip_next = False
                continue
            if t in _CD_REWRITE_REDIRECTS:
                skip_next = True
                if words and tokens[words[-1]].isdigit() and positions[words[-1]] + len(tokens[words[-1]]) == positions[i]:
                    words.pop()
                # A redirect that writes a real file is a write the session
                # would have been asked about; `2>&1` and `>/dev/null` are not.
                target = tokens[seg[k + 1]] if k + 1 < len(seg) else ""
                fd_dup = target.isdigit() or target.startswith("&")  # 2>&1, >&2
                if (">" in t and not fd_dup
                        and _unquote(target)[1] not in _CD_REWRITE_SINK_TARGETS):
                    read_only = False
                continue
            words.append(i)
        if not words:
            continue
        name = tokens[words[0]]
        if name not in _CD_REWRITE_READONLY:
            read_only = False
        elif name in _CD_REWRITE_WRITE_OPTS and any(
                tokens[i].split("=", 1)[0] in _CD_REWRITE_WRITE_OPTS[name] for i in words[1:]):
            read_only = False
        if name == "cd":
            args = [tokens[i] for i in words[1:]]
            if not args:
                target = os.path.expanduser("~")
            elif len(args) == 1 and not args[0].startswith("-") and "$" not in args[0]:
                _, inner = _unquote(args[0])
                if inner.startswith("~"):
                    target = os.path.expanduser(inner)
                elif os.path.isabs(inner):
                    target = inner
                else:
                    target = os.path.join(cur, inner)
            else:
                return None
            target = os.path.normpath(target)
            if not os.path.isdir(target):
                return None
            cur = target
            cd_seen = True
            continue
        if not cd_seen or name not in _CD_REWRITE_CMDS:
            continue
        value_opts = _CD_REWRITE_VALUE_OPTS[name]
        flag_opts = _CD_REWRITE_FLAG_OPTS[name]
        pattern_taken = name == "diff"
        opts_done = False
        k = 1
        while k < len(words):
            i = words[k]
            t = tokens[i]
            if not opts_done and t == "--":
                opts_done = True
            elif not opts_done and t.startswith("-") and t != "-":
                bare = t.split("=", 1)[0]
                has_eq = "=" in t
                if (bare.startswith("--") and not has_eq
                        and bare not in value_opts and bare not in flag_opts):
                    return None  # unknowable: value or flag?
                if bare in _CD_REWRITE_PATTERN_OPTS or (
                        not bare.startswith("--") and len(bare) > 2 and bare[-1] in "ef"):
                    pattern_taken = True
                if not has_eq and (bare in value_opts or (
                        not bare.startswith("--") and len(bare) > 2
                        and "-" + bare[-1] in value_opts)):
                    k += 1  # the value rides along
            elif not pattern_taken:
                pattern_taken = True
            else:
                q, inner = _unquote(t)
                if (inner and not inner.startswith(("/", "~", "-"))
                        and not any(c in inner for c in "$*?[{}")):
                    full = os.path.normpath(os.path.join(cur, inner))
                    if os.path.exists(full):
                        if _under_read_deny(full, deny_rules):
                            return None
                        edits.append((positions[i], t, q + full + q))
            k += 1
    if not edits:
        return None
    new = cmd
    for pos, old, rep in sorted(edits, reverse=True):
        new = new[:pos] + rep + new[pos + len(old):]
    shown = ", ".join(f"{_unquote(o)[1]} → {_unquote(r)[1]}" for _, o, r in edits[:3])
    if len(edits) > 3:
        shown += f", +{len(edits) - 3} more"
    n = len(edits)
    note = (
        f"goûteur rewrote {n} relative path{'s' if n > 1 else ''} after `cd` to "
        f"absolute ({shown}): Claude Code's Read-deny safety check cannot resolve "
        "a relative path after a cd and would have stalled on a human dialog. "
        "Output paths are absolute accordingly. Skip the cd and pass absolute "
        "paths to avoid the round trip. [traps.md: relative path after a bare cd]"
    )
    return new, note, read_only


# --- PermissionRequest: shape-only census of residual dialogs ---------------
#
# carte-datoje (2026-09-04): the rewrite above covers grep/rg/diff. Whether
# cp/mv/git after a cd still stall anyone is unknown, because a dialog that
# fired leaves no trace in anything we read. This logs the SHAPE of every
# permission request — never the command text (same secret-bearing-log rule
# as log_fires) — and returns no decision, so the permission flow is exactly
# what it was.

# GOUTEUR_STATE_DIR redirects both logs — the self-test sets it so its e2e
# subprocess runs never write fixture rows into the real census (cold-read
# finding on carte-sikoce's close: five self-test runs had left 15 `s-1`
# rows under a live render id, in the very log the proof method counts).
_PERMS_LOG = os.path.join(
    os.environ.get("GOUTEUR_STATE_DIR") or os.path.expanduser("~/.local/state/gouteur"),
    "perms.jsonl")
_PERM_PATH_CMDS = ("grep", "egrep", "fgrep", "rg", "diff", "git", "cp", "mv")


def perm_shape(cmd: str) -> dict:
    """First word of each segment, plus whether a cd precedes a command from
    CC's Read-check set carrying a relative (non -, /, ~) argument.

    Only command NAMES are recorded: a `VAR=value` prefix is skipped (its
    first token IS the value — a token was one call from this mode-644 log,
    twin review 2026-09-06) and a path-shaped name is reduced to its basename.
    """
    if _too_long(cmd):
        return {"parse": "too-long"}
    # A heredoc body is data, not commands: unstripped, its words were logged
    # as segment heads (`c['source']`, `Opus`, `}` in the 2026-09..11 rows).
    cmd = _drop_heredoc_bodies(cmd)
    try:
        # An unquoted newline ends a command as `;` does; as whitespace it
        # hid every segment head after the first line.
        lex = shlex.shlex(cmd, posix=False, punctuation_chars="();<>|&\n")
        lex.whitespace = " \t\r"
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        return {"parse": "failed"}
    firsts: list[str] = []
    cd_seen = False
    cd_relative = False
    new_seg = True
    for t in tokens:
        if t in _CD_REWRITE_SEPARATORS or (t and set(t) <= {"\n", ";"}):
            new_seg = True
            continue
        if all(c in lex.punctuation_chars for c in t):
            continue
        if new_seg:
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t):
                continue  # env assignment: stay at the segment start
            cur = os.path.basename(_unquote(t)[1]) or t
            firsts.append(cur)
            new_seg = False
            if cur == "cd":
                cd_seen = True
            continue
        if cd_seen and cur in _PERM_PATH_CMDS and not t.startswith(("-", "/", "~")):
            cd_relative = True
    return {"firsts": firsts[:12], "cd_then_relative": cd_relative}


def log_perm(data: dict) -> None:
    """Append one shape record. Never raises."""
    try:
        tool = data.get("tool_name") or ""
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tool": tool,
            "mode": data.get("permission_mode") or "",
            "agent": "agent_id" in data or "agent_type" in data,
            "session_id": data.get("session_id") or "",
        }
        if tool == "Bash":
            cmd = (data.get("tool_input") or {}).get("command", "")
            rec.update(perm_shape(str(cmd)))
            # Did this dialog match the rm-glob deny? True here means the
            # deny missed it; a dialog with rm in `firsts` and False here is
            # some other breaker (carte-datoje).
            # Its own guard: the outer catch-all would drop the whole row
            # silently, and a thin census would read as "no misses".
            try:
                rec["rm_glob"] = rm_glob_breaker(str(cmd), data.get("cwd") or "") is not None
            except Exception as exc:  # noqa: BLE001 — recorded in the row
                rec["rm_glob"] = f"crash: {type(exc).__name__}"
        os.makedirs(os.path.dirname(_PERMS_LOG), exist_ok=True)
        with open(_PERMS_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        return


# --- PostToolUse: Bash -----------------------------------------------------

def _scannable(cmd: str) -> str:
    """Reduce a command to the text where a tool NAME can actually be invoked.

    Two false-positive classes measured live on 2026-08-02, both from
    meta-work (commands that talk ABOUT commands): a citation string
    'rg -r' inside a python heredoc, and tool names inside quoted prose.
    Heredoc bodies and quoted spans cannot invoke anything, so name
    detection scans the command with both removed. Over-stripping (an
    unbalanced apostrophe) errs toward silence, which is the right
    direction — a render that fires wrongly is a distractor.
    """
    head = cmd.split("<<", 1)[0]
    return re.sub(r"'[^']*'|\"[^\"]*\"", " ", head)


# A tool name counts as invoked only at a command position: start of string
# or after whitespace / ; | & ( — not mid-word, mid-path, or mid-quote.
def _invoked(name: str, scan: str) -> bool:
    return re.search(rf"(?:^|[\s;|&(]){name}\s", scan) is not None


# ssh options that take a value as the NEXT token (ssh(1) synopsis). The old
# `(?:-\S+\s+)*` swallowed the flag and read its VALUE as the host, so
# `ssh -p 22 tube` never matched tube (garebi, 2026-09-06).
_SSH_VALUE_OPTS = set("BbcDEeFIiJLlmOopQRSWw")


def _ssh_target(args: str) -> str:
    """The host token of an ssh argument string, or '' when none is found."""
    words = args.split()
    k = 0
    while k < len(words):
        w = words[k]
        if w.startswith("-") and len(w) > 1:
            if len(w) == 2 and w[1] in _SSH_VALUE_OPTS:
                k += 1  # value rides along
        else:
            return w
        k += 1
    return ""


def _grep_recursive_hazard(scan: str) -> bool:
    """True when some sub-command runs the WRAPPED grep with -r/-R/--recursive.

    Judged per sub-command (split on | ; & ( ) and newlines) and only on the
    tokens AFTER the grep word. The
    old command-wide regex indicted a clean grep for another tool's -r — the
    three shapes caught by running a second model against probe() as an oracle were
    `xargs -r kill`, `jq -r` in a later segment, and the r inside find's
    `-newermt` (aug-nasami, 2026-09-21). `command grep` is GNU grep, not the
    ugrep wrapper, so it never counts.
    """
    for sub in re.split(r"[|;&()\n]+", scan):
        toks = sub.split()
        if "grep" not in toks:
            continue
        i = toks.index("grep")
        if i > 0 and toks[i - 1] == "command":
            continue
        for tok in toks[i + 1:]:
            if re.match(r"-[a-zA-Z]*[rR]", tok) or re.match(r"--(?:dereference-)?recursive$", tok):
                return True
    return False


def _mask_quotes(text: str) -> str:
    """Same-length copy of TEXT with every quoted span made inert.

    Quote marks become \x01 and the separators inside a span (whitespace,
    ; & | < > ( ) #) become \x00, so a quoted mention can neither sit at a
    command position nor split a segment — and every offset still indexes
    the raw text, which is what lets a nested ssh or `sh -c` payload be cut
    out of the original and read one quote layer down. Shell comments are
    blanked the same way.
    """
    def inert(m: "re.Match[str]") -> str:
        body = re.sub(r"[\s;&|<>()#]", "\x00", m.group(0)[1:-1])
        return "\x01" + body + "\x01"
    masked = re.sub(r"'[^']*'|\"[^\"]*\"", inert, text)
    return re.sub(r"(?m)(^|\s)#[^\n]*",
                  lambda m: m.group(1) + "\x00" * (len(m.group(0)) - len(m.group(1))), masked)


def _unmask(text: str) -> str:
    return text.replace("\x01", "").replace("\x00", " ")


def probe(
    cmd: str,
    stdout: str,
    stderr: str,
    cwd: str = "",
    permission_mode: str = "",
) -> list[str]:
    """Return renders for this command+output. Empty list = stay silent."""
    # Extension notes go first: probe() keeps two, and a personal render is
    # usually the one whose miss costs most on its own estate (a settings
    # change that reaches every machine sharing a config repo, say).
    notes = _ext_call("post_bash", cmd, stdout, stderr, cwd)
    null_result = len(stdout.strip()) < 3
    scan = _scannable(cmd)

    # traps.md: "A recursive grep returning nothing in Claude Code Bash"
    # In-harness grep is a ugrep wrapper: respects ignore files by default,
    # rejects rg-only flags (exit 2), skips .gz — all three read as absence.
    if null_result and _grep_recursive_hazard(scan):
        notes.append(
            "goûteur: null from in-harness `grep` — it is a ugrep wrapper: honours "
            "ignore files by default, rejects rg-only flags (exit 2), skips .gz. "
            "Before reading this as absence, re-run with `command grep -r` (zgrep for "
            ".gz) and compare — not bare `rg`, which honours .gitignore too, even on a "
            "directory you name. [traps.md: recursive grep]"
        )

    # traps.md: "find returning nothing in Claude Code Bash" — in-harness
    # find is bfs; -newermt rejects comma-decimal timestamps loudly, and a
    # 2>/dev/null converts that into a silent empty result.
    if (null_result and _invoked("find", scan) and "-newermt" in scan
            and not re.search(r"\bcommand\s+find\b", scan)):
        notes.append(
            "goûteur: null from in-harness `find` with -newermt — it is a bfs wrapper "
            "that rejects fractional timestamps (loudly, unless 2>/dev/null ate it). "
            "Use whole-second timestamps or `command find`. [traps.md: find/bfs]"
        )

    # traps.md: "git mv on the directory you're cd'd into" — the harness
    # chdirs to the recorded cwd before every Bash call; once that path is
    # renamed, every subsequent call fails with "Path does not exist."
    m = re.search(r"(?:^|[\s;|&(])git\s+mv\s+([^&|;]+)", scan)
    if m and cwd:
        args = [a for a in m.group(1).split() if not a.startswith("-")]
        if len(args) >= 2:
            # The mv source resolves against the shell's directory at mv time,
            # which a `cd` earlier in the compound changes — track the last one.
            effective_dir = cwd
            for cd_m in re.finditer(r"(?:^|&&|\|\||;)\s*cd\s+([^\s;&|]+)", scan[: m.start()]):
                effective_dir = os.path.join(
                    effective_dir, os.path.expanduser(cd_m.group(1).strip("'\""))
                )
            src = os.path.abspath(
                os.path.join(effective_dir, os.path.expanduser(args[0].strip("'\"")))
            )
            here = os.path.abspath(cwd)
            if here == src or here.startswith(src + os.sep):
                notes.append(
                    "goûteur: that `git mv` moved the directory this session is "
                    "cd'd into — the harness re-enters the OLD path before every "
                    "Bash call, so subsequent shell calls will fail. Finish file "
                    "work with Read/Write/Edit and defer bash to a fresh session. "
                    "[traps.md: git mv on cwd]"
                )

    # traps.md: "A compound Bash command touching a settings*.json under a
    # .claude/ directory" — CC gates the touch (a pure read prompts as a
    # WRITE, and the bare Bash allow does not cover it), and the dialog's
    # "don't ask again" mints the ENTIRE compound as allow rules, one per
    # subcommand — the source of ~165 junk rules swept 2026-08-14.
    # bypassPermissions runs no permission machinery and mints nothing
    # (measured 2026-08-16, CC 2.1.233), so the render arms only outside it;
    # an ABSENT mode field errs toward rendering.
    # Path test per SEGMENT on the raw text (quotes kept — `"$HOME/…"` is the
    # common spelling), skipping echo/printf segments so prose about settings
    # files stays quiet.
    _settings_touch = any(
        re.search(r"\.claude/settings[^/\s'\"]*\.json(?![\w.])", seg)
        and (seg.split() or [""])[0] not in ("echo", "printf")
        for seg in re.split(r"[;|&\n]+", cmd.split("<<", 1)[0])
    )
    if (
        permission_mode != "bypassPermissions"
        and re.search(r"[;|&\n]", scan)
        and _settings_touch
    ):
        notes.append(
            "goûteur: this compound command touched a `.claude` settings file — "
            "CC gates those, and the permission dialog's 'don't ask again' mints "
            "one allow rule per SUBCOMMAND (one machine collected 165 junk rules "
            "this way). If a dialog was just answered, check the project's "
            ".claude/settings.local.json for shrapnel; keep settings-file "
            "touches in their own command. [traps.md: settings-file shred]"
        )

    # traps.md: "Taking down a world-shared Drive file by trashing it" — a
    # trashed file still serves its full content to the anonymous public
    # (HTTP 200 from the bin, measured twice 2026-08-31); only files.delete
    # or moving it out of the granting folder revokes. Bash face: a Drive
    # API body setting trashed true (JSON or a python dict — the quoted key
    # with a colon; a `q='trashed = true'` LISTING uses `=` and stays
    # silent). The mise `do(operation="trash")` face is probe_mcp_do().
    if re.search(r"[\"']trashed[\"']\s*:\s*[Tt]rue", cmd) and re.search(
        r"drive|googleapis|files\(\)", cmd, re.I
    ):
        notes.append(_DRIVE_TRASH_NOTE)

    # RETIRED 2026-11-08 (goûteur moved into batterie; dot-claude-tipuce's
    # sort): rg -r as --replace, jq null for a missing key, xargs without -r,
    # `xargs command`, a pipeline's status consumed by its filter, csv
    # DictReader duplicate headers, detached HEAD, git worktree add, git add
    # under an ignored directory, git add with a stale pathspec, a divergence
    # count off an unfetched ref, and the silenced-stderr null. All general
    # command-line knowledge: the banc corpus ablation (27 Sep 2026) found
    # Opus 5.5 handles this class with no guidance at all, and together they
    # were ~half of all fires, so their false positives were the channel's
    # main noise. Their ids stay in RETIRED so old fires logs still read.
    # A personal scoped-search render went the same way on 2026-09-27.

    return notes[:2]


_DRIVE_TRASH_NOTE = (
    "goûteur: that trashed a Drive file — trash is NOT revocation. A trashed "
    "file still serves its full content to anyone with the link (HTTP 200 from "
    "the bin, measured 2026-08-31); only `files.delete` or moving it out of the "
    "granting folder revokes. If this was a takedown, finish with an anonymous "
    "content probe: `curl -sL 'https://drive.google.com/uc?export=download&id=ID'` "
    "from a credential-free session, checking for a known string. "
    "[traps.md: Drive trash]"
)


# --- PostToolUse: MCP `do` ----------------------------------------------------

def probe_mcp_do(tool_name: str, tool_input: object) -> list[str]:
    """Renders for a mise `do` call. Reached through settings.json's
    PostToolUse matcher `mcp__plugin_.*mise.*__do`; without that matcher it is
    inert, since this file cannot wire itself."""
    if not (tool_name.startswith("mcp__") and tool_name.endswith("__do") and "mise" in tool_name):
        return []
    if not isinstance(tool_input, dict):
        return []
    if str(tool_input.get("operation", "")).lower() == "trash":
        return [_DRIVE_TRASH_NOTE]
    return []


# --- PostToolUse: Edit / Write ---------------------------------------------

def _once_per_session(prefix: str, session_id: str) -> bool:
    """True the FIRST time this (prefix, session) pair is seen; False after.

    An unknown session (empty id) reads as first-time — the render fires,
    which is the safe direction. Marker files reuse the fallback probe's
    self-tidy pattern: stale ones are swept when a new session first appears.
    """
    safe = re.sub(r"[^A-Za-z0-9_-]", "", session_id or "")[:64]
    if not safe:
        return True
    marker = os.path.join(_STATE_DIR, f"{prefix}-{safe}")
    if os.path.exists(marker):
        return False
    try:
        os.makedirs(_STATE_DIR, exist_ok=True)
        cutoff = time.time() - 14 * 86400
        for stale in os.listdir(_STATE_DIR):
            p = os.path.join(_STATE_DIR, stale)
            # Per-file: a sibling process sweeping the same stale marker
            # raises here, and one try around the whole loop used to skip
            # the marker WRITE below, so the advisory repeated (garebi).
            try:
                if stale.startswith(f"{prefix}-") and os.path.getmtime(p) < cutoff:
                    os.unlink(p)
            except OSError:
                continue
        with open(marker, "w", encoding="utf-8"):
            pass
    except OSError:
        pass  # unwritable state dir: fire every time rather than break the hook
    return True


GUIDANCE_NOTE = (
    "goûteur: guidance and settings files are session-cached — this edit "
    "takes effect NEXT session (two exceptions in settings.json apply "
    "live: the hooks key, and the model key, which switches the RUNNING "
    "session and can drop its [1m] suffix, so read /context after a pin "
    "change). Don't verify it in this one, and say so when reporting. "
    "[traps.md: guidance edits]"
)


def probe_edit(file_path: str, session_id: str = "") -> list[str]:
    """Return renders for a completed Edit/Write. Empty list = stay silent."""
    notes = _ext_call("post_edit", file_path, session_id)
    p = os.path.abspath(os.path.expanduser(file_path))
    cfg = os.path.abspath(_config_dir())

    # traps.md: "Editing CLAUDE.md, rules/*.md, settings.json — or a skill's
    # frontmatter" — all session-cached; a correct edit that "failed" this
    # session is the trap. rules/ has the extra hazard of being regenerated:
    # plugins (batterie's own shards among them) rewrite their rules/ file at
    # every session start.
    if p.startswith(cfg + "/rules/"):
        # An extension that knows this machine's rules/ files (a hand-authored
        # machine-local shard, an installed platform copy) may already have
        # said something more specific — and opposite: "editing here is right".
        if not any("[traps.md: hand-editing rules/]" in n for n in notes):
            notes.append(
                "goûteur: files in ~/.claude/rules/ may be REGENERATED at session start "
                "(mtime == session start is the tell) — edit the upstream source, and "
                "either way the change lands next session, not this one. "
                "[traps.md: hand-editing rules/]"
            )
    elif (
        p.endswith("/CLAUDE.md")
        or p.endswith("/SKILL.md")
        or re.search(r"/\.?claude/settings(\.local)?\.json$", p)
        or p == cfg + "/settings.json"
    ):
        # Once per session: the fires log measured this advisory at 22 of 30
        # real fires as repeats (7 sessions, up to 7 in one) — the first tells
        # the session something new, the repeats are the habituation risk to
        # the whole channel. The rules/ render above stays per-fire: it guards
        # regeneration, not just caching.
        if _once_per_session("guidance-note", session_id):
            notes.append(GUIDANCE_NOTE)

    # traps.md: "bon board hand-edits" (bon-tusico). The post-hoc half of the
    # tripwire: fires after a Write/Edit landed on a board file, which only
    # happens where the PreToolUse matcher does not route the file tools to
    # the --pre deny.
    board = bon_board_tool_path({"tool_input": {"file_path": file_path}})
    if board:
        notes.append(
            _BON_BOARD_NOTE.format(path=board)
            .replace("this writes", "that edit wrote", 1)
            .replace(" [traps.md: bon board hand-edits]",
                     " Check the board still loads (`bon list`); if the edit lost "
                     "or mangled an item, `bon restore ID` brings it back. "
                     "[traps.md: bon board hand-edits]")
        )

    # traps.md: "Generating GitHub Actions YAML" — a mutable @tag is a
    # supply-chain risk; only a 40-hex commit SHA is a pin. A checker, not
    # a reminder: reads the post-edit file, fires only on a real @tag.
    if "/.github/workflows/" in p and p.endswith((".yml", ".yaml")):
        try:
            if os.path.isfile(p) and os.path.getsize(p) < 2_000_000:
                with open(p, encoding="utf-8") as f:
                    wf = f.read()
                tags = re.findall(r"uses:\s*(\S+@(?![0-9a-f]{40}\b)\S+)", wf)
                if tags:
                    notes.append(
                        f"goûteur: workflow pins by mutable ref ({tags[0]}"
                        + (f" +{len(tags)-1} more" if len(tags) > 1 else "")
                        + ") — pin to a full commit SHA (`uses: owner/repo@<sha> # vN`), "
                        "tags are a supply-chain risk. [traps.md: GitHub Actions YAML]"
                    )
        except (OSError, UnicodeDecodeError):
            pass

    # RETIRED 2026-11-08: the broken-JSON checker (CC and the model both
    # validate; one fire in its life). See RETIRED.

    return notes[:2]


_STATE_DIR = os.environ.get("GOUTEUR_STATE_DIR") or os.path.expanduser("~/.local/state/gouteur")


_FIRES_LOG = os.path.join(_STATE_DIR, "fires.jsonl")

# Every render ends with a bracketed source tag; that tag is the render's
# identity. Deriving the id from it costs no call-site churn across ~30
# append sites, and KNOWN_RENDER_IDS below freezes the set so an edited tag
# fails the self-test instead of silently splitting a render's history into
# two ids (the rot carte-mirote was filed to prevent — the 2026-08-28 census
# had to group by the first six words of the note text).
KNOWN_RENDER_IDS = frozenset(
    {
        "gouteur-bon-handedit-declared",
        "gouteur-deliberate-wait-declared",
        "gouteur-cd-rewrite-crash",
        "gouteur-crash",
        "gouteur-extension-failed",
        "traps-blind-sleep",
        "traps-bon-board-hand-edits",
        "traps-credential-directories",
        "traps-relative-path-after-a-bare-cd",
        "traps-drive-trash",
        "traps-find-bfs",
        "traps-git-mv-on-cwd",
        "traps-github-actions-yaml",
        "traps-guidance-edits",
        "traps-hand-editing-rules",
        "traps-pgrep-f-self-match",
        "traps-tmux-kill-without-a-socket",
        "traps-unresolvable-rm-glob",
        "traps-recursive-grep",
        "traps-settings-deny-rules",
        "traps-settings-file-shred",
        "verification-the-outrunning-write",
    }
)

# The existence condition per render — what would have to be true of the
# INSTRUMENT (not the model) for the render to be spent. The fires log
# measures precision; nothing else says when a render should go. Read by
# `--fires`, which prints it beside every count, and pinned by the self-test
# to KNOWN_RENDER_IDS so a render cannot be added without saying how it
# ends. "never" means the behaviour belongs to the tool itself.
RETIRE_WHEN = {
    "gouteur-bon-handedit-declared": "retires with traps-bon-board-hand-edits — it counts that tripwire's declared escapes",
    "gouteur-deliberate-wait-declared": "retires with traps-blind-sleep — it counts that render's declared escapes",
    "gouteur-cd-rewrite-crash": "never — structural: names an undesigned failure of this file",
    "gouteur-crash": "never — structural: names an undesigned failure of this file",
    "gouteur-extension-failed": "never — structural: names a gouteur.d module that failed to load or raised",
    "traps-blind-sleep": "CC's own Bash sleep-block stops riding the Monitor flag, so Vertex sessions get it too (re-measure: Monitor appears in a Vertex `claude -p --output-format stream-json --verbose` init tool list, and a Vertex `sleep 45; date` comes back Blocked)",
    "traps-bon-board-hand-edits": "bon boards stop being plain files a shell can write — a store only the CLI reaches (bon-tusico)",
    "traps-credential-directories": "secrets leave path-shaped homes (agent/keychain) AND shell profiles stop exporting them into the environment",
    "traps-drive-trash": "Google serves a 403/404 for trashed files to anonymous link-holders (re-measure with the content probe, not a status code)",
    "traps-find-bfs": "`type find` in a CC Bash is no longer the bfs wrapper",
    "traps-git-mv-on-cwd": "CC stops re-entering the recorded cwd before each Bash call",
    "traps-github-actions-yaml": "GitHub makes action tags immutable",
    "traps-guidance-edits": "CC reloads CLAUDE.md/rules/skills live mid-session",
    "traps-hand-editing-rules": "plugin shards stop regenerating rules/ at session start",
    "traps-tmux-kill-without-a-socket": "never — tmux behaviour: a client with no -S/-L follows $TMUX, then the default socket; only a machine with no shared tmux server would spend it",
    "traps-unresolvable-rm-glob": "CC's dangerous-removal check resolves `..` and follows a relative cd, or stops being bypass-immune (re-measure: `claude -p --permission-mode bypassPermissions` running `rm -rf ../b/*` from a sibling dir deletes the files)",
    "traps-pgrep-f-self-match": "the harness stops carrying the command string in a process cmdline (re-measure: `pgrep -l -f <marker>` from a CC Bash on Linux and Darwin -a finds nothing)",
    "traps-recursive-grep": "`type grep` in a CC Bash is no longer the ugrep wrapper",
    "traps-relative-path-after-a-bare-cd": "CC's Read-deny check tracks cd; dormant on any machine with no Read() deny rule",
    "traps-settings-deny-rules": "CC's own denial message names the settings rule that matched",
    "traps-settings-file-shred": "CC stops minting one allow rule per subcommand from a dialog's 'don't ask again'",
    "verification-the-outrunning-write": "bon edit refuses an empty value at source",
}

# Renders that left the file, with why, so a fires log that predates their
# retirement still reads (`--fires` prints these instead of UNSTATED).
_GENERAL = ("general command-line knowledge; the banc corpus ablation found Opus 5.5 "
            "handles it with no guidance (retired 2026-11-08, dot-claude-tipuce)")
RETIRED = {
    "traps-scoped-search-under-notes": "a personal-estate scope note; 301 of 306 fires were true empties in precise lookups (retired 2026-09-27)",
    "traps-rg-r": _GENERAL,
    "traps-jq-null": _GENERAL,
    "traps-xargs-without-r": _GENERAL,
    "traps-xargs-command": _GENERAL,
    "traps-pipeline-status-consumed": _GENERAL,
    "traps-csv-dictreader": _GENERAL + "; followed 1 time in 12",
    "traps-detached-head": _GENERAL,
    "traps-git-worktree-add": _GENERAL,
    "traps-git-add-under-an-ignored-directory": _GENERAL,
    "traps-git-add-stale-pathspec": _GENERAL,
    "traps-divergence-count": _GENERAL + "; also fired on output that merely quoted a status line",
    "verification-the-instrument-s-limits": _GENERAL + "; the single most-fired render, a catch-all",
    "traps-editing-a-json-config": "CC and the model both validate JSON; one fire in its life (retired 2026-11-08)",
}


def known_render_ids() -> frozenset:
    ids = set(KNOWN_RENDER_IDS)
    for extra in _ext_attr("RENDERS"):
        ids |= set(extra)
    return frozenset(ids)


def retire_when() -> dict:
    merged = dict(RETIRE_WHEN)
    for extra in _ext_attr("RENDERS"):
        merged.update(extra)
    return merged


def _render_id(note: str) -> str:
    """Derive a render's stable id from its trailing [source: name] tag."""
    m = re.search(r"\[([^\[\]]+)\]\s*$", note.strip())
    if not m:
        return "untagged"
    tag = m.group(1).strip().lower()
    tag = tag.replace(".md", "").replace(":", " ")
    slug = re.sub(r"[^a-z0-9]+", "-", tag).strip("-")
    return slug or "untagged"


_RENDER_TAG = re.compile(r"\[(?:traps\.md|verification\.md|(?:carte|dot-claude)-[a-z]+|gouteur)[^\]]*\]")


def _registry_drift(src: str) -> tuple[list[str], list[str]]:
    """(ids emitted somewhere in SRC but not registered, ids registered but
    emitted nowhere). Scans every bracketed source tag in the file rather
    than a handful of probe() fixtures: the fixture form let the second
    most-fired render live unregistered for a week (twin review 2026-09-06,
    carte-nasara)."""
    found = {_render_id("x " + t) for t in _RENDER_TAG.findall(src)}
    return sorted(found - KNOWN_RENDER_IDS), sorted(KNOWN_RENDER_IDS - found)


def log_fires(notes: list[str], data: dict) -> None:
    """Append one record per fire. Never raises — a full disk must not break
    the tool call being observed, which is the whole point of a passive hook.

    Deliberately records NO command text: goûteur sees credential paths and
    settings touches, so a log carrying commands would be a secret-bearing
    artefact needing its own gate (traps.md: credential directories). The tool-use
    id is enough to recover the command from the transcript when a human
    decides to look.
    """
    try:
        os.makedirs(_STATE_DIR, exist_ok=True)
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(_FIRES_LOG, "a", encoding="utf-8") as fh:
            for note in notes:
                fh.write(
                    json.dumps(
                        {
                            "ts": stamp,
                            "render": _render_id(note),
                            "tool_use_id": data.get("tool_use_id") or "",
                            "session_id": data.get("session_id") or "",
                            "cwd": data.get("cwd") or "",
                            # Same shape as perms.jsonl, plus host: the
                            # census merges seats and (soon) machines, and
                            # a record that cannot say where it fired
                            # cannot answer "which seat" (carte-nasara).
                            "host": socket.gethostname(),
                            "mode": data.get("permission_mode") or "",
                            "agent": "agent_id" in data or "agent_type" in data,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
    except Exception:
        return


def report_fires(since: str = "", repeats: bool = False) -> int:
    """Print fires-by-render over a window. Returns the number of records.

    With REPEATS, add the heeded proxy: a render that fires again in the SAME
    session was not acted on (a render whose advice is "re-run with
    --no-ignore" and then fires unchanged was ignored, or a script is looping
    through it). Computed from what is already logged; the stronger measure
    (did the next command change?) reads the transcript: `--followed`,
    report_followed() below (carte-pabafo).
    """
    counts: dict[str, int] = {}
    per_session: dict[str, dict[str, int]] = {}
    total = 0
    try:
        with open(_FIRES_LOG, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue  # a torn append must not sink the report
                if since and str(rec.get("ts", "")) < since:
                    continue
                rid = str(rec.get("render", "untagged"))
                counts[rid] = counts.get(rid, 0) + 1
                sid = str(rec.get("session_id") or "?")
                per_session.setdefault(rid, {})[sid] = per_session.get(rid, {}).get(sid, 0) + 1
                total += 1
    except FileNotFoundError:
        print("no fires logged yet (%s)" % _FIRES_LOG)
        return 0
    window = f" since {since}" if since else ""
    print(f"goûteur fires{window}: {total} across {len(counts)} renders")
    for rid, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        share = (100.0 * n / total) if total else 0.0
        line = f"  {n:6d}  {share:5.1f}%  {rid}"
        if repeats:
            sess = per_session[rid]
            repeated = sum(1 for c in sess.values() if c > 1)
            line += f"   sessions={len(sess)} repeat-sessions={repeated} max-in-one={max(sess.values())}"
        print(line)
        if rid in RETIRED:
            print(f"                  RETIRED: {RETIRED[rid]}")
        else:
            print(f"                  retire when: {retire_when().get(rid, 'UNSTATED — add to RETIRE_WHEN')}")
    silent = sorted(set(known_render_ids()) - set(counts))
    if silent:
        print(f"never fired{window} ({len(silent)}): " + ", ".join(silent))
        print("  a render that has never fired has never been tested — positive-control it before retiring it")
    return total


# Which renders can be scored on the NEXT command, and how (carte-pabafo).
# Each entry: (in_class, remedied). in_class says which later Bash commands
# count as "the same kind of command" the render fired on; remedied says
# whether the advice is in it. Only renders whose remedy is a command SHAPE
# belong here — guidance-edits, credential-directories, jq-null have no
# next-command form and stay on the --repeats proxy. A remedied predicate
# MUST be able to return False: the prototype scored rg -r 12/12 with "any
# later rg counts", which is a check that cannot fail (verification.md).
_SINGLE_DASH_R = re.compile(r"(?:^|\s)-[A-Za-z]*r[A-Za-z]*(?=\s|$)")


def _next_rg(c: str) -> bool:
    return bool(re.search(r"(?:^|[\s;&|(])rg\s", c))


def _recursive_search(c: str) -> bool:
    return (bool(re.search(r"(?:^|[\s;&|(])grep\s", c)) and bool(_SINGLE_DASH_R.search(c))) \
        or _next_rg(c) or "command grep" in c or "zgrep" in c


def _unwrapped_search(c: str) -> bool:
    # Bare rg escapes the wrapper's flag rejections but not the ignore files:
    # it honours .gitignore even on a named directory (measured 2026-09-27,
    # banc corpus-ablation t1), so only -u/--no-ignore counts as following.
    rg_unignored = _next_rg(c) and re.search(r"\s(-u+|--no-ignore\S*)\b", c) is not None
    return rg_unignored or "command grep" in c or "zgrep" in c


FOLLOWED = {
    "traps-recursive-grep": (_recursive_search, _unwrapped_search),
    # The next sleep either watches a condition, is short, or declares
    # itself. run_in_background is not in the command string, so a
    # backgrounded blind sleep scores as not-followed — a known undercount.
    "traps-blind-sleep": (
        lambda c: re.search(r"(?:^|[\s;&|(])sleep\s+\.?\d", c) is not None,
        lambda c: blind_sleep(c) is None or deliberate_wait_escape(c) is not None,
    ),
}


def followed() -> dict:
    merged = dict(FOLLOWED)
    for extra in _ext_attr("FOLLOWED"):
        merged.update(extra)
    return merged


_PROJECT_ROOTS = [os.path.join(_config_dir(), "projects")]


def project_roots() -> list:
    roots = list(_PROJECT_ROOTS)
    for extra in _ext_attr("PROJECT_ROOTS"):
        roots += [os.path.expanduser(r) for r in extra if os.path.expanduser(r) not in roots]
    return roots


def _bash_timeline(session_id: str) -> list[tuple[str, str]]:
    """(timestamp, command) for every Bash tool_use in a session's root and
    subagent transcripts. Read structurally — a substring scan would count
    commands quoted in tool results."""
    import glob as _glob
    safe = re.sub(r"[^A-Za-z0-9-]", "", session_id)
    if not safe:
        return []
    files: list[str] = []
    for root in project_roots():
        files += _glob.glob(os.path.join(root, "*", safe + ".jsonl"))
        files += _glob.glob(os.path.join(root, "*", safe, "subagents", "*.jsonl"))
    out: list[tuple[str, str]] = []
    for fp in files:
        try:
            with open(fp, "rb") as fh:
                for raw in fh:
                    if b'"Bash"' not in raw:
                        continue
                    try:
                        e = json.loads(raw)
                    except ValueError:
                        continue
                    if e.get("type") != "assistant":
                        continue
                    for blk in (e.get("message") or {}).get("content") or []:
                        if isinstance(blk, dict) and blk.get("type") == "tool_use" and blk.get("name") == "Bash":
                            cmd = (blk.get("input") or {}).get("command")
                            if isinstance(cmd, str):
                                out.append((str(e.get("timestamp") or ""), cmd))
        except OSError:
            continue
    # Two roots can be one directory under a symlink; dedupe rather than
    # list each command twice.
    return sorted(set(out))


def report_followed(since: str = "") -> dict[str, tuple[int, int, int]]:
    """Per render: of the sessions where it fired, how many carried the
    remedy in their NEXT command of the same class? Returns
    {render: (followed, scored, unscored)} — unscored is "no later command
    of the class", kept out of both sides rather than read as either.

    Scores the FIRST fire per render per session: that is the render the
    session had not yet seen. Later fires are the --repeats proxy's business.
    """
    fol = followed()
    fires: dict[str, list[dict]] = {}
    try:
        with open(_FIRES_LOG, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if since and str(rec.get("ts", "")) < since:
                    continue
                if rec.get("render") in fol and rec.get("session_id"):
                    fires.setdefault(str(rec["session_id"]), []).append(rec)
    except FileNotFoundError:
        print("no fires logged yet (%s)" % _FIRES_LOG)
        return {}
    tally: dict[str, list[int]] = {rid: [0, 0, 0] for rid in fol}
    no_transcript = 0
    for sid, recs in fires.items():
        timeline = _bash_timeline(sid)
        if not timeline:
            no_transcript += 1
            continue
        recs.sort(key=lambda r: str(r.get("ts", "")))
        seen: set[str] = set()
        for rec in recs:
            rid = str(rec["render"])
            if rid in seen:
                continue
            seen.add(rid)
            in_class, remedied = fol[rid]
            t0 = str(rec.get("ts", ""))
            later = [c for ts, c in timeline if ts > t0 and in_class(c)]
            if not later:
                tally[rid][2] += 1
            elif remedied(later[0]):
                tally[rid][0] += 1
                tally[rid][1] += 1
            else:
                tally[rid][1] += 1
    window = f" since {since}" if since else ""
    print(f"goûteur --followed{window}: first fire per render per session, scored on the next command of the same class")
    print(f"  ({len(fires)} sessions with a scorable render; {no_transcript} had no transcript on this host)")
    for rid, (ok, n, none) in sorted(tally.items(), key=lambda kv: -kv[1][1]):
        pct = f"{100.0 * ok / n:3.0f}%" if n else "  —"
        print(f"  {ok:4d}/{n:<4d} {pct}  followed   {none:3d} no-later-command   {rid}")
    print("  followed = the next same-class command carried the remedy; a low number says the render text or its remedy needs rewriting before the row needs retiring")
    print("  followed is not caused: there is no unrendered baseline, so a high number may be what the agent did anyway (the missing arm is a placebo bench)")
    return {rid: tuple(v) for rid, v in tally.items()}


# --- entry points ------------------------------------------------------------

def main() -> None:
    data = json.load(sys.stdin)
    tool = data.get("tool_name")

    if "--perm" in sys.argv:
        log_perm(data)
        return

    if "--pre" in sys.argv:
        if tool in CREDENTIAL_PATH_TOOLS:
            deny_credential_tool(data, tool)
            _report_ext_errors(data, "pre")
            return
        if tool in ("Write", "Edit", "NotebookEdit"):
            # Live only where the PreToolUse matcher routes these tools here;
            # probe_edit's post-hoc render is the sensor where it does not.
            deny_bon_board_tool(data, tool)
            return
        if tool != "Bash":
            return
        tool_input = data.get("tool_input")
        # A non-dict tool_input (a list, a scalar) used to raise here, and the
        # fail-open wrapper then ran the gated command silently (twin review
        # 2026-09-06, carte-visoce). Stringify it so the substring gate
        # still sees whatever the payload carried.
        cmd = tool_input.get("command", "") if isinstance(tool_input, dict) else tool_input
        if not isinstance(cmd, str):
            # Schema drift: a non-string command would raise inside the
            # fail-open wrapper below and the gated call would run silently.
            # str() keeps the substring match alive on any representation
            # (essayeur finding on carte-suruta, 2026-08-24).
            cmd = str(cmd)
        background = isinstance(tool_input, dict) and \
            str(tool_input.get("run_in_background")).lower() in ("true", "1")
        reason = probe_pre(cmd, data.get("cwd") or "", background)
        # A broken extension fails open: the shipped guards above still
        # ran. Logged by name, so the census shows it (and PostToolUse
        # says it to the session once).
        _report_ext_errors(data, "pre")
        if not reason:
            # A declared board repair passes, and is counted (bon-tusico).
            escape = bon_board_escape(cmd)
            if escape and _bon_board_write(cmd, data.get("cwd") or ""):
                # Its own id, so the census tells a declared repair from a
                # deny (both would otherwise count as the one render).
                log_fires([f"bon-handedit declared: {escape[:120]} "
                           "[gouteur: bon-handedit-declared]"], data)
            # Likewise a declared settle-pause (carte-holuka).
            wait = deliberate_wait_escape(cmd)
            if wait and blind_sleep(cmd, background):
                log_fires([f"deliberate-wait declared: {wait[:120]} "
                           "[gouteur: deliberate-wait-declared]"], data)
            # Last, so every tailored reason above wins: a settings deny that
            # would otherwise refuse mutely is named here (carte-ratenu).
            reason = probe_settings_deny(cmd, data.get("cwd") or "")
        if reason:
            # One decision, caller-aware REASON (carte-jegise, 2026-08-30):
            # a hook "ask" never renders a dialog — CC auto-denies it and
            # drops the reason text (measured, CC 2.1.251; see module
            # docstring). Every branch denies; only the coaching varies.
            decision = "deny"
            if _pre_caller(data) == "agent":
                reason = (
                    "goûteur DENIED this call, not the goal: it came from an "
                    "Agent-tool worker (agent_id in the hook payload), and "
                    "nobody sits at a worker's permission dialog — an "
                    "unattended ask stalls for 59-133 min where a deny is "
                    "self-served in seconds (carte-suruta). Rephrase and retry "
                    "per the guidance that follows, or park the item if the "
                    "blocked read is genuinely required: " + reason
                )
            else:
                reason = (
                    "goûteur DENIED this call, not the goal. (A hook ask "
                    "never renders a dialog — CC auto-denies it and drops "
                    "the reason, so this gate denies with the coaching "
                    "attached instead; carte-jegise, 2026-08-30.) Rephrase "
                    "and self-serve per the guidance that follows; an "
                    "unattended session whose blocked step is genuinely "
                    "required parks the item instead: " + reason
                )
            log_fires([reason], data)  # denies count in the census (carte-nasara)
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": decision,
                            "permissionDecisionReason": reason,
                        }
                    }
                )
            )
            return

        # Relative paths after a cd (carte-sikoce). Designed fallback is
        # None -> CC's own prompt, unchanged from before this existed; a
        # CRASH is the failure we did not design for, so it is logged by
        # name rather than swallowed into the same silence.
        try:
            rewritten = rewrite_after_cd(cmd, data.get("cwd") or "")
        except Exception as exc:  # noqa: BLE001 — logged, then fall through
            log_fires([f"cd-rewrite crashed: {type(exc).__name__}: {exc} "
                       "[gouteur: cd-rewrite-crash]"], data)
            rewritten = None
        if rewritten:
            new_cmd, note, read_only = rewritten
            mode = data.get("permission_mode") or ""
            # An "allow" approves the WHOLE compound. Outside bypass mode
            # that must not wave through a mutating tail the session would
            # otherwise have been asked about.
            if not read_only and mode != "bypassPermissions":
                return
            tool_input = dict(data.get("tool_input") or {})
            tool_input["command"] = new_cmd
            log_fires([note], data)
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "allow",
                            "permissionDecisionReason": (
                                "goûteur resolved relative paths after cd "
                                "(carte-sikoce)"),
                            "updatedInput": tool_input,
                            "additionalContext": note,
                        }
                    },
                    ensure_ascii=False,
                )
            )
        return

    notes: list[str] = []
    if tool == "Bash":
        cmd = (data.get("tool_input") or {}).get("command", "")
        resp = data.get("tool_response")
        if isinstance(resp, dict):
            stdout = str(resp.get("stdout") or "")
            stderr = str(resp.get("stderr") or "")
        else:
            stdout, stderr = str(resp or ""), ""
        notes = probe(
            cmd,
            stdout,
            stderr,
            cwd=data.get("cwd") or "",
            permission_mode=data.get("permission_mode") or "",
        )
    elif tool in ("Edit", "Write"):
        file_path = (data.get("tool_input") or {}).get("file_path", "")
        if file_path:
            notes = probe_edit(file_path, data.get("session_id") or "")
    elif isinstance(tool, str) and tool.startswith("mcp__"):
        notes = probe_mcp_do(tool, data.get("tool_input"))

    # Session-scoped probes from extensions ride whichever call comes next.
    notes = notes + _ext_call("post_any", data)

    # A gouteur.d module that failed is logged and said once per session.
    # (Only the PostToolUse stage can speak to the session; a --pre failure
    # is logged there and, being the same module, usually shows up here too.)
    ext_note = _report_ext_errors(data, "post")
    if ext_note:
        notes = notes + [ext_note]

    if notes:
        # Log before rendering: if the print fails the fire still happened,
        # and log_fires never raises (carte-mirote).
        log_fires(notes, data)
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": "\n".join(notes),
                    }
                }
            )
        )


def self_test() -> None:
    """Known-positive AND known-negative per pattern — a probe that reports
    absence is only checked once it has fired against a known positive."""
    # Phase 1 runs the shipped checks with no gouteur.d extension loaded,
    # in this process and in every subprocess it starts, so a person's own
    # renders cannot pass or fail a shipped case. Phase 2, at the end,
    # hands `check` to each extension's own self_test().
    global _EXTENSIONS
    _sv_ext_env = os.environ.get("GOUTEUR_EXTENSIONS")
    _sv_ext = _EXTENSIONS
    os.environ["GOUTEUR_EXTENSIONS"] = ""
    _EXTENSIONS = []
    import tempfile

    failures = 0
    total = 0

    def check(desc: str, fired: bool, expect: bool) -> None:
        nonlocal failures, total
        total += 1
        ok = fired == expect
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {desc}  (fired={fired}, expected={expect})")

    # -- probe(): Bash post-hoc renders (cmd, stdout, stderr, cwd, expect)
    bash_cases = [
        ('wrapped grep -r, empty', 'grep -rn --no-ignore foo ~/dir 2>/dev/null', '', '', '', True),
        ('command grep -r, empty', 'command grep -rn foo ~/dir', '', '', '', False),
        ('wrapped grep -r, hits', 'grep -rn foo ~/dir', 'dir/a.txt:1:foo', '', '', False),
        ('find -newermt, empty', "find . -newermt '2026-07-26T20:36:14,123' 2>/dev/null", '', '', '', True),
        ('find -newermt, hits', "find . -newermt '2026-07-26T20:36:14'", './fresh.txt', '', '', False),
        ('recursive grep null: capital -R fires', 'grep -Rn foo /x', '', '', '', True),
        ('recursive grep null: --recursive fires', 'grep --recursive foo /x', '', '', '', True),
        ('recursive grep: -r belongs to xargs, not grep (aug-nasami)', "ps -eo pid,args | grep -E '[p]ytest' | awk '{print $1}' | xargs -r kill", '', '', '', False),
        ('recursive grep: -r belongs to jq in a later segment (aug-nasami)', "bon list | grep -i foo | head -3; bon list --json | jq -r '.x'", '', '', '', False),
        ("recursive grep: r inside find's -newermt, grep has no -r (aug-nasami)", "grep -c '^saved' log; command find data -newermt '-20 minutes' | grep -q .", '', '', '', False),
        ('recursive grep: -r after the pattern still fires', 'grep foo -r /x', '', '', '', True),
        ('find -newermt via command find bypasses the wrapper (aug-nasami)', "command find . -newermt '2026-07-26T20:36:14,123'", '', '', '', False),
        ('git mv of cwd via cd', 'cd /home/u/repos && git mv myproj myproj-new', '', '', '/home/u/repos/myproj', True),
        ('git mv of cwd, absolute src', 'git mv /home/u/repos/myproj /tmp/x', '', '', '/home/u/repos/myproj/sub', True),
        ('git mv nested same-name is safe', 'git mv myproj myproj-new', '', '', '/home/u/repos/myproj', False),
        ('git mv of sibling is safe', 'cd /home/u/repos && git mv other-dir new-name', '', '', '/home/u/repos/myproj', False),
        ('grep prose in quotes, null + silenced', "echo 'try grep -r later' 2>/dev/null", '', '', '', False),
        ('settings shred: compound touch', 'mkdir -p /tmp/zz-e && cp ~/.claude/settings.json /tmp/zz-e/', '', '', '', True),
        ('settings shred: .local variant', 'cp ~/.claude/settings.local.json /tmp/x/ && ls /tmp/x', '', '', '', True),
        ('settings shred: single-command touch is fine', 'cp ~/.claude/settings.json /tmp/zz-d/', '', '', '', False),
        ('settings shred: compound without settings path is fine', 'mkdir -p /tmp/zz-a && cp /etc/hostname /tmp/zz-a/', '', '', '', False),
        ('settings shred: no .claude prefix is fine', 'cd /tmp/zz-b && cp settings.json /tmp/zz-c.json', '', '', '', False),
        ('settings shred: quoted prose stays silent', "echo 'junk came from ~/.claude/settings.local.json' && ls", 'done', '', '', False),
        ('settings shred: heredoc body stays silent', "cat <<'EOF' | bon new -q\nwhy: junk in ~/.claude/settings.local.json\nEOF", '', '', '', False),
        ('settings shred: settings.json.bak is fine', 'ls /tmp && cp ~/.claude/settings.json.bak /tmp/', '', '', '', False),
    ]
    for desc, cmd, stdout, stderr, cwd, expect in bash_cases:
        check(desc, bool(probe(cmd, stdout, stderr, cwd)), expect)

    # -- settings shred: the mode gate (permission_mode injected). The gate
    # must silence ONLY this rule — the grep-null case proves the others
    # ignore the mode entirely.
    shred_cmd = "mkdir -p /tmp/zz-e && cp ~/.claude/settings.json /tmp/zz-e/"
    pm_cases = [
        ("shred fires in default mode", shred_cmd, "default", True),
        ("shred fires in acceptEdits", shred_cmd, "acceptEdits", True),
        ("shred fires in auto mode", shred_cmd, "auto", True),
        ("shred fires when mode field absent", shred_cmd, "", True),
        ("shred silent under bypassPermissions", shred_cmd, "bypassPermissions", False),
        ("grep-null render ignores bypass mode",
         "grep -rn foo ~/dir 2>/dev/null", "bypassPermissions", True),
        # garebi: the QUOTED spelling is the common idiom and was silent.
        ("shred fires on a double-quoted $HOME path",
         'jq .x "$HOME/.claude/settings.json" && ls', "default", True),
        ("shred fires on a single-quoted absolute path",
         "cat '/home/u/.claude/settings.local.json' | jq . && ls", "default", True),
        ("shred: quoted prose in echo still stays silent",
         "echo 'junk came from ~/.claude/settings.local.json' && ls", "default", False),
    ]
    for desc, cmd, pm, expect in pm_cases:
        check(desc, bool(probe(cmd, "", "", "", permission_mode=pm)), expect)

    # -- Drive trash (carte-wapefe, 2026-09-23). Positives assert the render's
    # OWN tag (so another render firing cannot pass them); negatives assert
    # total silence. Broken to prove it goes red, then restored.
    def _tagged(tag: str, cmd: str, stdout: str = "x", **kw) -> bool:
        return any(tag in n for n in probe(cmd, stdout, "", "", **kw))

    TRASH = "[traps.md: Drive trash]"
    for desc, cmd, out in (
        ("Drive API JSON body",
         "curl -s -X PATCH 'https://www.googleapis.com/drive/v3/files/1abc' -H 'Content-Type: application/json' -d '{\"trashed\": true}'", "{}"),
        ("python client dict body",
         "python3 - <<'PY'\ndrive_service().files().update(fileId='1abc', body={'trashed': True}).execute()\nPY", ""),
    ):
        check(f"trash+ {desc}", _tagged(TRASH, cmd, out), True)
    for desc, cmd, out in (
        ("a LISTING query for trashed files is a read", "python3 -c \"drive.files().list(q='trashed = true and name contains \\\"x\\\"').execute()\"", "[]"),
        ("untrash", "curl -X PATCH https://www.googleapis.com/drive/v3/files/1abc -d '{\"trashed\": false}'", "{}"),
        ("trashed true with no Drive in sight", "python3 -c \"print({'trashed': True})\"", "x"),
    ):
        check(f"trash- {desc}", bool(probe(cmd, out, "", "")), False)
    check("trash+ mcp: mise do(operation=trash) renders",
          bool(probe_mcp_do("mcp__plugin_mit_mise__do", {"operation": "trash", "file_id": "1abc"})), True)
    check("trash+ mcp: family flavour renders too",
          bool(probe_mcp_do("mcp__plugin_family_mise__do", {"operation": "trash"})), True)
    check("trash+ mcp: pre-fold names still render (sessions started before the release)",
          bool(probe_mcp_do("mcp__plugin_batterie_mise__do", {"operation": "trash"})), True)
    check("trash- mcp: do(operation=archive) is Gmail, not Drive",
          bool(probe_mcp_do("mcp__plugin_mit_mise__do", {"operation": "archive"})), False)
    check("trash- mcp: another server's do is not mise",
          bool(probe_mcp_do("mcp__plugin_other_other__do", {"operation": "trash"})), False)
    check("trash- mcp: non-dict input never raises",
          bool(probe_mcp_do("mcp__plugin_mit_mise__do", ["trash"])), False)

    # -- garebi: the once-per-session marker under a sibling's concurrent sweep.
    # Two processes sweeping the same stale marker: the loser's unlink raises,
    # and the old single try skipped the marker WRITE, so the advisory repeated.
    with tempfile.TemporaryDirectory() as sd:
        _saved_sd = _STATE_DIR
        globals()["_STATE_DIR"] = sd
        stale = os.path.join(sd, "guidance-note-old")
        open(stale, "w").close()
        os.utime(stale, (0, 0))
        _real_unlink = os.unlink

        def _flaky_unlink(p):
            os.unlink = _real_unlink
            raise FileNotFoundError(p)
        os.unlink = _flaky_unlink
        try:
            first = _once_per_session("guidance-note", "sessR")
        finally:
            os.unlink = _real_unlink
            globals()["_STATE_DIR"] = _saved_sd
        check("once-per-session: a lost sweep race still writes the marker",
              first is True and os.path.exists(os.path.join(sd, "guidance-note-sessR")), True)

    # -- probe_edit(): Edit/Write renders, in a config dir of our own so no
    # verdict leans on the live ~/.claude.
    _sv_cfg, _sv_state = os.environ.get("CLAUDE_CONFIG_DIR"), _STATE_DIR
    fake_cfg = tempfile.mkdtemp()
    try:
        os.environ["CLAUDE_CONFIG_DIR"] = fake_cfg
        globals()["_STATE_DIR"] = tempfile.mkdtemp()
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write('{"broken": ')
            bad_json = f.name
        edit_cases = [
            ("repo CLAUDE.md", "/home/u/repos/thing/CLAUDE.md", True),
            ("skill frontmatter", f"{fake_cfg}/skills/foo/SKILL.md", True),
            ("rules/ shard", f"{fake_cfg}/rules/mise.md", True),
            ("tracked settings.json", f"{fake_cfg}/settings.json", True),
            ("project settings.local.json", "/home/u/repos/thing/.claude/settings.local.json", True),
            ("ordinary python file", "/home/u/repos/thing/main.py", False),
            ("ordinary markdown", "/home/u/repos/thing/notes.md", False),
            ("broken JSON is no longer rendered (retired)", bad_json, False),
        ]
        for desc, path, expect in edit_cases:
            check(desc, bool(probe_edit(path)), expect)
        os.unlink(bad_json)
        check("rules/ render names regeneration",
              "REGENERATED" in (probe_edit(f"{fake_cfg}/rules/mise.md") or [""])[0], True)
        # One-shot gate on the guidance-cache advisory: first edit in a
        # session renders, repeats stay silent, a new session starts fresh,
        # and the rules/ render ignores the gate.
        g_path = f"{fake_cfg}/skills/foo/SKILL.md"
        check("guidance advisory: 1st edit in session fires", bool(probe_edit(g_path, "sessA")), True)
        check("guidance advisory: 2nd edit same session silent", bool(probe_edit(g_path, "sessA")), False)
        check("guidance advisory: other file, same session, still silent",
              bool(probe_edit(f"{fake_cfg}/settings.json", "sessA")), False)
        check("guidance advisory: new session fires again", bool(probe_edit(g_path, "sessB")), True)
        check("guidance advisory: no session id fires every time",
              bool(probe_edit(g_path)) and bool(probe_edit(g_path)), True)
        check("rules/ render is NOT gated (2nd fire same session)",
              bool(probe_edit(f"{fake_cfg}/rules/mise.md", "sessA"))
              and bool(probe_edit(f"{fake_cfg}/rules/mise.md", "sessA")), True)
        # GitHub Actions pin checker — needs the real path shape on disk.
        wf_dir = tempfile.mkdtemp()
        wf_path = os.path.join(wf_dir, ".github", "workflows")
        os.makedirs(wf_path)
        tagged = os.path.join(wf_path, "ci.yml")
        with open(tagged, "w") as f:
            f.write("jobs:\n  b:\n    steps:\n      - uses: actions/checkout@v4\n")
        pinned = os.path.join(wf_path, "ok.yml")
        with open(pinned, "w") as f:
            f.write("jobs:\n  b:\n    steps:\n      - uses: actions/checkout@"
                    + "a" * 40 + " # v4\n")
        check("workflow with mutable tag", bool(probe_edit(tagged)), True)
        check("workflow pinned to SHA", bool(probe_edit(pinned)), False)
    finally:
        if _sv_cfg is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = _sv_cfg
        globals()["_STATE_DIR"] = _sv_state

    # Every registered render states how it ends.
    check("jakale: RETIRE_WHEN covers exactly the registered renders "
          f"(diff: {sorted(set(RETIRE_WHEN) ^ set(KNOWN_RENDER_IDS))})",
          set(RETIRE_WHEN) == set(KNOWN_RENDER_IDS), True)
    check("retired ids are not live ids", sorted(set(RETIRED) & set(KNOWN_RENDER_IDS)), [])

    # -- probe_pre(): credential-path denies
    pre_cases = [
        ("cat tilde secrets", "cat ~/dl/sa-key.json", True),
        ("grep gcloud logs", "grep -r token ~/.config/gcloud/logs/", True),
        ("HOME spelling", 'head "$HOME/dl/sa-key.json"', True),
        ("absolute spelling", "wc -l /home/u/.config/gcloud/logs/x.log", True),
        ("mac absolute spelling", "cat /Users/u/dl/sa-key.json", True),
        ("compound sweep", "cd /tmp && python3 -c \"open('/home/u/dl/sa-key.json')\"", True),
        ("deliberate over-block on superstring", "cat ~/dl/sa-key.jsonandlies", True),
        ("ls .local is fine", "ls -la ~/.local", False),
        ("gcloud non-log use", "gcloud logging read 'severity>=ERROR'", False),
        ("the word secrets alone", "echo secrets are never in dotfiles", False),
        # Clearing `bon edit`. First case is verbatim the command that blanked
        # carte-viviko's --how on 2026-08-04 — the regression this rule exists for.
        ("bon edit from $(cat), the live incident",
         'bon edit carte-viviko --how "$(cat $SP/viviko-how.txt)"', True),
        ("bon edit from a bare variable", 'bon edit carte-x --why "$WHY"', True),
        ("bon edit from braced variable", 'bon edit carte-x --what "${TEXT}"', True),
        ("bon edit from backticks", "bon edit carte-x --done `cat f.txt`", True),
        ("bon edit literal empty string", 'bon edit carte-x --how ""', True),
        ("bon edit after a cd", 'cd ~/.claude && bon edit carte-x --title "$T"', True),
        ("bon edit with literal text is fine",
         'bon edit carte-x --how "Ship the tranche once the cut-line is set"', False),
        ("bon new from a heredoc is fine", "cat <<'EOF' | bon new -q\n{}\nEOF", False),
        ("bon show is fine", "bon show carte-viviko --json", False),
        ("bon done with a note is fine", 'bon done carte-x --note "superseded"', False),
        ("prose mentioning bon edit stays silent",
         "echo 'never run bon edit carte-x --how \"$V\" unchecked'", False),
        ("non-brief flag from a variable is fine", 'bon edit carte-x --parent "$P"', False),
        # Environment dumps (carte-hazoti, 2026-09-06): a shell profile that
        # exports secrets puts every value in the Bash tool's environment,
        # and a bare `env` sweeps them all with no path in sight.
        ("bare env dumps every secret", "env", True),
        ("printenv piped is still a dump", "printenv | sort", True),
        ("env with only flags", "env -0", True),
        ("bare set prints every variable", "set", True),
        ("bare export prints every exported value", "export", True),
        ("export -p likewise", "export -p", True),
        ("declare -x likewise", "declare -x", True),
        ("/proc environ is the same dump by another door",
         "cat /proc/self/environ | tr '\\0' '\\n'", True),
        ("env dump after a cd", "cd /tmp && env", True),
        ("env as a launcher is fine", "env FOO=1 python3 x.py", False),
        ("printenv of one named variable is fine", "printenv HOME", False),
        ("set -e / set -o are fine", "set -euo pipefail; ls", False),
        ("export of one assignment is fine", "export FOO=bar", False),
        ("declare of one variable is fine", "declare -x FOO=1", False),
        ("compgen -e lists names without values — the coached route", "compgen -e", False),
        ("prose mentioning env stays silent", "echo 'run env to see'", False),
    ]
    # Hand-writes into a bon board (bon-tusico). Built from pieces so this
    # file's own text never reads as a board write to a scan of it.
    brd = "/home/u/repos/x/" + ".bon/" + "items.jsonl"
    arc = "~/repos/x/" + ".bon/" + "archive.jsonl"
    rel = ".bon/" + "items.jsonl"
    pre_cases += [
        ("board: append by redirect", f"echo '{{\"id\":\"x\"}}' >> {brd}", True),
        ("board: heredoc redirect", f"cat > {brd} <<'EOF'\n{{}}\nEOF", True),
        ("board: relative redirect", f"jq -c . fixed.jsonl > {rel}", True),
        ("board: sed -i after a cd", f"cd ~/repos/bon && sed -i 's/open/done/' {rel}", True),
        ("board: perl -pi on the archive", f"perl -pi -e 's/a/b/' {arc}", True),
        ("board: tee onto it", f"bon list --jsonl | tee {brd}", True),
        ("board: cp as destination", f"cp /tmp/fixed.jsonl {brd}", True),
        ("board: mv a rewritten copy over it", f"mv {rel}.new {rel}", True),
        ("board: git show restored by hand", f"git show HEAD~1:{rel} > {rel}", True),
        ("board: python open append in a heredoc",
         f"python3 - <<'PY'\nopen('{brd}', 'a').write('{{}}')\nPY", True),
        ("board: python write_text",
         f"python3 -c \"from pathlib import Path; Path('{brd}').write_text('')\"", True),
        ("board: reading it is fine", f"cat {brd} | jq .", False),
        ("board: redirecting a read elsewhere is fine", f"jq . {rel} > /tmp/out.json", False),
        ("board: copying it out is fine", f"cp {rel} ~/backup/items.jsonl", False),
        ("board: a pre-dolt ghost is not the board", f"echo x > {rel}.pre-dolt", False),
        ("board: sed without -i is a read", f"sed -n 1,5p {brd}", False),
        ("board: 2>&1 is not a path", f"wc -l {brd} 2>&1", False),
        ("board: git checkout is the refusal's own remedy", f"git checkout -- {rel}", False),
        ("board: rm of a stale copy is sanctioned", f"rm {rel}", False),
        ("board: a single-quoted mention", f"grep -c '> {rel}' notes.md", False),
        ("board: python read", f"python3 -c \"print(open('{brd}').read())\"", False),
        ("board: pytest tmp board", f"echo '{{}}' >> /tmp/pytest-of-u/p0/{rel}", False),
        ("board: scratch after a cd", f"cd /tmp/claude-1000/x && echo '{{}}' > {rel}", False),
        ("board: TMPDIR board", f"echo '{{}}' > \"$TMPDIR/b/{rel}\"", False),
        ("board: test fixture board", f"echo '{{}}' >> ~/repos/bon/tests/fixtures/{rel}", False),
        ("board: declared repair passes",
         f"sed -i 's/x/y/' {brd}  # bon-handedit: resolve merge conflict markers", False),
        ("board: bon restore is the verb", "bon restore bon-abcdef", False),
        # The false-positive classes the 2026-09-27 precision pass found
        # (3,261 past commands naming a board file; 11 true fires remain).
        ("board: > inside a quoted commit message is prose",
         f'git commit -m "a -> b" && git add {rel} && git commit -m "c"', False),
        ("board: a mktemp fixture spelled through variables",
         f'T=$(mktemp -d); R="$T/repo"; echo x>"$R/{rel}"', False),
        ("board: the cd BEFORE the write governs, not a later one",
         f"cd /tmp && cat > bt/{rel} <<'EOF'\n{{}}\nEOF\ncd ~/repos/bon && bon list", False),
        ("board: a cd through a /tmp variable",
         f"T=/tmp/sedoze && cd $T/repo && : > {rel}", False),
        ("board: a function-argument path in a /tmp fixture script",
         f'D=$(mktemp -d /tmp/j-XXXX); seed() {{ printf x > "$1/{rel}"; }}; seed $D/a', False),
        ("board: the same function shape on a real repo still fires",
         f'seed() {{ printf x > "$1/{rel}"; }}; seed ~/repos/x', True),
    ]
    for desc, cmd, expect in pre_cases:
        check(desc, probe_pre(cmd) is not None, expect)

    # -- ratenu: pgrep -f / pkill -f with a bare substring. The linux cases
    # are the settings prefix rule's measured gaps (reordered flags, a path
    # to the binary) and its over-block (the anchored remedy).
    pgrep_cases = [
        ("pgrep -f bare substring", "pgrep -f zzqq", "linux", True),
        ("pgrep -lf cluster (the measured gap)", "pgrep -lf zzqq", "linux", True),
        ("pgrep -l -f reordered", "pgrep -l -f zzqq", "linux", True),
        ("pgrep -af cluster", "pgrep -af zzqq", "linux", True),
        ("pgrep --full long form", "pgrep --full zzqq", "linux", True),
        ("pkill -9 -f (the dangerous one)", "pkill -9 -f zzqq", "linux", True),
        ("pkill -KILL -f", "pkill -KILL -f zzqq", "linux", True),
        ("pkill -f then signal", "pkill -f -9 zzqq", "linux", True),
        ("/usr/bin/pgrep -f path form", "/usr/bin/pgrep -f zzqq", "linux", True),
        ("sudo pkill -f", "sudo pkill -f zzqq", "linux", True),
        ("pgrep -u VALUE then -f", "pgrep -u alice -f zzqq", "linux", True),
        ("in a compound after cd", "cd /tmp && pgrep -f zzqq | wc -l", "linux", True),
        ("inside $( )", "kill $(pgrep -f zzqq)", "linux", True),
        ("inside backticks", "kill `pgrep -f zzqq`", "linux", True),
        ("through ssh, quoted", "ssh box 'pgrep -l -f zzqq'", "linux", True),
        ("through ssh from a Mac: remote platform unknown",
         "ssh box 'pkill -f zzqq'", "darwin", True),
        ("through bash -c", "bash -c 'pkill -f zzqq'", "linux", True),
        ("anchored with ^ runs", "pgrep -f '^/Applications/X'", "linux", False),
        ("anchored pkill runs", "pkill -9 -f '^/usr/bin/zzqq'", "linux", False),
        ("-x exact match runs", "pgrep -x -f zzqq", "linux", False),
        ("the [f]oo bracket cannot match itself, runs", "pgrep -f '[S]ublime Text'", "linux", False),
        ("a ^ anchor that DOES match the wrapper", "pgrep -f '^/bin/bash'", "linux", True),
        ("an alternation carrying its own text", "pgrep -f 'ruby.*rmate|^/usr/bin/rmate'", "linux", True),
        ("-i: case-folded pattern still self-matches", "pgrep -if ZZQQ", "linux", True),
        ("a POSIX class is not evaluated, denied", "pgrep -f '[[:alpha:]]zzqq'", "linux", True),
        ("the bracket through ssh cannot match the remote shell", "ssh box 'pgrep -f \"[z]zqq\"'", "linux", False),
        ("no -f runs", "pgrep zzqq", "linux", False),
        ("pkill signal letters are not -f", "pkill -HUP zzqq", "linux", False),
        ("pidof runs", "pidof zzqq", "linux", False),
        ("Darwin pgrep -f excludes ancestors", "pgrep -l -f zzqq", "darwin", False),
        ("Darwin pgrep -a -f includes them", "pgrep -a -l -f zzqq", "darwin", True),
        ("Darwin pkill -f still denied", "pkill -f zzqq", "darwin", True),
        ("prose in a commit message", 'git commit -m "never pkill -f zzqq"', "linux", False),
        ("echoed mention", "echo 'pgrep -f zzqq'", "linux", False),
        ("heredoc body is data", "cat > n.md <<'EOF'\npkill -f zzqq\nEOF", "linux", False),
        ("grep for the word", "grep -n 'pgrep -f' context/traps.md", "linux", False),
    ]
    for desc, cmd, plat, expect in pgrep_cases:
        check(f"ratenu: {desc}", _pgrep_self_match(cmd, plat) is not None, expect)
    # -- mewiwo: tmux kill-server / target-less kill-session with no socket.
    tmux_kill_cases = [
        ("the incident, verbatim", "export TMUX_TMPDIR=/tmp/x; tmux kill-server", True),
        ("bare kill-server", "tmux kill-server", True),
        ("unset in the same command is still no socket", "unset TMUX; tmux kill-server", True),
        ("env -u TMUX alone is the default server", "env -u TMUX tmux kill-server", True),
        ("abbreviated command", "tmux kill-ser", True),
        ("-f config is not a socket", "tmux -f ~/.tmux.conf kill-server", True),
        ("through ssh", "ssh box 'tmux kill-server'", True),
        ("through bash -c", "bash -c 'tmux kill-server'", True),
        ("in a compound after a private start", "tmux -L t new -d; tmux kill-server", True),
        ("kill-session with no target", "tmux kill-session", True),
        ("-L names the server", "tmux -L jt kill-server", False),
        ("-S names the server", "env -u TMUX tmux -S /tmp/x/default kill-server", False),
        ("glued -Lname", "tmux -Ljt kill-server", False),
        ("deliberate default", "tmux -L default kill-server", False),
        ("-S with $J variable expanded by the shell", "J='tmux -L jt'; tmux -L jt kill-server", False),
        ("kill-session with a target", "tmux kill-session -t hublot-x", False),
        ("kill-session -t glued", "tmux kill-session -thublot-x", False),
        ("kill-window is not this", "tmux kill-window -t @3", False),
        ("prose mention", 'git commit -m "never tmux kill-server bare"', False),
        ("grep for it", "grep -n 'kill-server' ~/.tmux.conf", False),
        ("heredoc body is data", "cat > n.md <<'EOF'\ntmux kill-server\nEOF", False),
    ]
    for desc, cmd, expect in tmux_kill_cases:
        check(f"mewiwo: {desc}", _tmux_kill_hazard(cmd) is not None, expect)
        check(f"mewiwo via probe_pre: {desc}", probe_pre(cmd) is not None, expect)
    # -- datoje: rm globs CC's dangerous-removal check cannot resolve. Every
    # case is a 2026-11-01 headless bypass probe (halt/ran on disk), or a
    # shape the parse must not misread.
    with tempfile.TemporaryDirectory() as rg:
        for d in ("a/sub/deep", "b/c"):
            os.makedirs(os.path.join(rg, d))
        ra = os.path.join(rg, "a")
        rm_glob_cases = [
            ("probe 1: cd then ../glob", f"cd {ra} && rm -rf ../b/*", True),
            ("probe 2: ../glob with no cd (the live halt)", "rm -rf ../b/*", True),
            ("probe 3: absolute glob runs", f"rm -rf {rg}/b/*", False),
            ("probe 4: absolute cd then relative glob runs", f"cd {ra} && rm -rf sub/*", False),
            ("probe 5: plain relative glob runs", "rm -rf sub/*", False),
            ("probe 6: two glob levels", f"rm -rf {rg}/b/*/*", True),
            ("probe 7: .. inside an absolute path", f"rm -rf {ra}/../b/*", True),
            ("probe 8: ../dir with no glob runs", f"cd {ra} && rm -rf ../b", False),
            ("probe 9: *.log runs", "rm -f *.log", False),
            ("probe 10: cd then *.log runs", f"cd {ra} && rm -f *.log", False),
            ("probe 11: ./sub/* runs", "rm -rf ./sub/*", False),
            ("probe 12: ~/.. glob", "rm -rf ~/../../tmp/x/b/*", True),
            ("probe 13: relative cd then glob", "cd sub && rm -f deep/*", True),
            ("probe 14: tracked-variable cd runs", f"X={rg}; cd $X/a && rm -f sub/*", False),
            ("probe 15: ../b/*.log runs", "rm -f ../b/*.log", False),
            ("probe 16: ../b/c/*", "rm -rf ../b/c/*", True),
            ("probe 19: cd into a dir made in this command", f"mkdir -p {rg}/new && cd {rg}/new && rm -rf *", True),
            ("the live command, verbatim tail", "T=/x; uv run -q --script run_nb.py $T/03.ipynb ../results-motoring --mode real 2>&1 | grep -E '^== '; rm -rf ../results-motoring/*; ls ../results-motoring", True),
            ("rmdir counts too", "rmdir ../b/*", True),
            ("after -- the glob is still a target", "rm -rf -- ../b/*", True),
            ("in a subshell", "(cd sub && rm -f deep/*)", True),
            ("a $VAR target is another branch, left alone", 'rm -rf "$S"/../b/*', False),
            ("heredoc body is data", "cat > n.sh <<'EOF'\nrm -rf ../b/*\nEOF", False),
            ("prose mention", 'git commit -m "never rm -rf ../b/*"', False),
            ("grep for it", "grep -n 'rm -rf ../b/*' notes.md", False),
            ("rsync is not rm", "rsync -a ../b/* /tmp/y/", False),
        ]
        for desc, cmd, expect in rm_glob_cases:
            check(f"datoje: {desc}", rm_glob_breaker(cmd, ra) is not None, expect)
            check(f"datoje via probe_pre: {desc}", probe_pre(cmd, ra) is not None, expect)
        rg_note = rm_glob_breaker("rm -rf ../b/*", ra) or ""
        check("datoje: the note names the resolved path and the source tag",
              f"`{os.path.realpath(rg)}/b/*`" in rg_note and rg_note.endswith(_RM_GLOB_TAG), True)
        check("datoje: a glob that lands on the cwd is not coached to an absolute path",
              "working directory" in (rm_glob_breaker("cd sub && rm -f ../*", ra) or ""), True)
        check("datoje: no cwd known, no invented path",
              "resolves to" not in (rm_glob_breaker("cd $D && cd x && rm -f y/*", ra) or "x"), True)
        check("datoje: perm_shape drops heredoc bodies",
              perm_shape("python3 - <<'EOF'\nc['source']\nEOF\nrm -rf ../b/*").get("firsts"), ["python3", "rm"])

    tk_note = _tmux_kill_hazard("tmux kill-server") or ""
    check("mewiwo: the reason names -L, -S and the source tag",
          all(s in tk_note for s in ("-L <name>", "-S <path>", "[traps.md: tmux kill without a socket]")), True)
    pg_note = _pgrep_self_match("pkill -9 -f zzqq", "linux") or ""
    check("ratenu: the reason names pidof, the ^ anchor and a PID",
          all(s in pg_note for s in ("pidof", "'^/path", "PID")), True)
    check("ratenu: probe_pre carries the pgrep deny",
          probe_pre("pgrep -lf zzqq") is not None if sys.platform != "darwin"
          else probe_pre("pgrep -a -lf zzqq") is not None, True)

    # -- ratenu: every settings.json Bash deny speaks (carte-habena's class).
    fake_rules = [("Bash(git add -A*)", "/x/settings.json"),
                  ("Bash(pgrep -f*)", "/x/settings.json"),
                  ("Bash(pkill -f*)", "/x/settings.json"),
                  ("Bash(npm publish:*)", "/x/settings.json"),
                  ("Bash(zzqq-unreasoned *)", "/x/settings.json"),
                  ("Read(~/.ssh/**)", "/x/settings.json"),
                  ("WebFetch", "/x/settings.json")]
    sd_cases = [
        ("git add -A alone", "git add -A", True),
        ("git add -A in a compound (the 28-30 Sep shape)",
         "cd ~/repos/x && git add -A && git commit -m wip", True),
        ("git add -A with a dir", "git add -A context/", True),
        ("git add by path", "git add context/traps.md", False),
        ("git add -A named in a commit message", 'git commit -m "no git add -A here"', False),
        ("env assignment stripped", "GIT_DIR=x git add -A", True),
        ("legacy :* prefix", "npm publish --dry-run", True),
        ("legacy :* is a word prefix", "npm publisher", False),
        ("a rule with no recorded reason still speaks", "zzqq-unreasoned now", True),
        ("Read and bare-tool rules are not Bash rules", "cat ~/.ssh/id_rsa.pub", False),
    ]
    for desc, cmd, expect in sd_cases:
        check(f"ratenu settings: {desc}",
              probe_settings_deny(cmd, rules=fake_rules) is not None, expect)
    sd_note = probe_settings_deny("pkill -f zzqq", rules=fake_rules) or ""
    check("ratenu settings: the reason names the rule, its file and the remedy",
          all(s in sd_note for s in ("`Bash(pkill -f*)`", "/x/settings.json",
                                     "pidof")), True)
    unr = probe_settings_deny("zzqq-unreasoned now", rules=fake_rules) or ""
    check("ratenu settings: an unrecorded rule points at its commit",
          "log -S 'Bash(zzqq-unreasoned *)'" in unr, True)
    check("ratenu settings: no Bash rules, no work",
          probe_settings_deny("git add -A", rules=[("WebFetch", "/x")]) is None, True)
    check("ratenu settings: every reason key is a Bash rule the live file can hold",
          all(k.startswith("Bash(") and k.endswith(")") for k in deny_rule_reasons()), True)
    # A broken settings file contributes nothing and never raises.
    with tempfile.TemporaryDirectory() as bad_cfg:
        os.makedirs(os.path.join(bad_cfg, ".claude"))
        with open(os.path.join(bad_cfg, ".claude", "settings.json"), "w") as fh:
            fh.write('{"permissions": {"deny": "not-a-list"')
        with open(os.path.join(bad_cfg, ".claude", "settings.local.json"), "w") as fh:
            fh.write('{"permissions": ["wrong-shape"]}')
        check("ratenu settings: malformed project settings read as no rules",
              [p for _, p in _settings_deny(bad_cfg) if p.startswith(bad_cfg)] == [], True)
    # End to end through --pre, against a config dir of our own, so the
    # test does not depend on what the live settings.json holds today.
    import subprocess as _sp
    with tempfile.TemporaryDirectory() as cfg:
        with open(os.path.join(cfg, "settings.json"), "w") as fh:
            json.dump({"permissions": {"deny": ["Bash(git add -A*)"]}}, fh)

        def _pre_e2e(command: str, background: bool = False):
            tin = {"command": command}
            if background:
                tin["run_in_background"] = True
            out = _sp.run(
                [sys.executable, __file__, "--pre"],
                input=json.dumps({"tool_name": "Bash", "cwd": "/tmp",
                                  "tool_input": tin,
                                  "agent_id": "t", "agent_type": "t"}),
                capture_output=True, text=True,
                env={**os.environ, "CLAUDE_CONFIG_DIR": cfg,
                     "GOUTEUR_STATE_DIR": cfg},
            ).stdout.strip()
            return json.loads(out)["hookSpecificOutput"] if out else None

        e2e = _pre_e2e("cd /tmp && git add -A")
        check("ratenu e2e: a settings deny arrives as a goûteur deny with the rule",
              bool(e2e) and e2e["permissionDecision"] == "deny"
              and "`Bash(git add -A*)`" in e2e["permissionDecisionReason"], True)
        check("ratenu e2e: a path-staged add passes untouched",
              _pre_e2e("cd /tmp && git add a.txt") is None, True)
        e2e_pg = _pre_e2e("pkill -9 -f zzqq")
        check("ratenu e2e: pkill -9 -f is denied with the pgrep reason",
              bool(e2e_pg) and "pgrep -f self-match" in e2e_pg["permissionDecisionReason"], True)
        e2e_bs = _pre_e2e("sleep 90; gh run list --limit 1")
        check("holuka e2e: a foreground blind sleep is denied with the rewrite",
              bool(e2e_bs) and e2e_bs["permissionDecision"] == "deny"
              and "run_in_background=true" in e2e_bs["permissionDecisionReason"], True)
        check("holuka e2e: the same command with run_in_background passes",
              _pre_e2e("sleep 90; gh run list --limit 1", background=True) is None, True)
        check("holuka e2e: a declared deliberate-wait passes",
              _pre_e2e("sleep 60; dig +short x  # deliberate-wait: TTL settle") is None, True)

    check("env dump coaching names compgen -e",
          "compgen -e" in (probe_pre("env") or ""), True)
    board_note = probe_pre(f"echo x >> {brd}") or ""
    check("board coaching names bon restore and the missing-verb route",
          "bon restore ID" in board_note and "missing verb" in board_note, True)
    check("board relative write resolves against the hook cwd (scratch cwd exempt)",
          probe_pre(f"echo x > {rel}", "/tmp/claude-1000/s") is None, True)
    check("board escape is read back with its reason",
          bon_board_escape("sed -i s/a/b/ f  # bon-handedit: conflict repair") == "conflict repair", True)

    # -- holuka: a foreground blind sleep. Positives are the census's own
    # shapes (1 Sep–6 Oct 2026); near misses are the watched, backgrounded,
    # short, quoted and declared forms that must stay silent.
    BS = "[traps.md: blind sleep]"
    blind_cases = [
        ("blind: the commonest census shape", "sleep 90; gh run list -R org/repo", False, True),
        ("blind: a settle after a restart", "systemctl --user restart paseo; sleep 45; systemctl --user is-active paseo", False, True),
        ("blind: through the command wrapper", "command sleep 45; gh run list --limit 2 2>&1 | head -3", False, True),
        ("blind: minutes", "sleep 2m && tail -3 run.log", False, True),
        ("blind: GNU sums its arguments", "sleep 20 20; date", False, True),
        ("blind: inside a substitution", "x=$(sleep 60; date)", False, True),
        ("blind: a bare long sleep", "sleep 290; echo waited", False, True),
        ("blind: 2>&1 is not a background &", "sleep 45; gh run list 2>&1 | tail -3", False, True),
        ("blind: exactly the threshold", "sleep 30; curl -s localhost:8080", False, True),
        ("near miss: run_in_background", "sleep 90; gh run list", True, False),
        ("near miss: an until-loop on the condition", "until gh run view 1 --json status -q .status | grep -qx completed; do sleep 30; done", False, False),
        ("near miss: a for-loop poll", "for i in 1 2 3; do sleep 60; curl -s x; done", False, False),
        ("near miss: a watchdog backgrounded with &", "(sleep 60; kill $pid) & wait $pid", False, False),
        ("near miss: the probe's own arming shape", "(sleep 45; touch /tmp/flag) & echo armed", False, False),
        ("near miss: under 30 s", "sleep 29; curl -s localhost:8080", False, False),
        ("near miss: sleep in quoted prose", "git commit -m 'sleep 90 then check'", False, False),
        ("near miss: inside an ssh payload (not unwrapped)", "ssh box 'sleep 60; uptime'", False, False),
        ("near miss: a variable duration", "sleep $n; date", False, False),
        ("near miss: sleep infinity", "sleep infinity", False, False),
        ("near miss: a heredoc body", "cat <<'EOF' > s.sh\nsleep 90\nEOF\nchmod +x s.sh", False, False),
        ("near miss: declared deliberate-wait", "sleep 60; dig x  # deliberate-wait: DNS TTL settle", False, False),
        ("near miss: sleep as a word, not a command", "ls ~/sleep-data/ && echo 90", False, False),
        # essayeur folds, 2026-10-10
        ("blind: a trailing comment does not hide the duration", "sleep 60  # wait for CI\ngh run list", False, True),
        ("blind: a redirect does not hide the duration", "sleep 60 2>/dev/null; gh run list", False, True),
        ("near miss: timeout caps the sleep", "timeout 5 sleep 60; echo $?", False, False),
        ("near miss: for over the positional args", "for x; do sleep 60; ./check $x; done", False, False),
        ("near miss: a select loop", "select x in a b; do sleep 60; done", False, False),
        ("near miss: a backslash heredoc delimiter", "git commit -m \"$(cat <<\\EOF\nwait\nsleep 60\nEOF\n)\"", False, False),
    ]
    for desc, cmd, bg, expect in blind_cases:
        check(desc, BS in (probe_pre(cmd, "", bg) or ""), expect)
    check("holuka: the note names the measured duration",
          "sleeps 120s" in (blind_sleep("sleep 2m; date") or ""), True)
    check("holuka: the escape is read back with its reason",
          deliberate_wait_escape("sleep 60  # deliberate-wait: TTL settle") == "TTL settle", True)
    in_class, remedied = FOLLOWED["traps-blind-sleep"]
    check("holuka FOLLOWED: a sleep is in class", in_class("sleep 90; gh run list"), True)
    check("holuka FOLLOWED: the until-loop counts as the remedy",
          remedied("until [ -f x ]; do sleep 5; done"), True)
    check("holuka FOLLOWED: a repeat blind sleep does not",
          remedied("sleep 120; gh run list"), False)
    check("board tool path: a real board is caught",
          bool(bon_board_tool_path({"tool_input": {"file_path": brd}})), True)
    check("board tool path: a /tmp board is exempt",
          bon_board_tool_path({"tool_input": {"file_path": "/tmp/x/" + rel}}) is None, True)
    check("board tool path: the bottle is not the board",
          bon_board_tool_path({"tool_input": {"file_path": brd.replace("items.jsonl", "README.md")}}) is None, True)
    check("board post-hoc render fires on a real board, tag last (its id)",
          [_render_id(n) for n in probe_edit(brd)] == ["traps-bon-board-hand-edits"], True)
    check("board post-hoc render silent on a scratch board",
          any("bon board hand-edits" in n for n in probe_edit("/tmp/x/" + rel)), False)

    # -- _pre_caller(): caller discrimination (carte-suruta). Fixtures mirror
    # the payloads measured live 2026-08-24 (CC 2.1.241). The gated command
    # is built programmatically so this file's own self-test invocation
    # never carries a gate-matching string.
    import subprocess
    import tempfile

    gated_cmd = "cat ~/dl/" + "sa-key" + ".json"
    with tempfile.NamedTemporaryFile(
        "w", suffix=".jsonl", delete=False
    ) as tf:
        tf.write(json.dumps({
            "type": "assistant", "isSidechain": False,
            "message": {"content": [{"type": "tool_use", "id": "toolu_TOP1"}]},
        }) + "\n")
        tf.write(json.dumps({
            "type": "assistant", "isSidechain": True,
            "message": {"content": [{"type": "tool_use", "id": "toolu_SIDE2"}]},
        }) + "\n")
        transcript = tf.name

    def top_payload(**over):
        p = {
            "cwd": "/tmp", "hook_event_name": "PreToolUse",
            "permission_mode": "bypassPermissions", "prompt_id": "p-1",
            "session_id": "s-1", "tool_input": {"command": gated_cmd},
            "tool_name": "Bash", "tool_use_id": "toolu_TOP1",
            "transcript_path": transcript, "effort": {"level": "xhigh"},
        }
        p.update(over)
        return p

    caller_cases = [
        ("worker depth-1: agent keys present",
         top_payload(agent_id="abc123", agent_type="general-purpose"),
         "agent"),
        ("worker shape drift: agent_type alone still a worker",
         top_payload(agent_type="fork"), "agent"),
        ("worker shape drift: agent_id present but null still a worker",
         top_payload(agent_id=None), "agent"),
        # sapaco (2026-09-30): no transcript proof is demanded any more, so
        # the id's presence, absence or sidechain marking changes nothing.
        ("top level, id in root transcript", top_payload(), "other"),
        ("top level, id not yet flushed (the measured 5-of-6 case)",
         top_payload(tool_use_id="toolu_NOWHERE"), "other"),
        ("renamed agent field: the accepted limit, coached as other",
         top_payload(subagent_ref="abc"), "other"),
        ("empty payload", {}, "other"),
    ]
    for desc, payload, expect in caller_cases:
        check(desc, _pre_caller(payload) == expect, True)

    # -- main() --pre end to end: every caller gets deny since 2026-08-30
    # (carte-jegise: a hook ask never renders a dialog — CC auto-denies it
    # and drops the reason). The caller discrimination now lives in the
    # REASON text, so that is what the fixtures pin.
    # Every e2e subprocess logs into THIS scratch dir, never the live census:
    # denies now log (carte-nasara), and a fixture row under a live render id
    # is indistinguishable from a real fire (the leak carte-sikoce's cold read
    # found, 15 rows deep).
    e2e_state = tempfile.mkdtemp(prefix="gouteur-e2e-")
    e2e_fires = os.path.join(e2e_state, "fires.jsonl")

    def run_pre(payload):
        out = subprocess.run(
            [sys.executable, __file__, "--pre"],
            input=json.dumps(payload), capture_output=True, text=True,
            env={**os.environ, "GOUTEUR_STATE_DIR": e2e_state},
        ).stdout.strip()
        if not out:
            return None
        return json.loads(out)["hookSpecificOutput"]

    def e2e_fired():
        try:
            return [json.loads(l) for l in open(e2e_fires, encoding="utf-8") if l.strip()]
        except OSError:
            return []

    check("e2e: worker caller gets deny",
          run_pre(top_payload(agent_id="abc", agent_type="general-purpose"))
          ["permissionDecision"] == "deny", True)
    top_out = run_pre(top_payload())
    check("e2e: top-level caller gets deny — a hook ask never renders",
          top_out["permissionDecision"] == "deny", True)
    # -- nasara: denies are census rows like any render, with the shared fields.
    _rows = e2e_fired()
    check("nasara: a Bash credential deny is logged under its render id",
          [r["render"] for r in _rows] == ["traps-credential-directories"] * 2, True)
    check("nasara: fires records carry host, mode and agent",
          len(_rows) == 2 and _rows[0]["agent"] is True and _rows[1]["agent"] is False
          and _rows[0]["mode"] == "bypassPermissions"
          and _rows[0]["host"] == socket.gethostname(), True)
    run_pre(top_payload(tool_name="Read", tool_input={"file_path": "~/dl/sa-key.json"}))
    check("nasara: a Read credential deny is logged too",
          [r["render"] for r in e2e_fired()][-1] == "traps-credential-directories", True)
    check("nasara: deny records carry no path text",
          "sa-key" not in open(e2e_fires, encoding="utf-8").read(), True)
    check("e2e: top-level reason is the rephrase coaching, not the drift "
          "message",
          "Rephrase and self-serve" in top_out["permissionDecisionReason"]
          and "could not recognise" not in
          top_out["permissionDecisionReason"], True)
    # Was "drifted shape gets deny" until 2026-08-30. An extra key is no
    # longer drift (carte-fijeva); what must still deny end-to-end is a
    # caller the poll cannot place — here a tool_use_id absent from the root
    # transcript, which is the shape a renamed agent field would present.
    for label, pl in (("unflushed id", top_payload(tool_use_id="toolu_NOWHERE")),
                      ("empty-ish payload", {"tool_name": "Bash",
                                             "tool_input": {"command": gated_cmd}})):
        _r = (run_pre(pl) or {}).get("permissionDecisionReason", "")
        check(f"sapaco e2e: {label} — denied, and no reason claims a CC update",
              bool(_r) and "Claude Code update" not in _r
              and "could not recognise" not in _r, True)
    check("e2e: unplaceable caller gets deny (fail closed)",
          run_pre(top_payload(tool_use_id="toolu_NOWHERE"))
          ["permissionDecision"] == "deny", True)
    check("e2e: extra payload key still classifies as top — its reason is "
          "the coaching, not the drift message",
          "Rephrase and self-serve" in
          run_pre(top_payload(novel_field=1))["permissionDecisionReason"],
          True)
    # -- the re-homed Read() deny rules (2026-09-06). Known-bad first: each of
    # the three paths the settings rules used to guard, through the tool that
    # would surface its content. Then the negatives that matter — an ordinary
    # file must stay silent through the SAME tool, or the gate is a brick.
    for tool_name, field, path, label in [
        ("Read", "file_path", "/home/u/dl/sa-key.json", "secrets, absolute"),
        ("Read", "file_path", "~/dl/sa-key.json", "secrets, tilde"),
        ("Read", "file_path", "$HOME/.config/gcloud/logs/x.log", "gcloud logs, $HOME"),
        ("Grep", "path", "/home/u/.config/gcloud/logs", "grep over the log dir"),
        ("Glob", "pattern", "**/sa-key.json", "glob at the secrets dir"),
    ]:
        out = run_pre(top_payload(tool_name=tool_name, tool_input={field: path}))
        check(f"e2e: {tool_name} denied — {label}",
              out is not None and out["permissionDecision"] == "deny", True)
    check("e2e: the credential deny names the core it matched",
          "sa-key.json" in run_pre(top_payload(
              tool_name="Read",
              tool_input={"file_path": "/home/u/dl/sa-key.json"},
          ))["permissionDecisionReason"], True)
    check("e2e: a worker is denied the same way — nobody sits at its dialog",
          run_pre(top_payload(
              tool_name="Read", tool_input={"file_path": "~/dl/sa-key.json"},
              agent_id="abc", agent_type="general-purpose",
          ))["permissionDecision"] == "deny", True)
    for tool_name, field, path, label in [
        ("Read", "file_path", "/home/u/.claude/CLAUDE.md", "an ordinary file"),
        ("Read", "file_path", "/home/u/.local/state/gouteur/fires.jsonl",
         "a sibling under .local that is not the secrets dir"),
        ("Grep", "path", "/home/u/.config/gcloud", "the gcloud dir above logs"),
        ("Glob", "pattern", "**/*.py", "an ordinary glob"),
    ]:
        check(f"e2e: {tool_name} stays silent — {label}",
              run_pre(top_payload(tool_name=tool_name,
                                  tool_input={field: path})) is None, True)
    check("e2e: a non-string path still denies rather than opening the gate",
          run_pre(top_payload(
              tool_name="Read",
              tool_input={"file_path": ["~/dl/sa-key.json"]},
          ))["permissionDecision"] == "deny", True)
    check("e2e: a tool outside the map is not gated by this branch",
          run_pre(top_payload(tool_name="WebFetch",
                              tool_input={"url": "http://x/dl/sa-key.json"}))
          is None, True)
    # Declaration without wiring is the fault this gate replaced. The matcher
    # in plugin.json (beside this file's hooks/ directory) must name every
    # tool the map claims, or the entries are inert and every fixture above
    # still passes (it drives the script, never the hook wiring).
    _pj = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                       ".claude-plugin", "plugin.json")
    try:
        with open(_pj, encoding="utf-8") as _f:
            _pre = json.load(_f)["hooks"]["PreToolUse"]
        _wired = " ".join(
            h.get("matcher", "") for h in _pre
            if any("gouteur" in c.get("command", "") and "--pre" in c.get("command", "")
                   for c in h.get("hooks", []))
        )
        check("wiring: every gated tool appears in plugin.json's PreToolUse matcher",
              sorted(t for t in CREDENTIAL_PATH_TOOLS if t not in _wired), [])
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        check(f"wiring: plugin.json unreadable ({type(exc).__name__}) "
              "— matcher coverage UNPROVEN", False, True)

    check("e2e: ungated command stays silent whoever calls",
          run_pre(top_payload(
              tool_input={"command": "ls -la /tmp"},
              agent_id="abc", agent_type="general-purpose",
          )) is None, True)
    check("e2e: non-string command with gated text still denies a worker",
          run_pre(top_payload(
              tool_input={"command": {"c": gated_cmd}},
              agent_id="abc", agent_type="general-purpose",
          ))["permissionDecision"] == "deny", True)

    # -- rewrite_after_cd(): relative paths after a cd (carte-sikoce).
    # The known-positive is the exact subagent command that stalled on
    # a terminal on 2026-09-03. Negatives are every decline rule,
    # each one a shape where a wrong rewrite would be worse than the prompt.
    with tempfile.TemporaryDirectory() as td:
        # Keep every e2e subprocess's log_fires/log_perm write out of the real
        # census — the allow path logs, and a fixture row under a live render
        # id is indistinguishable from a real fire.
        os.environ["GOUTEUR_STATE_DIR"] = td
        repo = os.path.join(td, "arm2")
        os.makedirs(os.path.join(repo, "src"))
        for name in ("pyproject.toml", "3", "py", "other.txt"):
            with open(os.path.join(repo, name), "w") as fh:
                fh.write("mcp\n")
        with open(os.path.join(repo, "src", "a.py"), "w") as fh:
            fh.write("x\n")
        secrets = os.path.join(td, "vault")
        os.makedirs(secrets)
        with open(os.path.join(secrets, "token"), "w") as fh:
            fh.write("shh\n")
        # `//` is CC's filesystem-root form: `//tmp/x` means /tmp/x.
        rules = [f"/{secrets}/**", "~/.config/gcloud/logs/**"]

        def rw(cmd, cwd=td, deny=rules):
            return rewrite_after_cd(cmd, cwd, deny)

        pos = rw(f'cd {repo} && grep -n "mcp" pyproject.toml | head -20 && '
                 'ls .venv/lib/python*/site-packages/ 2>/dev/null | head -5')
        check("cd-rewrite: known positive — the stalled subagent command "
              "rewrites pyproject.toml", pos is not None and
              f'grep -n "mcp" {repo}/pyproject.toml | head' in pos[0], True)
        check("cd-rewrite: everything else in the compound is byte-identical",
              pos is not None and pos[0].startswith(f"cd {repo} && ")
              and pos[0].endswith("2>/dev/null | head -5"), True)
        check("cd-rewrite: note names the row and the rewrite",
              pos is not None and "pyproject.toml →" in pos[1]
              and "[traps.md: relative path after a bare cd]" in pos[1], True)
        check("cd-rewrite: ls in the compound is read-only",
              pos is not None and pos[2] is True, True)
        check("cd-rewrite: no cd → None",
              rw("grep -n mcp pyproject.toml", cwd=repo) is None, True)
        check("cd-rewrite: already absolute → None",
              rw(f"cd {repo} && grep -n mcp {repo}/pyproject.toml") is None, True)
        check("cd-rewrite: ~ path → None",
              rw(f"cd {repo} && grep -n mcp ~/nothing.toml") is None, True)
        check("cd-rewrite: no Read deny rules → None (mirrors CC's gate)",
              rw(f"cd {repo} && grep -n mcp pyproject.toml", deny=[]) is None, True)
        check("cd-rewrite: resolved path under a Read deny rule DECLINES",
              rw(f"cd {secrets} && grep -n shh token") is None, True)
        check("cd-rewrite: relative cd resolves against the hook cwd",
              (rw("cd arm2 && rg -n mcp .") or ("",))[0]
              == f"cd arm2 && rg -n mcp {repo}", True)
        check("cd-rewrite: cd into a missing directory → None",
              rw(f"cd {td}/nope && grep mcp pyproject.toml") is None, True)
        check("cd-rewrite: 2>/dev/null survives and fd digit is not a path",
              (rw(f"cd {repo} && grep -rn mcp . 2>/dev/null") or ("",))[0]
              == f"cd {repo} && grep -rn mcp {repo} 2>/dev/null", True)
        check("cd-rewrite: 2>&1 survives",
              (rw(f"cd {repo} && grep -n mcp other.txt 2>&1 | head") or ("",))[0]
              == f"cd {repo} && grep -n mcp {repo}/other.txt 2>&1 | head", True)
        check("cd-rewrite: a value option's token is not a path even when a "
              "file of that name exists (-A 3, rg -t py)",
              (rw(f"cd {repo} && grep -A 3 mcp other.txt") or ("",))[0]
              == f"cd {repo} && grep -A 3 mcp {repo}/other.txt"
              and (rw(f"cd {repo} && rg -t py mcp .") or ("",))[0]
              == f"cd {repo} && rg -t py mcp {repo}", True)
        check("cd-rewrite: pattern equal to a filename stays the pattern",
              (rw(f"cd {repo} && grep pyproject.toml pyproject.toml") or ("",))[0]
              == f"cd {repo} && grep pyproject.toml {repo}/pyproject.toml", True)
        check("cd-rewrite: -e supplies the pattern, so the first positional "
              "is a path",
              (rw(f"cd {repo} && grep -e mcp other.txt") or ("",))[0]
              == f"cd {repo} && grep -e mcp {repo}/other.txt", True)
        check("cd-rewrite: short cluster ending in e (-rne) supplies the pattern",
              (rw(f"cd {repo} && grep -rne mcp src") or ("",))[0]
              == f"cd {repo} && grep -rne mcp {repo}/src", True)
        check("cd-rewrite: diff rewrites both positionals",
              (rw(f"cd {repo} && diff other.txt pyproject.toml") or ("",))[0]
              == f"cd {repo} && diff {repo}/other.txt {repo}/pyproject.toml", True)
        check("cd-rewrite: quoted path keeps its quotes",
              (rw(f"cd {repo} && grep -n mcp 'other.txt'") or ("",))[0]
              == f"cd {repo} && grep -n mcp '{repo}/other.txt'", True)
        check("cd-rewrite: glob and $ tokens are left alone",
              rw(f"cd {repo} && grep -n mcp *.toml") is None
              and rw(f"cd {repo} && grep -n mcp $F") is None, True)
        check("cd-rewrite: a path that does not exist is left alone",
              rw(f"cd {repo} && grep -n mcp missing.toml") is None, True)
        check("cd-rewrite: cp/mv/git are NOT rewritten",
              rw(f"cd {repo} && cp other.txt /tmp/x") is None
              and rw(f"cd {repo} && mv other.txt /tmp/x") is None
              and rw(f"cd {repo} && git diff other.txt") is None, True)
        check("cd-rewrite: subshell / substitution / heredoc / background bail",
              rw(f"(cd {repo} && grep mcp other.txt)") is None
              and rw(f"cd {repo} && grep mcp $(echo other.txt)") is None
              and rw(f"cd {repo} && grep mcp other.txt <<EOF\nx\nEOF") is None
              and rw(f"cd {repo} && grep mcp other.txt &") is None, True)
        check("cd-rewrite: grep before the cd is not touched",
              rw(f"grep mcp other.txt; cd {repo}", cwd=repo) is None, True)
        check("cd-rewrite: a mutating tail marks the compound not read-only",
              (rw(f"cd {repo} && grep -l mcp other.txt | xargs rm") or (0, 0, True))[2]
              is False, True)
        check("cd-rewrite: badly axis — unbalanced quote declines, no crash",
              rw(f"cd {repo} && grep \"mcp other.txt") is None, True)

        # -- twin review 2026-09-06 (carte-visoce): the six critical faults,
        # each shown red on cafed70/2edb199 before its fix.
        # 1. An unknown value-taking long option shifted the pattern into the
        #    path slot: with repo/foo present, `foo` was rewritten and the
        #    search then looked for a literal path string — a confident null.
        with open(os.path.join(repo, "foo"), "w") as fh:
            fh.write("x\n")
        check("cd-rewrite: unknown long option declines (value or flag is unknowable)",
              rw(f"cd {repo} && rg --ignore-file .gitignore foo src") is None
              and rw(f"cd {repo} && grep --group-separator foo other.txt") is None, True)
        check("cd-rewrite: known no-value long options still rewrite",
              (rw(f"cd {repo} && rg --no-ignore --hidden mcp other.txt") or ("",))[0]
              == f"cd {repo} && rg --no-ignore --hidden mcp {repo}/other.txt", True)
        # 2. read_only came from first words only, so `> f`, `| tee f` and
        #    `sort -o f` left it True and default mode waved a write through.
        check("cd-rewrite: a > redirect to a file marks the compound not read-only",
              (rw(f"cd {repo} && grep -n mcp other.txt > OUT") or (0, 0, True))[2] is False
              and (rw(f"cd {repo} && grep -n mcp other.txt >> OUT") or (0, 0, True))[2] is False, True)
        check("cd-rewrite: tee and sort -o mark the compound not read-only",
              (rw(f"cd {repo} && grep -n mcp other.txt | tee OUT") or (0, 0, True))[2] is False
              and (rw(f"cd {repo} && grep -n mcp other.txt | sort -o OUT") or (0, 0, True))[2] is False, True)
        check("cd-rewrite: 2>/dev/null and 2>&1 stay read-only",
              (rw(f"cd {repo} && grep -n mcp other.txt 2>/dev/null") or (0, 0, False))[2] is True
              and (rw(f"cd {repo} && grep -n mcp other.txt 2>&1 | sort") or (0, 0, False))[2] is True, True)
        # 6. shlex is quadratic in one token's length: an 800 KB base64 arg
        #    after a cd stalled --pre for 20-33 s. Bail before tokenising.
        _t0 = time.time()
        _long = rw(f"cd {repo} && grep -F {'a' * 300_000} other.txt")
        check("cd-rewrite: a 300 KB token declines in well under a second",
              _long is None and time.time() - _t0 < 1.0, True)
        _t0 = time.time()
        _long = perm_shape(f"cd {repo} && grep -F {'a' * 300_000} other.txt")
        check("perm-shape: a 300 KB token is reported, not tokenised",
              _long.get("parse") == "too-long" and time.time() - _t0 < 1.0, True)
        # 4. Dotfile rules: `.lstrip("./")` ate the leading dot, so Read(.env)
        #    never matched and the rewrite handed a denied path back as resolved.
        check("read-deny: dotfile rules match (.env, ./.env, .git/**)",
              _under_read_deny("/r/.env", [".env"])
              and _under_read_deny("/r/.env", ["./.env"])
              and _under_read_deny("/r/.git/config", [".git/**"])
              and _under_read_deny("/r/sub/.envrc", [".envrc"]), True)
        check("read-deny: a dotfile rule does not match the undotted name",
              _under_read_deny("/r/env", [".env"]), False)
        # -- garebi (2026-09-06)
        # A backslash-escaped space is two shlex tokens in non-posix mode; the
        # coverage check passed and the second half was rewritten alone.
        check("cd-rewrite: a backslash-escaped space declines",
              rw(f"cd {repo} && grep foo x\\ other.txt") is None, True)
        # `cd X || grep` runs the grep only when the cd FAILED, so resolving
        # against X is the wrong directory.
        check("cd-rewrite: a segment joined to the cd by || declines",
              rw(f"cd {repo} || grep mcp other.txt") is None, True)
        # --pre parsed three settings files on every Bash call before looking
        # for a cd; the cd check is free and 99% of calls have none.
        _saved_rd = globals()["_read_deny_rules"]

        def _boom(cwd):
            raise AssertionError("settings read before the cd check")
        globals()["_read_deny_rules"] = _boom
        try:
            try:
                _no_cd_ok = rewrite_after_cd("ls -la /tmp", repo) is None
            except AssertionError:
                _no_cd_ok = False
            try:
                rewrite_after_cd(f"cd {repo} && grep mcp other.txt", repo)
                _cd_reads = False
            except AssertionError:
                _cd_reads = True
        finally:
            globals()["_read_deny_rules"] = _saved_rd
        check("cd-rewrite: no cd → settings files are never opened; with a cd they are",
              _no_cd_ok and _cd_reads, True)

        # e2e through main(): allow + updatedInput + additionalContext, the
        # credential deny still wins, ordinary commands stay silent, and a
        # mutating tail is allowed only in bypass mode.
        shape = f"cd {repo} && grep -n mcp pyproject.toml"
        os.environ["CLAUDE_CONFIG_DIR"] = td
        os.makedirs(os.path.join(td, ".claude"), exist_ok=True)
        with open(os.path.join(td, "settings.json"), "w") as fh:
            json.dump({"permissions": {"deny": [f"Read(/{secrets}/**)"]}}, fh)
        try:
            out = run_pre(top_payload(tool_input={"command": shape, "description": "d"}))
            check("cd-rewrite e2e: allow with rewritten updatedInput",
                  out is not None and out["permissionDecision"] == "allow"
                  and out["updatedInput"]["command"] == f"cd {repo} && grep -n mcp {repo}/pyproject.toml"
                  and out["updatedInput"]["description"] == "d", True)
            check("cd-rewrite e2e: additionalContext carries the note",
                  out is not None and "goûteur rewrote 1 relative path" in out["additionalContext"], True)
            check("cd-rewrite e2e: credential deny still wins over a rewrite",
                  run_pre(top_payload(tool_input={
                      "command": f"cd {repo} && grep -n x pyproject.toml ~/dl/sa-key.json"}))
                  ["permissionDecision"] == "deny", True)
            check("cd-rewrite e2e: ordinary command stays silent",
                  run_pre(top_payload(tool_input={"command": "ls -la /tmp"})) is None, True)
            check("cd-rewrite e2e: mutating tail in default mode → silent (CC prompts as before)",
                  run_pre(top_payload(permission_mode="default", tool_input={
                      "command": f"cd {repo} && grep -l mcp other.txt | xargs rm"})) is None, True)
            check("cd-rewrite e2e: mutating tail in bypass mode → allow (nothing to over-approve)",
                  (run_pre(top_payload(tool_input={
                      "command": f"cd {repo} && grep -l mcp other.txt | xargs rm"})) or {})
                  .get("permissionDecision") == "allow", True)
            check("cd-rewrite e2e: worker caller gets the rewrite too",
                  (run_pre(top_payload(tool_input={"command": shape},
                                       agent_id="abc", agent_type="general-purpose")) or {})
                  .get("permissionDecision") == "allow", True)
            # 5. (carte-visoce) A list-shaped tool_input raised inside the gate;
            #    the outer fail-open swallowed it and the gated command ran.
            _lst = run_pre(top_payload(tool_input=[gated_cmd]))
            check("e2e: a list-shaped tool_input is still denied, not opened",
                  (_lst or {}).get("permissionDecision") == "deny", True)
            check("e2e: a scalar tool_input is handled, not crashed on",
                  run_pre(top_payload(tool_input=5)) is None, True)
            _crash = run_pre([1, 2])  # a payload that is not even a dict
            check("e2e: an undesigned --pre crash fails CLOSED and names itself",
                  (_crash or {}).get("permissionDecision") == "deny"
                  and "gouteur crashed" in (_crash or {}).get("permissionDecisionReason", ""), True)
        finally:
            del os.environ["CLAUDE_CONFIG_DIR"]

        # -- perm_shape() / --perm: the residual-dialog census (carte-datoje).
        # Shape only: the record must never carry the command text.
        sh = perm_shape(f"cd {repo} && git diff other.txt | head")
        check("perm-shape: cd then git with a relative arg is flagged",
              sh.get("cd_then_relative") is True and sh.get("firsts") == ["cd", "git", "head"], True)
        check("perm-shape: absolute arg after cd is not flagged",
              perm_shape(f"cd {repo} && cp /a /b").get("cd_then_relative") is False, True)
        check("perm-shape: no cd is not flagged",
              perm_shape("git diff other.txt").get("cd_then_relative") is False, True)
        check("perm-shape: badly axis — unbalanced quote reports parse failure, no crash",
              perm_shape('grep "x').get("parse") == "failed", True)
        # 3. (carte-visoce) The first token of `VAR=value cmd` IS the value, and
        #    it was logged verbatim — a token in a mode-644 census file.
        _sh = perm_shape("TOKEN=sk-SECRETVALUE claude -p hi | X=1 Y=2 grep -n foo")
        check("perm-shape: env assignments are never logged as first words",
              _sh.get("firsts") == ["claude", "grep"]
              and "SECRETVALUE" not in json.dumps(_sh), True)
        check("perm-shape: a path-shaped first word logs only its basename",
              perm_shape("/home/x/private-tool --flag; ./run-private.sh")
              .get("firsts") == ["private-tool", "run-private.sh"], True)
        global _PERMS_LOG
        saved_log = _PERMS_LOG
        _PERMS_LOG = os.path.join(td, "perms.jsonl")
        try:
            log_perm({"tool_name": "Bash", "permission_mode": "default",
                      "session_id": "s-9", "agent_id": "a1",
                      "tool_input": {"command": f"cd {repo} && mv SECRET-NAME.txt elsewhere"}})
            rec = json.loads(open(_PERMS_LOG).read().splitlines()[-1])
            check("perm-log: record carries shape fields and agent flag",
                  rec["tool"] == "Bash" and rec["agent"] is True
                  and rec["cd_then_relative"] is True and rec["firsts"] == ["cd", "mv"], True)
            check("perm-log: record carries NO command text",
                  "SECRET-NAME" not in open(_PERMS_LOG).read(), True)
        finally:
            _PERMS_LOG = saved_log
        os.environ.pop("GOUTEUR_STATE_DIR", None)
    shutil.rmtree(e2e_state, ignore_errors=True)
    os.unlink(transcript)

    # ---- carte-mirote: render ids and the fires log -------------------
    # Built fixture-first: each case below was written against the real
    # behaviour, then the checking side was broken to prove it goes red.

    def _check(label: str, got, want) -> None:
        nonlocal total, failures
        total += 1
        ok = got == want
        if not ok:
            failures += 1
        print(f"{'PASS' if ok else 'FAIL'}  {label}  (got={got!r}, expected={want!r})")

    _check(
        "mirote: id derives from the trailing source tag",
        _render_id("goûteur: blah blah. [traps.md: recursive grep]"),
        "traps-recursive-grep",
    )
    _check(
        "mirote: a bare card-id tag works too",
        _render_id("goûteur: model changed under it. [" + "carte-rovudo]"),
        "carte-rovudo",
    )
    _check(
        "mirote: NEGATIVE — an untagged note is named, not silently dropped",
        _render_id("goûteur: something with no tag at all"),
        "untagged",
    )
    _check(
        "mirote: NEGATIVE — a bracket mid-note does not become the id",
        _render_id("goûteur: use [this] instead. [traps.md: find/bfs]"),
        "traps-find-bfs",
    )

    # Every id this file can emit must be in the frozen registry, and every
    # registered id must still be emitted somewhere — this is what makes an
    # edited tag fail loudly instead of silently splitting one render's
    # history across two ids. Scanned from SOURCE (carte-nasara): the older
    # six-fixture form only saw probe(), and the cd-rewrite render sat
    # unregistered through 77 live fires.
    _src = open(__file__, encoding="utf-8").read()
    _unreg, _dead = _registry_drift(_src)
    _check("nasara: every render tag in source is registered", _unreg, [])
    _check("nasara: every registered id is emitted somewhere in source", _dead, [])
    # Positive control in the same run: the scan must be able to go red.
    # (Built by concatenation so the literal tag is not itself in the source.)
    _check("nasara: control — a synthetic unregistered tag IS flagged",
           _registry_drift(_src + "\n# [traps" + ".md: synthetic drift]\n")[0],
           ["traps-synthetic-drift"])

    # The log write itself — against a TEMP log, never production: this
    # fixture used to append to the real fires.jsonl on every self-test
    # run (11 selftest records by the time it was caught, carte-lekivi),
    # and report_fires counted them as real fires.
    _sv_dir, _sv_log = _STATE_DIR, _FIRES_LOG
    try:
        _tmp_state = tempfile.mkdtemp()
        globals()["_STATE_DIR"] = _tmp_state
        globals()["_FIRES_LOG"] = os.path.join(_tmp_state, "fires.jsonl")
        _probe_log = _FIRES_LOG
        _before = os.path.getsize(_probe_log) if os.path.exists(_probe_log) else 0
        log_fires(
            ["goûteur: self-test fixture. [traps.md: recursive grep]"],
            {"tool_use_id": "selftest", "session_id": "selftest", "cwd": "/tmp"},
        )
        _after = os.path.getsize(_probe_log) if os.path.exists(_probe_log) else 0
        _check("mirote: a fire appends a record", _after > _before, True)
        with open(_probe_log, encoding="utf-8") as _fh:
            _last = json.loads(_fh.readlines()[-1])
        _check("mirote: the record carries the render id", _last.get("render"), "traps-recursive-grep")
        _check(
            "mirote: the record carries NO command text (secret-bearing by design)",
            sorted(_last.keys()),
            ["agent", "cwd", "host", "mode", "render", "session_id", "tool_use_id", "ts"],
        )
    finally:
        globals()["_STATE_DIR"] = _sv_dir
        globals()["_FIRES_LOG"] = _sv_log

    # Failure tolerance: an unwritable state dir must not raise, because a
    # hook that dies on a full disk breaks the tool call it is observing.
    _saved = _STATE_DIR
    try:
        globals()["_STATE_DIR"] = "/proc/nonexistent-cannot-create"
        globals()["_FIRES_LOG"] = "/proc/nonexistent-cannot-create/fires.jsonl"
        _raised = False
        try:
            log_fires(["goûteur: x. [traps.md: find/bfs]"], {})
        except Exception:
            _raised = True
        _check("mirote: an unwritable log path never raises", _raised, False)
    finally:
        globals()["_STATE_DIR"] = _saved
        globals()["_FIRES_LOG"] = os.path.join(_saved, "fires.jsonl")

    # A torn line must not sink the reader.
    _check("mirote: reader tolerates a torn append", isinstance(report_fires("2099-01-01"), int), True)


    # ---- carte-pabafo: --followed predicates, known-positive AND known-negative
    for rid, (in_class, remedied) in FOLLOWED.items():
        _check(f"pabafo: {rid} registry id is a known render", rid in KNOWN_RENDER_IDS, True)
    _check("pabafo: recursive grep — wrapped grep -rn is in class, unremedied",
           _recursive_search("grep -rn foo ~/dir") and not _unwrapped_search("grep -rn foo ~/dir"), True)
    _check("pabafo: recursive grep — ls | grep -i is NOT a recursive search", _recursive_search("ls ext/ | grep -i qa"), False)
    _check("pabafo: recursive grep — command grep -rn is remedied", _unwrapped_search("command grep -rn foo ~/dir"), True)

    # End-to-end pair on a synthetic fires log + transcript under a temp root:
    # one session follows the recursive-grep advice, one does not, one has
    # no later search at all. Broken to prove it goes red: swapping the two
    # transcripts' second commands flips the tally.
    _sv_dir, _sv_log, _sv_roots = _STATE_DIR, _FIRES_LOG, list(_PROJECT_ROOTS)
    try:
        with tempfile.TemporaryDirectory() as td:
            proj = os.path.join(td, "projects", "-tmp-x")
            os.makedirs(proj)
            globals()["_STATE_DIR"] = td
            globals()["_FIRES_LOG"] = os.path.join(td, "fires.jsonl")
            globals()["_PROJECT_ROOTS"][:] = [os.path.join(td, "projects")]

            def _tx(sid: str, cmds: list[tuple[str, str]]) -> None:
                with open(os.path.join(proj, sid + ".jsonl"), "w", encoding="utf-8") as fh:
                    for ts, c in cmds:
                        fh.write(json.dumps({"type": "assistant", "timestamp": ts, "sessionId": sid,
                                             "message": {"content": [{"type": "tool_use", "name": "Bash",
                                                                      "id": "t", "input": {"command": c}}]}}) + "\n")
                    # an echo of the remedy inside a tool RESULT must not count
                    fh.write(json.dumps({"type": "user", "timestamp": "2026-01-01T00:00:09Z",
                                         "message": {"content": [{"type": "tool_result", "content": "command grep -rn foo"}]}}) + "\n")
            _tx("aaaa-1", [("2026-01-01T00:00:01Z", "grep -rn foo ~/d"),
                            ("2026-01-01T00:00:05Z", "command grep -rn foo ~/d")])
            _tx("aaaa-2", [("2026-01-01T00:00:01Z", "grep -rn foo ~/d"),
                            ("2026-01-01T00:00:05Z", "grep -rn bar ~/d")])
            _tx("aaaa-3", [("2026-01-01T00:00:01Z", "grep -rn foo ~/d"),
                            ("2026-01-01T00:00:05Z", "ls")])
            with open(_FIRES_LOG, "w", encoding="utf-8") as fh:
                for sid in ("aaaa-1", "aaaa-2", "aaaa-3"):
                    fh.write(json.dumps({"ts": "2026-01-01T00:00:02Z", "render": "traps-recursive-grep",
                                         "session_id": sid, "tool_use_id": "t"}) + "\n")
                    # a second fire in the same session is the proxy's business, not this one's
                    fh.write(json.dumps({"ts": "2026-01-01T00:00:03Z", "render": "traps-recursive-grep",
                                         "session_id": sid, "tool_use_id": "t2"}) + "\n")
            got = report_followed()
            _check("pabafo: end-to-end — 1 followed, 2 scored, 1 unscored",
                   got.get("traps-recursive-grep"), (1, 2, 1))
            _check("pabafo: end-to-end — --since after the fires scores nothing",
                   report_followed("2099-01-01").get("traps-recursive-grep"), (0, 0, 0))
    finally:
        globals()["_STATE_DIR"] = _sv_dir
        globals()["_FIRES_LOG"] = _sv_log
        globals()["_PROJECT_ROOTS"][:] = _sv_roots

    # ---- Review fixes, 2026-11-08 (a cold review before the move shipped) ----
    # 1. The ssh option table stayed in the engine: a pre gate that names it
    # must not crash. Each command here crashed the first cut (NameError),
    # and a --pre crash denies.
    for cmd in ("ssh -i k box 'pkill -x nginx'", "ssh -p 2222 box uptime; pgrep -x sshd",
                "ssh -t host 'tmux kill-server'"):
        try:
            probe_pre(cmd)
            crashed = ""
        except Exception as exc:  # noqa: BLE001 — the failure under test
            crashed = f"{type(exc).__name__}: {exc}"
        check(f"review: ssh with an option does not crash the pre gate — {cmd} {crashed}", crashed, "")

    # 2. A project settings file's `/path` Read rule is anchored at the
    # project, so the cd-rewrite declines a path under it.
    with tempfile.TemporaryDirectory() as proj, tempfile.TemporaryDirectory() as ucfg:
        os.makedirs(os.path.join(proj, ".claude"))
        os.makedirs(os.path.join(proj, "secrets"))
        os.makedirs(os.path.join(proj, "src"))
        for f in ("secrets/key.pem", "src/a.py"):
            open(os.path.join(proj, f), "w").close()
        with open(os.path.join(proj, ".claude", "settings.json"), "w") as fh:
            json.dump({"permissions": {"deny": ["Read(/secrets/**)"]}}, fh)
        _sv = os.environ.get("CLAUDE_CONFIG_DIR")
        os.environ["CLAUDE_CONFIG_DIR"] = ucfg
        try:
            check("review: project `Read(/secrets/**)` declines the rewrite of secrets/key.pem",
                  rewrite_after_cd(f"cd {proj} && grep foo secrets/key.pem", proj), None)
            check("review: control — an undenied path in the same project is still rewritten",
                  rewrite_after_cd(f"cd {proj} && grep foo src/a.py", proj) is not None, True)
        finally:
            if _sv is None:
                os.environ.pop("CLAUDE_CONFIG_DIR", None)
            else:
                os.environ["CLAUDE_CONFIG_DIR"] = _sv

    # 3. Broken extensions fail OPEN — through the real entry point, one
    # gouteur.d per breakage. Open means: an ordinary command still passes,
    # and a shipped guard still denies.
    import subprocess as _lsp

    def _hook(extdir: str, payload: dict, *flags: str, state: str = "") -> tuple[int, str]:
        r = _lsp.run([sys.executable, __file__, *flags], input=json.dumps(payload),
                     capture_output=True, text=True,
                     env={**os.environ, "GOUTEUR_EXTENSIONS": extdir,
                          "GOUTEUR_STATE_DIR": state or extdir + "-state"})
        return r.returncode, r.stdout

    _ls = {"tool_name": "Bash", "cwd": "/tmp", "session_id": "ldr", "tool_input": {"command": "ls /tmp"}}
    _key = {"tool_name": "Read", "cwd": "/tmp", "session_id": "ldr",
            "tool_input": {"file_path": "/home/u/dl/" + "sa-key" + ".json"}}
    breakages = {
        "pre_bash returns True": "def pre_bash(cmd, cwd):\n    return True\n",
        "pre_bash returns [42]": "def pre_bash(cmd, cwd):\n    return [42]\n",
        "pre_bash raises": "def pre_bash(cmd, cwd):\n    raise RuntimeError('boom')\n",
        "a bare string for CREDENTIAL_CORES": "CREDENTIAL_CORES = ('.config/x')\n",
        "an empty credential core": "CREDENTIAL_CORES = ('',)\n",
        "sys.exit(0) at import": "import sys\nsys.exit(0)\n",
        "sys.exit(2) at import": "import sys\nsys.exit(2)\n",
        "a syntax error": "def broken(:\n",
    }
    for label, body in breakages.items():
        with tempfile.TemporaryDirectory() as ext:
            with open(os.path.join(ext, "bad.py"), "w") as fh:
                fh.write(body)
            rc_ls, out_ls = _hook(ext, _ls, "--pre")
            rc_key, out_key = _hook(ext, _key, "--pre")
            check(f"review: broken extension ({label}) — ordinary Bash still passes",
                  (rc_ls, out_ls.strip()), (0, ""))
            check(f"review: broken extension ({label}) — the shipped credential deny still fires",
                  rc_key == 0 and '"deny"' in out_key, True)
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        with tempfile.TemporaryDirectory() as ext:
            locked = os.path.join(ext, "d")
            os.makedirs(locked)
            os.chmod(locked, 0)
            try:
                check("review: an unreadable gouteur.d — ordinary Bash still passes",
                      _hook(locked, _ls, "--pre", state=ext + "/s"), (0, ""))
            finally:
                os.chmod(locked, 0o700)

    # 4. A broken extension is logged once per session per stage, and the
    # session is told once — not on every call.
    with tempfile.TemporaryDirectory() as ext, tempfile.TemporaryDirectory() as st:
        with open(os.path.join(ext, "bad.py"), "w") as fh:
            fh.write("raise ImportError('half-edited')\n")
        post = {**_ls, "tool_response": {"stdout": "x", "stderr": ""}}
        outs = [_hook(ext, post, state=st)[1] for _ in range(3)]
        for _ in range(3):
            _hook(ext, _ls, "--pre", state=st)
        check("review: the session is told about a broken extension on the first call only",
              ["[gouteur: extension-failed]" in o for o in outs], [True, False, False])
        with open(os.path.join(st, "fires.jsonl"), encoding="utf-8") as fh:
            ids = [json.loads(x)["render"] for x in fh if x.strip()]
        check("review: one extension-failed record per stage per session (post + pre = 2)",
              ids.count("gouteur-extension-failed"), 2)

    # ---- Phase 2: the gouteur.d extensions' own checks ----------------------
    if _sv_ext_env is None:
        os.environ.pop("GOUTEUR_EXTENSIONS", None)
    else:
        os.environ["GOUTEUR_EXTENSIONS"] = _sv_ext_env
    _EXTENSIONS = None if _sv_ext is None or _sv_ext == [] else _sv_ext
    exts = extensions()
    print(f"\n-- extensions: {len(exts)} loaded from {_ext_dir() or '(disabled)'}")
    for err in _EXT_ERRORS:
        check(f"extension loads: {err}", False, True)
    for mod in exts:
        ids = set(getattr(mod, "RENDERS", {}))
        try:
            src = open(mod.__file__, encoding="utf-8").read()
        except OSError:
            src = ""
        found = {_render_id("x " + t) for t in _RENDER_TAG.findall(src)}
        name = os.path.basename(getattr(mod, "__file__", "?"))
        check(f"{name}: every tag it emits is registered here or in the engine "
              f"({sorted(found - ids - KNOWN_RENDER_IDS)})",
              sorted(found - ids - KNOWN_RENDER_IDS), [])
        check(f"{name}: every id in RENDERS is emitted ({sorted(ids - found)})",
              sorted(ids - found), [])
        check(f"{name}: no RENDERS id shadows a shipped one ({sorted(ids & KNOWN_RENDER_IDS)})",
              sorted(ids & KNOWN_RENDER_IDS), [])
        st = getattr(mod, "self_test", None)
        if st is not None:
            try:
                st(check)
            except Exception as exc:  # noqa: BLE001 — a crashing test is a failure
                check(f"{name}: self_test crashed: {type(exc).__name__}: {exc}", False, True)

    print(f"\n{total - failures}/{total} passed — fixtures prove the probes fire and stay quiet; whether a render changes behaviour is --followed's question")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
    elif "--self-test" in sys.argv:
        self_test()
    elif "--fires" in sys.argv:
        since = ""
        if "--since" in sys.argv:
            i = sys.argv.index("--since")
            if i + 1 < len(sys.argv):
                since = sys.argv[i + 1]
        report_fires(since, repeats="--repeats" in sys.argv)
    elif "--followed" in sys.argv:
        since = ""
        if "--since" in sys.argv:
            i = sys.argv.index("--since")
            if i + 1 < len(sys.argv):
                since = sys.argv[i + 1]
        report_followed(since)
    else:
        # Designed fallbacks return None inside main(); a crash HERE is the
        # failure nobody designed for, so it is logged by name instead of
        # swallowed (the cd-rewrite branch already did this for itself). The
        # render tiers fail open — a missed render costs one reminder — but
        # the --pre gate fails CLOSED, because an open gate on a malformed
        # payload is exactly how a credential sweep would get through, and
        # the deny names the fault so the next human can repair it (twin
        # review 2026-09-06, carte-visoce).
        try:
            main()
        except Exception as exc:  # noqa: BLE001 — logged, then decided
            log_fires([f"gouteur crashed: {type(exc).__name__}: {exc} "
                       "[gouteur: crash]"], {})
            if "--pre" in sys.argv:
                print(json.dumps({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "goûteur DENIED this call because gouteur crashed: "
                        f"{type(exc).__name__}: {exc}. Failing closed is by "
                        "design — a malformed payload must not open the "
                        "credential gate — but every Bash call will be denied "
                        f"until the fault is repaired: {__file__}, run its "
                        "--self-test; the crash is logged under [gouteur: crash] "
                        "in `gouteur.py --fires`."),
                }}))

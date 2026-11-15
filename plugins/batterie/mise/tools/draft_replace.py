"""
do(replace_text) on a Gmail draft id — the surgical draft edit (mise-en-space-gujuku).

do(draft, file_id=<draft_id>) rebuilds the whole body from the caller's
content: right for a rewrite, wrong for "change Thursday to Friday" in a reply
draft, where it re-renders the quote and re-appends the signature. This path
changes only the matched text: drafts.get(format=raw), splice the edit into the
text/plain and text/html bodies (tools/draft_mime.py), drafts.update with the
same threadId. Headers, threading, attachments, the quoted history and the
signature are the original bytes.

Guard: every body part must hold exactly `count` matches (default 1), or
nothing is written. No confirm gate — a draft reaches nobody until a human
sends it, which is why Doc replace_text and draft update write directly too.
Never sends.
"""

import threading
from email.parser import BytesHeaderParser
from email.policy import default as default_policy
from typing import Any

from adapters.gmail_draft_raw import get_draft_raw, put_draft_raw
from models import DoResult, MiseError
from token_store import ambient_mode
from tools.draft import _COMPOSE_NOTE, _LAST_WRITTEN, remember_write
from tools.draft_mime import plan_draft_edit


# One lock per draft id, held across read → plan → write. do() bodies run
# concurrently on worker threads, so two edits to one draft issued in parallel
# would otherwise both read the same message and the second write would drop
# the first edit (cold review, 2026-11-08). In-process only: another server,
# a human, or an open compose window can still save in between.
_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _draft_lock(draft_id: str) -> threading.Lock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(draft_id, threading.Lock())


def _err(message: str, kind: str = "invalid_input") -> dict[str, Any]:
    return {"error": True, "kind": kind, "message": message}


def _subject(raw: bytes) -> str:
    head = raw.split(b"\r\n\r\n", 1)[0].split(b"\n\n", 1)[0]
    try:
        return str(BytesHeaderParser(policy=default_policy).parsebytes(head).get("Subject") or "")
    except (ValueError, LookupError, UnicodeError):  # a malformed or unknown-charset Subject
        return ""


def do_draft_replace_text(
    draft_id: str,
    find: str,
    content: str,
    count: int | None = None,
) -> DoResult | dict[str, Any]:
    """Replace `find` with `content` in a Gmail draft's text, in place. Draft-only."""
    if ambient_mode():
        return _err("replace_text on a Gmail draft needs a mailbox, which a service "
                    "account (ambient mode) does not have.")
    expected = 1 if count is None else count
    if isinstance(expected, bool) or not isinstance(expected, int) or expected < 1:
        return _err(f"count= must be a whole number of 1 or more (got {count!r}); "
                    "it is how many times find must match in each body part.")
    if find == content:
        return _err("find and content are identical — there is nothing to change. "
                    "Nothing was written.")

    with _draft_lock(draft_id):
        return _edit_locked(draft_id, find, content, expected)


def _edit_locked(draft_id: str, find: str, content: str, expected: int) -> DoResult | dict[str, Any]:
    try:
        draft = get_draft_raw(draft_id)
    except MiseError as e:
        return _err(f"Could not load draft '{draft_id}': {e.message}", e.kind.value)
    if draft.label_ids and "DRAFT" not in draft.label_ids:
        return _err(f"'{draft_id}' is no longer a draft (labels: {', '.join(draft.label_ids)}) — "
                    "it has probably been sent. Nothing was written.")

    plan = plan_draft_edit(draft.raw, find, content, expected)
    if not plan.ok or plan.new_raw is None:
        result = _err(plan.message)
        if plan.parts:
            result["details"] = {"matches": {p.content_type: p.matches for p in plan.parts},
                                 "expected": expected, "written": False}
        return result

    moved_under_us = draft_id in _LAST_WRITTEN and _LAST_WRITTEN[draft_id] != draft.message_id
    try:
        new_id, new_message_id = put_draft_raw(draft_id, plan.new_raw, draft.thread_id)
    except MiseError as e:
        return _err(f"Draft not edited: {e.message}", e.kind.value)
    remember_write(new_id, new_message_id)

    cues: dict[str, Any] = {
        "action": "Draft edited in place — review and send from Gmail",
        "edits": {p.content_type: p.matches for p in plan.parts},
        "kept": "headers, threading, attachments, quoted history and signature are the "
                "draft's original bytes; only the matched text changed",
        "compose_window_note": _COMPOSE_NOTE,
    }
    if draft.thread_id:
        cues["thread_id"] = draft.thread_id
    if plan.previews:
        cues["preview"] = plan.previews
    if html_forms := [p.content_type for p in plan.parts if p.form != "verbatim"]:
        cues["html_matched_escaped"] = ", ".join(html_forms)
    warnings: list[str] = []
    if "text/html" not in cues["edits"]:
        warnings.append("This draft has no HTML part; only the plain-text body was edited.")
    elif "text/plain" not in cues["edits"]:
        warnings.append("This draft has no plain-text part; only the HTML body was edited.")
    if plan.reencoded:
        warnings.append("A part gained characters its old encoding could not carry, so its "
                        "Content-Transfer-Encoding/charset header changed: "
                        + "; ".join(plan.reencoded) + ".")
    if moved_under_us:
        warnings.append("This draft changed since mise last wrote it (a human edit or a compose "
                        "window's autosave); the edit was applied to that current version, so "
                        "their changes are kept.")
    if warnings:
        cues["warnings"] = warnings
    return DoResult(
        file_id=new_id,
        title=_subject(draft.raw),
        web_link=f"https://mail.google.com/mail/#drafts/{new_id}",
        operation="replace_text",
        cues=cues,
    )

"""
The refusal for updating a draft that changed since mise last wrote it — mise-cijugo.

drafts.update replaces the whole body, so an update over a human's edit (or a
compose window's autosave) deletes their words. tools/draft.py detects the
change by message id; this module builds the refusal, which shows the draft's
current opening lines and names the pull-merge-push route. Split from
tools/draft.py, which sits at the module-size cap.
"""

from typing import Any

from adapters.gmail import fetch_thread
from html_convert import html_to_text_with_links
from models import MiseError

_SNIPPET_LINES = 6
_SNIPPET_CHARS = 400


def _current_body(thread_id: str | None, message_id: str) -> str:
    """The draft's opening lines, quoted — or a sentence saying why not.

    The draft is a message in its thread, so one thread read finds it; that
    read is paid on the refusal path only. A failure here never lifts the
    refusal — the snippet is a courtesy, the refusal is the point.
    """
    if not thread_id:
        return "(Its current body could not be read here.)"
    try:
        msg = next((m for m in fetch_thread(thread_id).messages
                    if m.message_id == message_id), None)
    except MiseError as e:
        return f"(Its current body could not be read here: {e.message}.)"
    text = ""
    if msg is not None:
        text = msg.body_text or (html_to_text_with_links(msg.body_html) if msg.body_html else "")
    snippet = "\n".join(text.strip().splitlines()[:_SNIPPET_LINES])[:_SNIPPET_CHARS]
    if not snippet:
        return "(Its current body could not be read here.)"
    return "It now begins:\n" + "\n".join(f"> {line}" for line in snippet.splitlines())


def changed_since_refusal(draft_id: str, thread_id: str | None, message_id: str) -> dict[str, Any]:
    """Error dict refusing the update, with the current body and the pull route."""
    lead = (f"Draft '{draft_id}' was not updated: it changed since mise last wrote it "
            "(someone edited it in Gmail, or an open compose window autosaved), and "
            "an update replaces the whole body.")
    pull = (f"Pull, merge, then push: fetch https://mail.google.com/mail/#drafts/{draft_id} "
            "to read the current draft (it is the thread's latest message), put your change "
            "onto that text, then repeat this update with supersede=True — which says you "
            "have taken what is there into account, or mean to discard it. If it is open in "
            "a compose window, ask for that to be closed first, or its autosave will undo you.")
    body = _current_body(thread_id, message_id)
    return {"error": True, "kind": "invalid_input", "message": f"{lead}\n{body}\n{pull}"}

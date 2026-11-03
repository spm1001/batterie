"""
delete_event operation — take events off the user's own calendar via do()
(mise-en-space-naseto).

Built for releasing holds: a diary Claude places solo holds on the slots it
offers, books the one that is picked, and must then remove the rest without
a hand-rolled API script. So v1 deletes only what is the user's alone:

- They must be the ORGANISER. Deleting an event you were invited to is a
  different act (decline), and do(respond) owns it.
- Nobody else may be on it. Cancelling a real meeting emails every guest;
  refusing it outright means a mis-aimed id can never cancel one. Holds have
  no guests, so the guard costs the intended use nothing.
- Not a recurring SERIES (one instance is fine): a series id deletes every
  occurrence, which is the Calendar UI's job, with its own "this and
  following" choice.

Gated like the other calendar writes: without confirm=True it returns a
preview naming each event and its time, and deletes nothing. A refusal of
any id refuses the whole call, so what the human approves is exactly what
happens. sendUpdates is always none, since no guest exists to notify. A
deleted event sits in the calendar's bin for 30 days.

No elicitation dialog, deliberately: the blast radius is below a solo
create_event (which has no gate at all) — your own events, nobody emailed,
30 days in the bin — the expected caller is a diary sweep passing
confirm=True after the human's yes, and a preview of three or more events
breaks the 4×74 dialog budget anyway. If v2 ever lifts the guests refusal,
delete becomes CANCELLATION, which emails people: it must then join
CONFIRM_GATED_OPS (tools/confirm_gate.py) and the notification policy
(mise-en-space-tihusa).

Idempotent by design: an id already deleted (status cancelled on read, or
410 on the delete) is reported as "already gone", never as a failure, so a
caller retrying after a timeout gets success for an event that is gone.

Deliberately NOT in remote mode's allowed ops — destructive.
"""

import logging
from typing import Any

from adapters.calendar import get_event
from adapters.calendar_delete import delete_event
from cues_util import with_identity
from models import DoResult, ErrorKind, MiseError
from tools.event_clock import describe_when
from tools.events_util import error, other_guests
from tools.gmail_ops import _batch_result

logger = logging.getLogger(__name__)

_MAX_IDS = 50


def _refusal(event: dict[str, Any]) -> str | None:
    """Why this event may not be deleted here, or None if it may."""
    if not event.get("organizer", {}).get("self"):
        return (
            f"you are a guest, not the organiser "
            f"({event.get('organizer', {}).get('email', 'unknown')}) — to drop it "
            "from your diary, decline with do(operation='respond', action='decline')"
        )
    others = [a.get("email", "?") for a in other_guests(event)]
    if others:
        return (
            f"it has guests ({', '.join(others[:3])}"
            f"{', …' if len(others) > 3 else ''}) — cancelling a meeting emails "
            "them, so do that in the Calendar UI"
        )
    if event.get("recurrence"):
        return (
            "it is a recurring series — deleting it removes every occurrence; "
            "do that in the Calendar UI, or delete one instance by its own id"
        )
    return None


def _label(event: dict[str, Any]) -> str:
    return (
        f"'{event.get('summary', 'untitled')}', "
        f"{describe_when(event.get('start', {}), event.get('end', {}))}"
    )


def do_delete_event(
    file_id: str | list[str] | None = None,
    confirm: bool = False,
) -> DoResult | dict[str, Any]:
    """Delete solo events (holds) from the primary calendar; preview unless confirm=True."""
    ids = [file_id] if isinstance(file_id, str) else list(file_id or [])
    if any(not isinstance(i, str) for i in ids):
        return error("invalid_input", "delete_event's file_id must be event id strings.")
    ids = [i.strip() for i in ids if i.strip()]
    if not ids:
        return error("invalid_input", "delete_event needs file_id: a Calendar event id, or a list of them.")
    if len(ids) > _MAX_IDS:
        return error("invalid_input", f"delete_event takes at most {_MAX_IDS} ids per call.")
    ids = list(dict.fromkeys(ids))

    # Read every event first: one refusal refuses the call, before anything goes.
    events: list[dict[str, Any]] = []
    gone: list[str] = []
    refusals: list[str] = []
    for event_id in ids:
        try:
            event = get_event(event_id)
        except MiseError as e:
            if e.kind is ErrorKind.NOT_FOUND:
                refusals.append(f"{event_id}: not found as a Calendar event on your primary calendar")
                continue
            return error(e.kind.value, e.message)
        if event.get("status") == "cancelled":
            gone.append(event_id)
            continue
        why = _refusal(event)
        if why:
            refusals.append(f"{event_id} ({_label(event)}): {why}")
        else:
            events.append(event)
    if refusals:
        return error(
            "invalid_input",
            "Nothing was deleted. delete_event takes only your own events with "
            "no guests, and refused:\n- " + "\n- ".join(refusals),
        )
    if not events:  # a retry after a delete that landed: success, not an error
        return {"operation": "delete_event", "batch": isinstance(file_id, list),
                "already_gone": gone, "succeeded": 0, "failed": 0, "results": [],
                "cues": {"action": "Already deleted — nothing to do; nobody was emailed."}}

    labels = [_label(e) for e in events]
    if not confirm:
        return {
            "preview": True,
            "operation": "delete_event",
            "events": [{"id": e.get("id"), "title": e.get("summary"),
                        "start": e.get("start"), "end": e.get("end")} for e in events],
            "already_gone": gone,
            "message": (
                f"Delete {len(events)} event(s) from your calendar (no guests, "
                "so nobody is emailed; recoverable from the bin for 30 days):\n"
                + "\n".join(f"- {label}" for label in labels)
            ),
            "cues": with_identity({
                "confirm_required": (
                    "This is a preview — nothing is deleted. Show it to the "
                    "user; to delete, call again with confirm=True."
                ),
            }),
        }

    results: list[dict[str, Any]] = []
    succeeded = failed = 0
    for event, label in zip(events, labels):
        try:
            deleted = delete_event(event["id"])
            results.append({"file_id": event["id"], "ok": True, "title": label,
                            "result": "deleted" if deleted else "already gone"})
            succeeded += 1
        except MiseError as e:
            results.append({"file_id": event["id"], "ok": False, "title": label,
                            "error": e.message, "kind": e.kind.value})
            failed += 1
    logger.info("delete_event: %d deleted, %d failed", succeeded, failed)

    if isinstance(file_id, str) and failed == 0:
        landed = results[0]["result"] == "deleted"
        return DoResult(
            file_id=events[0]["id"], title=events[0].get("summary", ""),
            web_link="", operation="delete_event",
            cues={"action": (
                "Deleted — in the calendar's bin for 30 days; nobody was emailed."
                if landed else "Already gone (Google answered 410) — nothing more to do."
            )},
            extras={"type": "calendar_event"},
        )
    if isinstance(file_id, str):
        return error(results[0]["kind"], results[0]["error"])
    extra: dict[str, Any] = {"already_gone": gone}
    if failed:
        extra["partial_failure"] = (
            f"{failed} of {len(events)} deletes failed (see results); the rest are "
            "deleted. Calling again with the same ids is safe: deleted ones read "
            "as already gone."
        )
    return _batch_result("delete_event", results, succeeded, failed, **extra)

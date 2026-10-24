"""
Calendar event insert — split from adapters/calendar.py, which sat at its
500-line cap.

An insert is retried like a read (mise-busufu) because every insert carries a
client-minted event id. A 503 or a timeout can arrive after Google booked the
event; the retry then answers 409 "duplicate" instead of booking a second
event and re-sending every invite (probed live 2026-10-24 on a private,
attendee-free event: the repeat answered 409, reason "duplicate", "The
requested identifier already exists."). A 409 on a retry is therefore proof
the first attempt landed, and the event is fetched by id and returned.
"""

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from adapters.calendar import _CALENDAR_API
from adapters.http_client import get_sync_client
from models import ErrorKind, MiseError
from retry import with_retry

# Calendar's event-id rule: base32hex (a-v, 0-9), 5 to 1024 characters.
_ID_ALPHABET = "0123456789abcdefghijklmnopqrstuv"
_ID_LENGTH = 26  # 130 random bits: a collision with any existing id is not a real risk

# Rides the returned event when it was recovered rather than booked by the
# last attempt; tools/create_event.py pops it into a cue.
INSERT_RECOVERED_KEY = "_mise_insert_recovered"
_RECOVERED_CUE = (
    "Insert recovered: an attempt hit a transient error after Google had "
    "already booked the event, so the retry was refused as a duplicate (409) "
    "and the booked event was fetched by id. One event exists, and invites "
    "went out once, from the attempt that landed."
)


def _mint_event_id() -> str:
    return "".join(secrets.choice(_ID_ALPHABET) for _ in range(_ID_LENGTH))


def insert_event(body: dict[str, Any], send_updates: str = "all") -> dict[str, Any]:
    """Create an event on the primary calendar, returning the raw event.

    supportsAttachments rides every insert — harmless without attachments,
    and per Google's reference the API ignores attachments[] without it.
    conferenceDataVersion=1 likewise gates conferenceData.createRequest.
    (Attachment write-through verified live 2026-08-19: read-back showed the
    fileUrl enriched to a resolved fileId. The ignore paths are documented
    behaviour, not probed — both params are simply always sent.)

    Every insert is stamped with provenance in extendedProperties.private
    (mise:minted_by, mise:minted_at) — UI-invisible, queryable via
    list_events(private_property=…), the [agent]-comment pattern for events
    (mise-gujiro). Caller keys are preserved; the stamps win a collision so
    provenance stays trustworthy. Colon-in-key accepted, probed 2026-08-19.

    The body gets a client-minted id unless the caller supplied one, which is
    what makes the retries in _post_event safe (module docstring). A recovered
    event carries INSERT_RECOVERED_KEY with the cue text.
    """
    private = dict(body.get("extendedProperties", {}).get("private", {}))
    private.update({
        "mise:minted_by": "mise",
        "mise:minted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    body = {
        "id": _mint_event_id(),
        **body,
        "extendedProperties": {"private": private},
    }
    params = {
        "sendUpdates": send_updates,
        "supportsAttachments": "true",
        "conferenceDataVersion": "1",
    }
    attempts = _Attempts()
    try:
        return _post_event(body, params, attempts)
    except MiseError as e:
        raise _naming_the_id(e, body["id"], attempts.may_have_landed) from e


@dataclass
class _Attempts:
    """What the decorator's retries cannot tell us.

    count: a 409 proves an earlier landing only when there WAS an earlier
    attempt; on the first it means the id is someone else's.
    may_have_landed: an attempt failed after its request could have reached
    Google (a 5xx, a timeout, a dropped connection, anything but a definite
    4xx answer). Then a final failure does not mean nothing was booked.
    """
    count: int = 0
    may_have_landed: bool = False


def _naming_the_id(e: MiseError, event_id: str, may_have_landed: bool) -> MiseError:
    """The final error carries the minted id, so the caller can look before a
    repeat: a fresh call mints a fresh id, and a repeat after a landed attempt
    would book twice (essayeur, 2026-10-24)."""
    details = {**e.details, "event_id": event_id, "may_have_landed": may_have_landed}
    if not may_have_landed:
        return MiseError(e.kind, f"{e.message} (event id {event_id}; Google refused it, "
                         f"nothing was booked)", details=details, retryable=e.retryable)
    return MiseError(
        e.kind,
        f"{e.message} | Event id {event_id} may already be booked: an attempt "
        f"failed after it could have reached Google.",
        details=details,
        retryable=False,  # obeying a retryable flag here is what books twice
    )


@with_retry(max_attempts=3, delay_ms=1000, idempotent=True)
def _post_event(
    body: dict[str, Any], params: dict[str, str], attempts: _Attempts,
) -> dict[str, Any]:
    """One insert attempt. Idempotent because the body carries its own id."""
    attempts.count += 1
    client = get_sync_client()
    try:
        created: dict[str, Any] = client.post_json(
            f"{_CALENDAR_API}/primary/events", params=params, json_body=body,
        )
        return created
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status >= 500:
            attempts.may_have_landed = True
        if attempts.count == 1 or status != 409:
            raise
    except Exception:
        # No HTTP answer at all (timeout, dropped connection, auth refresh):
        # assume the request may have landed — the conservative reading.
        attempts.may_have_landed = True
        raise
    # A GET that fails transiently re-runs this whole attempt: the POST
    # 409s again and the fetch is retried, so no extra decorator is needed.
    landed: dict[str, Any] = client.get_json(f"{_CALENDAR_API}/primary/events/{body['id']}")
    # Google has now said who holds the id; _confirm_ours either returns it
    # as ours or raises because nothing of ours is booked.
    attempts.may_have_landed = False
    return _confirm_ours(landed, body)


def _confirm_ours(landed: dict[str, Any], sent: dict[str, Any]) -> dict[str, Any]:
    """Return the fetched event as the insert's result, or raise if it isn't ours."""
    if landed.get("status") == "cancelled":
        # Deleted events keep their id as a cancelled tombstone (probed
        # 2026-10-24), and a re-insert of that id also answers 409.
        raise MiseError(
            ErrorKind.UNKNOWN,
            f"Calendar insert: the retry was refused as a duplicate, but event "
            f"{sent['id']} is cancelled — it landed and was deleted, or the id "
            f"belonged to a deleted event. Nothing is booked; list the calendar "
            f"for that window before trying again.",
        )
    stamp = landed.get("extendedProperties", {}).get("private", {}).get("mise:minted_at")
    if stamp != sent["extendedProperties"]["private"]["mise:minted_at"]:
        raise MiseError(
            ErrorKind.UNKNOWN,
            f"Calendar insert: the retry was refused as a duplicate, but event "
            f"{sent['id']} is not the one this call sent (its mise:minted_at "
            f"stamp differs). Nothing was booked by this call; list the "
            f"calendar for that window before trying again.",
        )
    return {**landed, INSERT_RECOVERED_KEY: _RECOVERED_CUE}

"""
Calendar event delete — split from adapters/calendar.py, which sits at its
500-line cap (mise-en-space-naseto).

Retried like a read: deleting the same event twice cannot do twice the harm.
A retry after a delete that already landed answers 410 Gone, which is
returned as "already gone" rather than raised, so a transient error after the
first attempt never surfaces as a failure for an event that is in fact
deleted. A deleted event goes to the calendar's bin (recoverable in the
Calendar UI for 30 days), not straight to oblivion.
"""

import httpx

from adapters.calendar import _CALENDAR_API
from adapters.credential_errors import credentials_as_auth
from adapters.http_client import get_sync_client
from retry import with_retry


@with_retry(max_attempts=3, delay_ms=1000, idempotent=True)
@credentials_as_auth
def delete_event(event_id: str, send_updates: str = "none") -> bool:
    """Delete an event from the primary calendar.

    Returns True when this call deleted it, False when Google says it was
    already gone (410). sendUpdates defaults to none: the tools layer only
    deletes events that have no other guests, so there is nobody to email.
    """
    client = get_sync_client()
    try:
        client.delete(
            f"{_CALENDAR_API}/primary/events/{event_id}",
            params={"sendUpdates": send_updates},
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 410:
            return False
        raise
    return True

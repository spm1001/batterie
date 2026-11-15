"""
A Gmail draft as raw RFC 822 bytes, read and written back (mise-en-space-gujuku).

The surgical draft edit (do(replace_text) on a draft id) needs the message
exactly as Gmail stores it, so that everything outside the edited text survives
byte for byte: drafts.get with format=raw, then drafts.update with the edited
bytes and the same threadId. Split from adapters/gmail.py, which is
size-ratcheted. Draft-only: nothing here can send.
"""

import base64
from dataclasses import dataclass, field
from typing import Any

from adapters.http_client import get_sync_client
from retry import with_retry

_GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


@dataclass
class RawDraft:
    draft_id: str
    message_id: str
    thread_id: str | None
    raw: bytes
    label_ids: list[str] = field(default_factory=list)


@with_retry(max_attempts=3, delay_ms=1000, idempotent=True)
def get_draft_raw(draft_id: str) -> RawDraft:
    """drafts.get(format=raw). Raises MiseError (404 → NOT_FOUND for a bad id)."""
    client = get_sync_client()
    draft = client.get_json(f"{_GMAIL_API}/drafts/{draft_id}", params={"format": "raw"})
    message: dict[str, Any] = draft.get("message", {}) or {}
    raw = base64.urlsafe_b64decode(message.get("raw", "") + "=" * (-len(message.get("raw", "")) % 4))
    return RawDraft(
        draft_id=draft.get("id", draft_id),
        message_id=message.get("id", ""),
        thread_id=message.get("threadId"),
        raw=raw,
        label_ids=list(message.get("labelIds") or []),
    )


# Idempotent: the same bytes PUT twice leave the draft in the same state.
@with_retry(max_attempts=3, delay_ms=1000, idempotent=True)
def put_draft_raw(draft_id: str, raw: bytes, thread_id: str | None) -> tuple[str, str]:
    """drafts.update with the given raw bytes; returns (draft_id, new message id)."""
    client = get_sync_client()
    message: dict[str, Any] = {"raw": base64.urlsafe_b64encode(raw).decode("ascii")}
    if thread_id:
        message["threadId"] = thread_id
    draft = client.request(
        "PUT", f"{_GMAIL_API}/drafts/{draft_id}", json_body={"message": message},
    ).json()
    return draft.get("id", draft_id), (draft.get("message", {}) or {}).get("id", "")

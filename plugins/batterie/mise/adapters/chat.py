"""
Google Chat adapter — read the signed-in user's spaces, DMs and threads (mise-lumaha).

User-authenticated REST reads need NO Chat app configured (GA 17 Jul 2026),
only the four read-only Chat scopes and chat.googleapis.com enabled on the
OAuth client's project. Measured on ITV 2026-10-24 with a Chat-only token:
spaces.list, spaces.get, members.list, messages.list/get, the cross-space
messages:search and spaceReadState all answer 200.

Thin by design: every function returns Google's own JSON (dicts). Parsing and
rendering live in extractors/chat.py; cues and orchestration in tools/.

Facts the callers depend on, all measured 2026-10-24:
- messages.list defaults OLDEST-first; `orderBy=createTime desc` gets the newest.
- messages:search takes keywords in `filter` (quoted), not a `query` field;
  `is_unread()` is a filter function; an empty filter is a 400.
- message.sender carries displayName and email; a DM or group chat's space
  displayName is EMPTY, so naming one needs members.list.
- A space that doesn't exist and one you aren't in both answer 403
  "…or the resource doesn't exist"; a malformed name answers 400.
"""

from typing import Any, Callable

import httpx

from adapters.http_client import get_sync_client
from models import ErrorKind, MiseError
from retry import with_retry

CHAT_API = "https://chat.googleapis.com/v1"

# The re-consent remedy, named once so search and fetch teach the same move.
CHAT_SCOPE_REMEDY = (
    "Re-consent with do(operation='setup_oauth', force=True) — it asks for all "
    "four read-only Chat scopes (chat.spaces.readonly, chat.memberships.readonly, "
    "chat.messages.readonly, chat.users.readstate.readonly) — then start a new "
    "session: a running server keeps the grant it started with."
)

# Which scope each refused method needs, read from the 403's ErrorInfo
# metadata ('google.chat.v1.ChatService.ListMemberships' — measured shape), so
# a token holding three of the four is told which one it lacks.
_METHOD_SCOPE = {
    "ListSpaces": "chat.spaces.readonly", "GetSpace": "chat.spaces.readonly",
    "ListMemberships": "chat.memberships.readonly", "GetMembership": "chat.memberships.readonly",
    "ListMessages": "chat.messages.readonly", "GetMessage": "chat.messages.readonly",
    "SearchMessages": "chat.messages.readonly",
    "GetSpaceReadState": "chat.users.readstate.readonly",
    "GetThreadReadState": "chat.users.readstate.readonly",
}


def scope_refusal_message(method: str) -> str:
    """Teaching text for ACCESS_TOKEN_SCOPE_INSUFFICIENT, naming the scope if known."""
    scope = _METHOD_SCOPE.get(method.rsplit(".", 1)[-1])
    if scope:
        return (f"This mise token lacks the Google Chat scope {scope}, which "
                f"{method.rsplit('.', 1)[-1]} needs (a token minted before Chat "
                f"support lacks all four). {CHAT_SCOPE_REMEDY}")
    return f"This mise token lacks Google Chat access. {CHAT_SCOPE_REMEDY}"

# Google caps: search and messages.list page at 100 and 1000 respectively
# (measured — a 1000 search pageSize came back as 100 per page).
_SEARCH_PAGE = 100
_LIST_PAGE = 1000
_MAX_PAGES = 10


def _error_reasons(e: httpx.HTTPStatusError) -> tuple[str, set[str], str]:
    """Google's message, the ErrorInfo reasons and the refused method, tolerating non-JSON."""
    try:
        err = e.response.json().get("error", {})
    except ValueError:
        return e.response.text[:300], set(), ""
    details = [d for d in err.get("details", []) if isinstance(d, dict)]
    reasons = {d.get("reason", "") for d in details}
    method = next((str((d.get("metadata") or {}).get("method", "")) for d in details
                   if (d.get("metadata") or {}).get("method")), "")
    return str(err.get("message", ""))[:300], reasons, method


def _convert_error(e: httpx.HTTPStatusError, subject: str) -> MiseError:
    """Map Chat's refusals onto MiseError kinds with the next move named."""
    status = e.response.status_code
    google, reasons, method = _error_reasons(e)
    details: dict[str, Any] = {"subject": subject, "http_status": status, "diagnosed": True}
    if status == 403 and "ACCESS_TOKEN_SCOPE_INSUFFICIENT" in reasons:
        return MiseError(ErrorKind.PERMISSION_DENIED, scope_refusal_message(method),
                         details={**details, "missing_scope": True})
    if status == 403 and ("SERVICE_DISABLED" in reasons or "has not been used" in google):
        return MiseError(
            ErrorKind.PERMISSION_DENIED,
            "The Google Chat API is not enabled on the Google Cloud project behind "
            "this mise OAuth client — enable chat.googleapis.com there. Google "
            f"said: {google}",
            details=details,
        )
    if status in (403, 404):
        # Chat answers 403 for a well-formed name that doesn't exist AND for a
        # space you aren't in — it will not say which (measured 2026-10-24).
        return MiseError(
            ErrorKind.NOT_FOUND,
            f"No Google Chat {subject} visible to this account — it doesn't exist, or "
            "you are not a member (Google will not say which). Space, thread and "
            "message names come from search(sources=['chat']) results or a Chat "
            f"link. Google said: {google}",
            details=details,
        )
    if status == 400:
        return MiseError(
            ErrorKind.INVALID_INPUT,
            f"Google Chat refused {subject}: {google}",
            details=details,
        )
    return MiseError(ErrorKind.UNKNOWN, f"Google Chat HTTP {status} on {subject}: {google}",
                     details=details)


def _call(fn: Callable[..., dict[str, Any]], url: str, subject: str, **kw: Any) -> dict[str, Any]:
    """Run one request; convert final refusals, leave retryable ones to with_retry."""
    try:
        return fn(url, **kw)
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status in (401, 429) or status >= 500:
            raise  # with_retry retries 429/5xx, and turns a final 401 into AUTH_EXPIRED
        raise _convert_error(e, subject) from e


@with_retry(max_attempts=3, idempotent=True)
def search_messages(filter_text: str, max_results: int = 20) -> tuple[list[dict[str, Any]], bool]:
    """messages:search across every space. Returns (message dicts, truncated).

    Asks for the FULL view, whose results carry a per-message `read` flag;
    it is copied onto each message dict as `read` (the Message resource has
    no field of that name, so nothing is shadowed). Measured 2026-10-24: of
    is_unread()'s 399 hits, 20 were flagged read, including all 18 of the
    user's own — so callers decide unread from this flag, not from the filter.
    Results arrive roughly newest-first (the first 20 of 399 unread were
    exactly the newest 20; ~1 adjacent inversion in 10 within a day).
    """
    client = get_sync_client()
    out: list[dict[str, Any]] = []
    token: str | None = None
    for _ in range(_MAX_PAGES):
        body: dict[str, Any] = {
            "filter": filter_text,
            "pageSize": min(_SEARCH_PAGE, max(1, max_results - len(out))),
            "orderBy": "create_time desc",
            "view": "SEARCH_MESSAGES_VIEW_FULL",
        }
        if token:
            body["pageToken"] = token
        data = _call(client.post_json, f"{CHAT_API}/spaces/-/messages:search",
                     "search filter", json_body=body)
        for r in data.get("results", []):
            if r.get("message"):
                out.append({**r["message"], "read": r["read"]} if "read" in r else r["message"])
        token = data.get("nextPageToken")
        if not token or len(out) >= max_results:
            break
    return out[:max_results], bool(token) or len(out) > max_results


@with_retry(max_attempts=3, idempotent=True)
def get_space(space: str) -> dict[str, Any]:
    """spaces.get — type, displayName (empty for DMs/group chats), spaceUri."""
    return _call(get_sync_client().get_json, f"{CHAT_API}/{space}", f"space '{space}'")


@with_retry(max_attempts=3, idempotent=True)
def get_message(message: str) -> dict[str, Any]:
    """messages.get — used to find the thread a linked message belongs to."""
    return _call(get_sync_client().get_json, f"{CHAT_API}/{message}", f"message '{message}'")


@with_retry(max_attempts=3, idempotent=True)
def get_read_state(space: str) -> dict[str, Any]:
    """users/me/{space}/spaceReadState — the user's lastReadTime in that space."""
    return _call(get_sync_client().get_json, f"{CHAT_API}/users/me/{space}/spaceReadState",
                 f"read state of '{space}'")


@with_retry(max_attempts=3, idempotent=True)
def get_thread_read_state(thread: str) -> dict[str, Any]:
    """users/me/{thread}/threadReadState — lastReadTime for one thread's replies."""
    return _call(get_sync_client().get_json, f"{CHAT_API}/users/me/{thread}/threadReadState",
                 f"read state of '{thread}'")


@with_retry(max_attempts=3, idempotent=True)
def list_members(space: str, max_results: int = 500) -> list[dict[str, Any]]:
    """spaces.members.list, one page (members name the DM partner and back-fill senders)."""
    data = _call(get_sync_client().get_json, f"{CHAT_API}/{space}/members",
                 f"space '{space}'", params={"pageSize": str(min(max_results, _LIST_PAGE))})
    return list(data.get("memberships", []))


@with_retry(max_attempts=3, idempotent=True)
def list_messages(
    space: str, *, thread: str | None = None, max_results: int = 200,
) -> tuple[list[dict[str, Any]], bool]:
    """The NEWEST max_results messages of a space or one thread, newest-first.

    Returns (message dicts, truncated) — truncated means older ones exist.
    """
    client = get_sync_client()
    out: list[dict[str, Any]] = []
    token: str | None = None
    subject = f"thread '{thread}'" if thread else f"space '{space}'"
    for _ in range(_MAX_PAGES):
        params: dict[str, str] = {
            "pageSize": str(min(_LIST_PAGE, max(1, max_results - len(out)))),
            "orderBy": "createTime desc",
        }
        if thread:
            params["filter"] = f"thread.name = {thread}"
        if token:
            params["pageToken"] = token
        data = _call(client.get_json, f"{CHAT_API}/{space}/messages", subject, params=params)
        out.extend(data.get("messages", []))
        token = data.get("nextPageToken")
        if not token or len(out) >= max_results:
            break
    if len(out) > max_results:
        return out[:max_results], True
    if token:
        # A token at exactly max_results can have nothing behind it (7 of 12
        # full windows, live 2026-10-24), so look one message further before
        # claiming older messages exist.
        params = {**params, "pageSize": "1", "pageToken": token}
        token = None if not _call(client.get_json, f"{CHAT_API}/{space}/messages", subject,
                                  params=params).get("messages") else token
    return out, bool(token)

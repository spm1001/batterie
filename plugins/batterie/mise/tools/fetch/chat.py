"""
Fetch a Google Chat space, DM or thread to a markdown deposit (mise-lumaha).

The router hands over a ChatRef (validation.parse_chat_reference) for any
spaces/… name or Chat URL. A space deposits its newest SPACE_CAP messages, a
thread (or a linked message's thread) up to THREAD_CAP; both newest LAST,
like a Gmail thread, with a truncation cue whenever older messages exist.

Best-effort extras — members (to name a DM, back-fill a sender) and read state
(to mark unread messages) — fail open, and each fallback says why it fired.

Unread in the window needs TWO clocks (extractors/chat.py::unread_messages):
the space's lastReadTime for messages that start a thread, and each thread's
own for its replies. The first cut read only the space clock and called 84
unread replies read, with a confident unread_messages: 0. Thread clocks are
read for the reply-bearing threads in the window, newest first, up to
THREAD_STATE_CAP, three at a time. Against Google's per-message read flag the
two clocks were 265 of 265 right (measured 2026-10-24). An earlier union with
is_unread() is gone: it added the only two false marks and nothing correct.

Unread OLDER than the window are counted, not dropped (round 2: in the space
with most unread, all 111 sat behind the newest 200 and fetch said 0). They
come from the space-scoped is_unread() search, kept only where the FULL view's
read flag is false and the user is not the sender. That route, not a plain
space.name listing, because measured over the 10 spaces with most unread the
listing omitted 57 messages the clocks call unread and flagged 43 as unread
that the clocks call read, while is_unread() + read flag matched the clocks on
all 392 of its keeps.

Past the thread cap, on any failed read, or with the user's own address
unknown (their messages would count as unread), the count is withheld with
the reason rather than reported low.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from pathlib import Path
from typing import Any

from adapters.chat import (
    get_message, get_read_state, get_space, get_thread_read_state, list_members, list_messages,
    search_messages,
)
from cues_util import current_user_email
from extractors.chat import (
    UNREAD_VS_APP,
    format_time, parse_time, participants, render_conversation, reply_threads, sent_by,
    space_label, unread_messages,
)
from models import ErrorKind, FetchResult, MiseError
from token_store import ambient_mode
from validation import ChatRef
from workspace import get_deposit_folder, write_content, write_manifest

SPACE_CAP = 200
THREAD_CAP = 500
# Thread read states fetched per deposit, newest reply first. Measured
# 2026-10-24: the newest 200 messages of 26 spaces held 43 reply-bearing
# threads in all, so 40 covers a busy space (40 calls took about 4.5 s).
THREAD_STATE_CAP = 40
# Unread hits read back from Google's search for one space, to count those
# older than the window (the busiest live space held 115).
SPACE_UNREAD_CAP = 500


def _best_effort(what: str, fn: Any, *args: Any, warnings: list[str], **kw: Any) -> Any:
    """Run an optional read; on failure record the reason and return None.

    Only MiseError is caught: with_retry converts every adapter failure into
    one, so anything else escaping is a bug and should be loud.
    """
    try:
        return fn(*args, **kw)
    except MiseError as e:
        warnings.append(f"Could not read {what}: {e.message}")
    return None


def _unread(
    space: str, messages: list[dict[str, Any]], me: str | None, *,
    truncated: bool, thread: str | None,
) -> tuple[set[str], int, str | None]:
    """(unread names in the window, unread older than it, why the count is unknown)."""
    if not me:
        return set(), 0, ("your own address is unresolved, so your messages "
                          "cannot be told apart from others' unread ones")
    space_clock, clocks, gaps = _read_clocks(space, messages)
    unread = unread_messages(messages, space_clock, clocks, me)
    older = 0
    stamps = [t for t in (parse_time(m.get("createTime")) for m in messages) if t is not None]
    window_start = min(stamps, default=None)
    if truncated and window_start:
        try:
            found, more = search_messages(f'is_unread() AND space.name = "{space}"',
                                          max_results=SPACE_UNREAD_CAP)
            # Outside the window by NAME, not by time: a message sharing the
            # oldest shown message's timestamp but not shown is still older by
            # position. The time bound only keeps out messages newer than the
            # window (arrivals since the listing), which are not "older".
            shown = {m.get("name") for m in messages}
            older = sum(
                1 for m in found
                if m.get("read") is False and not sent_by(m, me)
                and (thread is None or (m.get("thread") or {}).get("name") == thread)
                and m.get("name") not in shown
                and (parse_time(m.get("createTime")) or window_start) <= window_start
            )
            if more:
                gaps.append(f"Google's unread search for this space stopped at "
                            f"{SPACE_UNREAD_CAP}, so older unread were not all counted")
        except MiseError as e:
            gaps.append(f"unread messages older than the window could not be counted ({e.message})")
    return unread, older, "; ".join(gaps) or None


def _read_clocks(
    space: str, messages: list[dict[str, Any]],
) -> tuple[datetime | None, dict[str, datetime | None], list[str]]:
    """(space lastReadTime, thread lastReadTimes, reasons the clocks are incomplete)."""
    gaps: list[str] = []
    space_clock: datetime | None = None
    try:
        space_clock = parse_time(get_read_state(space).get("lastReadTime"))
    except MiseError as e:
        gaps.append(f"the space's read state could not be read ({e.message})")
    threads = reply_threads(messages)
    if len(threads) > THREAD_STATE_CAP:
        gaps.append(f"{len(threads) - THREAD_STATE_CAP} of {len(threads)} reply threads "
                    f"were not checked (cap {THREAD_STATE_CAP} per fetch)")
    clocks: dict[str, datetime | None] = {}
    if threads:
        with ThreadPoolExecutor(max_workers=3) as pool:
            jobs = {t: pool.submit(get_thread_read_state, t) for t in threads[:THREAD_STATE_CAP]}
        failed = []
        for t, job in jobs.items():
            try:
                clocks[t] = parse_time(job.result().get("lastReadTime"))
            except MiseError as e:
                failed.append(e.message)
        if failed:
            gaps.append(f"{len(failed)} thread read state(s) could not be read (first: {failed[0]})")
    return space_clock, clocks, gaps


def fetch_chat(ref: ChatRef, base_path: Path | None = None) -> FetchResult:
    """Deposit a Chat space or thread as markdown and return path + cues."""
    if ambient_mode():
        raise MiseError(
            ErrorKind.PERMISSION_DENIED,
            "Google Chat is unavailable in ambient (service-account) mode: Chat is "
            "read as a signed-in person, and a service account has no Chat "
            "identity. Use a user token (the normal mise setup) to read Chat.",
            details={"diagnosed": True},
        )
    warnings: list[str] = []
    thread = ref.thread
    if ref.message:
        # The message's own record names its thread — trust it over the id's prefix.
        thread = (get_message(ref.message).get("thread") or {}).get("name") or thread

    space = get_space(ref.space)
    messages, truncated = list_messages(
        ref.space, thread=thread, max_results=THREAD_CAP if thread else SPACE_CAP,
    )
    unnamed_sender = any(not (m.get("sender") or {}).get("displayName") for m in messages)
    members: list[dict[str, Any]] = []
    if not space.get("displayName") or unnamed_sender:
        members = _best_effort("the space's members (used to name it)", list_members,
                               ref.space, warnings=warnings) or []

    me = current_user_email()
    unread, unread_older, unread_gap = _unread(
        ref.space, messages, me, truncated=truncated, thread=thread)

    label = space_label(space, members, me)
    title = f"Thread in {label}" if thread else label
    content = render_conversation(
        title, space, messages, members, truncated=truncated, thread=thread,
        target=ref.message, unread=unread,
    )

    resource_id = (thread or ref.space).rsplit("/", 1)[-1]
    folder = get_deposit_folder("chat", title, resource_id, base_path=base_path)
    content_path = write_content(folder, content)

    times = sorted(m.get("createTime", "") for m in messages if m.get("createTime"))
    who = participants(messages, members)
    metadata: dict[str, Any] = {
        "space": ref.space,
        "space_name": label,
        "space_type": space.get("spaceType", ""),
        "message_count": len(messages),
    }
    if thread:
        metadata["thread"] = thread
    if ref.message:
        metadata["linked_message"] = ref.message
    if space.get("spaceUri"):
        metadata["web_link"] = space["spaceUri"]

    extra = {**metadata, "participants": who}
    if warnings:
        extra["warnings"] = warnings
    write_manifest(folder, "chat", title, ref.name, extra=extra)

    cues: dict[str, Any] = {"participants": who}
    if times:
        first, last = format_time(times[0]), format_time(times[-1])
        cues["date_range"] = first if first == last else f"{first} to {last}"
    if truncated:
        cues["chat_truncated"] = (
            f"Only the newest {len(messages)} messages are deposited — OLDER ONES "
            "EXIST. Do not read an absence in this file as proof something was "
            "never said; search(sources=['chat'], query=…) reaches older messages, "
            "and fetching a hit's thread deposits that thread whole."
        )
    if unread_gap:  # a partial count must not read as the whole answer
        cues["unread_unknown"] = (
            f"Unread count withheld: {unread_gap}. Messages marked UNREAD in "
            f"content.md ({len(unread)}) are unread; an unmarked one may be too. "
            "search(sources=['chat'], query='is:unread') lists unread messages."
        )
    else:
        cues["unread_messages"] = len(unread)
        if unread or unread_older:
            cues["chat_unread_vs_app"] = UNREAD_VS_APP
        if unread_older:
            cues["unread_older_than_window"] = unread_older
            warnings.append(
                f"{unread_older} more unread message(s) are OLDER than the "
                f"{len(messages)} deposited and not in this file — unread_messages "
                "counts only those shown. search(sources=['chat'], "
                "query='is:unread') lists them; fetch a hit's thread to read one. "
                "The count comes from Google's Chat search, which skips muted "
                "spaces and app messages, so it can run low.")
    if any(m.get("attachment") for m in messages):
        cues["chat_attachments"] = (
            "Attachments are listed in content.md, not downloaded. Drive "
            "attachments carry a fetch('<id>') you can run; files uploaded "
            "straight to Chat are named only."
        )
    if space.get("spaceHistoryState") == "HISTORY_OFF":
        warnings.append("History is off in this space: Google keeps its messages 24 hours only.")
    if warnings:
        cues["warnings"] = warnings

    return FetchResult(
        path=str(folder),
        content_file=str(content_path),
        format="markdown",
        type="chat",
        metadata=metadata,
        cues=cues,
    )

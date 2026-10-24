"""
search(sources=['chat']) — Google Chat messages across every space (mise-lumaha).

A sibling of tools/search.py, which sits near the module-size cap: do_search
submits run_chat_search to its thread pool and hands the future to
collect_chat_results. Query grammar and row shape live in extractors/chat.py.

Every chat search carries `chat_coverage`, because Google documents that its
Chat search skips muted spaces, messages from apps, and private messages — so
a zero is never "nothing was said".
"""

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from adapters.chat import get_space, list_members, search_messages
from cues_util import current_user_email
from extractors.chat import UNREAD_VS_APP, build_search_filter, format_search_hit, has_phrase, sent_by, space_label
from models import MiseError, SearchResult

# Distinct spaces named per search: each costs a spaces.get, plus a
# members.list for a DM or group chat. Rows beyond keep the raw space name.
_LABEL_CAP = 25
# is:unread lists this many of Google's unread hits before filtering them by the
# read flag and the phrase (the live account held 399 on 2026-10-24); past it
# the scan says it stopped.
_UNREAD_SCAN_CAP = 1000

CHAT_COVERAGE = (
    "Google Chat's search skips muted spaces, messages sent by apps, and private "
    "messages, so it is not a complete index: zero hits is not proof nothing "
    "was said. To read a conversation whole, fetch its space or thread "
    "(`space`/`thread` on each row, or a Chat link)."
)


def _name_space(space_name: str, me: str | None) -> tuple[dict[str, Any], str]:
    space = get_space(space_name)
    members = None
    if not space.get("displayName"):
        members = list_members(space_name, max_results=50)
    return space, space_label(space, members, me)


def _identity_after_first_call() -> str | None:
    """The user's address — read only AFTER a Google call has run (mise-raloge).

    current_user_email() is a cache filled when the sync client is first built,
    so read before any call it is None in a cold process even though the token
    carries _identity, and the own-message guard goes silently off. The search
    call mints that client, inside with_retry's conversion, so a credential
    failure still arrives as a MiseError the per-source funnel catches. (Minting
    it here with get_sync_client() lost for that reason: its
    CredentialsUnavailable would escape collect_chat_results.)
    """
    return current_user_email()


def run_chat_search(query: str, max_results: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run the search and name its spaces. Returns (rows newest-first, cues)."""
    q = build_search_filter(query)
    notes = list(q.notes)
    if q.unread:
        # is_unread() alone is not the answer: of its 399 live hits, 20 were
        # flagged read, including all 18 of the user's own. Keep Google's
        # read == false, drop the user's own, then (with a keyword) keep
        # whole-word matches in the text.
        found, scan_cut = search_messages(q.filter, max_results=_UNREAD_SCAN_CAP)
        me = _identity_after_first_call()
        hits = [m for m in found if m.get("read") is False and not sent_by(m, me)]
        if q.post_filter:
            hits = [m for m in hits if has_phrase(m, q.post_filter)]
        messages, truncated = hits[:max_results], len(hits) > max_results
        if scan_cut:
            notes.append(f"Only Google's newest {_UNREAD_SCAN_CAP} unread hits were "
                         "scanned; older unread messages were not.")
        if not me:
            notes.append("Your address is unresolved, so your own messages are "
                         "excluded by Google's read flag alone (it flagged all 18 "
                         "of the user's own as read when measured).")
    else:
        messages, truncated = search_messages(q.filter, max_results=max_results)
        me = _identity_after_first_call()

    names: list[str] = []
    for m in messages:
        name = (m.get("space") or {}).get("name")
        if name and name not in names:
            names.append(name)
    labelled: dict[str, tuple[dict[str, Any], str]] = {}
    failures: list[str] = []
    if names:
        with ThreadPoolExecutor(max_workers=min(6, len(names))) as pool:
            jobs = {n: pool.submit(_name_space, n, me) for n in names[:_LABEL_CAP]}
        for n, job in jobs.items():
            try:
                labelled[n] = job.result()
            except MiseError as e:  # every adapter failure arrives as one
                failures.append(f"{n}: {e.message}")

    rows = []
    for m in messages:
        space, label = labelled.get((m.get("space") or {}).get("name", ""), ({}, ""))
        rows.append(format_search_hit(m, space or None, label or None, me))
    rows.sort(key=lambda r: r.get("time", ""), reverse=True)

    cues: dict[str, Any] = {"chat_coverage": CHAT_COVERAGE, "chat_filter": q.filter}
    if q.unread:
        cues["chat_unread_vs_app"] = UNREAD_VS_APP
    if notes:
        cues["chat_query"] = " ".join(notes)
    if truncated:
        cues["chat_truncated"] = (
            f"Results capped at {len(rows)} — MORE MATCHED. They are the newest "
            "matches; raise max_results or narrow the query to see older ones."
        )
    unnamed = len(names) - len(labelled)
    if unnamed:
        why = []
        if len(names) > _LABEL_CAP:
            why.append(f"only the first {_LABEL_CAP} spaces are named per search")
        if failures:
            why.append(f"{len(failures)} lookup(s) failed, first: {failures[0]}")
        cues["chat_space_names"] = (
            f"{unnamed} of {len(names)} spaces left unnamed — {'; '.join(why)}. "
            "Those rows keep the spaces/… name, which fetch accepts."
        )
    return rows, cues


def collect_chat_results(job: "Future[Any]", result: SearchResult) -> None:
    """Fold the chat source's outcome into the search result (errors are per-source)."""
    try:
        rows, cues = job.result()
    except (MiseError, ValueError) as e:
        result.errors.append(f"Chat search failed: {getattr(e, 'message', None) or e}")
        return
    result.chat_results = rows
    result.cues.update(cues)

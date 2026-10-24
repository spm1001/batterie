"""
Google Chat extraction — pure functions over the Chat API's JSON (mise-lumaha).

No I/O: adapters/chat.py fetches, tools/ wire. Four jobs:

1. build_search_filter — turn a caller's `query` into a ChatQuery. Google's
   messages:search grammar is NOT Gmail's and NOT free text (all measured
   2026-10-24): a quoted string is one exact phrase ('"next week"': 386 of 393
   hits held the phrase); separate terms do NOT AND — '"meeting" "agenda"'
   returned 50 rows of which 35 held neither word and 8 both — and OR and NOT
   are invalid. A keyword ANDed with is_unread() is not trustworthy either:
   '"meeting" AND is_unread()' returned 33 messages, 12 of them absent from
   is_unread()'s own list and 17 without the word, while the true answer was
   16. So that combination is answered by listing unread messages and keeping
   those that contain the phrase (tools/search_chat.py).
2. space_label / format_search_hit — name a space a person would recognise.
   A DM's or group chat's displayName is EMPTY (0 of 12 group chats had one),
   so they are named after their members.
3. message_body — what a message says, including the ones with no `text`: a
   live sweep found messages carrying only a rich link (a Meet or Drive link),
   only a GIF, or only formattedText, which rendered as blank bodies.
4. render_conversation — a space or thread as markdown, newest LAST, replies
   grouped under the message that started their thread, as Chat shows them.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Gmail-style operators a caller is likely to try. Chat's filter has none of
# them, and quoting one into a phrase would search for the literal text —
# a confident wrong answer — so they are refused instead (accept-and-drop).
_OPERATOR_RE = re.compile(
    r'(?<!\S)(?:from|to|cc|bcc|in|is|has|subject|label|after|before|older_than|'
    r'newer_than|filename|text|sender|space|thread):\S+', re.I)
_UNREAD_RE = re.compile(r'(?<!\S)(?:is:unread|is_unread\(\))(?!\S)', re.I)
# AND is Google's joiner. It is stripped only where it JOINS terms — at the
# ends once is:unread is lifted out, or beside a quote — never inside a phrase:
# '"Q AND A"' stripped everywhere became '"Q A"' (live: 10 non-matching rows).
_AND_JOIN_RE = re.compile(r'^\s*AND(?!\S)|(?<!\S)AND\s*$|(?<=")\s+AND(?=\s+")')
_QUOTED_RE = re.compile(r'"([^"]*)"')

SNIPPET_CHARS = 160
HIT_TEXT_CHARS = 2000

_ONE_PHRASE = (
    "Google Chat's search cannot combine separate terms: measured, "
    "'\"meeting\" \"agenda\"' returned 50 messages of which 35 held neither word. "
    "Search ONE word or ONE exact phrase (optionally with is:unread), then fetch "
    "the space or thread a hit is in to read around it."
)


@dataclass
class ChatQuery:
    """A caller's chat query, translated.

    `filter` goes to messages:search. When `unread`, the caller keeps only
    messages Google flags unread (FULL view `read` == false) that the user did
    not send; when `post_filter` is set it also keeps only those whose text
    holds that phrase as whole words (has_phrase) — Google's own
    keyword-AND-unread is unreliable.
    """
    filter: str
    phrase: str | None = None
    unread: bool = False
    post_filter: str | None = None
    notes: list[str] = field(default_factory=list)


def build_search_filter(query: str) -> ChatQuery:
    """Translate `query` into a ChatQuery.

    Raises ValueError, with the working grammar, for input that would
    otherwise be searched wrongly or not at all.
    """
    text = (query or "").strip()
    unread = bool(_UNREAD_RE.search(text))
    text = _UNREAD_RE.sub(" ", text).strip()
    text = _AND_JOIN_RE.sub(" ", text).strip()
    notes: list[str] = []

    phrase: str | None = None
    if text.count('"') % 2:
        raise ValueError(f"Unbalanced quote in {query!r}. {_ONE_PHRASE}")
    quoted = _QUOTED_RE.findall(text)
    unquoted = _QUOTED_RE.sub(" ", text).strip()
    if len(quoted) > 1 or (quoted and unquoted):
        raise ValueError(f"{query!r} mixes several search terms. {_ONE_PHRASE}")
    if quoted:
        phrase = " ".join(quoted[0].split())
    elif unquoted:
        operator = _OPERATOR_RE.search(unquoted)
        if operator:
            raise ValueError(
                f"Chat search does not understand {operator.group(0)!r} — Google "
                "Chat's search takes keywords and is:unread only (no from:, in:, "
                "has: or dates). Search a distinctive word, then fetch the space "
                "the hits are in to read around them."
            )
        phrase = " ".join(unquoted.split())
        if " " in phrase:
            notes.append(
                f"Chat matched {phrase!r} as ONE EXACT PHRASE. Google Chat's search "
                "cannot AND separate words (measured: two words return mostly "
                "messages holding neither), so a zero here may mean the words "
                "never appeared side by side — try one distinctive word."
            )

    if not phrase and not unread:
        raise ValueError(
            "Chat search needs keywords, or is:unread for your unread messages "
            "(the two combine: 'is:unread budget')."
        )
    if phrase and unread:
        notes.append(
            f"is:unread with {phrase!r}: mise listed your unread messages and kept "
            "those whose text holds the phrase as whole words (any case). Google's "
            "combined filter is not used because it returned read messages, your "
            "own, and messages without the word (measured 2026-10-24)."
        )
        return ChatQuery("is_unread()", phrase, True, post_filter=phrase, notes=notes)
    if unread:
        return ChatQuery("is_unread()", None, True, notes=notes)
    return ChatQuery(f'"{phrase}"', phrase, False, notes=notes)


def format_time(ts: str | None) -> str:
    """'2026-10-22T14:03:12.123456Z' → '2026-10-22 14:03 UTC'; anything else verbatim."""
    if ts and len(ts) >= 16 and ts.endswith("Z") and ts[10] == "T":
        return f"{ts[:10]} {ts[11:16]} UTC"
    return ts or ""


def parse_time(ts: str | None) -> datetime | None:
    """Chat's RFC 3339 'Z' timestamps (0-9 fractional digits) → aware datetime."""
    m = re.match(r'^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?Z$', ts or "")
    if not m:
        return None
    frac = (m.group(2) or "")[:6].ljust(6, "0")
    return datetime.fromisoformat(f"{m.group(1)}.{frac}+00:00")


def reply_threads(messages: list[dict[str, Any]]) -> list[str]:
    """Threads with at least one reply among these messages — the ones whose
    read state decides whether a reply is unread — newest reply first, so a
    cap on how many are checked keeps the most recent conversations."""
    latest: dict[str, str] = {}
    for m in messages:
        thread = (m.get("thread") or {}).get("name", "")
        if m.get("threadReply") and thread:
            latest[thread] = max(latest.get(thread, ""), m.get("createTime", ""))
    return sorted(latest, key=lambda t: latest[t], reverse=True)


# Typographic quotes folded to ASCII before matching, on both sides. Google's
# search treats them as the same character (live: "don't" returned 1,067 hits,
# 200 with the curly form), and 12 of 379 unread messages held U+2019.
_QUOTE_FOLD = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'",
                             "\u201c": '"', "\u201d": '"', "\u2033": '"'})


def has_phrase(msg: dict[str, Any], phrase: str) -> bool:
    """Does the message TEXT hold this phrase as whole words (any case)?

    Text only (formattedText when text is empty): link URLs are not text, and
    a substring match let 'the' match 'they'. Curly quotes match straight ones.
    """
    words = [re.escape(w) for w in phrase.translate(_QUOTE_FOLD).split()]
    if not words:
        return False
    pattern = r'(?<!\w)' + r'\s+'.join(words) + r'(?!\w)'
    text = (msg.get("text") or msg.get("formattedText") or "").translate(_QUOTE_FOLD)
    return re.search(pattern, text, re.I) is not None


def sent_by(msg: dict[str, Any], email: str | None) -> bool:
    """Was this message sent by `email`? False when the address is unknown."""
    sender = ((msg.get("sender") or {}).get("email") or "").lower()
    return bool(email) and sender == (email or "").lower()


def unread_messages(
    messages: list[dict[str, Any]],
    space_last_read: datetime | None,
    thread_last_read: dict[str, datetime | None],
    self_email: str | None,
) -> set[str]:
    """Names of the messages the user has not read.

    Chat keeps two clocks. A message that starts a thread is unread when it is
    newer than the SPACE's lastReadTime; a reply is unread when it is newer than
    its THREAD's lastReadTime — opening a space does not read its threads
    (one live space had 84 unread replies, all older than the space clock).
    Measured 2026-10-24 against the per-message `read` flag of Google's
    FULL-view search over the newest 200 messages of all 26 spaces holding
    unread: 265 of 265 agreed (an earlier comparison against is_unread() alone
    looked like 14 false marks; the read flag showed all 14 really unread).
    The user's own messages are never unread. A reply whose
    thread is absent from `thread_last_read` is left unmarked — the caller
    must say so rather than let the gap read as "read".
    """
    me = (self_email or "").lower()
    out: set[str] = set()
    for m in messages:
        if me and ((m.get("sender") or {}).get("email") or "").lower() == me:
            continue
        created = parse_time(m.get("createTime"))
        if m.get("threadReply"):
            thread = (m.get("thread") or {}).get("name", "")
            if thread not in thread_last_read:
                continue
            ref = thread_last_read[thread]
        else:
            if space_last_read is None:
                continue
            ref = space_last_read
        if created is not None and (ref is None or created > ref):
            out.add(m.get("name", ""))
    return out


def member_names(members: list[dict[str, Any]]) -> dict[str, str]:
    """users/… → display name, from a members.list page."""
    return {
        m["member"]["name"]: m["member"].get("displayName") or ""
        for m in members
        if isinstance(m.get("member"), dict) and m["member"].get("name")
    }


def space_label(space: dict[str, Any], members: list[dict[str, Any]] | None,
                self_email: str | None) -> str:
    """A name a person would recognise for this space.

    Named spaces use their displayName. A DM is 'DM with <the other person>'
    and a group chat 'Group chat: A, B, C' — built from members, leaving out
    the signed-in user when their address is known.
    """
    if space.get("displayName"):
        return str(space["displayName"])
    kind = space.get("spaceType", "")
    people = [
        m["member"] for m in members or []
        if isinstance(m.get("member"), dict) and m["member"].get("type", "HUMAN") == "HUMAN"
    ]
    others = [p for p in people if not self_email or (p.get("email") or "").lower() != self_email.lower()]
    names = [p.get("displayName") or p.get("email") or p.get("name", "") for p in others or people]
    names = [n for n in names if n]
    if kind == "DIRECT_MESSAGE":
        return f"DM with {names[0]}" if names else "Direct message"
    if names:
        shown = ", ".join(names[:5]) + (f" and {len(names) - 5} more" if len(names) > 5 else "")
        return f"Group chat: {shown}"
    return "Group chat" if kind == "GROUP_CHAT" else space.get("name", "Chat space")


def sender_name(msg: dict[str, Any], names: dict[str, str] | None = None) -> str:
    """The sender's display name, back-filled from members, else their user id."""
    sender = msg.get("sender") or {}
    name = sender.get("displayName") or (names or {}).get(sender.get("name", ""), "")
    name = name or sender.get("name") or "unknown sender"
    return f"{name} (app)" if sender.get("type") == "BOT" else name


def _attachment_notes(msg: dict[str, Any]) -> list[str]:
    notes = []
    for att in msg.get("attachment") or []:
        label = att.get("contentName") or "attachment"
        drive_id = (att.get("driveDataRef") or {}).get("driveFileId")
        if drive_id:
            notes.append(f"{label} (Drive file — fetch('{drive_id}'))")
        else:
            notes.append(f"{label} ({att.get('contentType') or 'file'}, uploaded to Chat — not downloaded)")
    return notes


_RICH_LINK_KINDS = {"DRIVE_FILE": "Drive file", "CHAT_SPACE": "Chat space", "MEET_SPACE": "Meet link"}


def message_body(msg: dict[str, Any]) -> str:
    """What a message says, for messages with and without `text`.

    Falls back to formattedText, and adds each rich link (Drive, Meet, Chat
    space) whose URI the text does not already show, and each GIF. Google's
    richLinkMetadata carries no title (86 rich links across 40 spaces held
    none), so a Drive link is named by its URI and, when present, its file id.
    """
    text = (msg.get("text") or "").strip("\n")
    if not text.strip():
        text = (msg.get("formattedText") or "").strip()
    extras: list[str] = []
    for a in msg.get("annotations") or []:
        md = a.get("richLinkMetadata") or {}
        uri = md.get("uri")
        if a.get("type") != "RICH_LINK" or not uri or uri in text:
            continue
        drive_id = ((md.get("driveLinkData") or {}).get("driveDataRef") or {}).get("driveFileId")
        kind = _RICH_LINK_KINDS.get(md.get("richLinkType", ""), "link")
        extras.append(f"[{kind}: {uri}" + (f" — fetch('{drive_id}')" if drive_id else "") + "]")
    extras += [f"[GIF: {g['uri']}]" for g in msg.get("attachedGifs") or [] if g.get("uri")]
    return "\n".join(t for t in (text, *extras) if t)


def format_search_hit(msg: dict[str, Any], space: dict[str, Any] | None,
                      label: str | None, self_email: str | None = None) -> dict[str, Any]:
    """One messages:search hit as a search-result row.

    `unread: true` when Google's FULL view flags it unread and the user did
    not send it.
    """
    text = message_body(msg)
    row: dict[str, Any] = {
        "message": msg.get("name", ""),
        "space": (msg.get("space") or {}).get("name", ""),
        "thread": (msg.get("thread") or {}).get("name", ""),
        "from": sender_name(msg),
        "time": msg.get("createTime", ""),
        "text": text[:HIT_TEXT_CHARS],
    }
    if label:
        row["space_name"] = label
    if space:
        row["space_type"] = space.get("spaceType", "")
        if space.get("spaceUri"):
            row["web_link"] = space["spaceUri"]
    sender_email = (msg.get("sender") or {}).get("email")
    if sender_email:
        row["from_email"] = sender_email
    if len(text) > HIT_TEXT_CHARS:
        row["text_truncated"] = True
    if msg.get("threadReply"):
        row["is_reply"] = True
    if msg.get("read") is False and not sent_by(msg, self_email):
        row["unread"] = True
    attachments = _attachment_notes(msg)
    if attachments:
        row["attachments"] = attachments
    return row


def snippet(text: str) -> str:
    """A one-line preview of a message body."""
    flat = " ".join((text or "").split())
    return flat if len(flat) <= SNIPPET_CHARS else flat[:SNIPPET_CHARS - 1] + "…"


def _render_message(msg: dict[str, Any], names: dict[str, str], *, reply: bool,
                    target: str | None, unread: bool) -> str:
    head = f"**{sender_name(msg, names)}** — {format_time(msg.get('createTime'))}"
    if msg.get("lastUpdateTime"):
        head += " (edited)"
    if unread:
        head += " · UNREAD"
    if target and msg.get("name") == target:
        head += "  ← the linked message"
    body: list[str] = [message_body(msg)] if message_body(msg) else []
    if msg.get("quotedMessageMetadata"):
        body.insert(0, "_(quote-replies to an earlier message)_")
    body += [f"[attachment: {a}]" for a in _attachment_notes(msg)]
    reactions = [
        f"{(r.get('emoji') or {}).get('unicode', '?')} {r.get('reactionCount', 0)}"
        for r in msg.get("emojiReactionSummaries") or []
    ]
    if reactions:
        body.append("Reactions: " + ", ".join(reactions))
    lines = [head, *("\n".join(body).splitlines() or [""])]
    if reply:
        return "\n".join(f"> {line}" if line else ">" for line in [f"↳ {lines[0]}", *lines[1:]])
    return "\n".join(lines)


def render_conversation(
    title: str,
    space: dict[str, Any],
    messages_newest_first: list[dict[str, Any]],
    members: list[dict[str, Any]],
    *,
    truncated: bool,
    thread: str | None = None,
    target: str | None = None,
    unread: set[str] | None = None,
) -> str:
    """A space or one thread as markdown: header, then threads oldest→newest.

    Each thread's replies sit under the message that started it, as Chat shows
    them, so a late reply appears beside its parent rather than at the bottom.
    Threads are ordered by their first message in the window.
    """
    names = member_names(members)
    msgs = sorted(messages_newest_first, key=lambda m: m.get("createTime", ""))
    groups: dict[str, list[dict[str, Any]]] = {}
    for m in msgs:
        key = (m.get("thread") or {}).get("name") or m.get("name", "")
        groups.setdefault(key, []).append(m)

    scope = f"thread {thread}" if thread else f"{space.get('spaceType', 'space').lower().replace('_', ' ')} {space.get('name', '')}"
    lines = [f"# {title}", "", f"Google Chat {scope}."]
    if space.get("spaceUri"):
        lines.append(f"Open in Chat: {space['spaceUri']}")
    window = f"{len(msgs)} message(s)"
    if truncated:
        window = f"the newest {len(msgs)} messages — OLDER MESSAGES EXIST and are not in this file"
    lines.append(f"Showing {window}; oldest first, times in UTC, replies under the message that began their thread.")
    if space.get("spaceHistoryState") == "HISTORY_OFF":
        lines.append("History is OFF in this space: Google keeps its messages for 24 hours only.")
    lines.append("")

    for group in groups.values():
        lines.append("---")
        lines.append("")
        if group[0].get("threadReply"):
            lines.append("_(this thread began before the messages shown)_")
            lines.append("")
        for i, m in enumerate(group):
            reply = i > 0 or bool(m.get("threadReply"))
            lines.append(_render_message(m, names, reply=reply, target=target,
                                         unread=m.get("name") in (unread or set())))
            lines.append("")
    if not msgs:
        lines.append("_(no messages visible)_")
    return "\n".join(lines).rstrip() + "\n"


def participants(messages: list[dict[str, Any]], members: list[dict[str, Any]]) -> list[str]:
    """Distinct sender names in order of first appearance (oldest first)."""
    names = member_names(members)
    seen: dict[str, None] = {}
    for m in sorted(messages, key=lambda m: m.get("createTime", "")):
        seen.setdefault(sender_name(m, names), None)
    return list(seen)


# Measured 2026-10-24: mise said 200+ unread while the app's Home "Unread" view
# said "all quiet". One read state: inside a space the app drew its Unread
# divider where the API's clock pointed. The summary views filter it.
UNREAD_VS_APP = (
    "This is the read state the Chat app shows INSIDE each space (its 'Unread' "
    "divider). The app's Home 'Unread' view and bold sidebar can look empty "
    "while spaces still hold unread — they don't surface every space (for "
    "example ones not set to notify) — so don't read a quiet sidebar as "
    "proof these are read."
)

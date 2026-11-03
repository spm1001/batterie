"""Inline replies written inside a quoted message (mise-lopune), and quoted
history the thread holds nowhere else (mise-nozolu, ThreadQuotes at the end).

A reply that says "response below" and answers inside the quote reaches the
plain-text part with its answers '>'-prefixed like the text they answer, so
quote stripping deletes them and the deposit reads as a complete, empty
reply. So the quote is compared with the thread's earlier messages instead:
runs of words inside the quote that no earlier message contains are the
replier's own.

Word 4-gram shingles rather than difflib: indifferent to rewrapping, to which
earlier message is quoted, and to nested quote levels, and linear in length.

Novel text in a quote is NOT enough on its own. The first sweep over real
mail (27 Sep 2026: 43 multi-message threads, 10 firings, 1 true) found that
quotes routinely carry text the earlier message as fetched never had — the
legal footer a mail gateway appends in transit, the links a client adds as it
quotes an address or phone number, the header block of a forward, a chain
of messages that never reached this thread. So the gates: the reply's own
text must point into the quote (or be empty); link targets, header lines and
footer paragraphs count as neither old nor new; and a passage must be an
INSERTION — the quoted words either side of it must sit side by side in an
earlier message, so that deleting the passage restores what was quoted. A
second sweep (97 threads that say "below" or "inline") kept 3 true
answer-in-quote replies and rejected every gateway footer and forward header.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

from extractors.talon_signature import split_forward_sections
from models import EmailMessage, GmailThreadData

_WORD = re.compile(r"\w+")
_QUOTE_PREFIX = re.compile(r"^(>\s?)+")
# Text a client or gateway adds around a quote, whose words count as known:
# link targets (<https://…>, <mailto:…>, <+44…>, <name@host>, bare URLs),
# message-header lines, and any paragraph carrying a legal-footer phrase.
_LINK = re.compile(r"<[^\s<>]+>|\b(?:https?://|www\.)\S+")
_HEADER_LINE = re.compile(
    r"^[*_\s]*(?:from|sent|to|cc|bcc|date|subject)[*_\s]*:.*$|^.*(?:forwarded message|original message).*$",
    re.IGNORECASE | re.MULTILINE,
)
_FOOTER = re.compile(
    r"registered (?:office|in england)|registration no|company (?:no|number)|intended (?:solely|only) for"
    r"|received this (?:e-?mail|message) in error|(?:confidential|privileged) (?:information|and)",
    re.IGNORECASE,
)
# The reply's own words saying its content is inside the quote.
_POINTS_IN = re.compile(
    r"\b(?:below|beneath|underneath|inline|in-line|interspersed|in\s+(?:red|blue|green|"
    r"orange|purple|pink|yellow|bold|italics?|caps|colou?r))\b"
    r"|\b(?:my|see)\s+(?:comments|answers|responses|replies|notes)\b",
    re.IGNORECASE,
)
_SHINGLE = 4        # words per shingle
_MIN_RUN = 4        # a shorter novel run is reflow or rendering noise
_MERGE_GAP = 3      # known words allowed inside one reply before it splits
_MIN_COVERAGE = 0.3  # below this the quote is not of an earlier message
_CONTEXT_WORDS = 8  # quoted words shown before each reply
_MIN_HISTORY = 30   # words of unknown quote worth keeping as history (mise-nozolu)


@dataclass
class InlineReply:
    after: str  # the quoted words the reply follows
    text: str


def reply_points_into_quote(own_text: str) -> bool:
    """Whether a reply's own text sends the reader into its quote, or is empty."""
    return bool(_POINTS_IN.search(own_text)) or len(_WORD.findall(own_text)) < 3


def quoted_text(body: str) -> str:
    """The '>'-prefixed lines of a body, unquoted at every nesting level."""
    lines = (line.lstrip() for line in body.split("\n"))
    return "\n".join(_QUOTE_PREFIX.sub("", line) for line in lines if line.startswith(">"))


def _shingles(text: str) -> set[tuple[str, ...]]:
    words = [m.group().lower() for m in _WORD.finditer(text)]
    return {tuple(words[i:i + _SHINGLE]) for i in range(len(words) - _SHINGLE + 1)}


def _span(text: str, start: int, end: int) -> str:
    """Text between two offsets, carrying trailing punctuation, whitespace collapsed."""
    tail = re.match(r"\S*", text[end:])
    return " ".join(text[start:end + (tail.end() if tail else 0)].split())


def _added_spans(quote: str) -> list[tuple[int, int]]:
    """Offsets of text the quoting client or a gateway added, not the author."""
    spans = [(m.start(), m.end()) for m in _LINK.finditer(quote)]
    spans += [(m.start(), m.end()) for m in _HEADER_LINE.finditer(quote)]
    offset = 0
    for para in re.split(r"(\n\s*\n)", quote):
        if _FOOTER.search(para):
            spans.append((offset, offset + len(para)))
        offset += len(para)
    return spans


Shingles = set[tuple[str, ...]]


@dataclass
class Known:
    """The earlier messages' shingles in two readings: as written, and with link targets removed.

    Kept apart on purpose. Matching the quote against the union let the
    link-free reading of a question ('read the brief <link> and the timeline
    <link>') mark an answer echoing it ('I read the brief and the timeline')
    as already said, and the answer was dropped (cold review, 3 Nov 2026). So
    the link-free reading is consulted only where the quote itself skips a link.
    """
    full: Shingles
    free: Shingles

    def add(self, text: str) -> None:
        self.full |= _shingles(text)
        self.free |= _shingles(_LINK.sub(" ", text))


def _nexts(skip: list[bool]) -> list[int]:
    """nxt[i]: the first index after i not skipped (len when none), computed once."""
    nxt, following = [0] * len(skip), len(skip)
    for i in range(len(skip) - 1, -1, -1):
        nxt[i] = following
        if not skip[i]:
            following = i
    return nxt


def _insertion_end(words: list[str], matched: list[bool], link: list[bool], neutral: list[bool],
                   start: int, end: int, known: Known) -> int | None:
    """Where the passage from `start` ends, if deleting it restores the original.

    The two quoted words before the passage and the two after it must sit side
    by side in an earlier message: an answer typed between two lines of a
    question passes; a footer, a forward header or a chain of messages from
    outside the thread does not. The end is searched backwards from `end`
    because a short quoted tail ("Thanks, Priya") is too short to match a
    shingle on its own and so arrives glued to the passage. Both anchors come
    from one reading, tried in turn: as written (a link's own words count),
    then with links skipped, each against its own shingles.
    """
    readings = (
        (known.full, [neutral[i] and not link[i] for i in range(len(words))]),
        (known.free, neutral),
    )
    for shingles, skip in readings:
        before = [words[i] for i in range(start - 1, -1, -1) if matched[i] and not skip[i]][:2][::-1]
        if len(before) < 2:
            continue
        nxt = _nexts(skip)
        for k in range(end, start + _MIN_RUN - 2, -1):
            a = nxt[k]
            b = nxt[a] if a < len(words) else len(words)
            if b < len(words) and tuple(before + [words[a], words[b]]) in shingles:
                return k
    return None


def find_inline_replies(body: str, earlier: list[str]) -> tuple[list[InlineReply], float]:
    """Novel passages inside a message's quote, and the share of it that is known.

    Returns ([], coverage) when the quote is mostly unknown — a quote of a
    message outside the thread, which is not an inline reply.
    """
    known = Known(set(), set())
    for text in earlier:
        known.add(text)
    return replies_against(body, known)


def _next_novel(covered: list[bool], seen: list[int], after: int, end: int) -> int | None:
    """The first novel word after the first known one following `after`, up to `end`."""
    rest = [i for i in seen if after < i <= end]
    first_known = next((n for n, i in enumerate(rest) if covered[i]), None)
    if first_known is None:
        return None
    return next((i for i in rest[first_known:] if not covered[i]), None)


def replies_against(body: str, known: Known, want_replies: bool = True) -> tuple[list[InlineReply], float]:
    """find_inline_replies against shingles already built from the earlier messages.

    want_replies=False stops at the coverage, for a reply that does not point
    into its quote and so can only need the quoted-history check.
    """
    quote = quoted_text(body)
    tokens = list(_WORD.finditer(quote))
    if not known.full or len(tokens) < _SHINGLE:
        return [], 0.0

    words = [t.group().lower() for t in tokens]
    links = [(m.start(), m.end()) for m in _LINK.finditer(quote)]
    link = [any(a <= t.start() < b for a, b in links) for t in tokens]
    added = _added_spans(quote)
    neutral = [any(a <= t.start() < b for a, b in added) for t in tokens]
    # A link must neither split an answer (mise-pogifo) nor stop a quoted link
    # anchoring the answer after it, so a window that steps OVER a link in the
    # quote may match the earlier messages' link-free reading; every other
    # window matches only as written (Known says why). Runs skip links.
    seen = [i for i in range(len(words)) if not link[i]]
    matched = [False] * len(words)
    for j in range(len(words) - _SHINGLE + 1):
        if tuple(words[j:j + _SHINGLE]) in known.full:
            matched[j:j + _SHINGLE] = [True] * _SHINGLE
    for j in range(len(seen) - _SHINGLE + 1):
        window = seen[j:j + _SHINGLE]
        if window[-1] - window[0] >= _SHINGLE and tuple(words[i] for i in window) in known.free:
            for i in window:
                matched[i] = True
    covered = [m or n for m, n in zip(matched, neutral)]
    coverage = sum(covered) / len(covered)
    if coverage < _MIN_COVERAGE or not want_replies:
        return [], coverage

    runs: list[list[int]] = []
    gap = 0  # known words since the last novel one, links not counted
    for i in seen:
        if covered[i]:
            gap += 1
            continue
        if runs and gap <= _MERGE_GAP:
            runs[-1][1] = i
        else:
            runs.append([i, i])
        gap = 0

    replies = []
    while runs:
        start, end = runs.pop(0)
        stop = _insertion_end(words, matched, link, neutral, start, end, known)
        # Two answers either side of a short quoted line merge into one run;
        # whatever follows the accepted part (or the rejected first part) is
        # judged again as a run of its own.
        rest = _next_novel(covered, seen, stop if stop is not None else start, end)
        if rest is not None:
            runs.insert(0, [rest, end])
        if stop is None or sum(not covered[i] for i in range(start, stop + 1)) < _MIN_RUN:
            continue
        text = _span(quote, tokens[start].start(), tokens[stop].end())
        ctx = max(0, start - _CONTEXT_WORDS)
        after = _span(quote, tokens[ctx].start(), tokens[start - 1].end()) if start else ""
        replies.append(InlineReply(after=after, text=text))
    return replies, coverage


def render_inline_replies(replies: list[InlineReply]) -> str:
    """The block appended to a reply's content — each passage after its anchor."""
    parts = [
        "**Inline replies** — text inside the quoted message that no earlier "
        "message in this thread contains, usually answers written into the "
        "quote. Each follows the quoted words shown:"
    ]
    for reply in replies:
        if reply.after:
            parts.append(f"> …{reply.after}")
        parts.append(reply.text)
    return "\n\n".join(parts)


def render_quoted_history(own: str) -> str:
    """The block appended when a quote holds history the thread lacks: its lines as quoted."""
    lines = [line.lstrip().rstrip("\r") for line in own.split("\n") if line.lstrip().startswith(">")]
    return ("**Quoted history** — quoted text that no earlier message in this thread "
            "contains, moved here by quote stripping (history from before you were copied in, "
            "a quote from outside the thread, or a newsletter's own blockquotes):\n\n"
            + "\n".join(lines))


class ThreadQuotes:
    """Each message's quote judged against the messages before it (mise-lopune, mise-nozolu).

    How much of a quote the earlier messages contain decides what it is:
    mostly known, and the novel runs inside it are answers typed into the
    quote; mostly unknown, and the quote IS the novel text, history from
    before you were copied in that the deposit held nowhere. A census of 516
    real threads (3 Nov 2026) found 12 such quotes in non-machine mail, 189 to
    2,930 words, all real content; deposited rather than cued, since a cue
    would send the reader to Gmail for text the deposit can carry for the cost
    of its length. Machine mail is judged the same way: keeping its '>' lines
    in place instead put a whole quoted message back into every out-of-office
    reply (cold review, 3 Nov 2026), while coverage keeps only what is novel.

    The earlier messages' shingles are kept as the thread is walked, so a
    long chain that quotes everything before it costs linear time, not cubic
    (a 100-message synthetic chain took 32 s when they were rebuilt per message).
    """

    def __init__(self, data: GmailThreadData, raw_body: Callable[[EmailMessage], str]):
        self.data, self.raw_body = data, raw_body
        self.known = Known(set(), set())

    def keep(self, i: int, body: str) -> str:
        """Message i's body (1-based) with what its quote holds that stripping would lose."""
        message = self.data.messages[i - 1]
        raw = self.raw_body(message)
        kept = self._judge(i, body, raw)
        self.known.add(raw)
        return kept

    def _judge(self, i: int, body: str, raw: str) -> str:
        own, _ = split_forward_sections(raw)
        replies, coverage = replies_against(own, self.known, want_replies=reply_points_into_quote(body))
        if replies:
            self.data.warnings.append(
                f"Message {i}: kept {len(replies)} inline reply passage(s) — text written "
                "inside the quoted message, which quote stripping would have dropped"
            )
            return f"{body}\n\n{render_inline_replies(replies)}".strip()
        words = len(_WORD.findall(quoted_text(own)))
        if coverage >= _MIN_COVERAGE or words < _MIN_HISTORY:
            return body
        self.data.warnings.append(
            f"Message {i}: kept {words} words of quoted history that no earlier message in "
            "this thread contains, as a 'Quoted history' block after the message"
        )
        return f"{body}\n\n{render_quoted_history(own)}".strip()

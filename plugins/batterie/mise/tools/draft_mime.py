"""
Byte-level surgery on a Gmail draft's raw MIME (mise-en-space-gujuku).

Pure functions — no I/O. tools/draft_replace.py fetches the raw message,
asks this module for a plan, and writes the result back with drafts.update.

Why byte offsets, not email.message round-tripping: re-serialising a parsed
message re-folds headers, re-encodes every part and can re-wrap boundaries, so
"the To/References/attachments survived" would be true of the decoded values
but not of the bytes Gmail stores. Here the tree is walked with offsets into
the original bytes, only the BODY of each inline text/plain and text/html leaf
is decoded, edited and re-encoded with its own transfer encoding, and the new
body is spliced back. Every other byte — top-level headers, part headers,
boundaries, attachments, inline signature images — is the original byte.

Inside an edited leaf, the decoded text outside the edited spans is unchanged
character for character; the ENCODED bytes may re-wrap (quoted-printable soft
breaks and base64 lines are recomputed), which is the honest limit of the
guarantee.

The one case where a part header must change: a 7bit part that gains a
non-ASCII character, or a part whose declared charset cannot hold the edit. Then
that part alone is switched to quoted-printable / UTF-8 and the plan says so.
"""

from __future__ import annotations

import base64
import binascii
import html
import re
from dataclasses import dataclass, field
from email.message import Message
from email.parser import BytesHeaderParser
from email.policy import compat32

_HEAD_END = re.compile(rb"\r?\n\r?\n")
_EDITABLE_TYPES = ("text/plain", "text/html")


@dataclass
class TextLeaf:
    """One inline text/plain or text/html leaf, located in the raw bytes."""
    content_type: str
    head_start: int   # first byte of this part's header block
    body_start: int   # first byte of the body (after the blank line)
    body_end: int     # one past the body's last byte (before the CRLF of the next delimiter)
    cte: str
    charset: str


@dataclass
class PartReport:
    content_type: str
    matches: int
    form: str = "verbatim"          # how find matched: verbatim | html-escaped
    note: str | None = None


@dataclass
class DraftEditPlan:
    ok: bool
    new_raw: bytes | None = None
    parts: list[PartReport] = field(default_factory=list)
    message: str = ""
    previews: list[str] = field(default_factory=list)
    reencoded: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Walking the tree with offsets
# ---------------------------------------------------------------------------

def _split_head(raw: bytes, start: int, end: int) -> tuple[Message, int]:
    """Parse the header block of the entity at raw[start:end]; return (headers, body_start)."""
    if raw.startswith(b"\r\n", start):
        return Message(), start + 2          # a part with no headers at all
    if raw.startswith(b"\n", start):
        return Message(), start + 1
    m = _HEAD_END.search(raw, start, end)
    head_end, body_start = (m.start(), m.end()) if m else (end, end)
    headers = BytesHeaderParser(policy=compat32).parsebytes(raw[start:head_end] + b"\r\n\r\n")
    return headers, body_start


def _delimiters(raw: bytes, boundary: bytes, start: int, end: int) -> list[tuple[int, int, bool]]:
    """(delimiter_start incl. its preceding line break, line_end, is_close) per delimiter line."""
    delim = b"--" + boundary
    found: list[tuple[int, int, bool]] = []
    i = start
    while True:
        j = raw.find(delim, i, end)
        if j < 0:
            break
        if not (j == start or raw[j - 1:j] == b"\n"):
            i = j + 1
            continue
        k = j + len(delim)
        is_close = raw[k:k + 2] == b"--"
        if is_close:
            k += 2
        eol = raw.find(b"\n", k, end)
        line_end = end if eol < 0 else eol + 1
        if raw[k:line_end].strip():
            i = j + 1                           # a longer token sharing the prefix
            continue
        pre = j
        if j > start and raw[j - 1:j] == b"\n":
            pre = j - 1
            if j - 1 > start and raw[j - 2:j - 1] == b"\r":
                pre = j - 2
        found.append((pre, line_end, is_close))
        i = line_end
        if is_close:
            break
    return found


def _is_attachment(headers: Message) -> bool:
    disposition = (headers.get("Content-Disposition") or "").strip().lower()
    return disposition.startswith("attachment") or bool(headers.get_filename())


def _walk(raw: bytes, start: int, end: int, out: list[TextLeaf]) -> None:
    headers, body_start = _split_head(raw, start, end)
    ctype = headers.get_content_type()
    if headers.get_content_maintype() == "multipart":
        boundary = headers.get_boundary()
        if not boundary:
            return
        delims = _delimiters(raw, boundary.encode("ascii", "replace"), body_start, end)
        for at, (_, part_start, close) in enumerate(delims):
            if close:
                break
            # A missing close delimiter leaves the last part running to the
            # end of the entity, as Python's own parser reads it.
            part_end = delims[at + 1][0] if at + 1 < len(delims) else end
            _walk(raw, part_start, part_end, out)
        return
    if ctype in _EDITABLE_TYPES and not _is_attachment(headers):
        out.append(TextLeaf(
            content_type=ctype,
            head_start=start,
            body_start=body_start,
            body_end=end,
            cte=(headers.get("Content-Transfer-Encoding") or "7bit").strip().lower(),
            charset=(headers.get_content_charset() or "us-ascii"),
        ))


def text_leaves(raw: bytes) -> list[TextLeaf]:
    """Every inline text/plain and text/html leaf of the message, in order."""
    out: list[TextLeaf] = []
    _walk(raw, 0, len(raw), out)
    return out


# ---------------------------------------------------------------------------
# Decoding and re-encoding one body
# ---------------------------------------------------------------------------

def _line_ending(body: bytes) -> bytes:
    return b"\r\n" if b"\r\n" in body else b"\n"


def decode_body(raw: bytes, leaf: TextLeaf) -> str:
    """The leaf's body as text. Raises ValueError/LookupError when it cannot be read."""
    body = raw[leaf.body_start:leaf.body_end]
    if leaf.cte == "base64":
        data = base64.b64decode(re.sub(rb"\s+", b"", body), validate=True)
    elif leaf.cte == "quoted-printable":
        data = binascii.a2b_qp(body)
    elif leaf.cte in ("7bit", "8bit", "binary"):
        data = body
    else:
        raise ValueError(f"unsupported Content-Transfer-Encoding {leaf.cte!r}")
    return data.decode(leaf.charset)


def _encode_base64(data: bytes, eol: bytes, trailing: bool) -> bytes:
    b64 = base64.b64encode(data)
    lines = [b64[i:i + 76] for i in range(0, len(b64), 76)] or [b""]
    return eol.join(lines) + (eol if trailing else b"")


def encode_body(
    text: str, leaf: TextLeaf, original: bytes, message_crlf: bool = True,
) -> tuple[bytes, str | None, str | None]:
    """Re-encode text with the leaf's own encoding.

    Returns (body_bytes, new_cte, new_charset): new_cte/new_charset are None
    when the part header can stay as it is, and name the replacement when a
    7bit part gained non-ASCII text or the declared charset cannot hold it.

    Line breaks the encoder adds (base64 wrapping, QP soft breaks) follow the
    body's own convention, or the message's when the body was one line —
    b2a_qp writes bare LF unless its input already holds CRLF, which would put
    bare LFs into a CRLF message (cold review, 2026-11-15).
    """
    eol = _line_ending(original) if b"\n" in original else (b"\r\n" if message_crlf else b"\n")
    trailing = original.endswith(b"\n")
    charset, new_charset = leaf.charset, None
    try:
        data = text.encode(charset)
    except UnicodeEncodeError:
        charset = new_charset = "utf-8"   # any declared charset that cannot hold the edit
        data = text.encode(charset)
    cte, new_cte = leaf.cte, None
    if cte == "7bit" and (not data.isascii() or any(len(l) > 998 for l in data.splitlines())):
        cte = new_cte = "quoted-printable"
    if cte == "base64":
        return _encode_base64(data, eol, trailing), new_cte, new_charset
    if cte == "quoted-printable":
        qp = binascii.b2a_qp(data, istext=True)
        if eol == b"\r\n":
            qp = re.sub(rb"(?<!\r)\n", b"\r\n", qp)
        return qp, new_cte, new_charset
    return data, new_cte, new_charset


_CTE_LINE = re.compile(rb"(?im)^content-transfer-encoding:[^\r\n]*(\r?\n[ \t][^\r\n]*)*")
_CHARSET_PARAM = re.compile(rb"(?i)(charset\s*=\s*)(\"[^\"]*\"|[^;\s]+)")
_CT_LINE = re.compile(rb"(?im)^content-type:[^\r\n]*(\r?\n[ \t][^\r\n]*)*")


def _rewrite_part_head(head: bytes, new_cte: str | None, new_charset: str | None) -> bytes:
    """Change only the CTE line and/or the charset parameter of one part's header block."""
    eol = _line_ending(head) if b"\n" in head else b"\r\n"
    added: list[bytes] = []
    if new_charset:
        m = _CT_LINE.search(head)
        if m:
            ct = m.group(0)
            if _CHARSET_PARAM.search(ct):
                ct = _CHARSET_PARAM.sub(lambda p: p.group(1) + b'"' + new_charset.encode() + b'"', ct, count=1)
            else:
                ct = ct + b'; charset="' + new_charset.encode() + b'"'
            head = head[:m.start()] + ct + head[m.end():]
        else:  # a headerless part is text/plain by RFC 2045's default
            added.append(b'Content-Type: text/plain; charset="' + new_charset.encode() + b'"')
    if new_cte:
        line = b"Content-Transfer-Encoding: " + new_cte.encode()
        if _CTE_LINE.search(head):
            head = _CTE_LINE.sub(lambda _: line, head, count=1)
        else:
            added.append(line)
    if added:
        kept = head.rstrip(b"\r\n")
        head = (kept + eol if kept else b"") + eol.join(added) + eol + eol
    return head


# ---------------------------------------------------------------------------
# The edit plan
# ---------------------------------------------------------------------------

def _crlf_normalised(text: str, message_crlf: bool) -> bool:
    """True when it is safe to edit text in LF form and convert back to CRLF.

    Every line break is CRLF — or there is none, in a CRLF message, so that a
    replacement carrying a line break does not insert a bare LF."""
    if "\r\n" in text:
        return "\n" not in text.replace("\r\n", "")
    return "\n" not in text and message_crlf


def html_forms(find: str) -> list[str]:
    """The spellings a plain-text phrase may take in an HTML source, verbatim first."""
    base = html.escape(find, quote=False)
    forms = [find, base]
    for apos in ("'", "&#39;", "&#x27;"):
        for quot in ('"', "&quot;"):
            forms.append(base.replace("'", apos).replace('"', quot))
    seen: list[str] = []
    for f in forms:
        if f not in seen:
            seen.append(f)
    return seen


def html_replacement(content: str) -> str:
    """Plain-text replacement rendered for the HTML part: escaped, line breaks as <br>."""
    # quote=False: the replacement only ever lands in a text node (see _edit_html).
    return html.escape(content, quote=False).replace("\n", "<br>")


# Markup a match must never land in: comments, style/script bodies, and tags
# (whose attributes — alt, title, style, href — are not the text a reader sees).
_HTML_NON_TEXT = re.compile(
    r"(<!--.*?-->|<style\b.*?</style\s*>|<script\b.*?</script\s*>|<[^>]*>)",
    re.S | re.I,
)


# A character reference in a text node: &amp; &#39; &#x27; &nbsp;
_CHAR_REF = re.compile(r"&(?:#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);")


def _text_segments(source: str) -> list[str]:
    """source split so that even indexes are text nodes and odd ones are markup."""
    return _HTML_NON_TEXT.split(source)


def visible_text_count(source: str, find: str) -> int:
    """How often find appears in the HTML's visible text — a diagnostic, never an edit target."""
    visible = "".join(_text_segments(source)[0::2])
    visible = html.unescape(visible).replace("\xa0", " ")
    squash = lambda s: re.sub(r"\s+", " ", s)
    return squash(visible).count(squash(find))


def _preview(text: str, replacement: str, limit: int = 3, width: int = 60) -> list[str]:
    out: list[str] = []
    start = 0
    while replacement and len(out) < limit:
        at = text.find(replacement, start)
        if at < 0:
            break
        lo, hi = max(0, at - width), min(len(text), at + len(replacement) + width)
        snippet = text[lo:hi].replace("\r\n", "\n").replace("\n", " / ")
        out.append(("…" if lo else "") + snippet + ("…" if hi < len(text) else ""))
        start = at + len(replacement)
    return out


def _edit_plain(text: str, find: str, content: str, message_crlf: bool) -> tuple[int, str]:
    if _crlf_normalised(text, message_crlf):
        lf = text.replace("\r\n", "\n")
        f, c = find.replace("\r\n", "\n"), content.replace("\r\n", "\n")
        n = lf.count(f)
        return n, lf.replace(f, c).replace("\n", "\r\n")
    return text.count(find), text.replace(find, content)


def _edit_html(text: str, find: str, content: str) -> tuple[int, str, str]:
    """Count across every HTML spelling of find, in text nodes only.

    Returns (matches, new_text, form). One alternation pass, longest spelling
    first, because sequential str.replace calls could re-match a spelling
    inside a replacement already inserted.
    """
    forms = sorted(html_forms(find), key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(f) for f in forms))
    rep = html_replacement(content)
    segments = _text_segments(text)
    used: set[str] = set()
    total = 0
    for at in range(0, len(segments), 2):
        segment = segments[at]
        refs = [(m.start(), m.end()) for m in _CHAR_REF.finditer(segment)]
        hits: list[re.Match[str]] = []
        for m in pattern.finditer(segment):
            # A match may cover a whole character reference ('&amp;') but never
            # begin or end inside one ('amp' in '&amp;', '39' in '&#39;').
            if any(lo < m.start() < hi or lo < m.end() < hi for lo, hi in refs):
                continue
            hits.append(m)
        for m in reversed(hits):
            segment = segment[:m.start()] + rep + segment[m.end():]
        used |= {m.group(0) for m in hits}
        segments[at] = segment
        total += len(hits)
    form = "verbatim" if used <= {find} else "html-escaped"
    return total, "".join(segments), form


def _labels(leaves: list[TextLeaf]) -> list[str]:
    """'text/plain', 'text/html', and '#2', '#3'… for a second part of a type."""
    seen: dict[str, int] = {}
    out = []
    for leaf in leaves:
        seen[leaf.content_type] = seen.get(leaf.content_type, 0) + 1
        n = seen[leaf.content_type]
        out.append(leaf.content_type if n == 1 else f"{leaf.content_type} #{n}")
    return out


def plan_draft_edit(raw: bytes, find: str, content: str, expected: int = 1) -> DraftEditPlan:
    """Plan one find/replace across a draft's text parts. Writes nothing.

    The plan is ok only when EVERY editable body part holds exactly
    `expected` matches — per part, not summed per type, so a match in one
    HTML part cannot stand in for a miss in another. Otherwise it carries a
    refusal message and per-part counts, and new_raw is None.
    """
    leaves = text_leaves(raw)
    if not leaves:
        return DraftEditPlan(ok=False, message=(
            "This draft has no inline text/plain or text/html body part to edit."))
    message_crlf = b"\r\n" in raw[:raw.find(b"\n") + 1] if b"\n" in raw else False

    decoded: list[tuple[TextLeaf, str]] = []
    for leaf in leaves:
        try:
            decoded.append((leaf, decode_body(raw, leaf)))
        except (ValueError, LookupError, binascii.Error) as e:
            return DraftEditPlan(ok=False, message=(
                f"The draft's {leaf.content_type} part could not be decoded "
                f"({leaf.cte}, charset {leaf.charset}: {e}); nothing was written."))

    reports: list[PartReport] = []
    edited: list[tuple[TextLeaf, str]] = []
    for (leaf, text), label in zip(decoded, _labels(leaves)):
        if leaf.content_type == "text/html":
            n, new, form = _edit_html(text, find, content)
            seen = visible_text_count(text, find)
            note = None
            if n < expected and seen > n:
                note = (f"the phrase appears {seen}x in this part's visible text, but with markup "
                        "inside it (a line break, link, formatting or &nbsp;), so it cannot be "
                        "matched as written")
            reports.append(PartReport(label, n, form, note))
        else:
            n, new = _edit_plain(text, find, content, message_crlf)
            reports.append(PartReport(label, n))
        edited.append((leaf, new))

    if any(r.matches != expected for r in reports):
        lines = [f"{r.content_type}: {r.matches} match(es), expected {expected}"
                 + (f" — {r.note}" if r.note else "") for r in reports]
        advice: list[str] = []
        if all(r.matches == 0 for r in reports):
            advice.append("The phrase is not in the draft as written: check spelling, curly "
                          "quotes and dashes against a fresh fetch of the thread.")
        if any(r.matches > expected for r in reports):
            advice.append("Add surrounding words to find to make it unique, or pass count=N "
                          "when all N matches are meant (the quoted history counts too).")
        if any(r.note for r in reports):
            advice.append("Edit a shorter span that sits inside one line and one style, "
                          "in more than one call if need be.")
        if not advice:
            advice.append("The parts disagree, so editing one would leave the other stale.")
        return DraftEditPlan(ok=False, parts=reports, message=(
            "Draft NOT edited — every body part must match find exactly "
            f"{expected} time(s) and at least one did not:\n  " + "\n  ".join(lines)
            + "\n" + " ".join(advice)))

    new_raw = bytearray(raw)
    reencoded: list[str] = []
    # Splice from the end so earlier offsets stay valid.
    for leaf, new_text in sorted(edited, key=lambda e: e[0].body_start, reverse=True):
        original = raw[leaf.body_start:leaf.body_end]
        body, new_cte, new_charset = encode_body(new_text, leaf, original, message_crlf)
        new_raw[leaf.body_start:leaf.body_end] = body
        if new_cte or new_charset:
            head = bytes(new_raw[leaf.head_start:leaf.body_start])
            new_raw[leaf.head_start:leaf.body_start] = _rewrite_part_head(head, new_cte, new_charset)
            reencoded.append(f"{leaf.content_type} -> {new_cte or leaf.cte}, charset {new_charset or leaf.charset}")

    plain_new = next((t for l, t in edited if l.content_type == "text/plain"), None)
    previews = _preview(plain_new, content) if plain_new is not None and content else []
    return DraftEditPlan(ok=True, new_raw=bytes(new_raw), parts=reports,
                         previews=previews, reencoded=reencoded)

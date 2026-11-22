# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""dragram — co-edit server.

Serves the scenario .html files (+ grammar.css, drag.js) and accepts POST /save from
drag.js, rewriting the dragged element's inline left/top (and, after a resize, width/height;
after a snap, data-align-x/-y) back into the .html on disk — and POST /comment, which sets or
clears an element's data-comment (point-and-comment: a note for Claude, never rendered).
The file is the single shared artefact: Sameer drags in the browser, Claude reads the
coordinate deltas + screenshots the result.

Run:   uv run serve.py            # binds 0.0.0.0:8731 (reachable over Tailscale)
Open:  http://<host>:8731/example.html?edit
Render a deliverable (no ?edit so drag.js stays passive):
       chromium --headless --screenshot=out.png --window-size=1720,1080 \\
                --force-device-scale-factor=2 http://localhost:8731/example.html
"""
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import threading
import time
from html import escape
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path(__file__).resolve().parent
PORT = int(os.environ.get("DRAGRAM_PORT", 8731))  # override for tests / a second server

# Serialise read-modify-write: dragging a keyline fires one concurrent /save per member,
# and ThreadingHTTPServer runs them in parallel — without this lock the writes race and all
# but the last silently clobber each other (lost box moves). One lock for all files is fine;
# saves are sub-millisecond.
_save_lock = threading.Lock()


def version(data: bytes) -> str:
    """A diagram file's version: a hash of its bytes. The editor sends the version it last saw with
    every save; a mismatch means the file changed under the page (Claude resolving a comment,
    another tab, a hand edit), and the save is refused (409) rather than silently undoing that."""
    return hashlib.sha1(data).hexdigest()[:16]


def write_html(target: Path, text: str) -> bytes:
    """Encode FIRST, then atomically replace — so a text that can't be encoded (a lone surrogate)
    raises before the file is touched, and a reader never sees a half-written file. Returns the
    bytes written. (Path.write_text opens with 'w', truncating, and only then encodes: one bad
    character used to leave a 0-byte diagram behind a 400.)"""
    data = text.encode("utf-8")
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".dragram-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.chmod(tmp, target.stat().st_mode & 0o777)
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return data


_SURROGATE = re.compile(r"[\ud800-\udfff]")


def _check_text(value, what: str):
    """Refuse at the edge what could never be written honestly."""
    if isinstance(value, str) and _SURROGATE.search(value):
        raise ValueError(f"{what} contains an unpaired surrogate")


# The patchers never pattern-match a whole tag: text inside one attribute's value ("style='…'" in a
# title, "id='b'" in a note) once took a write meant for the real attribute (essayeur, 2026-09-28).
# A tag is read attribute by attribute instead, so a match can only ever be an attribute NAME.
_ATTR = r"""\s+[^\s=/>"']+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'>]+))?"""
TAG_RE = re.compile(r"<[a-zA-Z][\w:-]*(?:" + _ATTR + r")*\s*/?>", re.S)
ATTR_RE = re.compile(r"""\s+([^\s=/>"']+)(?:\s*=\s*("[^"]*"|'[^']*'|[^\s"'>]+))?""", re.S)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def _attrs(tag: str) -> dict:
    """name (lower-cased) -> (value_start, value_end, attr_start, attr_end) within tag; the value
    span excludes its quotes. The first occurrence of a name that HAS a value wins (a browser
    would honour a valueless first copy — a known gap, drag-dekudi)."""
    out, pos = {}, re.match(r"<[a-zA-Z][\w:-]*", tag).end()
    while (a := ATTR_RE.match(tag, pos)):
        pos = a.end()
        if a.group(2) is None:
            continue  # a bare boolean attribute
        v0, v1 = a.start(2), a.end(2)
        if a.group(2)[0] in "\"'":
            v0, v1 = v0 + 1, v1 - 1
        out.setdefault(a.group(1).lower(), (v0, v1, a.start(), a.end()))
    return out


def iter_tags(html: str):
    """(start, end, tag, attrs) for every opening tag outside <!-- comments --> — so a
    commented-out copy of a block is never read or written. shot.py --comments reads through
    this too, so the listing and the writer can't disagree."""
    comments = [(c.start(), c.end()) for c in COMMENT_RE.finditer(html)]
    for m in TAG_RE.finditer(html):
        if not any(a <= m.start() < b for a, b in comments):
            yield m.start(), m.end(), m.group(0), _attrs(m.group(0))


def _find_tag(html: str, node_id: str):
    """(start, end, tag, attrs) for the opening tag whose id attribute is node_id, or None."""
    for start, end, tag, at in iter_tags(html):
        if "id" in at and tag[at["id"][0]:at["id"][1]] == node_id:
            return start, end, tag, at
    return None


def _after_id(tag: str, attrs: dict, text: str) -> str:
    """Insert ` text` straight after the id attribute, so it reads beside the name it qualifies."""
    end = attrs["id"][3]
    return tag[:end] + " " + text + tag[end:]


def _drop_attr(tag: str, name: str) -> str:
    """The tag without attribute `name` (and the whitespace before it) — every copy, or a second
    copy would take effect once the first is gone."""
    while name in (at := _attrs(tag)):
        tag = tag[:at[name][2]] + tag[at[name][3]:]
    return tag


def _edit_style(html: str, node_id: str, fn):
    """Apply fn to the inline style of the element carrying id="node_id".

    Only the style attribute's value is handed to fn, never the rest of the tag, so text in
    another attribute (a title, a comment) that happens to read "left: 20px" is never the match.
    fn returns (new_style, ok). Returns (new_html, changed: bool).
    """
    found = _find_tag(html, node_id)
    if not found or "style" not in found[3]:
        return html, False
    start, end, tag, at = found
    v0, v1 = at["style"][:2]
    if v0 == 0 or tag[v0 - 1] not in "\"'":
        return html, False  # an unquoted style would end at the first space a write adds: refuse, loudly
    new_style, ok = fn(tag[v0:v1])
    if not ok:
        return html, False
    return html[:start] + tag[:v0] + new_style + tag[v1:] + html[end:], True


def patch_position(html: str, node_id: str, left: int, top: int):
    """Rewrite left:/top: inside the inline style of the element carrying id="node_id".

    Other elements, other attributes and the CSS file are untouched. Returns (new_html, changed).
    """
    def fn(style):
        # (?<![\w-]) so `padding-left:`/`margin-top:` earlier in the style are never the match
        style, n_l = re.subn(r"(?<![\w-])left:\s*-?[\d.]+px", f"left:{left}px", style, count=1)
        style, n_t = re.subn(r"(?<![\w-])top:\s*-?[\d.]+px", f"top:{top}px", style, count=1)
        return style, bool(n_l and n_t)
    return _edit_style(html, node_id, fn)


def patch_size(html: str, node_id: str, width=None, height=None):
    """Set width:/height: (px) in the inline style of the element carrying id="node_id".

    Replaces the property if the style has it (whatever its value was), appends it if not —
    an element whose width came from CSS gains an inline one when someone drags its edge.
    None leaves that property alone. Returns (new_html, changed: bool).
    """
    def set_prop(style, prop, px):
        # only a declaration that STARTS the style or follows a ';' — so `max-width:`,
        # `border-width:`, `line-height:`, a `#width:` inside a url() or a commented-out width are
        # never the match; an `!important` on the old value is kept
        decl = re.compile(r"(^|;)(\s*)" + prop + r"\s*:[^;!]*(!\s*important)?\s*(?=;|$)", re.I)
        new, n = decl.subn(lambda d: f"{d.group(1)}{d.group(2)}{prop}:{px}px" +
                           (f" {d.group(3)}" if d.group(3) else ""), style, count=1)
        if n:
            return new
        # append; a trailing ';' only ends a declaration if it isn't an entity's (…&quot;)
        body = style.rstrip()
        ends = body.endswith(";") and not re.search(r"&#?\w+;$", body)
        sep = "" if not body or ends else ";"
        return f"{body}{sep} {prop}:{px}px;".lstrip()

    def fn(style):
        if width is not None:
            style = set_prop(style, "width", width)
        if height is not None:
            style = set_prop(style, "height", height)
        return style, True
    return _edit_style(html, node_id, fn)


ALIGN_ATTRS = {"x": "data-align-x", "y": "data-align-y"}
ALIGN_RE = re.compile(r"\w+:[^\s\"'<>]+\.\w+")  # "center:analyst.center" — see drag.js; fullmatch


def patch_align(html: str, node_id: str, align: dict):
    """Set or clear data-align-x / data-align-y on the element carrying id="node_id".

    align maps axis -> relation string, or None to clear it (dropping on the grid detaches).
    A new attribute is written straight after the id so it reads beside the name it qualifies.
    Returns (new_html, changed: bool); changed is False only if the element wasn't found.
    """
    found = _find_tag(html, node_id)
    if not found:
        return html, False
    start, end, tag, _ = found
    for axis, attr in ALIGN_ATTRS.items():
        if axis not in align:
            continue
        rel = align[axis]
        tag = _drop_attr(tag, attr)
        if rel is not None:
            if not ALIGN_RE.fullmatch(rel):
                raise ValueError(f"bad {attr} value {rel!r}")
            tag = _after_id(tag, _attrs(tag), f'{attr}="{rel}"')
    return html[:start] + tag + html[end:], True


MEMBER_RE = re.compile(r"[\w-]+")  # one id in data-members; drag.js sends them space-separated


def patch_members(html: str, node_id: str, members: str):
    """Set data-members on the keyline carrying id="node_id" (regroup by drag, dragram-jitova).

    Refuses (ValueError) an empty list, a malformed id, or an id no element in the file carries, so
    a keyline can never be left wrapping nothing or a name that isn't there. Written straight after
    the id, as the editor reads it. Returns (new_html, changed: bool); False if the keyline is missing.
    """
    if not isinstance(members, str):
        raise ValueError(f"members must be a string, not {type(members).__name__}")
    ids = members.split()
    if not ids:
        raise ValueError("data-members would be empty")
    for m in ids:
        if not MEMBER_RE.fullmatch(m):
            raise ValueError(f"bad member id {m!r}")
        if m == node_id or not _find_tag(html, m):
            raise ValueError(f"member {m!r} is not another element in this file")
    found = _find_tag(html, node_id)
    if not found:
        return html, False
    start, end, tag, _ = found
    if "data-members" not in _attrs(tag):
        raise ValueError(f"{node_id!r} is not a keyline (no data-members)")
    tag = _drop_attr(tag, "data-members")
    tag = _after_id(tag, _attrs(tag), f'data-members="{" ".join(ids)}"')
    return html[:start] + tag + html[end:], True


COMMENT_MAX = 2000
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")  # C0 and C1 controls, bar tab and newline


def patch_comment(html: str, node_id: str, text):
    """Set (text) or clear (None / "") data-comment on the element carrying id="node_id".

    The text is HTML-escaped — quotes, <, >, & — and newlines become &#10;, so a comment can never
    end its tag, pass for another attribute, or split the tag across lines. Written straight after
    the id so the request reads beside the name it's about. Returns (new_html, changed: bool).
    """
    found = _find_tag(html, node_id)
    if not found:
        return html, False
    start, end, tag, _ = found
    tag = _drop_attr(tag, "data-comment")
    if text:
        val = escape(text, quote=True).replace("\r", "").replace("\n", "&#10;")
        tag = _after_id(tag, _attrs(tag), f'data-comment="{val}"')
    return html[:start] + tag + html[end:], True


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(BASE), **k)

    def end_headers(self):
        # The file on disk is the live artefact — drops, and Claude's edits, rewrite it. Without
        # this Chrome heuristically caches a just-modified file and a reload shows the stale copy.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_head(self):
        """A diagram is served with its version (X-Dragram-Version), the base the editor sends back
        with each save. Everything else is served as usual."""
        path = Path(self.translate_path(self.path))
        if path.suffix != ".html" or not path.is_file():
            return super().send_head()
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Dragram-Version", version(data))
        self.end_headers()
        return io.BytesIO(data)

    def log_message(self, fmt, *args):  # quieter; one line per save is enough
        if self.command == "POST":
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _log(self, line: str):
        """One timestamped line per change — the save log is where "when" lives."""
        sys.stderr.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {line}\n")

    def _ok(self, **extra):
        body = json.dumps({"ok": True, **extra}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _stale(self, current: str):
        """409: the page's base isn't the file on disk any more. Nothing is written."""
        body = json.dumps({"ok": False, "stale": True, "version": current}).encode()
        self.send_response(409)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path not in ("/save", "/comment"):
            self.send_error(404)
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n))
            rel = data["file"].lstrip("/")
            target = (BASE / rel).resolve()
            # confine writes to .html files inside BASE
            if not str(target).startswith(str(BASE) + "/") or target.suffix != ".html":
                self.send_error(403, "refused: outside kit / not .html")
                return
            for key in ("id", "text", "members"):
                _check_text(data.get(key), key)
            for rel_ in (data.get("align") or {}).values():
                _check_text(rel_, "align")
            if self.path == "/comment":
                self._comment(data, rel, target)
                return
            # a resize sends width and/or height (the inline style px, as drag.js set them)
            size = {}
            for prop in ("width", "height"):
                v = data.get(prop)
                if v is None:
                    continue
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not 1 <= v <= 20000:
                    raise ValueError(f"bad {prop} {v!r}")
                size[prop] = round(v)
            with _save_lock:
                raw = target.read_bytes()
                # the editor sends its base; a direct API call (curl, a script) may omit it
                if data.get("base") and data["base"] != version(raw):
                    return self._stale(version(raw))
                # a regroup sends only members: a keyline's left/top is derived from its members, so a
                # placeholder written as `left:0` (no px) must never block the membership write
                if "members" in data and "left" not in data:
                    new_html, changed = raw.decode("utf-8"), True
                else:
                    new_html, changed = patch_position(
                        raw.decode("utf-8"), data["id"], int(data["left"]), int(data["top"])
                    )
                if changed and size:
                    new_html, changed = patch_size(new_html, data["id"], size.get("width"), size.get("height"))
                if changed and "align" in data:
                    new_html, changed = patch_align(new_html, data["id"], data["align"])
                if changed and "members" in data:
                    new_html, changed = patch_members(new_html, data["id"], data["members"])
                if changed:
                    written = write_html(target, new_html)
            if not changed:
                self.send_error(422, f"could not patch id={data['id']!r}")
                return
            rels = "".join(f"  {a}={v or '-'}" for a, v in data.get("align", {}).items())
            dims = "".join(f" {p}:{v}px" for p, v in size.items())
            if "members" in data:
                dims += f"  members={data['members']!r}"
            where = f"left:{int(data['left'])}px top:{int(data['top'])}px" if "left" in data else "(position untouched)"
            self._log(f"saved {data['id']} -> {where}{dims}{rels}  in {rel}")
            self._ok(version=version(written))
        except Exception as exc:  # noqa: BLE001 — surface to the browser flash
            self.send_error(400, str(exc))

    def _comment(self, data, rel, target):
        """POST /comment {file, id, text, base?}: point-and-comment (drag-wemitu). Empty clears it.
        Answers with the text as stored, which the page then shows — so page and file agree."""
        text = data.get("text")
        if text is not None and not isinstance(text, str):
            raise ValueError("text must be a string")
        text = text or ""
        # control characters are refused wherever they are — checked BEFORE trimming, so one at
        # an end can't be quietly stripped; then only spaces, tabs and newlines are trimmed
        if _CONTROL.search(text):
            raise ValueError("comment contains control characters")
        text = text.strip(" \t\n")
        if len(text) > COMMENT_MAX:
            raise ValueError(f"comment over {COMMENT_MAX} characters")
        with _save_lock:
            raw = target.read_bytes()
            if data.get("base") and data["base"] != version(raw):
                return self._stale(version(raw))
            new_html, changed = patch_comment(raw.decode("utf-8"), data["id"], text or None)
            if changed:
                written = write_html(target, new_html)
        if not changed:
            self.send_error(422, f"no element id={data['id']!r} in {rel}")
            return
        # one line in the save log: a Claude watching it sees the request arrive
        self._log(f"comment {data['id']}: {text!r}  in {rel}" if text else f"comment cleared on {data['id']}  in {rel}")
        self._ok(version=version(written), text=text)


if __name__ == "__main__":
    print(f"DFD co-edit server on http://0.0.0.0:{PORT}  (serving {BASE})", flush=True)
    for f in sorted(BASE.glob("*.html")):  # list the diagrams here with ?edit links
        print(f"  edit:  http://localhost:{PORT}/{f.name}?edit", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

"""How big the sender showed each inline image, read from the HTML part (mise-tenega).

The trivial-attachment filter used to call any image under 200 KB a logo. Byte
size tracks compression, not what an image is: a pasted budget slide (1267x712,
183 KB) was hidden as a 'logo or signature image'. The HTML part says how the
sender showed it, <img src="cid:..." width="718" height="403">, at no extra
API cost, so the filter can judge by that.

Measured on 516 real threads (3 Nov 2026), 942 image parts: 708 of 883 under
200 KB had a size in the HTML. The short side separates content from
signature banners better than the long side does: banners are wide and short
(515x109, 420x89, 658x183), and slides, screenshots and pasted tables are not
(718x403, 511x239). It does not separate cleanly at the margin: a pasted agenda
screenshot shown at 542x190 sits beside a 658x183 award banner, so the hidden
list names each image's shown size and the reader decides.
"""

import re
from html.parser import HTMLParser
from urllib.parse import unquote

_PX = re.compile(r"\s*(\d{1,6})(?:\.\d+)?\s*(?:px)?\s*", re.IGNORECASE)  # bounded: int() refuses 4,300+ digits


def _px(value: str | None) -> int | None:
    """Pixels from '718', '718px' or '718.5px'; None for '100%', '7.48in' or nothing."""
    match = _PX.fullmatch(value or "")
    return int(match.group(1)) if match else None


def _style_px(style: str, name: str) -> int | None:
    for decl in style.split(";"):
        prop, _, value = decl.partition(":")
        if prop.strip().lower() == name:
            return _px(value)
    return None


class _ImgSizes(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sizes: dict[str, tuple[int, int]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "img":
            return
        a = {k.lower(): v or "" for k, v in attrs}
        src = a.get("src", "").strip()
        if not src.lower().startswith("cid:"):
            return
        style = a.get("style", "")
        # A browser lets inline CSS win over the width/height attributes.
        width = _style_px(style, "width") or _px(a.get("width"))
        height = _style_px(style, "height") or _px(a.get("height"))
        if width and height:
            self.sizes.setdefault(unquote(src[4:]).strip(), (width, height))


def display_sizes(html: str | None) -> dict[str, tuple[int, int]]:
    """Content-ID (without angle brackets) -> (width, height) as shown, for images that state both."""
    parser = _ImgSizes()
    parser.feed(html or "")
    parser.close()
    return parser.sizes

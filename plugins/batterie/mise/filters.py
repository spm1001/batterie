"""
Shared attachment filtering logic.

Loads filter rules from config/attachment_filters.json (single source of truth).
Hides trivial attachments like calendar invites, vcards, small images, and
generic filenames from Claude.
"""

import json
import logging
import re
from pathlib import Path
from functools import lru_cache
from typing import Any

_CONFIG_PATH = Path(__file__).parent / "config" / "attachment_filters.json"

# Mirrors config/attachment_filters.json, and a test pins the two equal.
# filters.py is force-included into the wheel; when the JSON is absent from
# the installed layout (the packaging slip that killed glaneur.service
# nightly from 2026-08-08, mise-ditoja), filtering degrades to these defaults
# instead of taking down the caller's whole search with FileNotFoundError.
# The file wins when present, so the JSON stays the single tunable — and only
# a MISSING file falls back; malformed JSON still raises, because that is a
# config error someone made, not a packaging slip.
_DEFAULT_FILTER_CONFIG: dict[str, Any] = {
    "version": 1,
    "description": (
        "Built-in fallback mirror of config/attachment_filters.json. "
        "Calendar invites, vcards, GIFs, logo-sized images (short side shown under "
        "image_min_short_edge_px, else under image_size_threshold_bytes) and generic "
        "filenames are hidden from the deposit; each hidden entry says why."
    ),
    "image_size_threshold_bytes": 204800,
    "image_min_short_edge_px": 200,
    "excluded_mime_types": [
        "text/calendar",
        "application/ics",
        "text/vcard",
        "text/x-vcard",
        "image/gif",
    ],
    "excluded_filename_patterns": [
        "^image$",
        "^image\\.(png|jpg|jpeg|gif|webp)$",
        "^image\\d+\\.(png|jpg|jpeg|gif)$",
        "^photo\\.(png|jpg|jpeg|gif|webp)$",
        "^attachment\\.(pdf|docx?|xlsx?)$",
        "^document\\.(pdf|docx?)$",
        "^file\\.(pdf|docx?|xlsx?)$",
        "^untitled",
        "^screenshot\\.(png|jpg)$",
    ],
}


@lru_cache(maxsize=1)
def get_filter_config() -> dict[str, Any]:
    """
    Load filter configuration from JSON file.

    Cached for performance - config doesn't change during runtime.
    Degrades to _DEFAULT_FILTER_CONFIG when the file is absent (a wheel
    install missing the data file), never on malformed content.
    """
    try:
        config: dict[str, Any] = json.loads(_CONFIG_PATH.read_text())
    except FileNotFoundError:
        logging.getLogger(__name__).warning(
            "attachment_filters.json not found at %s — using built-in "
            "default filter config",
            _CONFIG_PATH,
        )
        return dict(_DEFAULT_FILTER_CONFIG)
    return config


@lru_cache(maxsize=1)
def _get_compiled_patterns() -> list[re.Pattern[str]]:
    """
    Pre-compile regex patterns at load time for 3x speedup.

    Benchmarked: 0.267s → 0.089s for 400K matches.
    """
    config = get_filter_config()
    patterns: list[re.Pattern[str]] = []
    for pattern in config.get("excluded_filename_patterns", []):
        try:
            patterns.append(re.compile(pattern, re.IGNORECASE))
        except re.error:
            # Invalid regex pattern - skip it
            continue
    return patterns


def is_trivial_attachment(filename: str, mime_type: str, size: int,
                          display_size: tuple[int, int] | None = None) -> bool:
    """Whether an attachment is hidden from the deposit. trivial_reason says why."""
    return trivial_reason(filename, mime_type, size, display_size) is not None


def trivial_reason(filename: str, mime_type: str, size: int,
                   display_size: tuple[int, int] | None = None) -> str | None:
    """
    Why an attachment is hidden from the deposit, or None when it is kept.

    Hidden: calendar invites, vcards, GIFs, non-image generic filenames
    (attachment.pdf), and images that look like logos. An image the HTML part
    shows at a stated size is judged by its short side, the side that tells a
    signature banner (515x109) from a pasted slide (718x403); without one it
    falls back to bytes (mise-tenega, measured in extractors/inline_images.py).
    The reason is printed beside each hidden attachment, so a reader can tell
    'shown at 542x190 px' from a logo and fetch it.
    """
    config = get_filter_config()
    name = (filename or "").lower().strip()

    if not name:
        return "no filename"

    if mime_type in config.get("excluded_mime_types", []):
        return f"{mime_type} is hidden by type"

    # Generic names ("attachment.pdf"). NOT for images: Gmail names every
    # pasted image 'image.png', so the name rule hid ~200KB budget slides that
    # WERE the message's payload (mise-sajeso, 2026-08-20).
    is_image = bool(mime_type) and mime_type.startswith("image/")
    if not is_image and any(p.match(name) for p in _get_compiled_patterns()):
        return "generic filename"
    if not is_image:
        return None

    if display_size:
        edge = config.get("image_min_short_edge_px", 200)
        if min(display_size) < edge:
            return f"image shown at {display_size[0]}x{display_size[1]} px, under {edge} px on its short side"
        return None

    threshold = config.get("image_size_threshold_bytes", 204800)
    if size < threshold:
        return f"image under {threshold // 1024} KB with no shown size in the message"
    return None


def filter_attachments(attachments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Filter a list of attachments, removing trivial ones.

    Args:
        attachments: List of attachment dicts with 'filename', 'mime_type'/'mimeType', 'size'

    Returns:
        Filtered list with trivial attachments removed
    """
    filtered = []
    for att in attachments:
        filename = att.get("filename", "")
        # Support both snake_case and camelCase
        mime_type = att.get("mime_type") or att.get("mimeType", "")
        size = att.get("size", 0)

        if not is_trivial_attachment(filename, mime_type, size, att.get("display_size")):
            filtered.append(att)

    return filtered

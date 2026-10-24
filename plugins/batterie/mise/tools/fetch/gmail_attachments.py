"""
Gmail attachment handling — MIME resolution, classification, download, deposit.

Single source of the MIME→category dispatch knowledge shared by both
orchestrators (fetch_gmail's eager loop and fetch_attachment's explicit
fetch). Before this module, the same knowledge lived in three places in
gmail.py and drifted independently.
"""

from pathlib import Path
from typing import Any, Literal

from adapters.drive import download_file
from adapters.gmail import download_attachment
from adapters.pdf import convert_pdf_content
from extractors.gmail import format_message_date
from extractors.image import resize_image_bytes, SUPPORTED_IMAGE_MIME_TYPES
from models import EmailAttachment
from workspace import write_content, write_image

from .common import is_text_file

# MIME types for Office files that are too slow to extract eagerly (5-10s each)
OFFICE_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # pptx
    "application/msword",  # doc
    "application/vnd.ms-excel",  # xls
    "application/vnd.ms-powerpoint",  # ppt
}

# Filename-extension → real MIME for fallback when sender mislabels the
# attachment as application/octet-stream (Outlook/Exchange tags everything
# it doesn't have a specific type for that way, including plain-text CSVs).
# Without this fallback, fetch would reject CSVs/JSON/etc. from Outlook
# clients — see mise-mugure field report.
_EXTENSION_MIME_FALLBACK = {
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".txt": "text/plain",
    ".log": "text/plain",
    ".json": "application/json",
    ".xml": "application/xml",
    ".yaml": "application/x-yaml",
    ".yml": "application/x-yaml",
    ".md": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}

# NOTE: In conversations with >20 accumulated images the limit drops to 2000px.
# We can't know conversation context at deposit time — note dimension in metadata
# so Claude can judge risk in long conversations.
# SUPPORTED_IMAGE_MIME_TYPES imported from extractors.image (single source of truth)

# Maximum attachments to extract eagerly (prevent runaway extraction)
MAX_EAGER_ATTACHMENTS = 10

AttachmentCategory = Literal[
    "office", "pdf", "image", "image_unsupported", "text", "unknown"
]


def _resolve_attachment_mime(declared_mime: str, filename: str) -> str:
    """Resolve a declared MIME type, falling back to filename extension for
    Outlook/Exchange-style octet-stream attachments.

    Outlook tags many text formats (CSV, JSON, XML) as application/octet-stream
    rather than text/csv etc. Without this resolver, fetch_attachment falls
    through to "Cannot extract" on anything sent from such clients.

    Returns the resolved MIME if filename has a known extension; otherwise
    returns the declared MIME unchanged.
    """
    if declared_mime != "application/octet-stream":
        return declared_mime
    if "." not in filename:
        return declared_mime
    ext = "." + filename.rsplit(".", 1)[-1].lower()
    return _EXTENSION_MIME_FALLBACK.get(ext, declared_mime)


def classify_attachment(mime_type: str) -> AttachmentCategory:
    """
    Map a (resolved) MIME type to its handling category.

    The one place that knows which MIME types route where:
    - office: skipped eagerly (5-10s each), extractable via fetch_attachment
    - pdf / image: extracted eagerly and individually
    - image_unsupported: an image format the Claude API can't take (no eager
      extraction; fetch_attachment can still deposit it)
    - text: deposited as-is by fetch_attachment (no eager extraction)
    - unknown: not extractable
    """
    if mime_type in OFFICE_MIME_TYPES:
        return "office"
    if mime_type == "application/pdf":
        return "pdf"
    if mime_type in SUPPORTED_IMAGE_MIME_TYPES:
        return "image"
    if mime_type.startswith("image/"):
        return "image_unsupported"
    if is_text_file(mime_type):
        return "text"
    return "unknown"


def _is_extractable_attachment(mime_type: str) -> bool:
    """
    Check if attachment MIME type is eagerly extractable.

    Office files are skipped (too slow for eager extraction).
    PDFs and supported images are extracted.
    """
    return classify_attachment(mime_type) in ("pdf", "image")


def assign_attachment_refs(messages: list[Any]) -> None:
    """Give every attachment in a thread a unique ref, in thread order.

    Visible and hidden parts share one numbering (image.png, image-2.png, ...)
    so the name a deposit uses, the name the hidden list shows and the name
    attachment= accepts are one vocabulary. Every part gets its OWN ref.
    A part matching an earlier one by name and size (the same slide carried
    by each reply) also gets duplicate_of = that earlier ref, so it is not
    extracted twice (essayeur on mise-sajeso: the 'two slides' deposited were
    one slide twice). It is never folded out of reach: name and size is a
    guess at sameness, and two versions of one .docx can share a length
    (essayeur on mise-malodi). Gmail's part metadata carries no content hash,
    and bytes are not downloaded to decide this.
    """
    seen: dict[tuple[str, int], str] = {}
    used: set[str] = set()
    for msg in messages:
        for att in [*getattr(msg, "attachments", []), *getattr(msg, "hidden_attachments", [])]:
            key = (att.filename.lower(), att.size)
            att.duplicate_of = seen.get(key)
            stem, dot, ext = att.filename.rpartition(".")
            if not dot:
                stem, ext = att.filename, ""
            ref, n = att.filename, 1
            while ref.lower() in used:
                n += 1
                ref = f"{stem}-{n}.{ext}" if dot else f"{stem}-{n}"
            used.add(ref.lower())
            att.ref = ref
            seen.setdefault(key, ref)  # a third copy points at the first, not the second


def _unique_name(folder: Path, filename: str) -> str:
    """A name no earlier attachment in this deposit took. Gmail names every
    pasted image 'image.png', so two slides wrote one file and the first was
    silently overwritten (mise-sajeso, found on its own evidence thread)."""
    stem, dot, ext = filename.rpartition(".")
    if not dot:
        stem, ext = filename, ""
    candidate, n = filename, 1
    taken = lambda name: any((folder / f).exists() for f in (name, f"{name}.md"))  # noqa: E731
    while taken(candidate):
        n += 1
        candidate = f"{stem}-{n}.{ext}" if dot else f"{stem}-{n}"
    return candidate


def _deposit_attachment_content(
    content_bytes: bytes,
    filename: str,
    mime_type: str,
    file_id: str,
    folder: Path,
) -> dict[str, Any] | None:
    """
    Route attachment bytes by MIME category and deposit to folder.

    Shared by both Drive (pre-exfil) and Gmail download paths.
    Returns extraction result dict or None if type not handled.
    """
    filename = _unique_name(folder, filename)
    category = classify_attachment(mime_type)

    if category == "pdf":
        # No thumbnails here — this deposits into the shared thread folder.
        # Multiple PDF attachments would collide on page_01.png filenames.
        # The raw PDF is deposited alongside for Claude to view directly.
        # Single-attachment fetch (fetch_attachment) gets its own folder and does render thumbnails.
        pdf_result = convert_pdf_content(content_bytes, file_id=file_id)

        content_filename = f"{filename}.md"
        write_content(folder, pdf_result.content, filename=content_filename)
        write_image(folder, content_bytes, filename)

        return {
            "filename": filename,
            "mime_type": mime_type,
            "extracted": True,
            "extraction_method": pdf_result.method,
            "content_file": content_filename,
            "char_count": pdf_result.char_count,
        }

    if category == "image":
        # Open with PIL, resize if needed, deposit.
        # Oversized images (long edge > MAX_LONG_EDGE_PX) are scaled down rather
        # than skipped — the API downscales internally above 1568px anyway.
        # Only PIL failures (genuine MIME mismatch, e.g. DOCX renamed .png) cause
        # a skip — depositing non-image bytes as image/png causes a hard 400 that
        # poisons the session and cannot be fixed by resizing.
        try:
            resized = resize_image_bytes(content_bytes, mime_type)
        except ValueError as e:
            return {
                "filename": filename,
                "mime_type": mime_type,
                "skipped": True,
                "reason": str(e),
            }

        deposited_filename = filename
        if resized.jpeg_fallback:
            # PNG was still > 4.5MB after resize — converted to JPEG.
            deposited_filename = filename.rsplit(".", 1)[0] + ".jpg"

        write_image(folder, resized.content_bytes, deposited_filename)

        result: dict[str, Any] = {
            "filename": filename,
            "mime_type": resized.mime_type,
            "extracted": True,
            "deposited_as": deposited_filename,
            "dimensions": resized.dimensions,
        }
        if resized.original_dimensions:
            result["original_dimensions"] = resized.original_dimensions
            result["scaled_to"] = resized.dimensions
            result["scale_factor"] = resized.scale_factor
        if resized.jpeg_fallback:
            result["jpeg_fallback"] = True
        return result

    return None


def _extract_from_drive(
    file_id: str,
    filename: str,
    mime_type: str,
    folder: Path,
    warnings: list[str],
) -> dict[str, Any] | None:
    """
    Extract content from a pre-exfiltrated Drive file.

    Faster when the file is already in Drive (background exfiltration).
    """
    try:
        content_bytes = download_file(file_id)
        return _deposit_attachment_content(content_bytes, filename, mime_type, file_id, folder)
    except Exception as e:
        warnings.append(f"Drive exfil fallback failed for {filename}: {str(e)}")
        return None


def _extract_attachment_content(
    message_id: str,
    att: EmailAttachment,
    folder: Path,
    warnings: list[str],
    mime_type: str | None = None,
) -> dict[str, Any] | None:
    """
    Download and extract content from a single Gmail attachment.

    mime_type is the resolved MIME for dispatch (see _resolve_attachment_mime);
    defaults to the declared att.mime_type when not given.

    Returns extraction result dict or None on failure.
    """
    mime = mime_type or att.mime_type
    try:
        download = download_attachment(
            message_id=message_id,
            attachment_id=att.attachment_id,
            filename=att.filename,
            mime_type=mime,
        )

        # Prefer temp_path for large files (content is cleared to save memory)
        if download.temp_path:
            content_bytes = download.temp_path.read_bytes()
        else:
            content_bytes = download.content

        result = _deposit_attachment_content(
            content_bytes, att.ref or att.filename, mime, att.attachment_id, folder
        )

        # Clean up temp file if created
        if download.temp_path:
            download.temp_path.unlink(missing_ok=True)

        return result

    except Exception as e:
        warnings.append(f"Failed to extract {att.filename}: {str(e)}")
        return None


def _download_attachment_bytes(msg: Any, att: Any, mime_type: str) -> bytes:
    """Download attachment bytes from Gmail."""
    dl = download_attachment(
        message_id=msg.message_id,
        attachment_id=att.attachment_id,
        filename=att.filename,
        mime_type=mime_type,
    )
    # Prefer temp_path for large files (content is cleared to save memory)
    if dl.temp_path:
        data = dl.temp_path.read_bytes()
        dl.temp_path.unlink(missing_ok=True)
        return data
    return dl.content


def _with_duplicate(entry: dict[str, Any], att: Any) -> dict[str, Any]:
    """Mark a part that matches an earlier one by name and size: probably, not surely."""
    if getattr(att, "duplicate_of", None):
        entry["probable_duplicate_of"] = att.duplicate_of
    return entry


def attachment_info(att: Any) -> dict[str, Any]:
    """One entry of a thread fetch's metadata.attachments, with the ref to fetch it by."""
    return _with_duplicate({"filename": att.filename, "fetch_as": att.ref or att.filename,
                            "mime_type": att.mime_type, "size": att.size}, att)


def hidden_attachment_cues(thread_data: Any) -> dict[str, Any]:
    """Name what the trivial filter hid, so hidden never means unreachable.

    Small images and generic filenames are kept out of the deposit (usually
    signature logos), but a thread whose payload was pasted slides fetched as
    'no attachments' (mise-sajeso). Each hidden part is listed with the ref
    attachment= accepts. Parts matching an earlier one by name and size (the
    logo every reply carries) come after the distinct ones, marked
    probable_duplicate_of, so the cap trims repeats first and nothing is
    dropped unnamed (mise-malodi). The cap keeps a long thread's list small.
    """
    parts = [a for msg in thread_data.messages for a in getattr(msg, "hidden_attachments", [])]
    hidden = [
        _with_duplicate({"fetch_as": a.ref or a.filename, "mime_type": a.mime_type, "size": a.size}, a)
        for a in sorted(parts, key=lambda a: bool(getattr(a, "duplicate_of", None)))
    ]
    if not hidden:
        return {}
    cues: dict[str, Any] = {
        "hidden_attachments": hidden[:_HIDDEN_LIST_CAP],
        "hidden_attachments_note": (
            f"{len(hidden)} attachment(s) not deposited because they look like "
            "logos or signature images (small images, generic names). If one is "
            "content, fetch it by its fetch_as name: fetch(<thread>, attachment='<fetch_as>')."
        ),
    }
    if len(hidden) > _HIDDEN_LIST_CAP:
        cues["hidden_attachments_note"] += f" Showing the first {_HIDDEN_LIST_CAP}."
    return cues


_HIDDEN_LIST_CAP = 10


def skipped_office_entry(msg: Any, att: Any) -> dict[str, Any]:
    """One skipped Office attachment, named by the ref attachment= resolves.

    Two versions of one .docx on two messages share a filename, so listing
    the filename sent both suggested fetches to the first, older version
    (mise-malodi). fetch_as is the thread-unique ref from
    assign_attachment_refs, the same handle hidden_attachments prints; the
    carrying message's date (UTC, as in content.md) says which is newer.
    A same-name, same-size repeat is listed too, marked probable_duplicate_of.
    """
    entry: dict[str, Any] = {"fetch_as": att.ref or att.filename, "filename": att.filename}
    if getattr(msg, "date", None):
        entry["date"] = format_message_date(msg.date)
    entry["size"] = att.size
    return _with_duplicate(entry, att)


def skipped_office_hint(thread_id: str, entries: list[dict[str, Any]]) -> str:
    """The copy-paste fetch calls for skipped Office files, one per ref."""
    def note(e: dict[str, Any]) -> str:
        bits = [f"message of {e['date']}"] if e.get("date") else []
        if e.get("probable_duplicate_of"):
            bits.append(f"same name and size as '{e['probable_duplicate_of']}': "
                        "probably the same file, possibly another version")
        return f" [{'; '.join(bits)}]" if bits else ""

    calls = [f"fetch('{thread_id}', attachment='{e['fetch_as']}')" + note(e) for e in entries]
    return f"Office files take 5-10s each. To extract: {'; '.join(calls)}"

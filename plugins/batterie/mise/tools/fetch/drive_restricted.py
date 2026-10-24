"""
Download-restricted Drive files — refused before the download, with the route (mise-radija).

An owner can stop viewers and commenters downloading, printing and copying a
file; a Shared Drive setting or an admin policy can do the same from outside
the file. Drive reports the result in `capabilities.canDownload` (and the why
in `downloadRestrictions`), both asked for by FILE_METADATA_FIELDS, so knowing
costs nothing extra. Without this module the download went ahead and Google's
403 `cannotDownloadFile` reached the caller as "Client error '403 Forbidden'
for url ...", which reads as "no access" on a file the user can open in the
browser.

**Scope is exactly what Google refuses** — measured live 2026-10-24 on files
the probing account did not own, every one with canDownload=false:

- `alt=media` (the binary download) — 403 cannotDownloadFile on PDF,
  text/plain, PPTX and MP4.
- Drive export of native Docs/Sheets/Slides — 403 cannotExportFile (9 of 9).
- The editor APIs the native routes actually read through — documents.get,
  spreadsheets.get + values.batchGet, presentations.get + getThumbnail — 200
  on all 9, and fetch deposited the full doc, sheet and deck.

So only the four routes that download bytes are refused: PDF, Office, text and
image. A native file is NOT refused (that would refuse content Google serves),
and neither is video, whose route asks the GenAI summary API rather than
downloading. A shortcut itself always reports canDownload=false (it has no
content); the check runs on the routed file, so a shortcut is judged by its
target. Only an explicit False refuses: an absent capability is no claim, and
the download then gets Google's own answer.
"""

from typing import Any

from adapters.image import is_image_file
from adapters.office import get_office_type_from_mime
from models import ErrorKind, MiseError

from .common import is_text_file


def _downloads_bytes(mime_type: str) -> bool:
    """The routes in _route_drive that read via alt=media."""
    return (
        mime_type == "application/pdf"
        or get_office_type_from_mime(mime_type) is not None
        or is_text_file(mime_type)
        or is_image_file(mime_type)
    )


def _why_and_route(metadata: dict[str, Any]) -> tuple[str, str]:
    """Explain the restriction from Drive's own fields, and the move that can lift it."""
    restrictions = metadata.get("downloadRestrictions") or {}
    item = restrictions.get("itemDownloadRestriction") or {}
    effective = restrictions.get("effectiveDownloadRestrictionWithContext") or {}
    if effective.get("restrictedForWriters"):
        return (
            "download, print and copy are disabled, and even editors cannot download it.",
            "Ask the owner for a copy you own, or to lift the restriction; "
            "being made an editor would not help.",
        )
    if effective.get("restrictedForReaders") and not item.get("restrictedForReaders"):
        # Inherited, not set on the file. driveId says where from: a Shared
        # Drive file (which has no owner) answers to that drive's managers; a
        # My Drive file can only be under an admin policy.
        if metadata.get("driveId"):
            return (
                "download, print and copy are disabled for viewers and commenters "
                "by the Shared Drive it lives in (or an admin policy).",
                "Editors can still download it: ask the Shared Drive's managers "
                "for edit access, or for a copy.",
            )
        return (
            "download, print and copy are disabled for viewers and commenters "
            "by an admin policy, not a setting on the file.",
            "Editors may still download it: ask the owner for edit access or a "
            "copy; if even that fails, it's a Workspace policy only an "
            "administrator can change.",
        )
    if item.get("restrictedForReaders"):
        return (
            "its owner has disabled download, print and copy for viewers and commenters.",
            "Editors can still download it: ask the owner for edit access, or for a copy.",
        )
    return (
        "Drive reports that this account cannot download it (capabilities.canDownload is false).",
        "Ask the owner for a copy, or for edit access.",
    )


def restriction_message(file_id: str, metadata: dict[str, Any], needs: str) -> str | None:
    """The teaching text for a file this account cannot download, or None if it can.

    `needs` says why mise wanted the bytes ("reads this kind of file", "edits
    this kind of file"), so fetch and the plain-file edit path (mise-togeha)
    share one explanation. Only an explicit canDownload=False counts.
    """
    if (metadata.get("capabilities") or {}).get("canDownload") is not False:
        return None
    name = metadata.get("name", "untitled")
    why, route = _why_and_route(metadata)
    link = metadata.get("webViewLink")
    browser = f" It can still be read in the browser: {link}" if link else ""
    return (
        f"'{name}' ({file_id}) can be opened but not downloaded by this "
        f"account: {why} mise {needs} by downloading its "
        f"bytes, which Google refuses here (403 cannotDownloadFile), so "
        f"mise stopped before asking. {route}{browser}"
    )


def refuse_if_download_restricted(file_id: str, metadata: dict[str, Any]) -> None:
    """Raise a teaching PERMISSION_DENIED if this route would download a file Google won't release."""
    if not _downloads_bytes(metadata.get("mimeType", "")):
        return
    message = restriction_message(file_id, metadata, "reads this kind of file")
    if message is None:
        return
    raise MiseError(
        ErrorKind.PERMISSION_DENIED,
        message,
        details={"file_id": file_id, "reason": "cannotDownloadFile", "diagnosed": True},
        retryable=False,
    )

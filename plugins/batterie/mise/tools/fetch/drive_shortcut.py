"""
Drive shortcuts — followed to their target, always disclosed (mise-rosifa).

A shortcut (application/vnd.google-apps.shortcut) is a pointer with no
content of its own. Until this module, fetch refused it as an unsupported
type: 3 real failures in 14 days of the call log, each leaving the caller to
work out that the id was a pointer and go and find what it pointed at.

Drive already says where it points: files.get returns
`shortcutDetails.targetId` and `targetMimeType` when the fields mask asks
(FILE_METADATA_FIELDS does). So detection costs nothing extra — the one
extra call, paid only for a shortcut, is the TARGET's metadata, which the
routing needs anyway (title, provenance, email context).

Three rules:
- **Never silent.** The result carries `cues.shortcut` with both ids plus a
  warning, so a caller who asked for X and got Y's content is told so.
- **Never loops, never deadlocks.** The target is routed by `route`, which
  does not follow shortcuts; a shortcut whose target is (or turns out to be)
  another shortcut is refused with both ids, not chased — and refused BEFORE
  the target's deposit lock is taken, which is what keeps lock order safe.
- **Unreadable target → teaching error naming the target.** A 404 or 403 on
  the target is a fact about the target, not the shortcut the caller passed
  — so it must not reach the router's funnel, whose 404 advice is keyed on
  the id that was passed and would diagnose the (perfectly fine) shortcut.
  Other failures (rate limit, network) propagate with their own kind, and
  any failure PAST the hop (the target's content read, an unsupported target
  type) carries a sentence naming both ids. A non-Google exception past the
  hop (an extractor's ValueError, say) arrives as kind `unknown`, never as
  the caller's `invalid_input`.
"""

from typing import Any, Callable

from adapters.drive import GOOGLE_FOLDER_MIME, GOOGLE_SHORTCUT_MIME, get_file_metadata
from models import ErrorKind, FetchError, FetchResult, MiseError
from workspace.manager import deposit_lock

Route = Callable[[str, dict[str, Any]], FetchResult | FetchError]


def follow_shortcut(shortcut_id: str, metadata: dict[str, Any], route: Route) -> FetchResult | FetchError:
    """Fetch the shortcut's target via `route`, disclosing the hop."""
    name = metadata.get("name", "untitled")
    details = metadata.get("shortcutDetails") or {}
    target_id = details.get("targetId")
    if not target_id:
        return FetchError(
            kind="unknown",
            message=(
                f"'{name}' ({shortcut_id}) is a Drive shortcut, but Drive sent no "
                f"shortcutDetails.targetId, so mise cannot tell what it points at. "
                f"Open it in Drive (right-click > Show file location) and fetch the "
                f"target's own id."
            ),
            file_id=shortcut_id,
            name=name,
        )

    def _chain_refusal() -> FetchError:
        return FetchError(
            kind="unsupported_type",
            message=(
                f"'{name}' ({shortcut_id}) is a shortcut to another shortcut "
                f"({target_id}). mise follows one hop only, so it cannot loop: "
                f"fetch '{target_id}' to see where that one points, or open it in "
                f"Drive and fetch the final file by its own id."
            ),
            file_id=shortcut_id,
            name=name,
        )

    if details.get("targetMimeType") == GOOGLE_SHORTCUT_MIME:
        return _chain_refusal()

    try:
        target_meta = get_file_metadata(target_id)
    except MiseError as e:
        if e.kind is ErrorKind.NOT_FOUND:
            return FetchError(
                kind=e.kind.value,
                message=(
                    f"'{name}' ({shortcut_id}) is a Drive shortcut, but its target "
                    f"'{target_id}' cannot be found: it was deleted, or it sits "
                    f"somewhere this account has never been able to see. Ask the "
                    f"owner whether the original still exists; the shortcut itself "
                    f"is fine and holds no content. (Google said: {e.message})"
                ),
                file_id=shortcut_id,
                name=name,
            )
        if e.kind is ErrorKind.PERMISSION_DENIED:
            return FetchError(
                kind=e.kind.value,
                message=(
                    f"'{name}' ({shortcut_id}) is a Drive shortcut, but this account "
                    f"cannot read its target '{target_id}'. A shortcut grants no "
                    f"access of its own: request access to '{target_id}' from its "
                    f"owner, then fetch again. (Google said: {e.message})"
                ),
                file_id=shortcut_id,
                name=name,
            )
        raise

    target_mime = target_meta.get("mimeType", "")
    # THIS CHECK IS WHAT KEEPS LOCK ORDER SAFE — not just loop prevention.
    # The router already holds the passed id's lock and we are about to take
    # the target's. If the target could itself be a shortcut, two shortcuts
    # pointing at each other, fetched at once, would take the two locks in
    # opposite orders and deadlock (targetMimeType can be stale, so the
    # pre-read check above is not enough). Refusing here, before
    # deposit_lock(target_id), means the inner lock is only ever a
    # non-shortcut's, which never takes a further lock.
    # tests/unit/test_drive_shortcut.py::TestLockOrder forces the interleave.
    if target_mime == GOOGLE_SHORTCUT_MIME:
        return _chain_refusal()

    # The router locked on the id it was given (the shortcut); the deposit is
    # keyed on the target. Take the target's lock too, so a concurrent direct
    # fetch of the target converges here (same pattern as the gmail
    # message→thread rescue's inner take).
    target_name = target_meta.get("name", "untitled")
    hop = (
        f"('{shortcut_id}' is a Drive shortcut, '{name}'; mise followed it to "
        f"'{target_id}', '{target_name}', and this is about that target.)"
    )
    with deposit_lock(target_id):
        try:
            result = route(target_id, target_meta)
        except MiseError as e:
            # A failure past the hop is about the TARGET; say so, and mark it
            # diagnosed so the router's 404 advice (keyed on the passed
            # shortcut id) is not appended. Live case 2026-10-24: a call-log
            # shortcut led to a download-restricted PDF, and the 403 named an
            # id the caller never passed.
            raise MiseError(
                e.kind, f"{e.message} {hop}",
                details={**e.details, "diagnosed": True}, retryable=e.retryable,
            ) from e
        except Exception as e:
            # Anything else past the hop is a processing failure on the
            # target (an extractor's ValueError/KeyError/RuntimeError). Left
            # bare it would lose the hop sentence, and the router would map a
            # ValueError to invalid_input, blaming the caller's id. Re-raise
            # as UNKNOWN, the router's own kind for an unanticipated
            # exception, keeping the type name and the chained traceback.
            raise MiseError(
                ErrorKind.UNKNOWN, f"{type(e).__name__}: {e} {hop}",
                details={"diagnosed": True},
            ) from e

    if isinstance(result, FetchError):
        result.message = f"{result.message} {hop}"
    elif isinstance(result, FetchResult):
        result.cues["shortcut"] = {
            "shortcut_id": shortcut_id,
            "shortcut_name": name,
            "target_id": target_id,
            "target_name": target_name,
            "target_mime_type": target_mime,
        }
        kind = "folder, so this is its listing" if target_mime == GOOGLE_FOLDER_MIME else "file"
        result.cues.setdefault("warnings", []).append(
            f"'{shortcut_id}' is a Drive shortcut ('{name}'). mise followed it to "
            f"its target '{target_id}' ('{target_name}', a {kind}) and deposited "
            f"the target's content. Use '{target_id}' to refer to the original."
        )
    return result

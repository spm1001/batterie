"""
Sheets row/column delete — do(trash, range='Tab!34:36' | 'Tab!C:E').

Split from tools/sheet_structure.py, which holds the grammar (A1 refs, tab
resolution) this module reuses.

The confirm gate here is stricter than share's, because share names a file
by id and this names POSITIONS, which move: a colleague inserting, deleting
or sorting rows between the preview and the yes would aim a delete at other
people's rows. So, beyond the share-style gate (preview, dialog or
confirm=True):

- Every preview this process shows (the confirm= preview, and the dialog's
  question, recorded by the confirm resolver on its first round) records a
  fingerprint of the whole target: every value in it, plus the tab's size.
- A delete runs only if the target read NOW matches the fingerprint of the
  preview the human saw. That covers both routes: a dialog yes (whose
  message shows only two clipped rows, so a message comparison alone missed
  a mid-block insert) and confirm=True (which had no re-check at all).
- confirm=True with no preview of that target in this process returns the
  preview instead of deleting, and a delete clears its record. So a retried
  confirm=True after a timeout returns a preview of the rows that moved up
  into the gap, rather than deleting them too.

Like the draft guard, the record is per server process: a restart between
preview and yes costs one extra preview, never a wrong delete. Cold review
2026-11-16 (W1, W2) motivated it.
"""

import hashlib
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable

import orjson
from mcp.server.elicitation import ElicitationResult

from adapters.sheets_structure import delete_dimension, get_range_values, get_tab_grids
from cues_util import with_identity
from models import DoResult, MiseError
from tools.elicit import (
    ConfirmAnswer,
    GateQuestion,
    dialog_lines,
    settle_gate,
    stale_preview,
)
from tools.sheet_edit import _quote_tab
from tools.sheet_structure import (
    _REF_TEACHING,
    DimRef,
    _err,
    _extent,
    _shift_cue,
    col_letters,
    label,
    resolve_target,
)

_PREVIEW_ROWS = 20  # values returned with a delete preview
_DIALOG_COLS = 74
_SEEN_MAX = 64

# (spreadsheet id, sheetId, dim, start, end) -> fingerprint of the last preview shown
_SEEN: "OrderedDict[tuple[Any, ...], str]" = OrderedDict()
_SEEN_LOCK = threading.Lock()




@dataclass(frozen=True)
class _DeletePlan:
    file_id: str
    spreadsheet: str
    tab: dict[str, Any]
    ref: DimRef
    existing: int
    values: list[list[Any]]


def _key(plan: _DeletePlan) -> tuple[Any, ...]:
    ref = plan.ref
    return (plan.file_id, plan.tab.get("sheetId", 0), ref.dim, ref.start, ref.end)


def _fingerprint(plan: _DeletePlan) -> str:
    """Every value in the target plus the tab's size: what a yes covers."""
    raw = orjson.dumps([plan.existing, [[str(c) for c in row] for row in plan.values]])
    return hashlib.sha256(raw).hexdigest()


def _record(plan: _DeletePlan) -> None:
    with _SEEN_LOCK:
        _SEEN[_key(plan)] = _fingerprint(plan)
        _SEEN.move_to_end(_key(plan))
        while len(_SEEN) > _SEEN_MAX:
            _SEEN.popitem(last=False)


def _seen(plan: _DeletePlan) -> str | None:
    with _SEEN_LOCK:
        return _SEEN.get(_key(plan))


def _forget(plan: _DeletePlan) -> None:
    with _SEEN_LOCK:
        _SEEN.pop(_key(plan), None)


def _clip(text: str) -> str:
    return text if len(text) <= _DIALOG_COLS else text[: _DIALOG_COLS - 1] + "…"


def _plan_delete(file_id: str, range_: str) -> _DeletePlan | dict[str, Any]:
    """Read what a delete would remove. Raises MiseError on a Google failure."""
    spreadsheet, tabs = get_tab_grids(file_id)
    resolved = resolve_target(tabs, range_, "trash")
    if isinstance(resolved, dict):
        return resolved
    tab, ref = resolved
    title = tab.get("title", "")
    if ref.col is not None:
        return _err(f"range='{range_}' names a cell on tab '{title}'; trash deletes whole "
                    f"rows or columns. {_REF_TEACHING} To clear cells, overwrite them.")
    existing = _extent(tab, ref.dim)
    noun = "rows" if ref.dim == "ROWS" else "columns"
    if ref.end > existing:
        return _err(f"Tab '{title}' has {existing} {noun}; "
                    f"{label(ref.dim, ref.start, ref.end)} runs past its end.")
    if ref.start == 0 and ref.end >= existing:
        return _err(f"That is every one of tab '{title}''s {existing} {noun} — a tab keeps at "
                    "least one. To empty it, overwrite it with range= and blank CSV.")
    a1 = (f"{ref.start + 1}:{ref.end}" if ref.dim == "ROWS"
          else f"{col_letters(ref.start)}:{col_letters(ref.end - 1)}")
    values = get_range_values(file_id, f"{_quote_tab(title)}!{a1}")
    return _DeletePlan(file_id, spreadsheet, tab, ref, existing, values)


def _delete_message(plan: _DeletePlan) -> str:
    """The preview's words, which are also the dialog's (≤4 lines of 74 columns
    for typical titles; a longer one takes the confirm= round-trip)."""
    ref, title = plan.ref, plan.tab.get("title", "")
    lines = [f"Delete {label(ref.dim, ref.start, ref.end)} of '{title}' in '{plan.spreadsheet}'?"]
    if ref.dim == "ROWS":
        shown = 0
        for i in range(min(ref.size, 2)):
            row = plan.values[i] if i < len(plan.values) else []
            cells = " | ".join(str(c) for c in row if str(c).strip()) or "(empty)"
            lines.append(_clip(f"{ref.start + i + 1}: {cells}"))
            shown += 1
        more = ref.size - shown
        tail = f"(+{more} more) " if more else ""
        lines.append(f"{tail}Rows below move up by {ref.size}.")
    else:
        heads = plan.values[0] if plan.values else []
        cols = [f"{col_letters(ref.start + i)}: "
                f"{heads[i] if i < len(heads) and str(heads[i]).strip() else '(blank)'}"
                for i in range(ref.size)]
        lines.append(_clip("Row 1 — " + " | ".join(cols)))
        lines.append(f"Columns to the right move left by {ref.size}.")
    return dialog_lines(lines)


def _web_link(plan: _DeletePlan) -> str:
    return (f"https://docs.google.com/spreadsheets/d/{plan.file_id}/edit"
            f"#gid={plan.tab.get('sheetId', 0)}")


def _delete_preview(plan: _DeletePlan) -> dict[str, Any]:
    ref, title = plan.ref, plan.tab.get("title", "")
    cues: dict[str, Any] = {"confirm_required": (
        "This is a preview. To delete, call again with confirm=True. Show this to "
        "the user and get their approval first — the rows are other people's on a "
        "shared sheet, and only Version history brings them back.")}
    if len(plan.values) > _PREVIEW_ROWS:
        cues["values_truncated"] = f"first {_PREVIEW_ROWS} of {len(plan.values)} rows shown"
    return {
        "preview": True, "operation": "trash", "file_id": plan.file_id,
        "title": plan.spreadsheet, "web_link": _web_link(plan),
        "message": _delete_message(plan), "tab": title,
        "deleting": label(ref.dim, ref.start, ref.end),
        "values": plan.values[:_PREVIEW_ROWS],
        "cues": with_identity(cues),
    }


def sheet_delete_confirm_message(file_id: Any, range_: Any, record: bool = True) -> str | None:
    """The dialog text for an unconfirmed row/column delete, or None (no dialog:
    the body reports the refusal). A Google error raises for the resolver.

    record: note the fingerprint of what the dialog will show. The resolver
    passes False on a retry round (>= 2026-07-28 re-runs it AFTER the human
    answered), so a re-read then cannot overwrite what the human actually saw."""
    if not isinstance(file_id, str) or not isinstance(range_, str):
        return None
    plan = _plan_delete(file_id, range_)
    if isinstance(plan, dict):
        return None
    if record:
        _record(plan)
    return _delete_message(plan)


_NO_PREVIEW = (
    "confirm=True found no preview of these rows from this session, so nothing was "
    "deleted: rows move when colleagues edit, and a yes covers only what the user saw. "
    "This is the preview — show it to the user and call again with confirm=True on their yes."
)
_CHANGED = (
    "The rows changed since the preview was shown (an edit, a sort, or rows inserted or "
    "deleted around them), so nothing was deleted. This is the current state — show it "
    "to the user and call again with confirm=True on their yes."
)


def sheet_delete(
    file_id: str, range_: str, confirm: bool,
    answer: ElicitationResult[ConfirmAnswer] | None = None,
    question: GateQuestion | None = None,
) -> DoResult | dict[str, Any]:
    """Delete whole rows/columns: preview unless confirmed or a dialog said yes."""
    try:
        plan = _plan_delete(file_id, range_)
        if isinstance(plan, dict):
            return plan
        gate_cue = None
        seen = _seen(plan)
        if confirm:
            if seen != _fingerprint(plan):
                _record(plan)
                cue = _NO_PREVIEW if seen is None else _CHANGED
                preview = _delete_preview(plan)
                return {**preview, "cues": {**preview["cues"], "confirm_gate": cue}}
        else:
            current: Callable[[], dict[str, Any]] = lambda: _delete_preview(plan)  # noqa: E731
            stop, gate_cue = settle_gate(answer, question, True, current,
                                         "Nothing was deleted", "deleted")
            if stop is None and seen != _fingerprint(plan):  # a yes to rows that have moved
                stop, gate_cue = stale_preview(current(), "the client answered proceed=true",
                                               "Nothing was deleted"), None
            if stop is not None:
                _record(plan)  # the preview returned is what the user will see next
                return stop
        ref, title = plan.ref, plan.tab.get("title", "")
        delete_dimension(file_id, int(plan.tab.get("sheetId", 0)), ref.dim, ref.start, ref.end)
        _forget(plan)  # a repeat of this call previews the rows that moved up; it never deletes them
    except MiseError as e:
        return {"error": True, "kind": e.kind.value, "message": e.message}

    cues: dict[str, Any] = {
        "tab": title,
        "deleted": label(ref.dim, ref.start, ref.end),
        "shifted": _shift_cue(ref.dim, ref.end, plan.existing, ref.size, down=False),
        "deleted_values": plan.values[:_PREVIEW_ROWS],
        "recover": "Rows and columns have no trash: File → Version history in "
                   "Sheets restores them.",
    }
    if gate_cue:
        cues["confirm_gate"] = gate_cue
    return DoResult(file_id=file_id, title=plan.spreadsheet, web_link=_web_link(plan),
                    operation="trash", cues=cues)

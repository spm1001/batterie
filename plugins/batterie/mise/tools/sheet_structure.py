"""
Sheets structure — insert and delete whole rows or columns (mise-en-space, Nov 2026).

Born of a real miss: a session had to add one event to a shared team sheet
whose rows sit in date order above a footer line. overwrite range= can write
cells but not make room, so the only routes were rewriting five colleagues'
rows one down (their formatting stays put; the last one inherits the
footer's) or asking the human to right-click Insert row.

Grammar — no new op names (do()'s description budget, CLAUDE.md "Three verbs
is a budget"):

- do(append, range='Tab!33', content=CSV) inserts rows AFTER row 33 and
  writes the CSV into them; do(prepend, range='Tab!34', …) inserts BEFORE
  row 34. A column letter ('Tab!C') does columns. A cell ('Tab!B33') names
  row 33 and starts the CSV in column B. count=N inserts N blank ones (or
  pads a CSV with blanks).
- The new rows take the formatting of the row the caller NAMED: after →
  inheritFromBefore, before → from the row below. That is the formatting
  option, carried by the verb rather than a flag: name a data row, not the
  header or the footer, and the cue says which row it copied.
- do(trash, range='Tab!34:36' | 'Tab!C:E') deletes, behind the confirm gate:
  tools/sheet_delete.py.

Every result says exactly what moved ("rows 34–1000 moved down by 3"), and
every refusal names the tab it was looking at, or all tabs when it could not
tell which was meant.

Insert-then-write is two calls (insertDimension, then values.update for
USER_ENTERED parsing — batchUpdate has no parsed-value write but pasteData,
whose CSV quoting is not the csv module's). If the write fails, the error
says the empty rows are there and how to fill or remove them.
"""

import re
from dataclasses import dataclass
from typing import Any, Literal

from adapters.sheets import add_sheet
from adapters.sheets_structure import (
    get_tab_grids,
    insert_dimension,
)
from adapters.drive import GOOGLE_SHEET_MIME
from models import DoResult, MiseError
from tools.suggestions import _no_suggest_here
from validation import validate_drive_id
from tools.sheet_edit import (
    _quote_tab,
    _split_range,
    find_tab,
    parse_csv_grid,
    sheet_result,
    write_grid,
)

_ROWS_RE = re.compile(r"^(\d+)(?::(\d+))?$")
_CELL_RE = re.compile(r"^([A-Za-z]{1,3})(\d+)$")
_COLS_RE = re.compile(r"^([A-Za-z]{1,3})(?::([A-Za-z]{1,3}))?$")


def _err(message: str) -> dict[str, Any]:
    return {"error": True, "kind": "invalid_input", "message": message}


def col_index(letters: str) -> int:
    """Zero-based column index of 'A', 'Z', 'AA'…"""
    n = 0
    for ch in letters.upper():
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def col_letters(index: int) -> str:
    """Column letters of a zero-based index."""
    out = ""
    n = index + 1
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(ord("A") + rem) + out
    return out


@dataclass(frozen=True)
class DimRef:
    """A whole-row or whole-column reference: [start, end) zero-based."""

    dim: Literal["ROWS", "COLUMNS"]
    start: int
    end: int
    col: int | None = None  # a cell anchor's column (rows only): where a CSV starts

    @property
    def size(self) -> int:
        return self.end - self.start


def parse_dimension_ref(ref: str) -> DimRef | None:
    """'33', '33:35', 'B33', 'C', 'C:E' → DimRef; anything else → None."""
    ref = ref.strip().replace("$", "")
    m = _ROWS_RE.match(ref)
    if m:
        a, b = int(m.group(1)), int(m.group(2) or m.group(1))
        if min(a, b) < 1:
            return None
        return DimRef("ROWS", min(a, b) - 1, max(a, b))
    m = _CELL_RE.match(ref)
    if m:
        row = int(m.group(2))
        return DimRef("ROWS", row - 1, row, col_index(m.group(1))) if row >= 1 else None
    m = _COLS_RE.match(ref)
    if m:
        a, b = col_index(m.group(1)), col_index(m.group(2) or m.group(1))
        return DimRef("COLUMNS", min(a, b), max(a, b) + 1)
    return None


def label(dim: str, start: int, end: int) -> str:
    """'row 34', 'rows 34–36', 'column C', 'columns C–E' (from zero-based [start, end))."""
    if dim == "ROWS":
        return f"row {start + 1}" if end - start == 1 else f"rows {start + 1}–{end}"
    if end - start == 1:
        return f"column {col_letters(start)}"
    return f"columns {col_letters(start)}–{col_letters(end - 1)}"


def _extent(tab: dict[str, Any], dim: str) -> int:
    grid = tab.get("gridProperties", {})
    return int(grid.get("rowCount" if dim == "ROWS" else "columnCount", 0))


def _tabs_list(tabs: list[dict[str, Any]]) -> str:
    return ", ".join(f"'{t.get('title', '')}'" for t in tabs)


_REF_TEACHING = ("Name whole rows ('Tab!34' or 'Tab!34:36') or columns "
                 "('Tab!C' or 'Tab!C:E').")


def resolve_target(
    tabs: list[dict[str, Any]], range_: str, op: str,
) -> tuple[dict[str, Any], DimRef] | dict[str, Any]:
    """(tab, ref) for a structural range=, or the refusal — which names the
    tab it looked at, or every tab when it could not tell which was meant."""
    if not tabs:
        return _err(f"{op}: this spreadsheet has no grid tabs.")
    tab_name, cell_part = _split_range(range_)
    if cell_part is None and range_.strip().startswith("'"):  # a quoted name is a tab, never a ref
        if find_tab(tabs, tab_name) is None:
            return _err(f"No tab named '{tab_name}' in this spreadsheet. Tabs: {_tabs_list(tabs)}.")
    if cell_part is None:  # no '!': a bare ref on a one-tab sheet, or a tab name alone
        named = find_tab(tabs, tab_name)
        if named is not None:
            title = named.get("title", "")
            return _err(f"range='{range_}' names the tab '{title}' but no rows or "
                        f"columns. {op} needs a position: range=\"{_quote_tab(title)}!33\" "
                        f"(row 33) or range=\"{_quote_tab(title)}!C\" (column C).")
        if len(tabs) > 1:
            return _err(f"This spreadsheet has {len(tabs)} tabs ({_tabs_list(tabs)}) — "
                        f"say which: range=\"{_quote_tab(tabs[0].get('title', ''))}!"
                        f"{range_}\".")
        target, cell_part = tabs[0], tab_name
    else:
        found = find_tab(tabs, tab_name)
        if found is None:
            return _err(f"No tab named '{tab_name}' in this spreadsheet. "
                        f"Tabs: {_tabs_list(tabs)}.")
        target = found
    ref = parse_dimension_ref(cell_part)
    if ref is None:
        return _err(f"range='{range_}' on tab '{target.get('title', '')}' is not a "
                    f"whole row or column. {_REF_TEACHING}")
    return target, ref


def _shift_cue(dim: str, start: int, existing: int, by: int, down: bool) -> str:
    """What moved: everything from zero-based `start` to the tab's end."""
    if start >= existing:
        return "nothing moved — no rows below" if dim == "ROWS" else \
            "nothing moved — no columns to the right"
    moved = label(dim, start, existing)
    now = label(dim, start + by, existing + by) if down else label(dim, start - by, existing - by)
    way = ("down" if down else "up") if dim == "ROWS" else ("right" if down else "left")
    return f"{moved} moved {way} by {by} (now {now.split(' ', 1)[1]})"


def sheet_insert(
    file_id: str, content: str | None, metadata: dict[str, Any] | None,
    range_: str | None, count: int | None, op: Literal["append", "prepend"],
) -> DoResult | dict[str, Any]:
    """Insert rows/columns after (append) or before (prepend) a named one."""
    where = "after" if op == "append" else "before"
    if range_ is None:
        return _err(
            f"{op} on a Spreadsheet inserts rows or columns where range= says: "
            f"range='Tab!33' puts new rows {where} row 33 (formatted like it) and "
            "writes content= (CSV) into them; range='Tab!C' does columns; count=N "
            "inserts N blank ones. To write existing cells, use overwrite with range=; "
            "to swap words in cells, replace_text.")
    grid: tuple[list[list[str]], Any] | None = None
    if content:
        parsed = parse_csv_grid(content, op)
        if isinstance(parsed, dict):
            return parsed
        rows, decorations = parsed
        while rows and not any(rows[-1]):  # a trailing newline is not a blank row to insert
            rows.pop()
        grid = (rows, decorations)
    elif count is None:
        return _err(f"{op} on a Spreadsheet needs content= (CSV for the new rows) "
                    "or count=N for N blank ones.")
    if count is not None and (not isinstance(count, int) or count < 1):
        return _err(f"count= must be a whole number of rows or columns, 1 or more (got {count!r}).")

    try:
        _, tabs = get_tab_grids(file_id)
    except MiseError as e:
        return {"error": True, "kind": e.kind.value, "message": e.message}
    resolved = resolve_target(tabs, range_, op)
    if isinstance(resolved, dict):
        return resolved
    tab, ref = resolved
    title = tab.get("title", "")
    if ref.size != 1:
        noun = "row" if ref.dim == "ROWS" else "column"
        return _err(f"{op} inserts {where} ONE named {noun}; '{range_}' on tab '{title}' "
                    f"names {ref.size}. Name one, and use count=N for N new {noun}s.")
    if grid is None:
        extent_needed = 0
    elif ref.dim == "COLUMNS":
        extent_needed = max(len(r) for r in grid[0])
    else:
        extent_needed = len(grid[0])
    n = count if count is not None else extent_needed
    if n < extent_needed:
        noun = "rows" if ref.dim == "ROWS" else "columns"
        return _err(f"count={count} is fewer than the CSV's {extent_needed} {noun}; "
                    "drop count= to insert exactly the CSV, or raise it to pad with blanks.")
    existing = _extent(tab, ref.dim)
    if ref.start >= existing:
        return _err(f"Tab '{title}' has {existing} {'rows' if ref.dim == 'ROWS' else 'columns'}; "
                    f"{label(ref.dim, ref.start, ref.end)} is past its end.")

    start = ref.start + 1 if op == "append" else ref.start
    try:
        insert_dimension(file_id, int(tab.get("sheetId", 0)), ref.dim, start, start + n,
                         inherit_from_before=(op == "append"))
    except MiseError as e:
        return {"error": True, "kind": e.kind.value, "message": e.message}

    named = label(ref.dim, ref.start, ref.end)
    cues: dict[str, Any] = {
        "tab": title,
        "inserted": f"{n} {'row' if ref.dim == 'ROWS' else 'column'}{'s' if n > 1 else ''} "
                    f"{where} {named} — new {label(ref.dim, start, start + n)}",
        "formatted_like": named if op == "append"
                          else f"{named} (now {label(ref.dim, ref.start + n, ref.end + n)})",
        "shifted": _shift_cue(ref.dim, start, existing, n, down=True),
    }
    if grid is not None:
        plain_rows, decorations = grid
        cell_part = (f"{col_letters(ref.col or 0)}{start + 1}" if ref.dim == "ROWS"
                     else f"{col_letters(start)}1")
        try:
            write_grid(file_id, tab, cell_part, plain_rows, decorations, cues)
        except MiseError as e:
            new = label(ref.dim, start, start + n)
            span = new.split(" ", 1)[1].replace("–", ":")
            return {"error": True, "kind": e.kind.value, "message": (
                f"Inserted {new} on tab '{title}', but writing the values failed: "
                f"{e.message} The new {new} {'is' if n == 1 else 'are'} there and EMPTY — fill with "
                f"do(overwrite, range=\"{_quote_tab(title)}!{cell_part}\", content=…) or remove "
                f"them with do(trash, range=\"{_quote_tab(title)}!{span}\", confirm=True).")}
    return sheet_result(file_id, metadata or {}, op, cues)


def sheet_rows_route(
    file_id: str, content: str | None, metadata: dict[str, Any] | None,
    range_: str | None, count: int | None, suggest: bool, op: Literal["append", "prepend"],
    tab: str | None = None,
) -> DoResult | dict[str, Any] | None:
    """A Sheet's prepend/append inserts rows; range=/count= elsewhere refuse.
    None means "not a Sheet, carry on down the Doc/plain-file path"."""
    mime = metadata.get("mimeType") if metadata else None
    if tab is not None and (range_ is not None or count is not None):
        return _err("tab= adds a new tab; range=/count= insert rows into an "
                    "existing one. One or the other.")
    if mime == GOOGLE_SHEET_MIME:
        if suggest:
            return _no_suggest_here(mime, op)
        try:
            validate_drive_id(file_id, "file_id")
        except ValueError as e:
            return {"error": True, "kind": "invalid_input", "message": str(e)}
        if tab is not None:  # append tab= on a Sheet; a Doc's tab= takes edit.py's branch
            return sheet_add_tab(file_id, content, metadata, tab)
        return sheet_insert(file_id, content, metadata, range_, count, op)
    if tab is not None:
        return None
    if range_ is not None or count is not None:
        named = " and ".join(p for p, v in (("range=", range_), ("count=", count)) if v is not None)
        return {"error": True, "kind": "invalid_input",
                "message": f"{named} on {op} inserts rows or columns into a Google Sheet; "
                           f"this file is {mime or 'not known to be a Sheet'}. Nothing was "
                           f"written. Drop {named} to {op} text."}
    return None


def sheet_add_tab(
    file_id: str, content: str | None, metadata: dict[str, Any] | None, tab: str,
) -> DoResult | dict[str, Any]:
    """append tab='T' on a Sheet: a new tab at the end, CSV written from A1.
    Sessions raw-called addSheet three times before this (Sep–Oct 2026)."""
    title = tab.strip()
    if not title:
        return _err("tab= requires a non-empty tab title")
    grid = parse_csv_grid(content, "append") if content else None
    if isinstance(grid, dict):
        return grid
    try:
        _, tabs = get_tab_grids(file_id)
        clash = find_tab(tabs, title)
        if clash is not None:
            name = clash.get("title", "")
            return _err(f"Tab '{name}' already exists (tabs: {_tabs_list(tabs)}). To add "
                        f"rows to it: append range=\"{_quote_tab(name)}!N\".")
        sheet_id = add_sheet(file_id, title)
    except MiseError as e:
        return {"error": True, "kind": e.kind.value, "message": e.message}
    after = f", after '{tabs[-1].get('title', '')}'" if tabs else ""
    cues: dict[str, Any] = {"tab": title, "tab_added": f"new tab '{title}' at the end{after}"}
    if grid is not None:
        try:
            write_grid(file_id, {"title": title, "sheetId": sheet_id}, None, grid[0], grid[1], cues)
        except MiseError as e:
            return {"error": True, "kind": e.kind.value, "message": (
                f"Added tab '{title}', but writing the values failed: {e.message} The tab "
                f"is there and EMPTY — fill it with do(overwrite, range=\"{_quote_tab(title)}\").")}
    return sheet_result(file_id, metadata or {}, "append", cues)

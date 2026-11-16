"""
Sheet formatting — do(format, range=, action='tidy'|'table'|'plain') (livacu, 16 Nov 2026).

Presets, not general styling. Six sessions (5 Oct–7 Nov 2026) hand-sent the
same four Sheets requests — freeze the header row, put a filter on it, style
it, size the columns — plus native tables twice, and nothing else (no
borders, merges, conditional formats). A named look keeps results consistent
and is easy to undo; free-form styling would spend do()'s description budget
on grammar nobody used. Scope: docs/research/2026-11-16-livacu-sheet-formatting-scope.md.

- tidy: header bold, filled, wrapped, with a rule under it; frozen; a basic
  filter over the block; columns auto-fitted and capped at COLUMN_CAP_PX so
  one long cell can't make a column 2,000 px wide. An existing freeze or
  filter is left alone and named in the cues.
- table: a native table (Format › Convert to table) over the block, sent
  bare then coloured (adapters/sheets_structure.add_table says why).
- plain: undoes tidy — clears the header style and rule, unfreezes, drops
  the basic filter. Native tables stay (removing one is a Sheets-menu act).

Colours follow the signed-in ACCOUNT (Sameer, 16 Nov 2026: "ITV colours by
kit"): an @itv.com account gets the ITV look (dark green header, white text,
Spark Yellow rule), any other the neutral one, because the same engine runs
the Planet Modha kit. Keyed on the account rather than the OAuth client so
the CLI and local dev agree with the plugin, and disclosed in cues.look.

Formatting changes no values, so there is no confirm gate; every result says
what changed and how to undo it. create doc_type='sheet' applies tidy to
every tab by default (apply_create_look; page_setup='plain' opts out).
"""

import re
from typing import Any

from adapters.drive import GOOGLE_SHEET_MIME, get_file_metadata
from adapters.sheets import batch_update
from adapters.sheets_structure import (
    add_table,
    get_column_widths,
    get_range_values,
    get_sheet_layout,
)
from cues_util import current_user_email
from models import DoResult, MiseError
from tools.sheet_edit import _quote_tab, _split_range, find_tab, sheet_result
from tools.sheet_structure import _err, _tabs_list, col_index, col_letters
from validation import validate_drive_id

COLUMN_CAP_PX = 320
CREATE_LOOK_MAX_TABS = 10
ACTIONS = ("tidy", "table", "plain")
ITV_LOOK = {"header_bg": "#0F2323", "header_fg": "#FFFFFF", "rule": "#DEEB52",
            "band1": "#FFFFFF", "band2": "#F1F4F4"}  # ITV/itv-slides-formatter tokens
NEUTRAL_LOOK = {"header_bg": "#EFEFEF", "header_fg": "#000000", "rule": "#B7B7B7"}
_BLOCK_RE = re.compile(r"^([A-Za-z]{1,3})(\d+):([A-Za-z]{1,3})(\d+)$")
_HEADER_FIELDS = ("userEnteredFormat(backgroundColorStyle,textFormat.bold,"
                  "textFormat.foregroundColorStyle,wrapStrategy,verticalAlignment)")

Block = tuple[int, int, int, int]  # zero-based rows [r0, r1), columns [c0, c1)


def _colour(hex_: str) -> dict[str, Any]:
    h = hex_.lstrip("#")
    return {"rgbColor": {"red": int(h[0:2], 16) / 255, "green": int(h[2:4], 16) / 255,
                         "blue": int(h[4:6], 16) / 255}}


def account_look() -> tuple[dict[str, str], str]:
    """(palette, cue) for the signed-in account."""
    email = current_user_email()
    if email and email.lower().endswith("@itv.com"):
        return ITV_LOOK, "ITV colours — the signed-in account is @itv.com"
    if email:
        return NEUTRAL_LOOK, "neutral colours — the signed-in account is not @itv.com"
    return NEUTRAL_LOOK, "neutral colours — the signed-in account could not be read"


def _block_a1(title: str, b: Block) -> str:
    r0, r1, c0, c1 = b
    return f"{title}!{col_letters(c0)}{r0 + 1}:{col_letters(c1 - 1)}{r1}"


def _grid(sheet_id: int, b: Block, header_only: bool = False) -> dict[str, Any]:
    r0, r1, c0, c1 = b
    return {"sheetId": sheet_id, "startRowIndex": r0, "endRowIndex": r0 + 1 if header_only else r1,
            "startColumnIndex": c0, "endColumnIndex": c1}


def _overlaps(b: Block, grid_range: dict[str, Any] | None) -> bool:
    if not grid_range:
        return False
    r0, r1, c0, c1 = b
    gr0, gr1 = grid_range.get("startRowIndex", 0), grid_range.get("endRowIndex", 10**9)
    gc0, gc1 = grid_range.get("startColumnIndex", 0), grid_range.get("endColumnIndex", 10**9)
    return bool(r0 < gr1 and gr0 < r1 and c0 < gc1 and gc0 < c1)


def _resolve(file_id: str, tabs: list[dict[str, Any]], range_: str | None,
             ) -> tuple[dict[str, Any], Block] | dict[str, Any]:
    """The tab and block to format, or the refusal (naming the tabs)."""
    if not tabs:
        return _err("format: this spreadsheet has no grid tabs.")
    cell: str | None = None
    if range_ is None:
        if len(tabs) > 1:
            return _err(f"This spreadsheet has {len(tabs)} tabs ({_tabs_list(tabs)}) — say which: "
                        f"range=\"{_quote_tab(tabs[0].get('title', ''))}\".")
        tab = tabs[0]
    else:
        name, cell = _split_range(range_)
        found = find_tab(tabs, name)
        if found is None and cell is None and len(tabs) == 1 and _BLOCK_RE.match(name):
            found, cell = tabs[0], name  # a bare 'A1:H5' on a one-tab sheet
        if found is None:
            return _err(f"No tab named '{name}' in this spreadsheet. Tabs: {_tabs_list(tabs)}.")
        tab = found
    title = tab.get("title", "")
    if cell is not None:
        m = _BLOCK_RE.match(cell.replace("$", ""))
        if not m:
            return _err(f"range='{range_}' on tab '{title}': format takes a whole tab "
                        f"(range=\"{title}\") or a bounded block with its header as the first row "
                        f"(range=\"{title}!A1:H20\").")
        a, b = sorted((int(m.group(2)), int(m.group(4))))
        c0, c1 = sorted((col_index(m.group(1)), col_index(m.group(3))))
        return tab, (a - 1, b, c0, c1 + 1)
    values = get_range_values(file_id, _quote_tab(title))
    filled = [i for i, row in enumerate(values) if any(str(v).strip() for v in row)]
    if not filled:
        return _err(f"Tab '{title}' holds no values, so there is no header to format.")
    r0, r1 = filled[0], filled[-1] + 1
    gap = next((i for i in range(r0, r1) if i not in set(filled)), None)
    if gap is not None:  # a title row above the header, most likely
        return _err(f"Tab '{title}' has a blank row (row {gap + 1}) inside its data, so which row is "
                    f"the header isn't clear. Give a bounded range starting at the header row, "
                    f"e.g. range=\"{_quote_tab(title)}!A{gap + 2}:H40\".")
    c0 = min(next(j for j, v in enumerate(values[i]) if str(v).strip()) for i in filled)
    return tab, (r0, r1, c0, max(len(values[i]) for i in filled))


def _same_block(b: Block, grid_range: dict[str, Any] | None) -> bool:
    if not grid_range:
        return False
    return (grid_range.get("startRowIndex", 0), grid_range.get("endRowIndex"),
            grid_range.get("startColumnIndex", 0), grid_range.get("endColumnIndex")) == b


def _widths(file_id: str, tab: dict[str, Any], b: Block) -> list[dict[str, Any]]:
    """Cap columns the auto-fit left wider than COLUMN_CAP_PX."""
    widths = get_column_widths(file_id, _quote_tab(tab.get("title", "")))
    return [{"updateDimensionProperties": {
        "range": {"sheetId": tab.get("sheetId", 0), "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
        "properties": {"pixelSize": COLUMN_CAP_PX}, "fields": "pixelSize"}}
        for i in range(b[2], min(b[3], len(widths))) if widths[i] > COLUMN_CAP_PX]


def _tidy(file_id: str, tab: dict[str, Any], b: Block, look: dict[str, str],
          applied: list[str], left: list[str]) -> dict[str, Any] | None:
    sid, title = int(tab.get("sheetId", 0)), tab.get("title", "")
    table = next((t for t in tab.get("tables", []) if _overlaps(b, t.get("range"))), None)
    if table is not None:
        return _err(f"Tab '{title}' has a native table ('{table.get('name', '')}') over that "
                    "range, and a table styles itself. Format another block, or leave it.")
    requests: list[dict[str, Any]] = [
        {"repeatCell": {"range": _grid(sid, b, header_only=True), "cell": {"userEnteredFormat": {
            "backgroundColorStyle": _colour(look["header_bg"]),
            "textFormat": {"bold": True, "foregroundColorStyle": _colour(look["header_fg"])},
            "wrapStrategy": "WRAP", "verticalAlignment": "MIDDLE"}}, "fields": _HEADER_FIELDS}},
        {"updateBorders": {"range": _grid(sid, b, header_only=True),
                           "bottom": {"style": "SOLID_MEDIUM", "colorStyle": _colour(look["rule"])}}},
    ]
    applied.append(f"header row {b[0] + 1} styled")
    frozen = int(tab.get("gridProperties", {}).get("frozenRowCount", 0))
    if b[0] == 0 and frozen == 0:
        requests.append({"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {
            "frozenRowCount": 1}}, "fields": "gridProperties.frozenRowCount"}})
        applied.append("row 1 frozen")
    elif frozen:
        left.append(f"freeze kept ({frozen} row{'s' if frozen > 1 else ''} already frozen)")
    if tab.get("basicFilter"):
        left.append("existing filter kept")
    else:
        requests.append({"setBasicFilter": {"filter": {"range": _grid(sid, b)}}})
        applied.append(f"filter on {_block_a1(title, b)} — a row outside it (a footer) stays put "
                       "when someone sorts; a row inside it moves")
    requests.append({"autoResizeDimensions": {"dimensions": {
        "sheetId": sid, "dimension": "COLUMNS", "startIndex": b[2], "endIndex": b[3]}}})
    batch_update(file_id, requests)
    caps = _widths(file_id, tab, b)
    if caps:
        batch_update(file_id, caps)
    applied.append(f"{b[3] - b[2]} columns auto-fitted" + (f", {len(caps)} capped at {COLUMN_CAP_PX}px" if caps else ""))
    return None


def _table(file_id: str, tab: dict[str, Any], b: Block, look: dict[str, str],
           applied: list[str], left: list[str], taken: frozenset[str] | set[str] = frozenset()) -> dict[str, Any] | None:
    sid, title = int(tab.get("sheetId", 0)), tab.get("title", "")
    clash = next((t for t in tab.get("tables", []) if _overlaps(b, t.get("range"))), None)
    if clash is not None:
        return _err(f"Tab '{title}' already has a native table ('{clash.get('name', '')}') over that range.")
    flt = tab.get("basicFilter")
    if flt and _same_block(b, flt.get("range")):
        # tidy's own footprint (create applies tidy): the table replaces it rather than
        # refusing, or "make a sheet, then table it" takes a pointless plain in between
        batch_update(file_id, [{"clearBasicFilter": {"sheetId": sid}},
                               {"repeatCell": {"range": _grid(sid, b, header_only=True), "cell": {},
                                               "fields": _HEADER_FIELDS}},
                               {"updateBorders": {"range": _grid(sid, b, header_only=True),
                                                  "bottom": {"style": "NONE"}}}])
        applied.append("tidy's filter and header style replaced by the table")
    elif flt and _overlaps(b, flt.get("range")):
        return _err(f"Tab '{title}' has a filter over a different range from this one; a table brings "
                    f"its own. Remove it first (do(format, range=\"{title}\", action='plain') removes "
                    "a filter on exactly that block), or give the filter's own range.")
    names = set(taken) | {t.get("name", "") for t in tab.get("tables", [])}
    base = re.sub(r"\W+", "_", title).strip("_") or "Table"
    base = f"T_{base}" if base[0].isdigit() else base
    name = next(n for n in (f"{base}_table" + (f"_{i}" if i else "") for i in range(100)) if n not in names)
    table_id = add_table(file_id, sid, name, *b)
    applied.append(f"native table '{name}' over {_block_a1(title, b)}")
    requests: list[dict[str, Any]] = []
    if look is ITV_LOOK:
        requests.append({"updateTable": {"table": {"tableId": table_id, "rowsProperties": {
            "headerColorStyle": _colour(look["header_bg"]), "firstBandColorStyle": _colour(look["band1"]),
            "secondBandColorStyle": _colour(look["band2"])}}, "fields": "rowsProperties"}})
    frozen = int(tab.get("gridProperties", {}).get("frozenRowCount", 0))
    if b[0] == 0 and frozen == 0:
        requests.append({"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {
            "frozenRowCount": 1}}, "fields": "gridProperties.frozenRowCount"}})
        applied.append("row 1 frozen")
    requests.append({"autoResizeDimensions": {"dimensions": {
        "sheetId": sid, "dimension": "COLUMNS", "startIndex": b[2], "endIndex": b[3]}}})
    try:
        batch_update(file_id, requests)
        caps = _widths(file_id, tab, b)
        if caps:
            batch_update(file_id, caps)
    except MiseError as e:
        return {"error": True, "kind": e.kind.value, "message": (
            f"Made native table '{name}' over {_block_a1(title, b)}, but finishing it (colours, "
            f"freeze, widths) failed: {e.message} The table is there with Google's default look; "
            "a repeat of this call will refuse because the table exists.")}
    return None


def _plain(file_id: str, tab: dict[str, Any], b: Block, look: dict[str, str],
           applied: list[str], left: list[str]) -> dict[str, Any] | None:
    sid = int(tab.get("sheetId", 0))
    requests: list[dict[str, Any]] = [
        {"repeatCell": {"range": _grid(sid, b, header_only=True), "cell": {}, "fields": _HEADER_FIELDS}},
        {"updateBorders": {"range": _grid(sid, b, header_only=True), "bottom": {"style": "NONE"}}},
    ]
    applied.append(f"header row {b[0] + 1} style cleared to defaults (a style from before tidy "
                   "isn't restored; Version history has it)")
    frozen = int(tab.get("gridProperties", {}).get("frozenRowCount", 0))
    if frozen == 1 and b[0] == 0:  # tidy's footprint: exactly one row, over a block at the top
        requests.append({"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {
            "frozenRowCount": 0}}, "fields": "gridProperties.frozenRowCount"}})
        applied.append("row 1 unfrozen")
    elif frozen:
        left.append(f"freeze kept ({frozen} rows, or not over this block — not tidy's)")
    flt = tab.get("basicFilter")
    if flt and _same_block(b, flt.get("range")):
        requests.append({"clearBasicFilter": {"sheetId": sid}})
        applied.append("filter removed")
    elif flt:
        left.append("filter kept (it covers a different range — not tidy's)")
    for t in tab.get("tables", []):
        if _overlaps(b, t.get("range")):
            left.append(f"native table '{t.get('name', '')}' kept — remove it in Sheets (Table menu)")
    left.append("column widths kept (their earlier widths aren't known)")
    batch_update(file_id, requests)
    return None


_LOOKS = {"tidy": _tidy, "table": _table, "plain": _plain}


def do_format(
    file_id: str | None = None, range_: str | None = None, action: str | None = None,
) -> DoResult | dict[str, Any]:
    """Apply a named look to a Sheet tab or block."""
    if not file_id or not isinstance(file_id, str):
        return _err("format requires one 'file_id' (a Google Sheet).")
    if action not in ACTIONS:
        return _err(f"format takes action='tidy' (header styled, frozen, filtered, columns sized), "
                    f"'table' (a native Sheets table) or 'plain' (undo tidy); got {action!r}.")
    try:
        validate_drive_id(file_id, "file_id")
    except ValueError as e:
        return _err(str(e))
    try:
        metadata = get_file_metadata(file_id)
        if metadata.get("mimeType") != GOOGLE_SHEET_MIME:
            return _err(f"format applies to Google Sheets; this file is {metadata.get('mimeType')}.")
        _, tabs = get_sheet_layout(file_id)
        resolved = _resolve(file_id, tabs, range_)
        if isinstance(resolved, dict):
            return resolved
        tab, block = resolved
        look, look_cue = account_look()
        applied: list[str] = []
        left: list[str] = []
        taken = {t.get("name", "") for other in tabs for t in other.get("tables", [])}
        refused = (_table(file_id, tab, block, look, applied, left, taken) if action == "table"
                   else _LOOKS[action](file_id, tab, block, look, applied, left))
        if refused:
            return refused
    except MiseError as e:
        return {"error": True, "kind": e.kind.value, "message": e.message}
    title = tab.get("title", "")
    cues: dict[str, Any] = {"tab": title, "range": _block_a1(title, block), "applied": applied}
    if action != "plain":
        cues["look"] = look_cue
        r0, r1, c0, c1 = block
        quoted = f"{_quote_tab(title)}!{col_letters(c0)}{r0 + 1}:{col_letters(c1 - 1)}{r1}"
        cues["undo"] = (f"do(format, range=\"{quoted}\", action='plain'), or File › Version history"
                        + (" — plain removes a one-row freeze and a filter on exactly this block "
                           "whoever set them, so with anything in left_alone, prefer Version history"
                           if left else ""))
    if left:
        cues["left_alone"] = left
    return sheet_result(file_id, metadata, "format", cues)


def apply_create_look(result: DoResult) -> None:
    """tidy every tab of a sheet mise just created. Fail-open by design: the
    sheet exists either way, so a formatting failure becomes a cue naming why."""
    done: list[str] = []
    skipped: list[str] = []
    try:
        _, tabs = get_sheet_layout(result.file_id)
        look, look_cue = account_look()
        for i, tab in enumerate(tabs):
            title = tab.get("title", "")
            if i >= CREATE_LOOK_MAX_TABS:  # ~4 Sheets calls a tab; keep a big deposit under the quota
                skipped.append(f"{title!r} (only the first {CREATE_LOOK_MAX_TABS} tabs are tidied at create)")
                continue
            resolved = _resolve(result.file_id, [tab], _quote_tab(title))
            if isinstance(resolved, dict):
                skipped.append(f"{title!r} ({resolved['message']})")
                continue
            if _tidy(result.file_id, tab, resolved[1], look, [], []) is None:
                done.append(title)
            else:
                skipped.append(f"{title!r} (it holds a native table)")
        if done:
            result.cues["look"] = (f"tidy applied to {', '.join(repr(t) for t in done)} ({look_cue}); "
                                   "page_setup='plain' skips it, do(format, action='plain') removes it")
    except MiseError as e:
        so_far = f" Tidied before it failed: {', '.join(repr(t) for t in done)}." if done else ""
        result.cues["look_error"] = f"The sheet was made, but its tidy look wasn't fully applied: {e.message}{so_far}"
    if skipped:
        result.cues["look_skipped"] = skipped

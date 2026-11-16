"""
Sheets structural writes — insert and delete whole rows or columns.

spreadsheets.batchUpdate's insertDimension / deleteDimension, plus the two
reads the tools layer needs around them: each tab's grid size (to say what
shifted, and to refuse a row past the end) and a range's values (the delete
preview shows what is about to go).

Both writes are NOT idempotent, and that is the whole reason they live
apart from adapters/sheets.py's batch_update: a retried insert adds a second
block of rows, and a retried delete removes the rows that had shifted into
the gap — other people's rows, on a shared sheet. So they retry only on 429
(rejected before it ran), never on a 5xx that may have landed.
"""

from typing import Any, Literal

from adapters.http_client import get_sync_client
from adapters.sheets import _SHEETS_API, _path_range
from retry import with_retry

Dimension = Literal["ROWS", "COLUMNS"]


@with_retry(max_attempts=3, delay_ms=1000, idempotent=True)
def get_tab_grids(spreadsheet_id: str) -> tuple[str, list[dict[str, Any]]]:
    """The spreadsheet's title and its GRID tabs' properties, grid size
    (gridProperties.rowCount / columnCount) included."""
    client = get_sync_client()
    response = client.get_json(
        f"{_SHEETS_API}/{spreadsheet_id}",
        params={"fields": "properties.title,sheets.properties(sheetId,title,index,"
                          "sheetType,gridProperties(rowCount,columnCount))"},
    )
    props = [s.get("properties", {}) for s in response.get("sheets", [])]
    title = str(response.get("properties", {}).get("title", ""))
    return title, [p for p in props if p.get("sheetType", "GRID") == "GRID"]


@with_retry(max_attempts=3, delay_ms=1000, idempotent=True)
def get_range_values(spreadsheet_id: str, range_: str) -> list[list[Any]]:
    """Formatted values of an A1 range, as the sheet shows them."""
    client = get_sync_client()
    response = client.get_json(
        f"{_SHEETS_API}/{spreadsheet_id}/values/{_path_range(range_)}",
        params={"valueRenderOption": "FORMATTED_VALUE"},
    )
    return list(response.get("values", []))


@with_retry(max_attempts=3, delay_ms=1000, idempotent=False)
def insert_dimension(
    spreadsheet_id: str, sheet_id: int, dimension: Dimension,
    start: int, end: int, inherit_from_before: bool,
) -> None:
    """Insert rows/columns [start, end) (zero-based) — existing ones shift on."""
    client = get_sync_client()
    client.post_json(
        f"{_SHEETS_API}/{spreadsheet_id}:batchUpdate",
        json_body={"requests": [{"insertDimension": {
            "range": {"sheetId": sheet_id, "dimension": dimension,
                      "startIndex": start, "endIndex": end},
            "inheritFromBefore": inherit_from_before,
        }}]},
    )


@with_retry(max_attempts=3, delay_ms=1000, idempotent=False)
def delete_dimension(
    spreadsheet_id: str, sheet_id: int, dimension: Dimension, start: int, end: int,
) -> None:
    """Delete rows/columns [start, end) (zero-based) — later ones shift back."""
    client = get_sync_client()
    client.post_json(
        f"{_SHEETS_API}/{spreadsheet_id}:batchUpdate",
        json_body={"requests": [{"deleteDimension": {
            "range": {"sheetId": sheet_id, "dimension": dimension,
                      "startIndex": start, "endIndex": end},
        }}]},
    )

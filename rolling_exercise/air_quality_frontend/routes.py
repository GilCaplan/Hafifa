"""Endpoints that only exist for the frontend: its logs panel (GET /logs) and its table browser (GET /tables/...)."""

import logging
import re
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status

from air_quality_api.const import LOG_FILE
from air_quality_api.utils import run_query
from air_quality_db.queries import count_rows, fetch_rows
from air_quality_frontend.const import (
    BROWSABLE_TABLES,
    DEFAULT_LOG_LIMIT,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SORT_COLUMN,
    LOG_LINE_PATTERN,
    MAX_LOG_LIMIT,
    MAX_PAGE_SIZE,
)

logger = logging.getLogger(__name__)
router = APIRouter()

LOG_LINE_REGEX = re.compile(LOG_LINE_PATTERN)


def read_log_entries(limit: int, request_id: str | None = None) -> list[dict]:
    """
    Parses the log file into entries, newest first. Multi-line messages (like tracebacks) stay in one entry.
    With `request_id`, only that request's entries are returned.
    """
    log_path = Path(LOG_FILE)
    if not log_path.exists():
        return []

    entries = []
    for line in log_path.read_text().splitlines():
        match = LOG_LINE_REGEX.match(line)
        if match:
            entries.append(match.groupdict())
        elif entries:
            entries[-1]["message"] += f"\n{line}"
    if request_id:
        entries = [entry for entry in entries if entry["request_id"] == request_id]
    return entries[-limit:][::-1]


@router.get("/logs")
def get_logs(limit: int = Query(DEFAULT_LOG_LIMIT, ge=1, le=MAX_LOG_LIMIT), request_id: str | None = None):
    """
    GET logs
    Description: Retrieves the most recent log entries, newest first. Used by the frontend.
    Query Parameters:
        limit: How many entries to return.
        request_id: Only entries written while handling this request (from the X-Request-ID response header).
    """
    return read_log_entries(limit, request_id)


@router.get("/tables/{table}")
def browse_table(
    table: str,
    city: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    sort: str = DEFAULT_SORT_COLUMN,
    descending: bool = True,
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
):
    """
    GET table rows
    Description: Retrieves one page of the readings or alerts table, for browsing in the frontend.
    Path Parameters:
        table: "readings" or "alerts".
    Query Parameters:
        city: Only rows whose city contains this text (case-insensitive).
        start_date, end_date: Only rows in this date range (YYYY-MM-DD, inclusive).
        sort: The column to sort by. descending: Sort direction.
        limit, offset: Page size and how many rows to skip.
    """
    if table not in BROWSABLE_TABLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown table {table}. Available tables: {list(BROWSABLE_TABLES)}",
        )
    columns = BROWSABLE_TABLES[table]["columns"]
    if sort not in columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot sort by {sort}. Columns: {columns}"
        )

    db_table = BROWSABLE_TABLES[table]["table"]
    filters = {"city_contains": city, "start_date": start_date, "end_date": end_date}
    rows = run_query(
        f"read {table}",
        fetch_rows,
        table=db_table,
        columns=columns,
        sort=sort,
        descending=descending,
        limit=limit,
        offset=offset,
        **filters,
    )
    total = run_query(f"count {table}", count_rows, table=db_table, **filters)

    logger.info(f"Viewed {table}: {len(rows)} of {total} rows (city={city}, dates={start_date}..{end_date})")
    return {"columns": columns, "rows": rows, "total": total, "limit": limit, "offset": offset}

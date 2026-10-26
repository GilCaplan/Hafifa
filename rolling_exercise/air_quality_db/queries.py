from datetime import date

import pandas as pd
from psycopg import sql
from psycopg.rows import dict_row

from air_quality_db.connection import get_connection
from air_quality_db.statements import (
    ALERT_COLUMNS,
    INSERT_ALERT,
    INSERT_READING,
    READING_COLUMNS,
)
from air_quality_db.utils import (
    build_columns,
    build_filters,
    build_order_by,
    to_rows,
)


def save_readings(readings: pd.DataFrame, alerts: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Saves readings and their alerts in one transaction, skipping readings whose (date, city) is already saved
    and their alerts. `alerts` must share `readings`' index. Returns (skipped readings, number of alerts inserted).
    """
    if readings.empty:
        return readings, 0

    with get_connection() as connection, connection.cursor() as cursor:
        cursor.executemany(INSERT_READING, to_rows(readings, READING_COLUMNS), returning=True)
        # One result per reading, in order: the RETURNING row if it was inserted, nothing if it was a duplicate
        inserted = []
        while True:
            inserted.append(cursor.fetchone() is not None)
            if not cursor.nextset():
                break
        was_inserted = pd.Series(inserted, index=readings.index)

        # .loc selects rows: plain alerts[...] with an empty list would select zero columns instead
        new_alerts = to_rows(alerts.loc[was_inserted[alerts.index]], ALERT_COLUMNS)
        if new_alerts:
            cursor.executemany(INSERT_ALERT, new_alerts)

    return readings[~was_inserted], len(new_alerts)


def fetch_rows(
    table: str,
    columns: list[str] | None = None,
    city: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    sort: str | list[str] | None = None,
) -> list[dict]:
    """
    Returns list of dictionary per table row by SQL query
    for input values that are not None.
    """

    where, params = build_filters(city, start_date, end_date)
    query = sql.SQL("SELECT {columns} FROM {table}{where}{order_by}").format(
        columns=build_columns(columns),
        table=sql.Identifier(table),
        where=where,
        order_by=build_order_by(sort),
    )

    with get_connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def count_rows(
    table: str,
    city: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> int:
    """Returns how many rows of `table` match the filters (same filters as fetch_rows)."""
    where, params = build_filters(city, start_date, end_date)
    query = sql.SQL("SELECT count(*) AS total FROM {table}").format(table=sql.Identifier(table)) + where

    with get_connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, params)
        return cursor.fetchone()["total"]


def get_date_range(table: str) -> tuple[date | None, date | None]:
    """Returns the earliest and latest date in `table`, or (None, None) if it's empty."""
    query = sql.SQL("SELECT min(date) AS first, max(date) AS last FROM {table}").format(table=sql.Identifier(table))
    with get_connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query)
        row = cursor.fetchone()
    return row["first"], row["last"]

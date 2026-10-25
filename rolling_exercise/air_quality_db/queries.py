from datetime import date

import pandas as pd
from psycopg import sql
from psycopg.rows import dict_row

from air_quality_db.connection import get_connection
from air_quality_db.statements import ALERT_COLUMNS, INSERT_ALERT, INSERT_READING, READING_COLUMNS


def to_rows(df: pd.DataFrame, columns: list[str]) -> list[tuple]:
    return list(df[columns].itertuples(index=False, name=None))


def save_readings(readings: pd.DataFrame, alerts: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Saves readings and their alerts in one transaction: either both are saved or neither is.
    Readings whose (date, city) is already saved, or appears earlier in the same upload, are skipped as duplicates,
    and so are their alerts. `alerts` must be rows of `readings` (same index).
    Returns (the duplicate readings, the number of alerts inserted).
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


def active_clauses(clauses: list[tuple[str, object]]) -> tuple[list[sql.SQL], list]:
    """Keeps the (SQL, value) pairs whose value is not None, and returns their SQL pieces and their values."""
    active = [(clause, value) for clause, value in clauses if value is not None]
    return [sql.SQL(clause) for clause, _ in active], [value for _, value in active]


def build_filters(
    city: str | None = None,
    city_contains: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[sql.Composable, list]:
    """Builds the WHERE clause and its parameters. Filters left as None are not applied."""
    conditions, params = active_clauses(
        [
            ("city = %s", city),
            ("city ILIKE %s", None if city_contains is None else f"%{city_contains}%"),
            ("date >= %s", start_date),
            ("date <= %s", end_date),
        ]
    )

    if not conditions:
        return sql.SQL(""), params
    return sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conditions), params


def fetch_rows(
    table: str,
    columns: list[str] | None = None,
    city: str | None = None,
    city_contains: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    sort: str | list[str] | None = None,
    descending: bool = False,
    limit: int | None = None,
    offset: int | None = None,
) -> list[dict]:
    """
    Returns a table's rows as dicts. Every option left as None is not applied:
    no columns -> all columns, no filters -> all rows, no sort -> no ORDER BY, no limit/offset -> every row.

    city: exact match. city_contains: case-insensitive partial match. start_date/end_date: inclusive.
    sort: one column, or a list of columns where each later one breaks ties in the ones before it.
    `descending` applies to all of them, and `id` breaks any ties left.
    `table`, `columns` and `sort` go into the SQL as identifiers, so callers must check them against a fixed list
    first, never pass user input straight through.
    """
    selected = sql.SQL(", ").join(map(sql.Identifier, columns)) if columns else sql.SQL("*")
    where, params = build_filters(city, city_contains, start_date, end_date)
    query = sql.SQL("SELECT {columns} FROM {table}").format(columns=selected, table=sql.Identifier(table)) + where

    sort_columns = [sort] if isinstance(sort, str) else sort or []
    direction = sql.SQL("DESC" if descending else "ASC")
    order_by = (
        sql.SQL(" ORDER BY {}, id").format(
            sql.SQL(", ").join([sql.SQL("{} {}").format(sql.Identifier(column), direction) for column in sort_columns])
        )
        if sort_columns
        else sql.SQL("")
    )
    paging, paging_params = active_clauses([(" LIMIT %s", limit), (" OFFSET %s", offset)])
    query += order_by + sql.SQL("").join(paging)

    with get_connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, [*params, *paging_params])
        return cursor.fetchall()


def count_rows(
    table: str,
    city: str | None = None,
    city_contains: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> int:
    """Returns how many rows of `table` match the filters (same filters as fetch_rows)."""
    where, params = build_filters(city, city_contains, start_date, end_date)
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

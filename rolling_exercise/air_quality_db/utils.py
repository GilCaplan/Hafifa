"""Helper file for queries.py"""

from datetime import date

import pandas as pd
from psycopg import sql


def convert_tuple_list(df: pd.DataFrame, columns: list[str]) -> list[tuple]:
    return list(df[columns].itertuples(index=False, name=None))


def active_clauses(clauses: list[tuple[str, object]]) -> tuple[list[sql.SQL], list]:
    """Drops (SQL, value) pairs whose value is None. Returns the remaining SQL pieces and values."""
    active = [(clause, value) for clause, value in clauses if value is not None]
    sql_clauses, values = [sql.SQL(clause) for clause, _ in active], [value for _, value in active]
    return sql_clauses, values


def build_filters(
    city: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[sql.Composable, list]:
    """Builds the WHERE clause and its parameters. Filters left as None are not applied."""
    conditions, params = active_clauses(
        [
            ("city = %s", city),
            ("date >= %s", start_date),
            ("date <= %s", end_date),
        ]
    )

    if not conditions:
        return sql.SQL(""), params
    return sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conditions), params


def build_columns(columns: list[str] | None) -> sql.Composable:
    """The SELECT list: the given columns, or * for all of them."""
    return sql.SQL(", ").join(map(sql.Identifier, columns)) if columns else sql.SQL("*")


def build_order_by(sort: str | list[str] | None) -> sql.Composable:
    """ORDER BY the sort column(s), then id to break ties. Empty if there's nothing to sort by."""
    sort_columns = [sort] if isinstance(sort, str) else sort or []
    if not sort_columns:
        return sql.SQL("")
    return sql.SQL(" ORDER BY {}, id").format(sql.SQL(", ").join(map(sql.Identifier, sort_columns)))

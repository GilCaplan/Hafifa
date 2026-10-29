"""Helper file for queries.py"""

from collections.abc import Iterator
from datetime import date

from sqlalchemy import ColumnElement

from air_quality_api.const import Consts
from air_quality_db.models import Table


def chunks(rows: list[dict]) -> Iterator[list[dict]]:
    """Splits the rows into INSERT-sized pieces (see Consts.insert_chunk_size)."""
    for start in range(0, len(rows), Consts.insert_chunk_size):
        yield rows[start : start + Consts.insert_chunk_size]


def build_filters(
    table: Table,
    city: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ColumnElement[bool]]:
    """The WHERE conditions for the filters that aren't None."""
    conditions = []
    if city is not None:
        conditions.append(table.city == city)
    if start_date is not None:
        conditions.append(table.date >= start_date)
    if end_date is not None:
        conditions.append(table.date <= end_date)
    return conditions

from collections.abc import Iterator
from datetime import date

from sqlalchemy import ColumnElement

from app.core.constants import Consts
from app.db.models import Table


def chunks(rows: list[dict]) -> Iterator[list[dict]]:
    for start in range(0, len(rows), Consts.insert_chunk_size):
        yield rows[start : start + Consts.insert_chunk_size]


def build_city_filters(table: Table, city: str | None = None) -> list[ColumnElement[bool]]:
    return [table.city == city] if city is not None else []


def build_date_filters(
    table: Table,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ColumnElement[bool]]:
    conditions = []
    if start_date is not None:
        conditions.append(table.date >= start_date)

    if end_date is not None:
        conditions.append(table.date <= end_date)

    return conditions

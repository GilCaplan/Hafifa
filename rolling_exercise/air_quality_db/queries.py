from datetime import date

import pandas as pd
from sqlalchemy import func, inspect, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import InstrumentedAttribute

from air_quality_db.connection import get_session
from air_quality_db.models import Alert, Reading, Table
from air_quality_db.utils import build_filters, chunks


def save_readings_and_alerts(readings: pd.DataFrame, alerts: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Saves readings and their alerts in one transaction, skipping readings whose (date, city) is already saved
    and their alerts. `alerts` must share `readings`' index. Returns (skipped readings, number of alerts inserted).
    """
    if readings.empty:
        return readings, 0

    with get_session() as session, session.begin():
        inserted_keys = set()
        for chunk in chunks(readings.to_dict("records")):
            insert_readings = (
                insert(Reading)
                .values(chunk)
                .on_conflict_do_nothing(index_elements=[Reading.date, Reading.city])
                .returning(Reading.date, Reading.city)
            )
            inserted_keys |= {tuple(row) for row in session.execute(insert_readings)}
        # RETURNING lists only the inserted (date, city) pairs. A pair repeated in the file is inserted once: the first
        key_columns = [Reading.date.key, Reading.city.key]
        was_returned = pd.MultiIndex.from_frame(readings[key_columns]).isin(inserted_keys)
        was_inserted = pd.Series(was_returned, index=readings.index) & ~readings.duplicated(key_columns)

        new_alerts = alerts.loc[was_inserted[alerts.index]]
        for chunk in chunks(new_alerts.to_dict("records")):
            session.execute(insert(Alert).values(chunk).on_conflict_do_nothing())

    return readings[~was_inserted], len(new_alerts)


def fetch_rows(
    table: Table,
    columns: list[InstrumentedAttribute] | None = None,
    city: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    sort: InstrumentedAttribute | list[InstrumentedAttribute] | None = None,
) -> list[dict]:
    """
    Returns list of dictionary per table row by SQL query
    for input values that are not None. `columns` and `sort` are the model's columns, e.g. [Reading.date].
    """
    query = select(*(columns or inspect(table).columns))\
                    .where(*build_filters(table, city, start_date, end_date))
    sort_columns = sort if isinstance(sort, list) else [sort] if sort is not None else []
    if sort_columns:
        query = query.order_by(*sort_columns, table.id)

    with get_session() as session:
        return [dict(row) for row in session.execute(query).mappings()]


def count_rows(
    table: Table,
    city: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> int:
    """Returns how many rows of `table` match the filters (same filters as fetch_rows)."""
    query = select(func.count()).select_from(table)\
                        .where(*build_filters(table, city, start_date, end_date))
    with get_session() as session:
        return session.scalar(query)


def get_average_aqi(cities: list[str] | None = None) -> dict[str, float]:
    """Each city's average AQI over all its readings, as {city: average}: of the given cities, or of all if None."""
    query = select(Reading.city, func.avg(Reading.aqi)).group_by(Reading.city)
    if cities is not None:
        query = query.where(Reading.city.in_(cities))
    with get_session() as session:
        return {city: average for city, average in session.execute(query)}


def get_date_range(table: Table) -> tuple[date | None, date | None]:
    """Returns the earliest and latest date in `table`, or (None, None) if it's empty."""
    with get_session() as session:
        first, last = session.execute(select(func.min(table.date), func.max(table.date))).one()
    return first, last

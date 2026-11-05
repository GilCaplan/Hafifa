from datetime import date

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.db.models import Alert, Reading, Table
from app.db.session import get_session
from app.db.utils import build_city_filters, build_date_filters, chunks


def insert_readings(session: Session, readings: pd.DataFrame) -> pd.Series:
    """
    Inserts each (date, city) once, from its first row in the file, unless it's already saved.
    Returns, for each row, whether it was inserted.
    """
    key_columns = [Reading.date.key, Reading.city.key]
    unique_readings = readings.drop_duplicates(key_columns)
    inserted_keys = set()

    for chunk in chunks(unique_readings.to_dict("records")):
        insert_query = (
            insert(Reading)
            .values(chunk)
            .on_conflict_do_nothing(index_elements=[Reading.date, Reading.city])
            .returning(Reading.date, Reading.city)
        )
        inserted_keys |= {tuple(row) for row in session.execute(insert_query)}

    unique_was_inserted = pd.MultiIndex.from_frame(unique_readings[key_columns]).isin(inserted_keys)
    was_inserted = pd.Series(unique_was_inserted, index=unique_readings.index).reindex(readings.index, fill_value=False)
    return was_inserted


def insert_alerts(session: Session, alerts: pd.DataFrame) -> None:
    for chunk in chunks(alerts.to_dict("records")):
        session.execute(insert(Alert).values(chunk).on_conflict_do_nothing())


def save_readings_and_alerts(readings: pd.DataFrame, alerts: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Saves the new readings and their alerts in one transaction. `alerts` must share `readings`' index.
    Returns (skipped readings, number of alerts inserted).
    """
    if readings.empty:
        return readings, 0

    with get_session() as session, session.begin():
        was_inserted = insert_readings(session, readings)
        new_alerts = alerts.loc[was_inserted[alerts.index]]
        insert_alerts(session, new_alerts)

    return readings[~was_inserted], len(new_alerts)


def fetch_rows(
    table: Table,
    city: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    sort: InstrumentedAttribute | list[InstrumentedAttribute] | None = None,
) -> list[dict]:
    """Returns the matching rows as dicts. Filters that are None are ignored."""
    query = select(table.__table__).where(
        *build_city_filters(table, city), *build_date_filters(table, start_date, end_date)
    )
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
    query = (
        select(func.count())
        .select_from(table)
        .where(*build_city_filters(table, city), *build_date_filters(table, start_date, end_date))
    )
    with get_session() as session:
        return session.scalar(query)


def get_average_aqi(cities: list[str] | None = None, limit: int | None = None) -> dict[str, float]:
    """{city: average AQI}, lowest first, for the given cities or for all of them if None."""
    average = func.avg(Reading.aqi)
    query = select(Reading.city, average).group_by(Reading.city).order_by(average, Reading.city).limit(limit)
    if cities is not None:
        query = query.where(Reading.city.in_(cities))

    with get_session() as session:
        return {city: average for city, average in session.execute(query)}


def get_date_range(table: Table) -> tuple[date | None, date | None]:
    with get_session() as session:
        first, last = session.execute(select(func.min(table.date), func.max(table.date))).one()

    return first, last

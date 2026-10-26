import logging
from datetime import date

import psycopg
from fastapi import HTTPException, status

from air_quality_api.const import City, Tables
from air_quality_db.queries import count_rows, get_date_range

logger = logging.getLogger(__name__)


def clean_city_name(city: str) -> str:
    """
    Collapses extra spaces ("  Tel   Aviv " -> "Tel Aviv").
    Raises ValueError, with a message for the user, if the name is empty, too long or has invalid characters.
    """
    cleaned = " ".join(city.split())
    if not cleaned:
        raise ValueError("City name is empty")
    if len(cleaned) > City.MAX_NAME_LENGTH:
        raise ValueError(f"City name is longer than {City.MAX_NAME_LENGTH} characters")
    if not City.NAME_REGEX.match(cleaned):
        raise ValueError(f"City name {cleaned!r} can only contain letters, spaces, hyphens and apostrophes")
    return cleaned


def call_database(action: str, db_operation, **kwargs):
    """
    Runs a database function, logging failures and raising 503 if the database is unreachable, 500 otherwise.
    `action` describes the call for the log and the 500's detail, e.g. "read alerts for Haifa".
    """
    try:
        return db_operation(**kwargs)
    except psycopg.OperationalError as error:
        logger.error(f"Failed to {action}: database unavailable ({error})")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is unavailable, try again later"
        ) from error
    except psycopg.Error as error:
        logger.error(f"Failed to {action}: database error ({error})")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not {action}") from error


def validate_city(city: str) -> str:
    """Returns the cleaned city name (see clean_city_name). Raises 400 if it's malformed, 404 if it has no readings."""
    try:
        cleaned = clean_city_name(city)
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error

    if call_database(f"look up city {cleaned}", count_rows, table=Tables.READINGS, city=cleaned) == 0:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"No readings for city {cleaned}. Check the spelling: city names are case-sensitive",
        )
    return cleaned


def validate_dates(start_date: date, end_date: date | None = None) -> None:
    """
    Checks a date, or date range, against the data's dates: a range must overlap them, a single date fall inside.
    Raises 400 if start_date is after end_date, 404 if there's no data for the dates.
    """
    end_date = end_date or start_date
    requested = str(start_date) if start_date == end_date else f"{start_date} to {end_date}"
    if start_date > end_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"start_date {start_date} is after end_date {end_date}")

    first, last = call_database("read the data's date range", get_date_range, table=Tables.READINGS)
    if first is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "There is no data yet, upload a CSV first")
    if end_date < first or start_date > last:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No data for {requested}. The data covers {first} to {last}")

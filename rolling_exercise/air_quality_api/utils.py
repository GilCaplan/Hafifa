import logging
import re
from contextvars import ContextVar
from datetime import date
from pathlib import Path

import pandas as pd
import psycopg
from fastapi import HTTPException, status

from air_quality_api.const import (
    ALERT_AQI_THRESHOLD,
    AQI_COLUMN,
    AQI_LEVEL_COLUMN,
    CITY_COLUMN,
    CITY_NAME_PATTERN,
    CO2_COLUMN,
    CSV_EXTENSION,
    CSV_HEADER_LINES,
    DATE_COLUMN,
    DATE_FORMAT,
    LOG_FILE,
    LOG_FORMAT,
    LOG_LEVEL,
    LOG_LINE_PATTERN,
    MAX_CITY_NAME_LENGTH,
    MIN_POLLUTANT_VALUE,
    NO2_COLUMN,
    NO_REQUEST_ID,
    PM25_COLUMN,
    POLLUTANT_COLUMNS,
    READINGS_TABLE,
    REQUIRED_COLUMNS,
)
from air_quality_db.queries import count_rows, get_date_range
from calculate_aqi import calculate_aqi

logger = logging.getLogger(__name__)

LOG_LINE_REGEX = re.compile(LOG_LINE_PATTERN)
CITY_NAME_REGEX = re.compile(CITY_NAME_PATTERN)

# The id of the API request being handled. Set by the request middleware; each request runs in its own context.
request_id_var: ContextVar[str] = ContextVar("request_id", default=NO_REQUEST_ID)


class RequestIdFilter(logging.Filter):
    """Adds the current request id to every log record, so LOG_FORMAT can write it."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def setup_logging() -> None:
    logging.basicConfig(filename=LOG_FILE, level=LOG_LEVEL, format=LOG_FORMAT)
    for handler in logging.getLogger().handlers:
        handler.addFilter(RequestIdFilter())


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


def clean_city_name(city: str) -> str:
    """
    Trims the name and collapses repeated spaces, e.g. "  Tel   Aviv " -> "Tel Aviv".
    Raises ValueError, with a message for the user, if the name is empty, too long or has invalid characters.
    """
    cleaned = " ".join(city.split())
    if not cleaned:
        raise ValueError("City name is empty")
    if len(cleaned) > MAX_CITY_NAME_LENGTH:
        raise ValueError(f"City name is longer than {MAX_CITY_NAME_LENGTH} characters")
    if not CITY_NAME_REGEX.match(cleaned):
        raise ValueError(f"City name {cleaned!r} can only contain letters, spaces, hyphens and apostrophes")
    return cleaned


def run_query(action: str, query, **kwargs):
    """
    Runs a database query function. If the database can't be reached, logs it and returns a 503 to the user.
    `action` describes what was being done, for the log, e.g. "read alerts for Haifa".
    """
    try:
        return query(**kwargs)
    except psycopg.OperationalError as error:
        logger.error(f"Failed to {action}: database unavailable ({error})")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is unavailable, try again later"
        ) from error


def validate_city(city: str) -> str:
    """
    Cleans a city name from a request (see clean_city_name) and checks the city has readings.
    Returns the cleaned name. Logs and raises HTTPException 400 for a malformed name, 404 for an unknown city.
    """
    try:
        cleaned = clean_city_name(city)
    except ValueError as error:
        logger.warning(f"Rejected city {city!r}: {error}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    if run_query(f"look up city {cleaned}", count_rows, table=READINGS_TABLE, city=cleaned) == 0:
        logger.warning(f"Rejected city {cleaned}: no readings for this city")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No readings for city {cleaned}. Check the spelling: city names are case-sensitive",
        )
    return cleaned


def validate_dates(start_date: date, end_date: date | None = None) -> None:
    """
    Checks a requested date, or date range, against the dates the readings in the database cover.
    A range only has to overlap the data (e.g. a whole month around the uploaded days); a single date must fall in it.
    Logs and raises HTTPException 400 if start_date is after end_date, and 404 if there's no data for the dates.
    (The date format itself is checked by FastAPI, from the endpoint's `date` type hints.)
    """
    end_date = end_date or start_date
    requested = str(start_date) if start_date == end_date else f"{start_date} to {end_date}"
    if start_date > end_date:
        logger.warning(f"Rejected dates {requested}: start is after end")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"start_date {start_date} is after end_date {end_date}"
        )

    first, last = run_query("read the data's date range", get_date_range, table=READINGS_TABLE)
    if first is None:
        logger.warning(f"Rejected dates {requested}: the database has no readings yet")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="There is no data yet, upload a CSV first")
    if end_date < first or start_date > last:
        logger.warning(f"Rejected dates {requested}: outside the data, which covers {first} to {last}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No data for {requested}. The data covers {first} to {last}"
        )


def is_csv_file(filename: str | None) -> bool:
    return filename is not None and filename.lower().endswith(CSV_EXTENSION)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.strip().str.lower()
    return df


def get_missing_columns(df: pd.DataFrame) -> list[str]:
    return [column for column in REQUIRED_COLUMNS if column not in df.columns]


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Converts each column to its expected type. Values that can't be converted become NaN."""
    df = df.copy()
    df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], format=DATE_FORMAT, errors="coerce").dt.date
    df[CITY_COLUMN] = df[CITY_COLUMN].astype("string").str.strip().replace("", pd.NA)
    for column in POLLUTANT_COLUMNS:
        values = pd.to_numeric(df[column], errors="coerce")
        df[column] = values.where(values >= MIN_POLLUTANT_VALUE)
    return df


def split_valid_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Splits rows into (valid, invalid), where invalid rows have a missing or corrupted value."""
    is_invalid = df[REQUIRED_COLUMNS].isna().any(axis=1)
    return df[~is_invalid], df[is_invalid]


def get_csv_line_numbers(df: pd.DataFrame) -> list[int]:
    return [index + CSV_HEADER_LINES + 1 for index in df.index]


def add_aqi(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    results = [
        calculate_aqi(pm25, no2, co2)
        for pm25, no2, co2 in zip(df[PM25_COLUMN], df[NO2_COLUMN], df[CO2_COLUMN], strict=True)
    ]
    df[AQI_COLUMN] = [aqi for aqi, _ in results]
    df[AQI_LEVEL_COLUMN] = [level for _, level in results]
    return df


def get_alerts(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[df[AQI_COLUMN] > ALERT_AQI_THRESHOLD, [DATE_COLUMN, CITY_COLUMN, AQI_COLUMN]]

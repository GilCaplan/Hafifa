"""The CSV upload pipeline: reading and validating the file, cleaning its rows and calculating their AQI."""

import logging

import pandas as pd
from air_quality_api.const import (
    ALERT_AQI_THRESHOLD,
    AQI_COLUMN,
    AQI_COLUMNS,
    AQI_LEVEL_COLUMN,
    CITY_COLUMN,
    CSV_EXTENSION,
    CSV_HEADER_LINES,
    DATE_COLUMN,
    DATE_FORMAT,
    MIN_POLLUTANT_VALUE,
    POLLUTANT_COLUMNS,
    REQUIRED_COLUMNS,
)
from calculate_aqi import calculate_aqi
from fastapi import HTTPException, UploadFile, status

logger = logging.getLogger(__name__)


def upload_summary(
    filename: str | None,
    inserted_rows: int = 0,
    duplicate_rows: int = 0,
    skipped_rows: list[int] | None = None,
    alerts: int = 0,
    reason: str | None = None,
) -> dict:
    """The upload endpoint's response. `reason` is only included when given."""
    summary = {
        "filename": filename,
        "inserted_rows": inserted_rows,
        "duplicate_rows": duplicate_rows,
        "skipped_rows": skipped_rows or [],
        "alerts": alerts,
    }
    if reason:
        summary["reason"] = reason
    return summary


def is_csv_file(filename: str | None) -> bool:
    return filename is not None and filename.lower().endswith(CSV_EXTENSION)


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.strip().str.lower()
    return df


def get_missing_columns(df: pd.DataFrame) -> list[str]:
    return [column for column in REQUIRED_COLUMNS if column not in df.columns]


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Converts each column to its expected type. Invalid values become NaN."""
    df = df.copy()
    df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], format=DATE_FORMAT, errors="coerce").dt.date
    df[CITY_COLUMN] = df[CITY_COLUMN].astype("string").str.strip().replace("", pd.NA)
    for column in POLLUTANT_COLUMNS:
        values = pd.to_numeric(df[column], errors="coerce")
        df[column] = values.where(values >= MIN_POLLUTANT_VALUE)
    return df


def split_valid_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Splits rows into (valid, invalid). Invalid rows have a missing or invalid value."""
    is_invalid = df[REQUIRED_COLUMNS].isna().any(axis=1)
    return df[~is_invalid], df[is_invalid]


def get_csv_line_numbers(df: pd.DataFrame) -> list[int]:
    return [index + CSV_HEADER_LINES + 1 for index in df.index]


def add_aqi(df: pd.DataFrame) -> pd.DataFrame:
    results = [calculate_aqi(*row) for row in df[POLLUTANT_COLUMNS].itertuples(index=False)]

    df = df.copy()
    df[AQI_COLUMN] = [aqi for aqi, _ in results]
    df[AQI_LEVEL_COLUMN] = [level for _, level in results]
    return df


def get_alerts(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[df[AQI_COLUMN] > ALERT_AQI_THRESHOLD, AQI_COLUMNS]


def read_upload_csv(file: UploadFile) -> pd.DataFrame | None:
    """
    Reads an uploaded CSV and cleans its column names. Returns None if the file is empty.
    Raises 400 if it isn't a CSV, can't be parsed or is missing REQUIRED_COLUMNS.
    """
    filename = file.filename
    if not is_csv_file(filename):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{filename} is not a CSV file")

    try:
        df = clean_columns(pd.read_csv(file.file))
    except pd.errors.EmptyDataError:
        logger.warning(f"Skipped {filename}: file is empty")
        return None
    except (pd.errors.ParserError, UnicodeDecodeError) as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Could not parse {filename} as CSV ({error})") from error

    missing_columns = get_missing_columns(df)
    if missing_columns:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Missing columns: {missing_columns}. Expected columns: {REQUIRED_COLUMNS}"
        )
    return df


def prepare_readings(df: pd.DataFrame, filename: str | None) -> tuple[pd.DataFrame, pd.DataFrame, list[int]]:
    """
    Converts types, skips (and logs) invalid rows and adds the AQI.
    Returns (readings, alerts, skipped CSV line numbers).
    """
    valid_rows, invalid_rows = split_valid_rows(coerce_types(df[REQUIRED_COLUMNS]))

    skipped_lines = get_csv_line_numbers(invalid_rows)
    for line in skipped_lines:
        logger.warning(f"Skipped line {line} in {filename}: missing or invalid values")

    readings = add_aqi(valid_rows)
    alerts = get_alerts(readings)
    logger.info(f"Calculated AQI for {len(readings)} rows in {filename}, {len(alerts)} alerts")
    return readings, alerts, skipped_lines


def log_duplicates(duplicates: pd.DataFrame, filename: str | None) -> None:
    """Logs the CSV line of each reading skipped because it was already saved."""
    lines = get_csv_line_numbers(duplicates)
    for line, day, city in zip(lines, duplicates[DATE_COLUMN], duplicates[CITY_COLUMN], strict=True):
        logger.warning(f"Skipped line {line} in {filename}: {city} on {day} is already saved")

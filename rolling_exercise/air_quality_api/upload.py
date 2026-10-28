"""The CSV upload pipeline: reading and validating the file, cleaning its rows and calculating their AQI."""

import logging

import pandas as pd
from fastapi import HTTPException, UploadFile, status

from air_quality_api.const import Aqi, Columns, Validation
from calculate_aqi import calculate_aqi

logger = logging.getLogger(__name__)


def upload_summary(
    filename: str | None,
    inserted_rows: int = 0,
    duplicate_rows: int = 0,
    skipped_rows: list[int] | None = None,
    alerts: int = 0,
    reason: str | None = None,
) -> dict:
    """The upload endpoint's response. `reason` explains an upload that saved nothing, e.g. an empty file."""
    return {
        "filename": filename,
        "inserted_rows": inserted_rows,
        "duplicate_rows": duplicate_rows,
        "skipped_rows": skipped_rows or [],
        "alerts": alerts,
        "reason": reason,
    }


def is_csv_file(filename: str | None) -> bool:
    return filename is not None and filename.lower().endswith(Validation.CSV_EXTENSION)


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.strip().str.lower()
    return df


def get_missing_columns(df: pd.DataFrame) -> list[str]:
    missing_columns = [column for column in Columns.REQUIRED if column not in df.columns]
    return missing_columns


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Converts each column to its expected type. Invalid values become NaN."""
    df = df.copy()
    df[Columns.DATE] = pd.to_datetime(df[Columns.DATE], format=Validation.DATE_FORMAT, errors="coerce").dt.date
    # coerce where values aren't parsed become NaT (Not a Time)
    df[Columns.CITY] = df[Columns.CITY].astype("string").str.strip().replace("", pd.NA)
    for column in Columns.POLLUTANTS:
        values = pd.to_numeric(df[column], errors="coerce")
        df[column] = values.where(values >= Validation.MIN_POLLUTANT_VALUE)
    return df


def split_valid_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Splits rows into (valid, invalid). Invalid rows have a missing or invalid value."""
    is_invalid = df[Columns.REQUIRED].isna().any(axis=1)
    valid = ~is_invalid
    return df[valid], df[is_invalid]


def get_csv_line_numbers(df: pd.DataFrame) -> list[int]:
    return [index + Validation.CSV_HEADER_LINES + 1 for index in df.index]


def add_aqi(df: pd.DataFrame) -> pd.DataFrame:
    results = [calculate_aqi(*row) for row in df[Columns.POLLUTANTS].itertuples(index=False)]

    df = df.copy()
    df[Columns.AQI] = [aqi for aqi, _ in results]
    df[Columns.AQI_LEVEL] = [level for _, level in results]
    return df


def get_alerts(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[df[Columns.AQI] > Aqi.ALERT_THRESHOLD, Columns.ALERT]


def read_upload_csv(file: UploadFile) -> pd.DataFrame | None:
    """
    Reads an uploaded CSV and cleans its column names. Returns None if the file is empty.
    Raises 400 if it isn't a CSV, can't be parsed or is missing Columns.REQUIRED.
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
            status.HTTP_400_BAD_REQUEST, f"Missing columns: {missing_columns}. Expected columns: {Columns.REQUIRED}"
        )
    return df


def prepare_readings(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[int]]:
    """
    Converts types, skips invalid rows and adds the AQI.
    Returns (readings, alerts, skipped CSV line numbers).
    """
    valid_rows, invalid_rows = split_valid_rows(coerce_types(df[Columns.REQUIRED]))
    readings = add_aqi(valid_rows)
    return readings, get_alerts(readings), get_csv_line_numbers(invalid_rows)

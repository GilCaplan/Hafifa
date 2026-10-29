"""The CSV upload pipeline: reading and validating the file, cleaning its rows and calculating their AQI."""

import pandas as pd
from fastapi import UploadFile

from air_quality_api.const import AqiConsts, ColumnSets, Validation
from air_quality_api.errors import ValidationError
from air_quality_db.models import Reading
from calculate_aqi import calculate_aqi


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
    """Strips and lowercases the column names and drops dots, so "PM2.5" matches the database's "pm25"."""
    df.columns = df.columns.str.strip().str.lower().str.replace(".", "", regex=False)
    return df


def get_missing_columns(df: pd.DataFrame) -> list[str]:
    missing_columns = [column for column in ColumnSets.REQUIRED if column not in df.columns]
    return missing_columns


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Converts each column to its expected type. Invalid values become NaN."""
    df[Reading.date.key] = pd.to_datetime(df[Reading.date.key], format=Validation.DATE_FORMAT, errors="coerce").dt.date
    # coerce where values aren't parsed become NaT (Not a Time)
    df[Reading.city.key] = df[Reading.city.key].astype("string").str.strip().replace("", pd.NA)
    for column in ColumnSets.POLLUTANTS:
        values = pd.to_numeric(df[column], errors="coerce")
        df[column] = values.where(values >= Validation.MIN_POLLUTANT_VALUE)
    return df


def split_valid_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Splits rows into (valid, invalid). Invalid rows have a missing or invalid value."""
    is_invalid = df[ColumnSets.REQUIRED].isna().any(axis=1)
    valid = ~is_invalid
    return df[valid], df[is_invalid]


def get_csv_line_numbers(df: pd.DataFrame) -> list[int]:
    return [index + Validation.CSV_HEADER_LINES + 1 for index in df.index]


def add_aqi(df: pd.DataFrame) -> pd.DataFrame:
    results = [calculate_aqi(*row) for row in df[ColumnSets.POLLUTANTS].itertuples(index=False)]

    df = df.copy()
    df[Reading.aqi.key] = [aqi for aqi, _ in results]
    df[Reading.aqi_level.key] = [level for _, level in results]
    return df


def get_alerts(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[df[Reading.aqi.key] > AqiConsts.ALERT_THRESHOLD, ColumnSets.ALERT]


def read_upload_csv(file: UploadFile) -> pd.DataFrame | None:
    """
    Reads an uploaded CSV and cleans its column names. Returns None if the file is empty.
    Raises ValidationError if it isn't a CSV, can't be parsed, has two columns with the same cleaned name
    (e.g. "PM2.5" and "pm25") or is missing ColumnSets.REQUIRED.
    """
    filename = file.filename
    if not is_csv_file(filename):
        raise ValidationError(f"{filename} is not a CSV file")

    try:
        df = clean_columns(pd.read_csv(file.file))
    except pd.errors.EmptyDataError:
        return None
    except (pd.errors.ParserError, UnicodeDecodeError) as error:
        raise ValidationError(f"Could not parse {filename} as CSV ({error})") from error

    duplicate_columns = df.columns[df.columns.duplicated()].unique().tolist()
    if duplicate_columns:
        raise ValidationError(f"{filename} has the same column more than once: {duplicate_columns}")

    missing_columns = get_missing_columns(df)
    if missing_columns:
        raise ValidationError(f"Missing columns: {missing_columns}. Expected columns: {ColumnSets.REQUIRED}")
    return df


def prepare_readings(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Converts types, skips invalid rows and adds the AQI.
    Returns (readings, alerts, the invalid rows, with NaN where a value was missing or invalid).
    """
    valid_rows, invalid_rows = split_valid_rows(coerce_types(df[ColumnSets.REQUIRED]))
    readings = add_aqi(valid_rows)
    return readings, get_alerts(readings), invalid_rows

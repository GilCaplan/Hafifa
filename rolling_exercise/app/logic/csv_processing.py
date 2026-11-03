import pandas as pd
from fastapi import UploadFile

from app.core.constants import ColumnSets, Validation
from app.core.errors import ValidationError
from app.db.models import Reading


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strips and lowercases the column names and drops dots, so "PM2.5" matches the database's "pm25"."""
    df.columns = df.columns.str.strip().str.lower().str.replace(".", "", regex=False)
    return df


def find_invalid_values(df: pd.DataFrame) -> pd.DataFrame:
    """True where a value is missing or invalid. Leaves `df` unchanged."""
    pollutants = df[ColumnSets.POLLUTANTS].apply(pd.to_numeric, errors="coerce")
    dates = pd.to_datetime(df[Reading.date.key], format=Validation.DATE_FORMAT, errors="coerce")
    cities = df[Reading.city.key].astype("string")
    is_valid_city = cities.str.match(Validation.CITY_NAME_REGEX).fillna(False)

    invalid = pollutants.isna() | (pollutants < Validation.MIN_POLLUTANT_VALUE)
    invalid[Reading.date.key] = dates.isna()
    invalid[Reading.city.key] = ~is_valid_city | (cities.str.len() > Validation.MAX_CITY_NAME_LENGTH)
    return invalid[ColumnSets.REQUIRED]


def split_valid_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (valid rows, typed as dates and numbers; find_invalid_values for the invalid rows)."""
    df = df[ColumnSets.REQUIRED]
    invalid_values = find_invalid_values(df)
    is_invalid = invalid_values.any(axis=1)

    valid_rows = df[~is_invalid].astype(dict.fromkeys(ColumnSets.POLLUTANTS, float))
    valid_rows[Reading.date.key] = pd.to_datetime(valid_rows[Reading.date.key], format=Validation.DATE_FORMAT).dt.date
    return valid_rows, invalid_values[is_invalid]


def get_csv_line_numbers(df: pd.DataFrame) -> list[int]:
    return [index + Validation.CSV_HEADER_LINES + 1 for index in df.index]


def read_upload_csv(file: UploadFile) -> pd.DataFrame | None:
    """
    Returns None if the file is empty. Raises ValidationError if it can't be parsed as CSV or its columns, after
    cleaning, aren't exactly ColumnSets.REQUIRED (in any order).
    """
    filename = file.filename
    try:
        df = clean_columns(pd.read_csv(file.file))
    except pd.errors.EmptyDataError:
        return None
    except (pd.errors.ParserError, UnicodeDecodeError) as error:
        raise ValidationError(f"Could not parse {filename} as CSV ({error})") from error

    if sorted(df.columns) != sorted(ColumnSets.REQUIRED):
        raise ValidationError(f"{filename} has columns {df.columns.tolist()}, expected {ColumnSets.REQUIRED}")

    return df

import logging

import pandas as pd
from fastapi import UploadFile

from app.controllers.aqi import add_aqi, get_alerts
from app.controllers.csv_processing import get_csv_line_numbers, read_upload_csv, split_valid_rows
from app.db.models import Reading
from app.db.queries import save_readings_and_alerts
from app.schemas import UploadSummary

logger = logging.getLogger(__name__)


def handle_invalid_rows(df: pd.DataFrame, invalid_values: pd.DataFrame, filename: str | None) -> list[int]:
    """Logs each invalid row with its bad columns and raw values. Returns their CSV line numbers."""
    skipped_lines = get_csv_line_numbers(invalid_values)
    for line, (index, is_bad) in zip(skipped_lines, invalid_values.iterrows(), strict=True):
        bad_values = ", ".join(f"{column}={df.at[index, column]}" for column in is_bad[is_bad].index)
        logger.warning(f"Skipped line {line} in {filename}: missing or invalid {bad_values}")

    return skipped_lines


def handle_duplicates(duplicates: pd.DataFrame, filename: str | None) -> None:
    """Logs each reading skipped because its city and date were already saved."""
    lines = get_csv_line_numbers(duplicates)
    for line, day, city in zip(lines, duplicates[Reading.date.key], duplicates[Reading.city.key], strict=True):
        logger.warning(f"Skipped line {line} in {filename}: {city} on {day} is already saved")


def upload_air_quality_data(file: UploadFile) -> UploadSummary:
    filename = file.filename
    if (df := read_upload_csv(file)) is None:
        logger.warning(f"Skipped {filename}: file is empty")
        return UploadSummary(filename=filename, reason="file is empty")

    valid_rows, invalid_values = split_valid_rows(df)
    skipped_lines = handle_invalid_rows(df, invalid_values, filename)
    alerts = get_alerts(readings := add_aqi(valid_rows))
    logger.info(f"Calculated AQI for {len(readings)} rows in {filename}, {len(alerts)} alerts")
    duplicates, inserted_alerts = save_readings_and_alerts(readings, alerts)
    summary = UploadSummary(
        filename=filename,
        inserted_rows=len(readings) - len(duplicates),
        duplicate_rows=len(duplicates),
        skipped_rows=skipped_lines,
        alerts=inserted_alerts,
    )

    handle_duplicates(duplicates, filename)
    logger.info(
        f"Saved {summary.inserted_rows} rows and {inserted_alerts} alerts from {filename}, "
        f"{summary.duplicate_rows} duplicates skipped"
    )
    return summary

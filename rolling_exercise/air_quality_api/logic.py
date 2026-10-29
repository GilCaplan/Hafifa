"""
The API's logic: one function per endpoint, called by api.py (at the bottom).
Each endpoint function does its work first and logs at the end. The CSV upload pipeline is in csv_processing.py.
"""

import logging
from datetime import date

from fastapi import UploadFile

from air_quality_api.const import AqiConsts
from air_quality_api.csv_processing import get_csv_line_numbers, prepare_readings, read_upload_csv, upload_summary
from air_quality_api.logs import log_duplicates, log_prepared_readings
from air_quality_api.utils import validate_city, validate_dates
from air_quality_db.models import Alert, Reading
from air_quality_db.queries import fetch_rows, get_average_aqi, save_readings_and_alerts

logger = logging.getLogger(__name__)


def format_average_to_dict(city: str, average: float) -> dict:
    """A city's average AQI as the API returns it."""
    return {Reading.city.key: city, AqiConsts.AVERAGE_KEY: round(average, AqiConsts.AVERAGE_DECIMALS)}


# One function per endpoint, called by api.py


def upload_air_quality_data(file: UploadFile) -> dict:
    """Reads, cleans and saves an uploaded CSV. Returns the upload summary."""
    filename = file.filename
    df = read_upload_csv(file)
    if df is None:
        logger.warning(f"Skipped {filename}: file is empty")
        return upload_summary(filename, reason="file is empty")

    readings, alerts, invalid_rows = prepare_readings(df)
    skipped_lines = get_csv_line_numbers(invalid_rows)
    log_prepared_readings(invalid_rows, skipped_lines, readings, alerts, filename)
    duplicates, inserted_alerts = save_readings_and_alerts(readings, alerts)
    duplicate_lines = get_csv_line_numbers(duplicates)
    summary = upload_summary(
        filename,
        inserted_rows=len(readings) - len(duplicates),
        duplicate_rows=len(duplicates),
        skipped_rows=skipped_lines,
        alerts=inserted_alerts,
    )

    log_duplicates(duplicates, duplicate_lines, filename)
    logger.info(
        f"Saved {summary['inserted_rows']} rows and {inserted_alerts} alerts from {filename}, "
        f"{summary['duplicate_rows']} duplicates skipped"
    )
    return summary


def get_air_quality_data(start_date: date, end_date: date) -> list[dict]:
    validate_dates(start_date, end_date)
    readings = fetch_rows(Reading, start_date=start_date, end_date=end_date, sort=[Reading.date, Reading.city])

    logger.info(f"Found {len(readings)} readings from {start_date} to {end_date}")
    return readings


def get_air_quality_data_by_city(city: str) -> list[dict]:
    city = validate_city(city)
    readings = fetch_rows(Reading, city=city)

    logger.info(f"Found {len(readings)} readings for {city}")
    return readings


def get_city_aqi_history(city: str) -> list[dict]:
    city = validate_city(city)
    history = fetch_rows(Reading, [Reading.date, Reading.city, Reading.aqi, Reading.aqi_level], city, sort=Reading.date)

    logger.info(f"Found {len(history)} days of AQI history for {city}")
    return history


def get_city_aqi_average(city: str) -> dict:
    city = validate_city(city)
    averages = get_average_aqi([city])
    average = format_average_to_dict(city, averages[city]) if city in averages else {}

    logger.info(f"Average AQI for {city}: {average.get(AqiConsts.AVERAGE_KEY)}")
    return average


def get_best_cities() -> list[dict]:
    # The instructions don't define "best", so it's the lowest average AQI over all of a city's dates
    averages = sorted(
        (format_average_to_dict(city, average) for city, average in get_average_aqi().items()),
        key=lambda average: (average[AqiConsts.AVERAGE_KEY], average[Reading.city.key]),
    )
    best = averages[: AqiConsts.BEST_CITIES_COUNT]

    logger.info(f"Best cities: {', '.join(f'{row[Reading.city.key]} ({row[AqiConsts.AVERAGE_KEY]})' for row in best)}")
    return best


def get_all_alerts() -> list[dict]:
    alerts = fetch_rows(Alert)

    logger.info(f"Found {len(alerts)} alerts")
    return alerts


def get_alerts_by_date(alert_date: date) -> list[dict]:
    validate_dates(alert_date, alert_date)
    alerts = fetch_rows(Alert, start_date=alert_date, end_date=alert_date, sort=Alert.city)

    logger.info(f"Found {len(alerts)} alerts on {alert_date}")
    return alerts


def get_alerts_by_city(city: str) -> list[dict]:
    city = validate_city(city)
    alerts = fetch_rows(Alert, city=city, sort=Alert.date)

    logger.info(f"Found {len(alerts)} alerts for {city}")
    return alerts

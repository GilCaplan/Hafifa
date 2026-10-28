import logging
from datetime import date

from fastapi import FastAPI, File, Query, UploadFile

from air_quality_api.const import Aqi, Columns, Tables
from air_quality_api.handlers import register_handlers
from air_quality_api.logs import log_duplicates, log_prepared_readings, setup_logging
from air_quality_api.upload import prepare_readings, read_upload_csv, upload_summary
from air_quality_api.utils import validate_city, validate_dates
from air_quality_db.queries import fetch_rows, save_readings_and_alerts

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI()
register_handlers(app)  # logging and error responses around every request (see handlers.py)


@app.post("/air-quality/upload")
def upload_air_quality_data(file: UploadFile = File(...)):  # noqa: B008
    """
    Post - Uploads air quality data from a CSV file to database.
    Request Body: A multipart/form-data request containing a CSV file.
    """
    filename = file.filename
    logger.info(f"Received upload: {filename}")

    df = read_upload_csv(file)
    if df is None:
        return upload_summary(filename, reason="file is empty")

    readings, alerts, skipped_lines = prepare_readings(df)
    log_prepared_readings(skipped_lines, readings, alerts, filename)
    duplicates, inserted_alerts = save_readings_and_alerts(readings, alerts)
    log_duplicates(duplicates, filename)

    duplicate_rows = len(duplicates)
    inserted_rows = len(readings) - duplicate_rows
    logger.info(
        f"Saved {inserted_rows} rows and {inserted_alerts} alerts from {filename}, {duplicate_rows} duplicates skipped"
    )

    return upload_summary(
        filename,
        inserted_rows=inserted_rows,
        duplicate_rows=duplicate_rows,
        skipped_rows=skipped_lines,
        alerts=inserted_alerts,
    )


@app.get("/air-quality")
def get_air_quality_data(start_date: date, end_date: date):
    validate_dates(start_date, end_date)
    return fetch_rows(Tables.READINGS, start_date=start_date, end_date=end_date, sort=[Columns.DATE, Columns.CITY])


@app.get("/air-quality/city")
def get_air_quality_data_by_city(city: str):
    city = validate_city(city)
    return fetch_rows(Tables.READINGS, None, city)


@app.get("/aqi/history")
def get_city_aqi_history(city: str):
    city = validate_city(city)
    return fetch_rows(Tables.READINGS, Columns.AQI_HISTORY, city, sort=Columns.DATE)


@app.get("/aqi/average")
def get_city_aqi_average(city: str):
    city = validate_city(city)
    city_aqi_data = fetch_rows(Tables.READINGS, [Columns.AQI], city)
    aqi_values = [data_point[Columns.AQI] for data_point in city_aqi_data]

    if not aqi_values:
        logger.info(f"0 readings from the city {city} fetched")
        return None

    city_avg = sum(aqi_values) / len(aqi_values)
    return {Columns.CITY: city, Aqi.AVERAGE_KEY: round(city_avg, Aqi.AVERAGE_DECIMALS)}


@app.get("/aqi/best-cities")
def get_best_cities():
    # The instructions don't define "best", so it's the lowest average AQI over all of a city's dates
    rows = fetch_rows(Tables.READINGS, [Columns.CITY])
    cities = {row[Columns.CITY] for row in rows}

    city_aqi_averages = [get_city_aqi_average(city) for city in cities]
    city_aqi_averages.sort(key=lambda average: (average[Aqi.AVERAGE_KEY], average[Columns.CITY]))
    return city_aqi_averages[: Aqi.BEST_CITIES_COUNT]


@app.get("/alerts")
def get_all_alerts():
    return fetch_rows(Tables.ALERTS)


@app.get("/alerts/date")
def get_alerts_by_date(alert_date: date = Query(alias="date")):  # noqa: B008
    validate_dates(alert_date, alert_date)
    alerts = fetch_rows(Tables.ALERTS, start_date=alert_date, end_date=alert_date, sort=Columns.CITY)
    logger.info(f"Found {len(alerts)} alerts on {alert_date}")
    return alerts


@app.get("/alerts/city")
def get_alerts_by_city(city: str):
    city = validate_city(city)
    alerts = fetch_rows(Tables.ALERTS, city=city, sort=Columns.DATE)
    logger.info(f"Found {len(alerts)} alerts for {city}")
    return alerts

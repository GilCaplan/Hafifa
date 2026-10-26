import logging
import time
from datetime import date

from air_quality_api.const import (
    ALERTS_TABLE,
    AQI_COLUMN,
    AQI_LEVEL_COLUMNS,
    AVERAGE_AQI_DECIMALS,
    AVERAGE_AQI_KEY,
    BEST_CITIES_COUNT,
    CITY_COLUMN,
    DATE_COLUMN,
    READINGS_TABLE,
)
from air_quality_api.logs import (
    describe_validation_problem,
    log_request,
    setup_logging,
)
from air_quality_api.upload import (
    log_duplicates,
    prepare_readings,
    read_upload_csv,
    upload_summary,
)
from air_quality_api.utils import call_database, validate_city, validate_dates
from air_quality_db.queries import fetch_rows, save_readings
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI()


@app.middleware("http")
async def handle_api_call(request: Request, call_next):
    """Turns unhandled exceptions into a 500 and logs the call."""
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(f"Unexpected error on {request.method} {request.url.path}")
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Unexpected server error, see the logs for details"},
        )
    log_request(request, response.status_code, (time.perf_counter() - start) * 1000)
    return response


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, errors: RequestValidationError):
    """
    Logs invalid parameters, then returns FastAPI's 422 response.
    """
    problems = "; ".join(describe_validation_problem(error) for error in errors.errors())
    logger.warning(f"Invalid request to {request.url.path}: {problems}")
    return await request_validation_exception_handler(request, errors)


@app.exception_handler(HTTPException)
async def handle_http_error(request: Request, error: HTTPException):
    """Logs rejected requests (4xx), then returns FastAPI's usual error response."""
    if error.status_code < status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.warning(f"Rejected {request.url.path}: {error.detail}")
    return await http_exception_handler(request, error)


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

    readings, alerts, skipped_lines = prepare_readings(df, filename)
    duplicates, inserted_alerts = call_database(
        f"save {filename} to the database", save_readings, readings=readings, alerts=alerts
    )
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
    return fetch_rows(READINGS_TABLE, start_date=start_date, end_date=end_date, sort=[DATE_COLUMN, CITY_COLUMN])


@app.get("/air-quality/city")
def get_air_quality_data_by_city(city: str):
    city = validate_city(city)
    return fetch_rows(READINGS_TABLE, None, city)


@app.get("/aqi/history")
def get_city_aqi_history(city: str):
    city = validate_city(city)
    return fetch_rows(READINGS_TABLE, AQI_LEVEL_COLUMNS, city, sort=DATE_COLUMN)


@app.get("/aqi/average")
def get_city_aqi_average(city: str):
    city = validate_city(city)
    data = fetch_rows(READINGS_TABLE, [AQI_COLUMN], city)
    aqi_values = [data_point[AQI_COLUMN] for data_point in data]

    if not aqi_values:
        logger.info(f"0 readings from the city {city} fetched")
        return None

    city_avg = sum(aqi_values) / len(aqi_values)
    return {CITY_COLUMN: city, AVERAGE_AQI_KEY: round(city_avg, AVERAGE_AQI_DECIMALS)}


@app.get("/aqi/best-cities")
def get_best_cities():
    # The instructions don't define "best", so it's the lowest average AQI over all of a city's dates
    cities = {row[CITY_COLUMN] for row in fetch_rows(READINGS_TABLE, [CITY_COLUMN])}
    city_aqi_averages = [get_city_aqi_average(city) for city in cities]
    city_aqi_averages.sort(key=lambda average: (average[AVERAGE_AQI_KEY], average[CITY_COLUMN]))
    return city_aqi_averages[:BEST_CITIES_COUNT]


@app.get("/alerts")
def get_all_alerts():
    return fetch_rows(ALERTS_TABLE)


@app.get("/alerts/date")
def get_alerts_by_date(alert_date: date = Query(alias="date")):  # noqa: B008
    validate_dates(alert_date)
    alerts = call_database(
        f"read alerts for {alert_date}",
        fetch_rows,
        table=ALERTS_TABLE,
        start_date=alert_date,
        end_date=alert_date,
        sort=CITY_COLUMN,
    )
    logger.info(f"Found {len(alerts)} alerts on {alert_date}")
    return alerts


@app.get("/alerts/city")
def get_alerts_by_city(city: str):
    city = validate_city(city)
    alerts = call_database(f"read alerts for {city}", fetch_rows, table=ALERTS_TABLE, city=city, sort=DATE_COLUMN)
    logger.info(f"Found {len(alerts)} alerts for {city}")
    return alerts

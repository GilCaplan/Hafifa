import logging
import time
from datetime import date
from uuid import uuid4

import pandas as pd
import psycopg
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from air_quality_api.const import (
    ALERTS_TABLE,
    AQI_COLUMN,
    AQI_LEVEL_COLUMN,
    AVERAGE_AQI_DECIMALS,
    AVERAGE_AQI_KEY,
    BEST_CITIES_COUNT,
    BROWSABLE_TABLES,
    CITY_COLUMN,
    DATE_COLUMN,
    DEFAULT_LOG_LIMIT,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SORT_COLUMN,
    MAX_LOG_LIMIT,
    MAX_PAGE_SIZE,
    READINGS_TABLE,
    REQUEST_ID_HEADER,
    REQUEST_ID_LENGTH,
    REQUIRED_COLUMNS,
    UNLOGGED_ROUTES,
)
from air_quality_api.utils import (
    add_aqi,
    coerce_types,
    get_alerts,
    get_csv_line_numbers,
    get_missing_columns,
    is_csv_file,
    normalize_columns,
    read_log_entries,
    request_id_var,
    run_query,
    setup_logging,
    split_valid_rows,
    validate_city,
    validate_dates,
)
from air_quality_db.queries import count_rows, fetch_rows, save_readings

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI()


@app.middleware("http")
async def handle_api_call(request: Request, call_next):
    """
    Wraps every request:
    - gives it an id, written on all of its log lines and returned in the REQUEST_ID_HEADER response header;
    - logs any unhandled exception with its traceback and returns a clean 500;
    - logs the call with its status code (static files, docs and UNLOGGED_ROUTES are skipped).
    """
    request_id = uuid4().hex[:REQUEST_ID_LENGTH]
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    try:
        try:
            response = await call_next(request)
        except Exception as error:
            logger.exception(f"Unexpected error on {request.method} {request.url.path}: {error}")
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Unexpected server error, see the logs for details"},
            )

        route = request.scope.get("route")
        if isinstance(route, APIRoute) and route.path not in UNLOGGED_ROUTES:
            duration_ms = (time.perf_counter() - start) * 1000
            query = f"?{request.url.query}" if request.url.query else ""
            if response.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
                level = logging.ERROR
            elif response.status_code >= status.HTTP_400_BAD_REQUEST:
                level = logging.WARNING
            else:
                level = logging.INFO
            logger.log(
                level, f"{request.method} {request.url.path}{query} -> {response.status_code} ({duration_ms:.0f} ms)"
            )

        response.headers[REQUEST_ID_HEADER] = request_id
        return response
    finally:
        request_id_var.reset(token)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, error: RequestValidationError):
    """Logs invalid parameters (like a malformed date), then returns FastAPI's usual 422 response."""
    problems = "; ".join(f"{'.'.join(map(str, item['loc']))}: {item['msg']}" for item in error.errors())
    logger.warning(f"Invalid request to {request.url.path}: {problems}")
    return await request_validation_exception_handler(request, error)


@app.post("/air-quality/upload")
def upload_air_quality_data(file: UploadFile = File(...)):
    """
    POST upload air quality data
    Description: Uploads air quality data from a CSV file to the database.
    Request Body: A multipart/form-data request containing a CSV file.
    """
    filename = file.filename
    logger.info(f"Received upload: {filename}")

    if not is_csv_file(filename):
        logger.error(f"Rejected {filename}: not a CSV file")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{filename} is not a CSV file")

    try:
        df = pd.read_csv(file.file)
    except pd.errors.EmptyDataError:
        logger.warning(f"Skipped {filename}: file is empty")
        return {
            "filename": filename,
            "inserted_rows": 0,
            "duplicate_rows": 0,
            "skipped_rows": [],
            "alerts": 0,
            "reason": "file is empty",
        }
    except (pd.errors.ParserError, UnicodeDecodeError) as error:
        logger.error(f"Rejected {filename}: could not parse CSV ({error})")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not parse {filename} as CSV"
        ) from error

    df = normalize_columns(df)
    missing_columns = get_missing_columns(df)
    if missing_columns:
        logger.error(f"Rejected {filename}: missing columns {missing_columns}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing columns: {missing_columns}. Expected columns: {REQUIRED_COLUMNS}",
        )

    df = coerce_types(df[REQUIRED_COLUMNS])
    valid_rows, invalid_rows = split_valid_rows(df)

    skipped_lines = get_csv_line_numbers(invalid_rows)
    for line in skipped_lines:
        logger.warning(f"Skipped line {line} in {filename}: missing or invalid values")

    valid_rows = add_aqi(valid_rows)
    alerts = get_alerts(valid_rows)
    logger.info(f"Calculated AQI for {len(valid_rows)} rows in {filename}, {len(alerts)} alerts")

    try:
        inserted_rows, inserted_alerts = save_readings(valid_rows, alerts)
    except psycopg.OperationalError as error:
        logger.error(f"Failed to save {filename}: database unavailable ({error})")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is unavailable, try again later"
        ) from error
    except psycopg.Error as error:
        logger.error(f"Failed to save {filename}: database error ({error})")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not save {filename} to the database"
        ) from error

    duplicate_rows = len(valid_rows) - inserted_rows
    logger.info(
        f"Saved {inserted_rows} rows and {inserted_alerts} alerts from {filename}, {duplicate_rows} duplicates skipped"
    )

    return {
        "filename": filename,
        "inserted_rows": inserted_rows,
        "duplicate_rows": duplicate_rows,
        "skipped_rows": skipped_lines,
        "alerts": inserted_alerts,
    }


@app.get("/air-quality")
def get_air_quality_data(start_date: date, end_date: date):
    """
    GET air quality data
    Description: Retrieves air quality data for a specific date range, by date then city.
    Query Parameters:
        start_date: The start date in YYYY-MM-DD format.
        end_date: The end date in YYYY-MM-DD format.
    """
    validate_dates(start_date, end_date)
    return fetch_rows(READINGS_TABLE, start_date=start_date, end_date=end_date, sort=[DATE_COLUMN, CITY_COLUMN])


@app.get("/air-quality/city")
def get_air_quality_data_by_city(city: str):
    """
    GET air quality data by city
    Description: Retrieves air quality data for a specific city.
    Query Parameters:
        city: The name of the city.
    """
    city = validate_city(city)
    return fetch_rows(READINGS_TABLE, None, city)


@app.get("/aqi/history")
def get_city_aqi_history(city: str):
    """
    GET city aqi history
    Description: Retrieves the AQI history for a specific city.
    Query Parameters:
        city: The name of the city.
    """
    city = validate_city(city)
    columns = [DATE_COLUMN, CITY_COLUMN, AQI_COLUMN, AQI_LEVEL_COLUMN]
    return fetch_rows(READINGS_TABLE, columns, city, sort=DATE_COLUMN)


@app.get("/aqi/average")
def get_city_aqi_average(city: str):
    """
    GET city aqi average
    Description: Retrieves the AQI average for a specific city.
    Query Parameters:
        city: The name of the city.
    """
    city = validate_city(city)
    columns = [DATE_COLUMN, CITY_COLUMN, AQI_COLUMN]
    data = fetch_rows(READINGS_TABLE, columns, city)
    aqi_values = [data_point[AQI_COLUMN] for data_point in data]

    if not aqi_values:
        logger.info(f"0 readings from the city {city} fetched")
        return None

    city_avg = sum(aqi_values) / len(aqi_values)
    return {CITY_COLUMN: city, AVERAGE_AQI_KEY: round(city_avg, AVERAGE_AQI_DECIMALS)}


@app.get("/aqi/best-cities")
def get_best_cities():
    """
    GET best cities
    Description: Retrieves the 3 cities with the best air quality based on the AQI.
    The best cities will have the lowest AQI values.
    """
    # Comment: instructions don't explain the metrics for best air quality
    # There are multiple dates for each city
    cities = {row[CITY_COLUMN] for row in fetch_rows(READINGS_TABLE, [CITY_COLUMN])}
    city_aqi_averages = [get_city_aqi_average(city) for city in cities]
    city_aqi_averages.sort(key=lambda average: (average[AVERAGE_AQI_KEY], average[CITY_COLUMN]))
    return city_aqi_averages[:BEST_CITIES_COUNT]


@app.get("/alerts")
def get_all_alerts():
    """
    GET all alerts
    Description: Retrieves all alerts.
    """
    return fetch_rows(ALERTS_TABLE)


@app.get("/alerts/date")
def get_alerts_by_date(alert_date: date = Query(alias="date")):
    """
    GET all alerts by date
    Description: Retrieves all alerts from a specific date.
    Query Parameters:
        date: The date in YYYY-MM-DD format.
    """
    # The query parameter is called "date" (see alias); the variable isn't, so it doesn't hide the `date` type.
    validate_dates(alert_date)
    alerts = run_query(
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
    """
    GET all alerts by city
    Description: Retrieves all alerts for a specific city, oldest first.
    Query Parameters:
        city: The name of the city. Extra spaces are trimmed; empty or malformed names are rejected (400),
              and so are cities with no readings at all (404).
    """
    city = validate_city(city)
    alerts = run_query(f"read alerts for {city}", fetch_rows, table=ALERTS_TABLE, city=city, sort=DATE_COLUMN)
    logger.info(f"Found {len(alerts)} alerts for {city}")
    return alerts


@app.get("/logs")
def get_logs(limit: int = Query(DEFAULT_LOG_LIMIT, ge=1, le=MAX_LOG_LIMIT), request_id: str | None = None):
    """
    GET logs
    Description: Retrieves the most recent log entries, newest first. Used by the frontend.
    Query Parameters:
        limit: How many entries to return.
        request_id: Only entries written while handling this request (from the X-Request-ID response header).
    """
    return read_log_entries(limit, request_id)


@app.get("/tables/{table}")
def browse_table(
    table: str,
    city: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    sort: str = DEFAULT_SORT_COLUMN,
    descending: bool = True,
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
):
    """
    GET table rows
    Description: Retrieves one page of the readings or alerts table, for browsing in the frontend.
    Path Parameters:
        table: "readings" or "alerts".
    Query Parameters:
        city: Only rows whose city contains this text (case-insensitive).
        start_date, end_date: Only rows in this date range (YYYY-MM-DD, inclusive).
        sort: The column to sort by. descending: Sort direction.
        limit, offset: Page size and how many rows to skip.
    """
    if table not in BROWSABLE_TABLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown table {table}. Available tables: {list(BROWSABLE_TABLES)}",
        )
    columns = BROWSABLE_TABLES[table]["columns"]
    if sort not in columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot sort by {sort}. Columns: {columns}"
        )

    db_table = BROWSABLE_TABLES[table]["table"]
    try:
        rows = fetch_rows(
            db_table,
            columns=columns,
            city_contains=city,
            start_date=start_date,
            end_date=end_date,
            sort=sort,
            descending=descending,
            limit=limit,
            offset=offset,
        )
        total = count_rows(db_table, city_contains=city, start_date=start_date, end_date=end_date)
    except psycopg.OperationalError as error:
        logger.error(f"Failed to read {table}: database unavailable ({error})")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is unavailable, try again later"
        ) from error

    logger.info(f"Viewed {table}: {len(rows)} of {total} rows (city={city}, dates={start_date}..{end_date})")
    return {"columns": columns, "rows": rows, "total": total, "limit": limit, "offset": offset}

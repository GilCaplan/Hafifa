"""Logging setup, the access log for API calls, and the upload's log messages."""

import logging

import pandas as pd
from fastapi import Request, status
from fastapi.routing import APIRoute

from air_quality_api.const import Columns, settings
from air_quality_api.upload import get_csv_line_numbers

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=settings.log_file, level=settings.log_level, format=settings.log_format)


def get_request_log_level(status_code: int) -> int:
    """ERROR for 5xx responses, WARNING for 4xx, INFO for everything else."""
    if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        return logging.ERROR
    if status_code >= status.HTTP_400_BAD_REQUEST:
        return logging.WARNING
    return logging.INFO


def log_request(request: Request, status_code: int, duration_ms: float) -> None:
    """Logs a finished API call at its status code's level. Skips the docs and unknown paths."""
    if not isinstance(request.scope.get("route"), APIRoute):
        return
    url = request.url
    path = f"{url.path}?{url.query}" if url.query else url.path
    method = request.method
    message = f"{method} {path} -> {status_code} ({duration_ms:.0f} ms)"
    logger.log(get_request_log_level(status_code), message)


def describe_validation_problem(problem: dict) -> str:
    """Formats one FastAPI validation error as "location: message", e.g. "query.start_date: Field required"."""
    location = ".".join(str(part) for part in problem["loc"])  # loc can hold ints - indexes
    return f"{location}: {problem['msg']}"


def log_prepared_readings(
    skipped_lines: list[int], readings: pd.DataFrame, alerts: pd.DataFrame, filename: str | None
) -> None:
    """Logs each skipped CSV line, then how many readings and alerts are ready to save."""
    for line in skipped_lines:
        logger.warning(f"Skipped line {line} in {filename}: missing or invalid values")
    logger.info(f"Calculated AQI for {len(readings)} rows in {filename}, {len(alerts)} alerts")


def log_duplicates(duplicates: pd.DataFrame, filename: str | None) -> None:
    """Logs the CSV line of each reading skipped because it was already saved."""
    lines = get_csv_line_numbers(duplicates)
    for line, day, city in zip(lines, duplicates[Columns.DATE], duplicates[Columns.CITY], strict=True):
        logger.warning(f"Skipped line {line} in {filename}: {city} on {day} is already saved")

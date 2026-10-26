"""Logging setup and the access log for API calls."""

import logging

from air_quality_api.const import LOG_FILE, LOG_FORMAT, LOG_LEVEL
from fastapi import Request, status
from fastapi.routing import APIRoute

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=LOG_FILE, level=LOG_LEVEL, format=LOG_FORMAT)


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
    message = f"{request.method} {path} -> {status_code} ({duration_ms:.0f} ms)"
    logger.log(get_request_log_level(status_code), message)


def describe_validation_problem(problem: dict) -> str:
    """Formats one FastAPI validation error as "location: message", e.g. "query.start_date: Field required"."""
    location = ".".join(str(part) for part in problem["loc"])  # loc can hold ints (list indexes)
    return f"{location}: {problem['msg']}"

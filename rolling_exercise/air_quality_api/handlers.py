"""
Middleware and error handlers around each request
Each log calls and errors become responses.
"""

import logging
import time

from fastapi import FastAPI, Request, status
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from starlette.exceptions import HTTPException

from air_quality_api.errors import NotFoundError, ValidationError
from air_quality_api.logs import describe_validation_problem, log_request

logger = logging.getLogger(__name__)


async def handle_api_call(request: Request, handle_request):
    """Turns unhandled exceptions into a 500 and logs the call."""
    start = time.perf_counter()
    try:
        response = await handle_request(request)
    except Exception:
        logger.exception(f"Unexpected error on {request.method} {request.url.path}")
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Unexpected server error, see the logs for details"},
        )
    log_request(request, response.status_code, (time.perf_counter() - start) * 1000)
    return response


async def handle_validation_error(request: Request, errors: RequestValidationError):
    """Logs invalid parameters, then returns FastAPI's 422 response."""
    problems = "; ".join(describe_validation_problem(error) for error in errors.errors())
    logger.warning(f"Invalid request to {request.url.path}: {problems}")
    return await request_validation_exception_handler(request, errors)


async def handle_http_error(request: Request, error: HTTPException):
    """Logs rejected requests (4xx), then returns FastAPI's usual error response."""
    if error.status_code < status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.warning(f"Rejected {request.url.path}: {error.detail}")
    return await http_exception_handler(request, error)


async def handle_input_error(request: Request, error: ValidationError | NotFoundError) -> JSONResponse:
    """Logs a rejected input (see errors.py) and returns 400 for invalid input, 404 for no matching data."""
    logger.warning(f"Rejected {request.url.path}: {error}")
    status_code = status.HTTP_404_NOT_FOUND if isinstance(error, NotFoundError) else status.HTTP_400_BAD_REQUEST
    return JSONResponse(status_code=status_code, content={"detail": str(error)})


async def handle_database_unavailable(request: Request, error: OperationalError) -> JSONResponse:
    """The database can't be reached: logs it and returns 503, so the client knows to try again later."""
    logger.error(f"Database unavailable on {request.method} {request.url.path}: {error}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database is unavailable, try again later"},
    )


async def handle_database_error(request: Request, error: SQLAlchemyError) -> JSONResponse:
    """Any other database error: logs it and returns 500."""
    logger.error(f"Database error on {request.method} {request.url.path}: {error}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database error, see the logs for details"},
    )


def register_handlers(app: FastAPI) -> None:
    """Attaches the middleware and error handlers above to the app."""
    app.middleware("http")(handle_api_call)
    app.exception_handler(RequestValidationError)(handle_validation_error)
    app.exception_handler(HTTPException)(handle_http_error)
    app.exception_handler(ValidationError)(handle_input_error)
    app.exception_handler(NotFoundError)(handle_input_error)
    app.exception_handler(OperationalError)(handle_database_unavailable)
    app.exception_handler(SQLAlchemyError)(handle_database_error)

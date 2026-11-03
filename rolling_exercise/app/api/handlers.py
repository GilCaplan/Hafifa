import logging

from fastapi import FastAPI, Request, Response, status
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from starlette.exceptions import HTTPException

from app.core.errors import NotFoundError, ValidationError
from app.core.logs import RequestHandler, describe_validation_problem, log_request_time

logger = logging.getLogger(__name__)


@log_request_time
async def handle_api_call(request: Request, handle_request: RequestHandler) -> Response:
    """Turns unhandled exceptions into a 500."""
    try:
        return await handle_request(request)
    except Exception:
        logger.exception(f"Unexpected error on {request.method} {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Unexpected server error, see the logs for details"},
        )


async def handle_validation_error(request: Request, errors: RequestValidationError) -> JSONResponse:
    problems = "; ".join(describe_validation_problem(error) for error in errors.errors())
    logger.warning(f"Invalid request to {request.url.path}: {problems}")
    return await request_validation_exception_handler(request, errors)


async def handle_http_error(request: Request, error: HTTPException) -> Response:
    if error.status_code < status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.warning(f"Rejected {request.url.path}: {error.detail}")

    return await http_exception_handler(request, error)


async def handle_input_error(request: Request, error: ValidationError | NotFoundError) -> JSONResponse:
    logger.warning(f"Rejected {request.url.path}: {error}")
    status_code = status.HTTP_404_NOT_FOUND if isinstance(error, NotFoundError) else status.HTTP_400_BAD_REQUEST
    return JSONResponse(status_code=status_code, content={"detail": str(error)})


async def handle_database_unavailable(request: Request, error: OperationalError) -> JSONResponse:
    logger.error(f"Database unavailable on {request.method} {request.url.path}: {error}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database is unavailable, try again later"},
    )


async def handle_database_error(request: Request, error: SQLAlchemyError) -> JSONResponse:
    logger.error(f"Database error on {request.method} {request.url.path}: {error}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database error, see the logs for details"},
    )


def register_handlers(app: FastAPI) -> None:
    app.middleware("http")(handle_api_call)
    app.exception_handler(RequestValidationError)(handle_validation_error)
    app.exception_handler(HTTPException)(handle_http_error)
    app.exception_handler(ValidationError)(handle_input_error)
    app.exception_handler(NotFoundError)(handle_input_error)
    app.exception_handler(OperationalError)(handle_database_unavailable)
    app.exception_handler(SQLAlchemyError)(handle_database_error)

import logging
from collections.abc import Awaitable, Callable
from functools import wraps

from codetiming import Timer
from fastapi import Request, Response, status
from fastapi.routing import APIRoute

from app.core.config import settings
from app.core.constants import Consts

logger = logging.getLogger(__name__)

RequestHandler = Callable[[Request], Awaitable[Response]]
Middleware = Callable[[Request, RequestHandler], Awaitable[Response]]


def setup_logging() -> None:
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)
    # The file keeps every run; the terminal shows the current one. force: replace handlers already on the root
    # logger (pytest adds its own while it imports the tests), which would otherwise make basicConfig do nothing
    logging.basicConfig(
        level=settings.log_level,
        format=Consts.log_format,
        handlers=[logging.FileHandler(settings.log_file), logging.StreamHandler()],
        force=True,
    )


def log_request(request: Request, status_code: int, duration_ms: float) -> None:
    """Skips the docs and unknown paths, which have no APIRoute."""
    if not isinstance(request.scope.get("route"), APIRoute):
        return

    url = request.url
    path = f"{url.path}?{url.query}" if url.query else url.path
    message = f"{request.method} {path} -> {status_code} ({duration_ms:.0f} ms)"
    if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.error(message)
    elif status_code >= status.HTTP_400_BAD_REQUEST:
        logger.warning(message)
    else:
        logger.info(message)


def log_request_time(middleware: Middleware) -> Middleware:
    """Logs each API call with its status code and duration."""

    # A new Timer per call: @Timer itself can't time async functions and shares one Timer between concurrent requests
    @wraps(middleware)
    async def timed_middleware(request: Request, handle_request: RequestHandler) -> Response:
        with Timer(logger=None) as timer:
            response = await middleware(request, handle_request)

        log_request(request, response.status_code, timer.last * 1000)
        return response

    return timed_middleware


def describe_validation_problem(problem: dict) -> str:
    """Formats one FastAPI validation error, e.g. "query.start_date: Field required"."""
    location = ".".join(str(part) for part in problem["loc"])
    return f"{location}: {problem['msg']}"

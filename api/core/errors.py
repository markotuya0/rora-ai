"""Standard error envelope + exception handlers for api-design-reviewer compliance."""
import uuid
from datetime import datetime, timezone
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


def _envelope(code: str, message: str, status_code: int, details=None, request_id: str = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "requestId": request_id or f"req-{uuid.uuid4().hex[:12]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return _envelope(
        "VALIDATION_ERROR",
        "The request contains invalid parameters.",
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        [{"field": ".".join(str(x) for x in e.get("loc", [])), "code": e.get("type"), "message": e.get("msg")} for e in exc.errors()],
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "DB_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }
    detail = exc.detail
    if isinstance(detail, str) and detail.startswith("Unsafe SQL"):
        return _envelope("UNSAFE_SQL", detail, exc.status_code)
    if isinstance(detail, str) and "retry" in detail.lower():
        return _envelope("UNSAFE_SQL", detail, exc.status_code)
    return _envelope(code_map.get(exc.status_code, "INTERNAL_ERROR"), str(detail), exc.status_code)


async def generic_exception_handler(request: Request, exc: Exception):
    return _envelope("INTERNAL_ERROR", "An unexpected error occurred.", status.HTTP_500_INTERNAL_SERVER_ERROR)

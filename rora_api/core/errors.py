"""Fastapi exception handlers for the standard error envelope (api-design-reviewer)."""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from rora_api.core.envelope import envelope_body


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=envelope_body(
            "VALIDATION_ERROR",
            "The request contains invalid parameters.",
            details=[{"field": ".".join(str(x) for x in e.get("loc", [])), "code": e.get("type"), "message": e.get("msg")} for e in exc.errors()],
        ),
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
    if isinstance(detail, str) and "Unsafe SQL" in detail:
        return JSONResponse(status_code=exc.status_code, content=envelope_body("UNSAFE_SQL", detail))
    return JSONResponse(status_code=exc.status_code, content=envelope_body(code_map.get(exc.status_code, "INTERNAL_ERROR"), str(detail)), headers=getattr(exc, "headers", None))


async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=envelope_body("INTERNAL_ERROR", "An unexpected error occurred."))

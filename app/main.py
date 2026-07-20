from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import limiter, router
from app.config import settings
from app.middleware.gateway_auth import GatewayAuthMiddleware
from app.utils.log_helper import CentralLoggerMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("format_service")

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "Pure rule-based JSON / CSV / Text beautifier API. No AI/LLM inference "
        "is used — formatting is deterministic, powered by Python's stdlib "
        "json/csv/textwrap modules."
    ),
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(GatewayAuthMiddleware)
app.add_middleware(CentralLoggerMiddleware, service_name="csv-prettier")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False if settings.cors_origin_list == ["*"] else True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code, content={"error": str(detail), "code": "error"}
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error.", "code": "internal_error"},
    )


app.include_router(router, prefix="/api/v1")


@app.get("/", tags=["system"])
def root():
    return {
        "service": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
        "endpoints": [
            "/api/v1/format",
            "/api/v1/format/json",
            "/api/v1/format/csv",
            "/api/v1/format/text",
            "/api/v1/format/auto",
        ],
    }

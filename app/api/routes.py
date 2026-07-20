from __future__ import annotations

import logging
from typing import Optional, Union

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.models import FormatResponse, HealthResponse
from app.services import csv_formatter, format_detector, json_formatter, text_formatter
from app.utils.constants import CSV_OUTPUT_STYLES, MAX_JSON_INDENT
from app.utils.validators import InputValidationError, validate_and_decode

logger = logging.getLogger("format_service")

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


async def _resolve_input(file: Optional[UploadFile], raw_text: Optional[str]) -> tuple[bytes, Optional[str]]:
    """
    Accepts either a file upload OR a raw_text form field (not both empty).
    Returns (raw_bytes, filename).
    """
    if file is not None and file.filename:
        data = await file.read()
        return data, file.filename
    if raw_text is not None and raw_text != "":
        return raw_text.encode("utf-8"), None
    raise HTTPException(
        status_code=400,
        detail={"error": "Provide either a file upload or raw_text.", "code": "no_input_provided"},
    )


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", version=settings.version)


@router.post("/format/json", response_model=FormatResponse, tags=["format"])
@limiter.limit(settings.rate_limit)
async def format_json_endpoint(
    request: Request,
    file: Optional[UploadFile] = File(default=None),
    raw_text: Optional[str] = Form(default=None),
    indent: int = Form(default=2, ge=0, le=MAX_JSON_INDENT),
    sort_keys: bool = Form(default=False),
    minify: bool = Form(default=False),
) -> FormatResponse:
    data, filename = await _resolve_input(file, raw_text)
    try:
        text = validate_and_decode(data)
    except InputValidationError as exc:
        raise HTTPException(status_code=400, detail={"error": exc.message, "code": exc.code}) from exc

    result = json_formatter.format_json(text, indent=indent, sort_keys=sort_keys, minify=minify)
    if not result.is_valid:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Invalid JSON data: {result.error}", "code": "invalid_json"}
        )

    return FormatResponse(
        detected_format="json",
        is_valid=result.is_valid,
        formatted_content=result.formatted_content,
        error=result.error,
        stats=result.stats,
        filename=filename,
    )


@router.post("/format/csv", response_model=FormatResponse, tags=["format"])
@limiter.limit(settings.rate_limit)
async def format_csv_endpoint(
    request: Request,
    file: Optional[UploadFile] = File(default=None),
    raw_text: Optional[str] = Form(default=None),
    output_style: str = Form(default="aligned"),
    delimiter: Optional[str] = Form(default=None),
    has_header: bool = Form(default=True),
) -> FormatResponse:
    if output_style not in CSV_OUTPUT_STYLES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"output_style must be one of {sorted(CSV_OUTPUT_STYLES)}.",
                "code": "invalid_output_style",
            },
        )

    data, filename = await _resolve_input(file, raw_text)
    try:
        text = validate_and_decode(data)
    except InputValidationError as exc:
        raise HTTPException(status_code=400, detail={"error": exc.message, "code": exc.code}) from exc

    result = csv_formatter.format_csv(
        text, output_style=output_style, delimiter_override=delimiter, has_header=has_header
    )
    if not result.is_valid:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Invalid CSV data: {result.error}", "code": "invalid_csv"}
        )

    return FormatResponse(
        detected_format="csv",
        is_valid=result.is_valid,
        formatted_content=result.formatted_content,
        error=result.error,
        stats=result.stats,
        preview_records=result.preview_records or None,
        filename=filename,
    )


@router.post("/format/text", response_model=FormatResponse, tags=["format"])
@limiter.limit(settings.rate_limit)
async def format_text_endpoint(
    request: Request,
    file: Optional[UploadFile] = File(default=None),
    raw_text: Optional[str] = Form(default=None),
    wrap_width: Optional[int] = Form(default=None),
    max_consecutive_blank_lines: int = Form(default=1, ge=0),
    strip_trailing_whitespace: bool = Form(default=True),
    expand_tabs: bool = Form(default=True),
    tab_size: int = Form(default=4, ge=1, le=16),
) -> FormatResponse:
    data, filename = await _resolve_input(file, raw_text)
    try:
        text = validate_and_decode(data)
    except InputValidationError as exc:
        raise HTTPException(status_code=400, detail={"error": exc.message, "code": exc.code}) from exc

    result = text_formatter.format_text(
        text,
        wrap_width=wrap_width,
        max_consecutive_blank_lines=max_consecutive_blank_lines,
        strip_trailing_whitespace=strip_trailing_whitespace,
        expand_tabs=expand_tabs,
        tab_size=tab_size,
    )

    return FormatResponse(
        detected_format="text",
        is_valid=True,
        formatted_content=result.formatted_content,
        error=None,
        stats=result.stats,
        filename=filename,
    )


@router.post("/format/auto", response_model=FormatResponse, tags=["format"])
@limiter.limit(settings.rate_limit)
async def format_auto_endpoint(
    request: Request,
    file: Optional[UploadFile] = File(default=None),
    raw_text: Optional[str] = Form(default=None),
) -> FormatResponse:
    """
    Auto-detects JSON vs CSV vs plain text (from filename, then content
    sniffing) and applies that formatter with default options.
    """
    data, filename = await _resolve_input(file, raw_text)
    try:
        text = validate_and_decode(data)
    except InputValidationError as exc:
        raise HTTPException(status_code=400, detail={"error": exc.message, "code": exc.code}) from exc

    detected = format_detector.detect_format(text, filename)

    if detected == "json":
        result = json_formatter.format_json(text)
        if not result.is_valid:
            raise HTTPException(
                status_code=400,
                detail={"error": f"Invalid JSON data: {result.error}", "code": "invalid_json"}
            )
        return FormatResponse(
            detected_format="json",
            is_valid=result.is_valid,
            formatted_content=result.formatted_content,
            error=result.error,
            stats=result.stats,
            filename=filename,
        )
    if detected == "csv":
        result = csv_formatter.format_csv(text)
        if not result.is_valid:
            raise HTTPException(
                status_code=400,
                detail={"error": f"Invalid CSV data: {result.error}", "code": "invalid_csv"}
            )
        return FormatResponse(
            detected_format="csv",
            is_valid=result.is_valid,
            formatted_content=result.formatted_content,
            error=result.error,
            stats=result.stats,
            preview_records=result.preview_records or None,
            filename=filename,
        )

    result = text_formatter.format_text(text)
    return FormatResponse(
        detected_format="text",
        is_valid=True,
        formatted_content=result.formatted_content,
        error=None,
        stats=result.stats,
        filename=filename,
    )


@router.post("/format", response_model=FormatResponse, tags=["format"])
@limiter.limit(settings.rate_limit)
async def format_unified_endpoint(
    request: Request,
    file: Optional[UploadFile] = File(default=None),
    raw_text: Optional[str] = Form(default=None),
    format: str = Form(default="auto"),
    # JSON options
    indent: int = Form(default=2, ge=0, le=MAX_JSON_INDENT),
    sort_keys: bool = Form(default=False),
    minify: bool = Form(default=False),
    # CSV options
    output_style: str = Form(default="aligned"),
    delimiter: Optional[str] = Form(default=None),
    has_header: bool = Form(default=True),
    # Text options
    wrap_width: Optional[int] = Form(default=None),
    max_consecutive_blank_lines: int = Form(default=1, ge=0),
    strip_trailing_whitespace: bool = Form(default=True),
    expand_tabs: bool = Form(default=True),
    tab_size: int = Form(default=4, ge=1, le=16),
) -> FormatResponse:
    """
    Unified endpoint that formats JSON, CSV, or Text data.
    Accepts format options: "json", "csv", "text", "auto".
    """
    fmt = format.lower().strip()
    valid_formats = {"auto", "json", "csv", "text"}
    if fmt not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Invalid format option. Must be one of {sorted(valid_formats)}.",
                "code": "invalid_format_option",
            },
        )

    data, filename = await _resolve_input(file, raw_text)
    try:
        text = validate_and_decode(data)
    except InputValidationError as exc:
        raise HTTPException(status_code=400, detail={"error": exc.message, "code": exc.code}) from exc

    if fmt == "auto":
        fmt = format_detector.detect_format(text, filename)

    if fmt == "json":
        result = json_formatter.format_json(text, indent=indent, sort_keys=sort_keys, minify=minify)
        if not result.is_valid:
            raise HTTPException(
                status_code=400,
                detail={"error": f"Invalid JSON data: {result.error}", "code": "invalid_json"}
            )
        return FormatResponse(
            detected_format="json",
            is_valid=result.is_valid,
            formatted_content=result.formatted_content,
            error=result.error,
            stats=result.stats,
            filename=filename,
        )
    elif fmt == "csv":
        if output_style not in CSV_OUTPUT_STYLES:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"output_style must be one of {sorted(CSV_OUTPUT_STYLES)}.",
                    "code": "invalid_output_style",
                },
            )
        result = csv_formatter.format_csv(
            text, output_style=output_style, delimiter_override=delimiter, has_header=has_header
        )
        if not result.is_valid:
            raise HTTPException(
                status_code=400,
                detail={"error": f"Invalid CSV data: {result.error}", "code": "invalid_csv"}
            )
        return FormatResponse(
            detected_format="csv",
            is_valid=result.is_valid,
            formatted_content=result.formatted_content,
            error=result.error,
            stats=result.stats,
            preview_records=result.preview_records or None,
            filename=filename,
        )
    else:  # text
        result = text_formatter.format_text(
            text,
            wrap_width=wrap_width,
            max_consecutive_blank_lines=max_consecutive_blank_lines,
            strip_trailing_whitespace=strip_trailing_whitespace,
            expand_tabs=expand_tabs,
            tab_size=tab_size,
        )
        return FormatResponse(
            detected_format="text",
            is_valid=True,
            formatted_content=result.formatted_content,
            error=None,
            stats=result.stats,
            filename=filename,
        )


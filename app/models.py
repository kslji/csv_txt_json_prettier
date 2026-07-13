from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class JsonErrorDetail(BaseModel):
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    position: Optional[int] = None


class FormatResponse(BaseModel):
    detected_format: str
    is_valid: bool
    formatted_content: Optional[str] = None
    error: Optional[dict] = None
    stats: dict = Field(default_factory=dict)
    preview_records: Optional[list[dict]] = None
    filename: Optional[str] = None



class ErrorResponse(BaseModel):
    error: str
    code: str


class HealthResponse(BaseModel):
    status: str
    version: str

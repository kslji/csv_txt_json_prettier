"""
Pure-code JSON formatter. Uses Python's stdlib `json` module only —
no AI. Parses, validates, pretty-prints (or minifies), and reports
structural stats plus precise error locations on invalid JSON.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class JsonFormatResult:
    is_valid: bool
    formatted_content: str | None
    error: dict | None
    stats: dict = field(default_factory=dict)


def _line_col_from_pos(text: str, pos: int) -> tuple[int, int]:
    line = text.count("\n", 0, pos) + 1
    last_newline = text.rfind("\n", 0, pos)
    col = pos - last_newline if last_newline != -1 else pos + 1
    return line, col


def _compute_stats(obj) -> dict:
    key_count = 0
    array_count = 0
    max_depth = 0

    def walk(node, depth):
        nonlocal key_count, array_count, max_depth
        max_depth = max(max_depth, depth)
        if isinstance(node, dict):
            key_count += len(node)
            for v in node.values():
                walk(v, depth + 1)
        elif isinstance(node, list):
            array_count += 1
            for item in node:
                walk(item, depth + 1)

    walk(obj, 1)
    root_type = "object" if isinstance(obj, dict) else "array" if isinstance(obj, list) else type(obj).__name__

    return {
        "root_type": root_type,
        "max_depth": max_depth,
        "total_keys": key_count,
        "total_arrays": array_count,
    }


def format_json(
    raw_text: str,
    indent: int = 2,
    sort_keys: bool = False,
    minify: bool = False,
) -> JsonFormatResult:
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        line, col = _line_col_from_pos(raw_text, exc.pos)
        return JsonFormatResult(
            is_valid=False,
            formatted_content=None,
            error={
                "message": exc.msg,
                "line": line,
                "column": col,
                "position": exc.pos,
            },
        )

    if minify:
        formatted = json.dumps(
            parsed, sort_keys=sort_keys, ensure_ascii=False, separators=(",", ":")
        )
    else:
        formatted = json.dumps(
            parsed, indent=indent, sort_keys=sort_keys, ensure_ascii=False
        )

    stats = _compute_stats(parsed)
    stats["original_size_bytes"] = len(raw_text.encode("utf-8"))
    stats["formatted_size_bytes"] = len(formatted.encode("utf-8"))

    return JsonFormatResult(
        is_valid=True, formatted_content=formatted, error=None, stats=stats
    )

"""
Pure-code plain-text formatter. Uses Python's stdlib `textwrap`/`re` only.
Normalizes line endings, trims trailing whitespace, collapses excess blank
lines, expands tabs, and optionally word-wraps to a target width.
"""
from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field


@dataclass
class TextFormatResult:
    formatted_content: str
    stats: dict = field(default_factory=dict)


def format_text(
    raw_text: str,
    wrap_width: int | None = None,
    max_consecutive_blank_lines: int = 1,
    strip_trailing_whitespace: bool = True,
    expand_tabs: bool = True,
    tab_size: int = 4,
    trim_document: bool = True,
) -> TextFormatResult:
    text = raw_text

    # Normalize all line-ending variants to \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    if expand_tabs:
        text = text.expandtabs(tab_size)

    lines = text.split("\n")

    if strip_trailing_whitespace:
        lines = [line.rstrip() for line in lines]

    if wrap_width and wrap_width > 0:
        wrapped_lines = []
        for line in lines:
            if line.strip() == "":
                wrapped_lines.append("")
                continue
            wrapped = textwrap.wrap(
                line, width=wrap_width, break_long_words=False, break_on_hyphens=False
            )
            wrapped_lines.extend(wrapped if wrapped else [""])
        lines = wrapped_lines

    # Collapse runs of blank lines beyond the allowed maximum
    collapsed_lines: list[str] = []
    blank_run = 0
    for line in lines:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= max_consecutive_blank_lines:
                collapsed_lines.append("")
        else:
            blank_run = 0
            collapsed_lines.append(line)

    formatted = "\n".join(collapsed_lines)

    if trim_document:
        formatted = formatted.strip("\n") + "\n" if formatted.strip() else ""

    word_count = len(re.findall(r"\S+", raw_text))
    stats = {
        "original_line_count": raw_text.count("\n") + (1 if raw_text else 0),
        "formatted_line_count": formatted.count("\n") + (1 if formatted else 0),
        "word_count": word_count,
        "original_size_bytes": len(raw_text.encode("utf-8")),
        "formatted_size_bytes": len(formatted.encode("utf-8")),
    }

    return TextFormatResult(formatted_content=formatted, stats=stats)

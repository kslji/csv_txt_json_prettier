"""
Pure-code CSV formatter. Uses Python's stdlib `csv` module only — no AI.
Detects delimiter, validates row/column consistency, and renders output
in one of three human-readable styles.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from app.utils.constants import (
    CSV_SNIFFER_SAMPLE_SIZE,
    FALLBACK_DELIMITERS,
    MAX_CSV_PREVIEW_RECORDS,
)


@dataclass
class CsvFormatResult:
    is_valid: bool
    formatted_content: str | None
    error: dict | None
    stats: dict = field(default_factory=dict)
    preview_records: list[dict] = field(default_factory=list)


def _detect_delimiter(sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="".join(FALLBACK_DELIMITERS))
        return dialect.delimiter
    except csv.Error:
        # Fallback: count occurrences of each candidate delimiter on the
        # first line and pick the most frequent one.
        first_line = sample.splitlines()[0] if sample.splitlines() else ""
        counts = {d: first_line.count(d) for d in FALLBACK_DELIMITERS}
        best = max(counts, key=counts.get)
        return best if counts[best] > 0 else ","


def _strip_cells(rows: list[list[str]]) -> list[list[str]]:
    return [[str(cell).strip() for cell in row] for row in rows]


def _render_aligned(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    rows = _strip_cells(rows)
    col_count = max(len(r) for r in rows)
    padded_rows = [r + [""] * (col_count - len(r)) for r in rows]
    col_widths = [
        max(len(str(row[i])) for row in padded_rows) for i in range(col_count)
    ]
    lines = []
    for idx, row in enumerate(padded_rows):
        cells = [str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)]
        lines.append("  ".join(cells).rstrip())
        if idx == 0:
            separator = "  ".join("-" * col_widths[i] for i in range(col_count))
            lines.append(separator)
    return "\n".join(lines)


def _render_markdown(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    rows = _strip_cells(rows)
    col_count = max(len(r) for r in rows)
    padded_rows = [r + [""] * (col_count - len(r)) for r in rows]
    header, *body = padded_rows
    lines = ["| " + " | ".join(str(c) for c in header) + " |"]
    lines.append("| " + " | ".join(["---"] * col_count) + " |")
    for row in body:
        # Escape pipe characters so they don't break the markdown table
        safe_row = [str(c).replace("|", "\\|") for c in row]
        lines.append("| " + " | ".join(safe_row) + " |")
    return "\n".join(lines)


def _render_clean_csv(rows: list[list[str]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    for row in rows:
        writer.writerow([str(cell).strip() for cell in row])
    return output.getvalue()


def format_csv(
    raw_text: str,
    output_style: str = "aligned",
    delimiter_override: str | None = None,
    has_header: bool = True,
) -> CsvFormatResult:
    stripped = raw_text.strip("\ufeff\n\r ")
    if not stripped:
        return CsvFormatResult(
            is_valid=False,
            formatted_content=None,
            error={"message": "CSV content is empty after trimming whitespace."},
        )

    delimiter = delimiter_override or _detect_delimiter(
        stripped[:CSV_SNIFFER_SAMPLE_SIZE]
    )

    try:
        reader = csv.reader(io.StringIO(stripped), delimiter=delimiter)
        rows = [row for row in reader if row]
    except csv.Error as exc:
        return CsvFormatResult(
            is_valid=False,
            formatted_content=None,
            error={"message": f"Could not parse CSV: {exc}"},
        )

    if not rows:
        return CsvFormatResult(
            is_valid=False,
            formatted_content=None,
            error={"message": "No data rows found in CSV content."},
        )

    header_row = rows[0]
    expected_cols = len(header_row)
    mismatched_rows = [
        i for i, row in enumerate(rows[1:], start=2) if len(row) != expected_cols
    ]
    duplicate_headers = [
        h for h in set(header_row) if header_row.count(h) > 1
    ] if has_header else []
    empty_cells = sum(1 for row in rows for cell in row if cell.strip() == "")

    if output_style == "markdown":
        formatted = _render_markdown(rows)
    elif output_style == "clean_csv":
        formatted = _render_clean_csv(rows)
    else:
        formatted = _render_aligned(rows)

    preview_records = []
    if has_header:
        clean_header = [h.strip() for h in header_row]
        for row in rows[1 : 1 + MAX_CSV_PREVIEW_RECORDS]:
            padded = row + [""] * (expected_cols - len(row))
            clean_row = [c.strip() for c in padded[:expected_cols]]
            preview_records.append(dict(zip(clean_header, clean_row)))

    stats = {
        "delimiter_detected": delimiter,
        "row_count": len(rows) - (1 if has_header else 0),
        "column_count": expected_cols,
        "mismatched_rows": mismatched_rows,
        "duplicate_headers": duplicate_headers,
        "empty_cell_count": empty_cells,
        "output_style": output_style,
    }

    warnings = []
    if mismatched_rows:
        warnings.append(
            f"{len(mismatched_rows)} row(s) have a different column count than the header "
            f"(rows: {mismatched_rows[:10]}{'...' if len(mismatched_rows) > 10 else ''})."
        )
    if duplicate_headers:
        warnings.append(f"Duplicate column header(s) detected: {duplicate_headers}.")
    stats["warnings"] = warnings

    return CsvFormatResult(
        is_valid=True,
        formatted_content=formatted,
        error=None,
        stats=stats,
        preview_records=preview_records,
    )

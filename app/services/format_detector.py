"""
Pure heuristic format auto-detector — no AI. Uses filename extension when
available, then falls back to content sniffing (JSON parse attempt, then
CSV delimiter/row consistency check).
"""
from __future__ import annotations

import csv
import io
import json


def detect_from_filename(filename: str | None) -> str | None:
    if not filename:
        return None
    lowered = filename.lower()
    if lowered.endswith(".json"):
        return "json"
    if lowered.endswith(".csv") or lowered.endswith(".tsv"):
        return "csv"
    if lowered.endswith(".txt"):
        return "text"
    return None


def detect_from_content(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return "text"

    # Try JSON first — cheapest, most unambiguous signal
    if stripped[0] in "{[":
        try:
            json.loads(stripped)
            return "json"
        except json.JSONDecodeError:
            pass

    # CSV heuristic: at least 2 lines, consistent delimiter count across lines
    lines = [ln for ln in stripped.splitlines() if ln.strip()][:10]
    if len(lines) >= 2:
        for delimiter in (",", "\t", ";", "|"):
            counts = [line.count(delimiter) for line in lines]
            if counts[0] > 0 and len(set(counts)) == 1:
                try:
                    list(csv.reader(io.StringIO(stripped), delimiter=delimiter))
                    return "csv"
                except csv.Error:
                    continue

    return "text"


def detect_format(text: str, filename: str | None = None) -> str:
    by_filename = detect_from_filename(filename)
    if by_filename:
        return by_filename
    return detect_from_content(text)

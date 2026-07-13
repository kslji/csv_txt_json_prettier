"""
Static configuration for the formatter service. No AI/ML — just limits
and default option values used by the deterministic formatters.
"""

MAX_INPUT_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB of raw text/json/csv content

# JSON defaults
DEFAULT_JSON_INDENT = 2
MAX_JSON_INDENT = 8

# CSV defaults
DEFAULT_CSV_OUTPUT_STYLE = "aligned"  # aligned | markdown | clean_csv
CSV_OUTPUT_STYLES = {"aligned", "markdown", "clean_csv"}
CSV_SNIFFER_SAMPLE_SIZE = 4096
FALLBACK_DELIMITERS = [",", "\t", ";", "|"]
MAX_CSV_PREVIEW_RECORDS = 20

# Text defaults
DEFAULT_MAX_CONSECUTIVE_BLANK_LINES = 1
DEFAULT_TAB_SIZE = 4

SUPPORTED_FORMATS = {"json", "csv", "text"}

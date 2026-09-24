"""YAML ↔ JSON ↔ CSV ↔ NDJSON transforms for pipelines and shell use."""

from .convert import convert, detect_format, infer_format, parse, serialize
from .csv_io import escape_csv_field, parse_csv, parse_csv_rows, stringify_csv
from .shape import (
    filter_rows,
    get_path,
    omit_keys,
    pick_keys,
    sort_rows,
    unique_rows,
)

__all__ = [
    "convert",
    "detect_format",
    "infer_format",
    "parse",
    "serialize",
    "parse_csv",
    "parse_csv_rows",
    "stringify_csv",
    "escape_csv_field",
    "get_path",
    "pick_keys",
    "omit_keys",
    "filter_rows",
    "sort_rows",
    "unique_rows",
]

__version__ = "0.3.0"

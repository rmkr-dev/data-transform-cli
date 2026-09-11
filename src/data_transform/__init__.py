"""YAML ↔ JSON ↔ CSV transforms for pipelines and shell use."""

from .convert import convert, detect_format, infer_format, parse, serialize
from .csv_io import escape_csv_field, parse_csv, parse_csv_rows, stringify_csv

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
]

__version__ = "0.1.0"

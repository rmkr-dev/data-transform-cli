"""YAML ↔ JSON ↔ CSV ↔ NDJSON transforms for pipelines and shell use."""

from .convert import convert, detect_format, infer_format, parse, serialize
from .csv_io import escape_csv_field, parse_csv, parse_csv_rows, stringify_csv
from .shape import (
    filter_rows,
    flatten_object,
    get_path,
    head_rows,
    omit_keys,
    pick_keys,
    rename_keys,
    sort_rows,
    tail_rows,
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
    "rename_keys",
    "flatten_object",
    "filter_rows",
    "sort_rows",
    "unique_rows",
    "head_rows",
    "tail_rows",
]

__version__ = "0.4.0"

"""YAML ↔ JSON ↔ CSV ↔ NDJSON transforms for pipelines and shell use."""

from .convert import convert, detect_format, infer_format, parse, serialize
from .csv_io import escape_csv_field, parse_csv, parse_csv_rows, stringify_csv
from .shape import (
    count_rows,
    filter_rows,
    flatten_object,
    get_path,
    group_rows,
    head_rows,
    omit_keys,
    pick_keys,
    rename_keys,
    sort_rows,
    tail_rows,
    unflatten_object,
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
    "unflatten_object",
    "filter_rows",
    "sort_rows",
    "unique_rows",
    "head_rows",
    "tail_rows",
    "group_rows",
    "count_rows",
]

__version__ = "0.5.0"

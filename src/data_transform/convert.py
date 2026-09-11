"""Format detection, parse, serialize, and convert helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

import yaml

from .csv_io import parse_csv, stringify_csv

FormatName = Literal["json", "yaml", "csv"]


def detect_format(filename: str | None) -> FormatName | None:
    """Detect format from filename extension."""
    if not filename:
        return None
    lower = str(filename).lower()
    # Support bare names and paths.
    name = Path(lower).name
    if name.endswith(".json"):
        return "json"
    if name.endswith(".yaml") or name.endswith(".yml"):
        return "yaml"
    if name.endswith(".csv"):
        return "csv"
    return None


def parse(text: str, format: FormatName) -> Any:
    """Parse input text as the given format."""
    if format == "json":
        return json.loads(text)
    if format == "yaml":
        return yaml.safe_load(text)
    if format == "csv":
        return parse_csv(text)
    raise ValueError(f"Unsupported parse format: {format}")


def serialize(
    data: Any,
    format: FormatName,
    *,
    pretty: bool | None = None,
    minify: bool = False,
) -> str:
    """Serialize data to the given format."""
    if format == "json":
        if minify:
            return json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        space = 0 if pretty is False else 2
        body = json.dumps(data, indent=space or None, ensure_ascii=False)
        if space:
            return body + "\n"
        return body
    if format == "yaml":
        return yaml.safe_dump(
            data,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=10**9,
        )
    if format == "csv":
        if not isinstance(data, list):
            raise ValueError("CSV output requires an array (of objects or rows)")
        return stringify_csv(data)
    raise ValueError(f"Unsupported serialize format: {format}")


def convert(
    text: str,
    from_format: FormatName,
    to_format: FormatName,
    *,
    pretty: bool | None = None,
    minify: bool = False,
) -> str:
    """Convert between formats."""
    data = parse(text, from_format)
    return serialize(data, to_format, pretty=pretty, minify=minify)


def infer_format(text: str) -> FormatName:
    """Infer source format from content heuristics when extension is unknown."""
    trimmed = text.lstrip()
    if not trimmed:
        return "json"
    if trimmed[0] in "{[":
        try:
            json.loads(text)
            return "json"
        except json.JSONDecodeError:
            pass
    first_line = trimmed.splitlines()[0] if trimmed else ""
    if (
        "," in first_line
        and not trimmed.startswith("---")
        and not re.search(r":\s", first_line)
    ):
        return "csv"
    return "yaml"

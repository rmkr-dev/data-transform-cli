"""CSV parse/stringify helpers built on the stdlib csv module (RFC 4180-ish)."""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Mapping, Sequence


def escape_csv_field(value: Any) -> str:
    """Escape a single CSV field (mirrors Node escapeCsvField behavior)."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    else:
        text = str(value)
    if any(ch in text for ch in '",\r\n'):
        return '"' + text.replace('"', '""') + '"'
    return text


def parse_csv_rows(text: str) -> list[list[str]]:
    """Parse CSV into raw rows (lists of strings)."""
    raw = str(text).lstrip("\ufeff")
    if raw == "":
        return []
    reader = csv.reader(io.StringIO(raw), lineterminator="\n")
    rows = [list(row) for row in reader]
    # Drop a single trailing empty row produced by a final newline (parity with Node).
    if rows and len(rows[-1]) == 1 and rows[-1][0] == "" and (
        text.endswith("\n") or text.endswith("\r")
    ):
        # csv.reader usually does not produce this; keep defensive parity.
        rows.pop()
    return rows


def parse_csv(text: str, *, no_header: bool = False) -> list[dict[str, str]] | list[list[str]]:
    """
    Parse a CSV string into an array of row objects (header row required)
    or an array of arrays if no_header is True.
    """
    rows = parse_csv_rows(text)
    if not rows:
        return []
    if no_header:
        return rows
    headers = [h.strip() for h in rows[0]]
    result: list[dict[str, str]] = []
    for cells in rows[1:]:
        obj: dict[str, str] = {}
        for i, header in enumerate(headers):
            obj[header] = cells[i] if i < len(cells) else ""
        result.append(obj)
    return result


def stringify_csv(
    data: Sequence[Any],
    *,
    headers: Sequence[str] | None = None,
) -> str:
    """
    Stringify data to CSV.
    Accepts a sequence of mappings (uses union of keys as header) or a sequence of sequences.
    """
    if not isinstance(data, Sequence) or isinstance(data, (str, bytes)):
        raise TypeError("CSV output requires an array (of objects or rows)")

    if len(data) == 0:
        if headers:
            return ",".join(escape_csv_field(h) for h in headers) + "\n"
        return ""

    first = data[0]
    is_objects = isinstance(first, Mapping)

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)

    if is_objects:
        if headers is None:
            key_order: dict[str, None] = {}
            for row in data:
                if row is None:
                    continue
                for key in row.keys():
                    key_order.setdefault(str(key), None)
            hdrs = list(key_order.keys())
        else:
            hdrs = list(headers)
        writer.writerow(hdrs)
        for row in data:
            mapping = row if isinstance(row, Mapping) else {}
            writer.writerow(
                [
                    _cell_for_writer(mapping.get(h) if mapping is not None else None)
                    for h in hdrs
                ]
            )
        return buf.getvalue()

    for row in data:
        cells = list(row) if isinstance(row, Sequence) and not isinstance(row, (str, bytes)) else [row]
        writer.writerow([_cell_for_writer(c) for c in cells])
    return buf.getvalue()


def _cell_for_writer(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    return str(value)

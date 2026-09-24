"""Path extraction and object key shaping helpers."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

FILTER_OPS = frozenset({"eq", "ne", "gt", "ge", "lt", "le", "contains", "exists"})


def _parse_path(path: str) -> list[str | int]:
    """Split a dotted path into segments; raise ValueError on invalid syntax."""
    if not isinstance(path, str) or path == "":
        raise ValueError(f"Invalid path: {path!r}")
    parts = path.split(".")
    if any(p == "" for p in parts):
        raise ValueError(f"Invalid path: {path!r}")
    segments: list[str | int] = []
    for part in parts:
        if part.isdigit():
            segments.append(int(part))
        else:
            # Reject leading-minus negatives.
            if part.startswith("-") and part[1:].isdigit():
                raise ValueError(f"Invalid path segment (negative index): {part!r}")
            segments.append(part)
    return segments


def get_path(data: Any, path: str) -> Any:
    """
    Resolve a dotted path against data.

    Integer segments index lists. Missing keys/indices return None.
    Invalid path syntax raises ValueError.
    """
    segments = _parse_path(path)
    current: Any = data
    for seg in segments:
        if isinstance(seg, int):
            if not isinstance(current, Sequence) or isinstance(current, (str, bytes)):
                return None
            if seg < 0 or seg >= len(current):
                return None
            current = current[seg]
        else:
            if not isinstance(current, Mapping):
                return None
            if seg not in current:
                return None
            current = current[seg]
    return current


def pick_keys(data: Any, keys: Sequence[str]) -> Any:
    """
    Keep only listed top-level keys from an object, or from each object in a list.

    Non-mapping items in a list are left unchanged. A non-mapping, non-list
    root is returned unchanged.
    """
    key_list = list(keys)
    if isinstance(data, list):
        return [_pick_one(item, key_list) for item in data]
    return _pick_one(data, key_list)


def omit_keys(data: Any, keys: Sequence[str]) -> Any:
    """
    Drop listed top-level keys from an object, or from each object in a list.

    Non-mapping items in a list are left unchanged. A non-mapping, non-list
    root is returned unchanged.
    """
    drop = set(keys)
    if isinstance(data, list):
        return [_omit_one(item, drop) for item in data]
    return _omit_one(data, drop)


def _pick_one(item: Any, keys: Sequence[str]) -> Any:
    if not isinstance(item, Mapping):
        return item
    return {k: item[k] for k in keys if k in item}


def _omit_one(item: Any, drop: set[str]) -> Any:
    if not isinstance(item, Mapping):
        return item
    return {k: v for k, v in item.items() if k not in drop}


def _require_list(data: Any, command: str) -> list[Any]:
    """Raise ValueError unless data is a list; return it typed."""
    if not isinstance(data, list):
        raise ValueError(
            f"{command}: root must be a list (array), got {type(data).__name__}"
        )
    return data


def _looks_number(value: Any) -> bool:
    """True when value is an int/float (not bool) or a numeric string."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            float(value)
            return True
        except ValueError:
            return False
    return False


def _as_number(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return float(str(value))


def _compare(left: Any, op: str, right: Any) -> bool:
    """Compare left to right with op; numeric when both look like numbers."""
    if op == "exists":
        return left is not None

    if op == "contains":
        return str(right) in str(left) if left is not None else False

    use_numeric = _looks_number(left) and _looks_number(right)
    if use_numeric:
        lv: Any = _as_number(left)
        rv: Any = _as_number(right)
    else:
        lv = "" if left is None else str(left)
        rv = "" if right is None else str(right)

    if op == "eq":
        return lv == rv
    if op == "ne":
        return lv != rv
    if op == "gt":
        return lv > rv
    if op == "ge":
        return lv >= rv
    if op == "lt":
        return lv < rv
    if op == "le":
        return lv <= rv
    raise ValueError(
        f"Unsupported filter operator: {op!r} "
        "(use eq, ne, gt, ge, lt, le, contains, exists)"
    )


def filter_rows(data: Any, key: str, op: str, value: Any = None) -> list[Any]:
    """
    Keep objects where top-level KEY compares via OP to VALUE.

    Root must be a list. Non-object items are dropped. For ``exists``, VALUE
    is ignored and the key must be present and not null.
    """
    rows = _require_list(data, "filter")
    op_norm = op.lower()
    if op_norm not in FILTER_OPS:
        raise ValueError(
            f"Unsupported filter operator: {op!r} "
            "(use eq, ne, gt, ge, lt, le, contains, exists)"
        )

    out: list[Any] = []
    for item in rows:
        if not isinstance(item, Mapping):
            continue
        if op_norm == "exists":
            if key in item and item[key] is not None:
                out.append(item)
            continue
        if key not in item:
            continue
        if _compare(item[key], op_norm, value):
            out.append(item)
    return out


def sort_rows(data: Any, key: str, *, desc: bool = False) -> list[Any]:
    """
    Sort an array of objects by top-level KEY.

    Missing keys sort last (first when ``desc``). Non-object items are treated
    as missing the key. Uses a None sentinel so ordering is stable-ish via
    Python's ``sorted``.
    """
    rows = _require_list(data, "sort")

    def sort_key(item: Any) -> tuple[int, int, float, str]:
        # (missing, non_numeric, number, text) — always comparable across types.
        if not isinstance(item, Mapping) or key not in item or item[key] is None:
            # Missing / null: sort last for ascending, first for descending.
            return (1, 1, 0.0, "")
        val = item[key]
        if _looks_number(val):
            return (0, 0, _as_number(val), "")
        return (0, 1, 0.0, str(val))

    return sorted(rows, key=sort_key, reverse=desc)


def unique_rows(data: Any, key: str | None = None) -> list[Any]:
    """
    Deduplicate an array. First occurrence wins (order-preserving).

    With KEY, dedupe by that top-level key (non-objects / missing key each keep
    their own slot). Without KEY, dedupe by JSON-serialized item.
    """
    rows = _require_list(data, "unique")
    seen: set[Any] = set()
    out: list[Any] = []

    if key is None:
        for item in rows:
            try:
                marker = json.dumps(item, sort_keys=True, default=str)
            except (TypeError, ValueError):
                marker = repr(item)
            if marker in seen:
                continue
            seen.add(marker)
            out.append(item)
        return out

    for item in rows:
        if isinstance(item, Mapping) and key in item:
            marker: Any = (
                "k",
                json.dumps(item[key], sort_keys=True, default=str),
            )
        else:
            # Non-object or missing key: keep each occurrence (unique by position).
            marker = ("i", id(item), len(out))
        if marker in seen:
            continue
        seen.add(marker)
        out.append(item)
    return out

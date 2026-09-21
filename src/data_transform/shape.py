"""Path extraction and object key shaping helpers."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


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

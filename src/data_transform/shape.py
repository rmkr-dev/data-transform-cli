"""Path extraction, key shaping, and list slicing helpers."""

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


def rename_keys(data: Any, mapping: Mapping[str, str]) -> Any:
    """
    Rename top-level keys on an object, or on each object in a list.

    Non-mapping items in a list are left unchanged. A non-mapping, non-list
    root is returned unchanged. Keys absent from ``mapping`` are kept (missing
    OLD keys are no-ops). Renames apply in one pass over the original keys, so
    a key is not renamed again after it is written. When two original keys
    produce the same new name, the later key wins.
    """
    if not isinstance(mapping, Mapping):
        raise ValueError("rename: expected a mapping of old keys to new keys")
    pairs = dict(mapping)
    if isinstance(data, list):
        return [_rename_one(item, pairs) for item in data]
    return _rename_one(data, pairs)


def _rename_one(item: Any, mapping: Mapping[Any, Any]) -> Any:
    if not isinstance(item, Mapping):
        return item
    renamed: dict[Any, Any] = {}
    for key, value in item.items():
        new_key = mapping[key] if key in mapping else key
        renamed[new_key] = value
    return renamed


def flatten_object(data: Any, sep: str = ".") -> Any:
    """
    Flatten nested mappings into ``sep``-joined top-level keys.

    A list root is mapped item-wise; non-mapping items are left unchanged.
    Nested lists are kept as values and are not expanded into indexed keys.
    Empty mappings are left as values. A non-mapping, non-list root is
    returned unchanged. An empty separator raises ValueError. When two paths
    collide, the later value wins.
    """
    if not isinstance(sep, str) or sep == "":
        raise ValueError("flatten: separator must be a non-empty string")
    if isinstance(data, list):
        return [_flatten_one(item, sep) for item in data]
    return _flatten_one(data, sep)


def _flatten_one(item: Any, sep: str) -> Any:
    if not isinstance(item, Mapping):
        return item
    flat: dict[str, Any] = {}
    _flatten_mapping(item, sep, "", flat)
    return flat


def _flatten_mapping(
    mapping: Mapping[Any, Any], sep: str, prefix: str, out: dict[str, Any]
) -> None:
    for key, value in mapping.items():
        name = key if isinstance(key, str) else str(key)
        path = f"{prefix}{sep}{name}" if prefix else name
        if isinstance(value, Mapping) and value:
            _flatten_mapping(value, sep, path, out)
        else:
            out[path] = value


def unflatten_object(data: Any, sep: str = ".") -> Any:
    """
    Expand ``sep``-joined top-level keys back into nested mappings.

    The inverse of :func:`flatten_object`. A list root is mapped item-wise;
    non-mapping items are left unchanged. A non-mapping, non-list root is
    returned unchanged. Only top-level string keys are split; values are kept
    as-is, and no list indices are created (segments such as ``"0"`` stay
    string keys). Keys are split literally, so empty segments become empty
    keys. Object values merge with branches built from joined keys; when a
    path collides with a non-object value, the later key wins. An empty
    separator raises ValueError.
    """
    if not isinstance(sep, str) or sep == "":
        raise ValueError("unflatten: separator must be a non-empty string")
    if isinstance(data, list):
        return [_unflatten_one(item, sep) for item in data]
    return _unflatten_one(data, sep)


def _unflatten_one(item: Any, sep: str) -> Any:
    if not isinstance(item, Mapping):
        return item
    nested: dict[Any, Any] = {}
    for key, value in item.items():
        parts = key.split(sep) if isinstance(key, str) else [key]
        current = nested
        for part in parts[:-1]:
            child = current.get(part)
            if not isinstance(child, dict):
                # Missing or a non-object value: the later key wins.
                child = {}
                current[part] = child
            current = child
        _merge_value(current, parts[-1], value)
    return nested


def _merge_value(target: dict[Any, Any], key: Any, value: Any) -> None:
    """Set target[key]; objects merge into an existing object branch."""
    if isinstance(value, Mapping):
        branch = target.get(key)
        if not isinstance(branch, dict):
            branch = {}
            target[key] = branch
        # Copy object values so later keys never mutate the input.
        for sub_key, sub_value in value.items():
            _merge_value(branch, sub_key, sub_value)
    else:
        target[key] = value


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


def _group_label(value: Any) -> str:
    """Turn a group value into an object key: strings as-is, else compact JSON."""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        return str(value)


def group_rows(data: Any, key: str) -> dict[str, list[Any]]:
    """
    Group an array of objects by top-level KEY.

    Returns an object mapping each group label to the list of items in that
    group. Groups keep first-seen order and items keep input order. Labels
    are the value itself for strings and compact JSON otherwise (``1`` →
    ``"1"``, ``true`` → ``"true"``, ``null`` → ``"null"``), so ``1`` and
    ``"1"`` share a group. Non-object items and objects without KEY are
    dropped. Root must be a list.
    """
    return _group(_require_list(data, "group-by"), key)


def _group(rows: list[Any], key: str) -> dict[str, list[Any]]:
    groups: dict[str, list[Any]] = {}
    for item in rows:
        if not isinstance(item, Mapping) or key not in item:
            continue
        groups.setdefault(_group_label(item[key]), []).append(item)
    return groups


def _is_grouped(data: Any) -> bool:
    """True for a mapping whose values are all lists (``group-by`` output)."""
    return isinstance(data, Mapping) and all(
        isinstance(v, list) for v in data.values()
    )


def count_rows(data: Any, key: str | None = None) -> int | dict[str, int]:
    """
    Count records.

    Without KEY, a list root returns its length, and an object whose values
    are all lists (the output of :func:`group_rows`) returns the length of
    each list under the same group label. With KEY, a list root returns an
    object of per-value counts using the same labels and dropping rules as
    :func:`group_rows`. Any other root raises ValueError.
    """
    if key is None:
        if isinstance(data, list):
            return len(data)
        if _is_grouped(data):
            return {str(label): len(items) for label, items in data.items()}
        raise ValueError(
            "count: root must be a list (array) or an object of lists "
            f"(group-by output), got {type(data).__name__}"
        )
    rows = _require_list(data, "count")
    return {label: len(items) for label, items in _group(rows, key).items()}


def _require_count(n: Any, command: str) -> int:
    """Raise ValueError unless n is a non-negative integer (not bool)."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError(f"{command}: N must be a non-negative integer, got {n!r}")
    return n


def head_rows(data: Any, n: int) -> list[Any]:
    """
    Return the first ``n`` items of a list root.

    ``n`` must be a non-negative integer. Counts larger than the list return
    the whole list. ``n == 0`` returns an empty list.
    """
    rows = _require_list(data, "head")
    count = _require_count(n, "head")
    return rows[:count]


def tail_rows(data: Any, n: int) -> list[Any]:
    """
    Return the last ``n`` items of a list root.

    ``n`` must be a non-negative integer. Counts larger than the list return
    the whole list. ``n == 0`` returns an empty list.
    """
    rows = _require_list(data, "tail")
    count = _require_count(n, "tail")
    # rows[-0:] returns the whole list, so zero is handled on its own.
    if count == 0:
        return []
    return rows[-count:]

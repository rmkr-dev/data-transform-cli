"""Record validation: required paths, value types, and unique keys."""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Sequence

from .shape import _group_label, _parse_path

TYPE_NAMES = ("string", "integer", "number", "boolean", "object", "array", "null")

_INT_RE = re.compile(r"^[+-]?\d+$")
_NUM_RE = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")

_MISSING = object()


def _resolve(data: Any, path: str) -> Any:
    """Resolve a dotted path, returning _MISSING (not None) when absent."""
    current: Any = data
    for seg in _parse_path(path):
        if isinstance(seg, int):
            if not isinstance(current, list) or seg >= len(current):
                return _MISSING
            current = current[seg]
        else:
            if not isinstance(current, Mapping) or seg not in current:
                return _MISSING
            current = current[seg]
    return current


def parse_type_spec(spec: str) -> list[str]:
    """Split a type spec like ``string|null`` into known type names."""
    names = [part.strip().lower() for part in spec.split("|")]
    if not names or any(name == "" for name in names):
        raise ValueError(f"Invalid type spec: {spec!r}")
    unknown = [name for name in names if name not in TYPE_NAMES]
    if unknown:
        raise ValueError(
            f"Unknown type {unknown[0]!r}; expected one of: {', '.join(TYPE_NAMES)}"
        )
    return names


def parse_type_option(option: str) -> tuple[str, list[str]]:
    """Parse a ``PATH=TYPE[|TYPE...]`` CLI option."""
    path, sep, spec = option.partition("=")
    if not sep or not path:
        raise ValueError(f"--type expects PATH=TYPE, got {option!r}")
    _parse_path(path)
    return path, parse_type_spec(spec)


def type_of(value: Any, *, coerce: bool = False) -> set[str]:
    """Return every type name a value satisfies.

    With ``coerce``, strings that look like integers, numbers, or booleans
    (``true`` / ``false``, any case) also satisfy those types, and an empty
    string satisfies ``null``. This suits CSV, where every cell is a string.
    """
    if value is None:
        return {"null"}
    if isinstance(value, bool):
        return {"boolean"}
    if isinstance(value, int):
        return {"integer", "number"}
    if isinstance(value, float):
        return {"number"}
    if isinstance(value, Mapping):
        return {"object"}
    if isinstance(value, list):
        return {"array"}
    if isinstance(value, str):
        found = {"string"}
        if coerce:
            text = value.strip()
            if text == "":
                found.add("null")
            elif _INT_RE.match(text):
                found.update({"integer", "number"})
            elif _NUM_RE.match(text):
                found.add("number")
            elif text.lower() in ("true", "false"):
                found.add("boolean")
        return found
    return {type(value).__name__}


def _describe(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, Mapping):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    return type(value).__name__


def load_schema(schema: Any) -> tuple[list[str], dict[str, list[str]], list[str]]:
    """Read ``required``, ``types``, and ``unique`` from a parsed schema document."""
    if not isinstance(schema, Mapping):
        raise ValueError("schema must be an object with required / types / unique")
    unknown = set(schema) - {"required", "types", "unique"}
    if unknown:
        raise ValueError(f"schema: unknown key {sorted(unknown)[0]!r}")

    required = schema.get("required", []) or []
    unique = schema.get("unique", []) or []
    types = schema.get("types", {}) or {}
    for name, value in (("required", required), ("unique", unique)):
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ValueError(f"schema: {name} must be a list of paths")
    if not isinstance(types, Mapping):
        raise ValueError("schema: types must map PATH to TYPE")

    parsed_types: dict[str, list[str]] = {}
    for path, spec in types.items():
        if isinstance(spec, list):
            spec = "|".join(str(item) for item in spec)
        if not isinstance(path, str) or not isinstance(spec, str):
            raise ValueError("schema: types must map PATH to TYPE")
        _parse_path(path)
        parsed_types[path] = parse_type_spec(spec)
    for path in [*required, *unique]:
        _parse_path(path)
    return list(required), parsed_types, list(unique)


def validate_rows(
    data: Any,
    *,
    required: Sequence[str] = (),
    types: Mapping[str, Sequence[str]] | None = None,
    unique: Sequence[str] = (),
    coerce: bool = False,
    max_errors: int | None = None,
) -> dict[str, Any]:
    """Validate a list of records (or a single object) and return a report.

    - ``required`` paths must be present (``null`` counts as present).
    - ``types`` maps a path to allowed type names; absent paths are skipped,
      so combine with ``required`` to demand both.
    - ``unique`` paths must not repeat across records (absent values
      skipped). Values compare like ``group-by`` labels, so ``1`` and
      ``"1"`` count as the same value.

    The report is ``{"valid", "records", "error_count", "errors"}``; each
    error has ``record`` (list index, or ``None`` for an object root),
    ``path``, and ``message``. ``max_errors`` caps the listed errors, not
    ``error_count``.
    """
    type_map = {path: [t.lower() for t in names] for path, names in (types or {}).items()}
    for names in type_map.values():
        for name in names:
            if name not in TYPE_NAMES:
                raise ValueError(f"Unknown type {name!r}")
    for path in [*required, *type_map, *unique]:
        _parse_path(path)
    if max_errors is not None and max_errors < 0:
        raise ValueError("max_errors must be a non-negative integer")

    if isinstance(data, list):
        records: Iterable[tuple[int | None, Any]] = enumerate(data)
        total = len(data)
    elif isinstance(data, Mapping):
        records = [(None, data)]
        total = 1
    else:
        raise ValueError("validate: root must be a list of objects or an object")

    errors: list[dict[str, Any]] = []
    error_count = 0

    def add(record: int | None, path: str | None, message: str) -> None:
        nonlocal error_count
        error_count += 1
        if max_errors is None or len(errors) < max_errors:
            errors.append({"record": record, "path": path, "message": message})

    seen: dict[str, dict[str, int | None]] = {path: {} for path in unique}

    for index, item in records:
        if not isinstance(item, Mapping):
            add(index, None, f"record is {_describe(item)}, not an object")
            continue
        for path in required:
            if _resolve(item, path) is _MISSING:
                add(index, path, "missing required value")
        for path, allowed in type_map.items():
            value = _resolve(item, path)
            if value is _MISSING:
                continue
            if not type_of(value, coerce=coerce) & set(allowed):
                add(
                    index,
                    path,
                    f"expected {'|'.join(allowed)}, got {_describe(value)}",
                )
        for path in unique:
            value = _resolve(item, path)
            if value is _MISSING:
                continue
            label = _group_label(value)
            first = seen[path].get(label, _MISSING)
            if first is _MISSING:
                seen[path][label] = index
            else:
                where = "an earlier record" if first is None else f"record {first}"
                add(index, path, f"duplicate value {label!r} (first seen in {where})")

    return {
        "valid": error_count == 0,
        "records": total,
        "error_count": error_count,
        "errors": errors,
    }

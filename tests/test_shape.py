import pytest

from data_transform.shape import (
    filter_rows,
    get_path,
    omit_keys,
    pick_keys,
    sort_rows,
    unique_rows,
)


def test_get_path_nested_object():
    data = {"user": {"name": "Ada", "age": 36}}
    assert get_path(data, "user.name") == "Ada"
    assert get_path(data, "user.age") == 36


def test_get_path_list_index():
    data = {"items": [{"id": 1}, {"id": 2}]}
    assert get_path(data, "items.0.id") == 1
    assert get_path(data, "items.1.id") == 2


def test_get_path_missing_returns_none():
    data = {"a": 1}
    assert get_path(data, "b") is None
    assert get_path(data, "a.x") is None
    assert get_path([1, 2], "5") is None


def test_get_path_invalid_syntax():
    with pytest.raises(ValueError, match="Invalid path"):
        get_path({}, "")
    with pytest.raises(ValueError, match="Invalid path"):
        get_path({}, "a..b")
    with pytest.raises(ValueError, match="Invalid path"):
        get_path({}, ".a")
    with pytest.raises(ValueError, match="negative"):
        get_path([1, 2], "-1")


def test_pick_keys_object():
    data = {"id": 1, "name": "a", "note": "x"}
    assert pick_keys(data, ["id", "name"]) == {"id": 1, "name": "a"}
    assert pick_keys(data, ["missing"]) == {}


def test_pick_keys_array_of_objects():
    data = [{"id": 1, "name": "a"}, {"id": 2, "name": "b", "extra": True}]
    assert pick_keys(data, ["id", "name"]) == [
        {"id": 1, "name": "a"},
        {"id": 2, "name": "b"},
    ]


def test_omit_keys_object():
    data = {"id": 1, "secret": "x", "name": "a"}
    assert omit_keys(data, ["secret"]) == {"id": 1, "name": "a"}


def test_omit_keys_array_of_objects():
    data = [{"id": 1, "secret": "x"}, {"id": 2, "secret": "y", "ok": True}]
    assert omit_keys(data, ["secret"]) == [{"id": 1}, {"id": 2, "ok": True}]


def test_pick_omit_passthrough_non_objects():
    assert pick_keys(42, ["a"]) == 42
    assert omit_keys("hi", ["a"]) == "hi"
    assert pick_keys([1, {"a": 1, "b": 2}], ["a"]) == [1, {"a": 1}]


def test_filter_eq_and_numeric_ge():
    data = [
        {"name": "Ada", "age": 36},
        {"name": "Bob", "age": 22},
        {"name": "Cy", "age": "30"},
    ]
    assert filter_rows(data, "name", "eq", "Ada") == [{"name": "Ada", "age": 36}]
    assert filter_rows(data, "age", "ge", "30") == [
        {"name": "Ada", "age": 36},
        {"name": "Cy", "age": "30"},
    ]


def test_filter_ne_lt_contains_exists():
    data = [
        {"id": 1, "role": "admin", "note": "x"},
        {"id": 2, "role": "user"},
        {"id": 3, "role": "guest", "note": None},
        "skip-me",
    ]
    assert filter_rows(data, "id", "ne", "1") == [
        {"id": 2, "role": "user"},
        {"id": 3, "role": "guest", "note": None},
    ]
    assert filter_rows(data, "id", "lt", "2") == [
        {"id": 1, "role": "admin", "note": "x"}
    ]
    assert filter_rows(data, "role", "contains", "adm") == [
        {"id": 1, "role": "admin", "note": "x"}
    ]
    assert filter_rows(data, "note", "exists") == [
        {"id": 1, "role": "admin", "note": "x"}
    ]


def test_filter_drops_non_objects_and_requires_list():
    assert filter_rows([1, {"a": 1}, None], "a", "eq", "1") == [{"a": 1}]
    with pytest.raises(ValueError, match="root must be a list"):
        filter_rows({"a": 1}, "a", "eq", "1")
    with pytest.raises(ValueError, match="Unsupported filter operator"):
        filter_rows([{"a": 1}], "a", "bogus", "1")


def test_sort_asc_desc_and_missing_last():
    data = [{"id": 2}, {"id": 1}, {"id": 3}, {"name": "x"}]
    assert sort_rows(data, "id") == [
        {"id": 1},
        {"id": 2},
        {"id": 3},
        {"name": "x"},
    ]
    assert sort_rows(data, "id", desc=True) == [
        {"name": "x"},
        {"id": 3},
        {"id": 2},
        {"id": 1},
    ]


def test_sort_requires_list():
    with pytest.raises(ValueError, match="root must be a list"):
        sort_rows({"id": 1}, "id")


def test_unique_whole_and_by_key():
    data = [
        {"id": 1, "n": "a"},
        {"id": 1, "n": "b"},
        {"id": 2, "n": "c"},
        {"id": 1, "n": "a"},
    ]
    assert unique_rows(data) == [
        {"id": 1, "n": "a"},
        {"id": 1, "n": "b"},
        {"id": 2, "n": "c"},
    ]
    assert unique_rows(data, "id") == [
        {"id": 1, "n": "a"},
        {"id": 2, "n": "c"},
    ]


def test_unique_requires_list():
    with pytest.raises(ValueError, match="root must be a list"):
        unique_rows({"id": 1})

import pytest

import data_transform
from data_transform.shape import (
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


def test_public_exports_include_reshape_helpers():
    assert data_transform.__version__ == "0.4.0"
    for name in ("rename_keys", "flatten_object", "head_rows", "tail_rows"):
        assert getattr(data_transform, name) is not None


def test_rename_keys_object_preserves_order_and_values():
    inner = {"x": 1}
    data = {"id": 1, "name": "Ada", "note": inner}
    result = rename_keys(data, {"name": "title", "note": "comment"})
    assert list(result) == ["id", "title", "comment"]
    assert result == {"id": 1, "title": "Ada", "comment": inner}
    assert result["comment"] is inner


def test_rename_keys_array_and_missing_are_noop():
    data = [{"name": "Ada"}, {"id": 2}, 1, "keep"]
    assert rename_keys(data, {"name": "title", "missing": "gone"}) == [
        {"title": "Ada"},
        {"id": 2},
        1,
        "keep",
    ]
    assert rename_keys(42, {"a": "b"}) == 42
    assert rename_keys("hi", {"a": "b"}) == "hi"


def test_rename_keys_one_pass_swap_and_collision():
    assert rename_keys({"a": 1, "b": 2}, {"a": "b", "b": "c"}) == {"b": 1, "c": 2}
    assert rename_keys({"a": 1, "b": 2}, {"a": "b", "b": "a"}) == {"b": 1, "a": 2}
    # Later original key wins when several keys share a destination.
    assert rename_keys({"a": 1, "b": 2, "c": 3}, {"a": "c", "b": "c"}) == {"c": 3}
    collided = rename_keys({"a": 1, "b": 2, "c": 3}, {"a": "z", "c": "z"})
    assert collided == {"z": 3, "b": 2}


def test_rename_keys_requires_mapping():
    with pytest.raises(ValueError, match="mapping"):
        rename_keys({"a": 1}, [("a", "b")])  # type: ignore[arg-type]


def test_flatten_nested_object_and_keeps_lists():
    tags = [{"id": 1}, {"id": 2}]
    data = {
        "user": {"name": "Ada", "addr": {"city": "London"}},
        "tags": tags,
        "ok": True,
    }
    result = flatten_object(data)
    assert result == {
        "user.name": "Ada",
        "user.addr.city": "London",
        "tags": tags,
        "ok": True,
    }
    assert result["tags"] is tags


def test_flatten_list_root_custom_sep_and_passthrough():
    data = [{"user": {"name": "Ada"}}, 2, "x", {"tags": [1, 2]}]
    assert flatten_object(data, sep="_") == [
        {"user_name": "Ada"},
        2,
        "x",
        {"tags": [1, 2]},
    ]
    assert flatten_object(42) == 42
    assert flatten_object("hi") == "hi"
    assert flatten_object(None) is None
    assert flatten_object({}) == {}
    assert flatten_object([]) == []


def test_flatten_empty_nested_mapping_stays_and_collision_later_wins():
    assert flatten_object({"name": "Ada", "meta": {}}) == {
        "name": "Ada",
        "meta": {},
    }
    assert flatten_object({"a.b": 1, "a": {"b": 2}}) == {"a.b": 2}
    assert flatten_object({"a": {"b": 2}, "a.b": 1}) == {"a.b": 1}
    assert flatten_object({1: {"a": 2}}) == {"1.a": 2}


def test_flatten_rejects_empty_separator():
    with pytest.raises(ValueError, match="separator"):
        flatten_object({"a": {"b": 1}}, sep="")
    with pytest.raises(ValueError, match="separator"):
        flatten_object({"a": 1}, sep=None)  # type: ignore[arg-type]


def test_head_and_tail_rows():
    data = [{"id": 1}, {"id": 2}, {"id": 3}]
    assert head_rows(data, 2) == [{"id": 1}, {"id": 2}]
    assert tail_rows(data, 1) == [{"id": 3}]
    assert head_rows(data, 0) == []
    assert tail_rows(data, 0) == []
    assert head_rows(data, 10) == data
    assert tail_rows(data, 10) == data
    assert head_rows(data, 3) == data
    assert tail_rows(data, 3) == data
    assert head_rows([], 2) == []
    assert tail_rows([], 2) == []
    # Slices are copies.
    assert head_rows(data, 2) is not data
    assert tail_rows(data, 2) is not data


def test_head_and_tail_reject_bad_count_and_non_list():
    for fn, label in ((head_rows, "head"), (tail_rows, "tail")):
        with pytest.raises(ValueError, match="root must be a list"):
            fn({"id": 1}, 1)
        with pytest.raises(ValueError, match="non-negative integer"):
            fn([1, 2], -1)
        with pytest.raises(ValueError, match="non-negative integer"):
            fn([1, 2], True)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="non-negative integer"):
            fn([1, 2], 1.5)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match=label):
            fn("abc", 1)

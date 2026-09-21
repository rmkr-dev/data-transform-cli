import pytest

from data_transform.shape import get_path, omit_keys, pick_keys


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

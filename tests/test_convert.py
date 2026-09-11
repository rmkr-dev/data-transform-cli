import json
import re

import pytest

from data_transform.convert import (
    convert,
    detect_format,
    infer_format,
    parse,
    serialize,
)


def test_detects_by_extension():
    assert detect_format("a.json") == "json"
    assert detect_format("a.YAML") == "yaml"
    assert detect_format("a.yml") == "yaml"
    assert detect_format("a.csv") == "csv"
    assert detect_format("a.txt") is None


def test_infers_from_content():
    assert infer_format('{"a":1}') == "json"
    assert infer_format("[1,2]") == "json"
    assert infer_format("a: 1\nb: 2\n") == "yaml"
    assert infer_format("id,name\n1,a\n") == "csv"


def test_json_yaml_json_preserves_data(fixture_text):
    json_text = fixture_text("sample.json")
    data = parse(json_text, "json")
    yaml_text = serialize(data, "yaml")
    back = parse(yaml_text, "yaml")
    assert back == data


def test_yaml_json_yaml_preserves_data(fixture_text):
    yaml_text = fixture_text("sample.yaml")
    data = parse(yaml_text, "yaml")
    json_text = serialize(data, "json", pretty=True)
    back = parse(json_text, "json")
    assert back == data


def test_json_csv_json_preserves_stringified_fields(fixture_text):
    data = parse(fixture_text("sample.json"), "json")
    as_csv_objects = [
        {"id": str(row["id"]), "name": row["name"], "note": row["note"]} for row in data
    ]
    csv_text = serialize(as_csv_objects, "csv")
    back = parse(csv_text, "csv")
    assert back == as_csv_objects


def test_csv_fixture_parses_and_re_serializes(fixture_text):
    csv_text = fixture_text("sample.csv")
    data = parse(csv_text, "csv")
    again = serialize(data, "csv")
    assert parse(again, "csv") == data


def test_convert_helper_json_to_yaml():
    out = convert('{"x":1}', "json", "yaml")
    assert re.search(r"x:\s*1", out)


def test_pretty_and_minify_json():
    data = {"a": 1, "b": [2]}
    pretty = serialize(data, "json", pretty=True)
    mini = serialize(data, "json", minify=True)
    assert "\n" in pretty
    assert mini == '{"a":1,"b":[2]}'
    assert json.loads(pretty) == data
    assert json.loads(mini) == data


def test_csv_serialize_rejects_non_arrays():
    with pytest.raises(ValueError, match="array"):
        serialize({"a": 1}, "csv")

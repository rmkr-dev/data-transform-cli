import json

import pytest

from data_transform import load_schema, validate_rows
from data_transform.validate import parse_type_option, type_of
from test_cli import run_cli

ROWS = [
    {"id": 1, "email": "a@x.io", "user": {"name": "Ada"}},
    {"id": "2", "email": None, "user": {}},
    {"id": 1, "user": {"name": "Cy"}},
]


def test_required_paths_and_null_counts_as_present():
    report = validate_rows(ROWS, required=["id", "email", "user.name"])
    assert report["valid"] is False
    assert report["records"] == 3
    assert report["errors"] == [
        {"record": 1, "path": "user.name", "message": "missing required value"},
        {"record": 2, "path": "email", "message": "missing required value"},
    ]


def test_types_with_union_and_absent_paths_skipped():
    report = validate_rows(ROWS, types={"id": ["integer"], "email": ["string", "null"]})
    assert report["error_count"] == 1
    assert report["errors"][0] == {
        "record": 1, "path": "id", "message": "expected integer, got string",
    }


def test_coerce_lets_csv_strings_match():
    rows = [{"id": "7", "ms": "1.5", "ok": "TRUE", "note": ""}]
    types = {"id": ["integer"], "ms": ["number"], "ok": ["boolean"], "note": ["null"]}
    assert validate_rows(rows, types=types)["error_count"] == 4
    assert validate_rows(rows, types=types, coerce=True)["valid"] is True


def test_type_of_basics():
    assert type_of(True) == {"boolean"}
    assert type_of(3) == {"integer", "number"}
    assert type_of(2.5) == {"number"}
    assert type_of([1]) == {"array"}
    assert type_of({}) == {"object"}
    assert type_of("1e3", coerce=True) == {"string", "number"}
    assert type_of("abc", coerce=True) == {"string"}


def test_unique_reports_first_seen_record():
    report = validate_rows(ROWS, unique=["id"])
    assert report["errors"] == [
        {"record": 2, "path": "id", "message": "duplicate value '1' (first seen in record 0)"}
    ]
    # Same labels as group-by / join: 1 and "1" collide, null is a value
    assert validate_rows([{"id": 1}, {"id": "1"}], unique=["id"])["valid"] is False
    assert validate_rows([{"id": 1}, {}, {}], unique=["id"])["valid"] is True


def test_object_root_and_non_object_records():
    assert validate_rows({"id": 1}, required=["id"]) == {
        "valid": True, "records": 1, "error_count": 0, "errors": [],
    }
    report = validate_rows([{"id": 1}, 5, None], required=["id"])
    assert [e["message"] for e in report["errors"]] == [
        "record is integer, not an object",
        "record is null, not an object",
    ]


def test_max_errors_caps_list_not_count():
    rows = [{} for _ in range(5)]
    report = validate_rows(rows, required=["id"], max_errors=2)
    assert report["error_count"] == 5
    assert len(report["errors"]) == 2


def test_bad_root_and_bad_specs():
    with pytest.raises(ValueError, match="root must be"):
        validate_rows(5, required=["id"])
    with pytest.raises(ValueError, match="Unknown type"):
        parse_type_option("id=int")
    with pytest.raises(ValueError, match="PATH=TYPE"):
        parse_type_option("id")
    with pytest.raises(ValueError, match="Invalid path"):
        validate_rows([], required=["a..b"])


def test_load_schema_shapes():
    req, types, uniq = load_schema(
        {"required": ["id"], "types": {"id": "integer", "tags": ["array", "null"]}, "unique": ["id"]}
    )
    assert req == ["id"] and uniq == ["id"]
    assert types == {"id": ["integer"], "tags": ["array", "null"]}
    with pytest.raises(ValueError, match="unknown key"):
        load_schema({"require": ["id"]})
    with pytest.raises(ValueError, match="list of paths"):
        load_schema({"required": "id"})


def test_cli_valid_exit_zero():
    code, stdout, _ = run_cli(
        ["validate", "-r", "id", "--type", "id=integer", "-f", "json", "--minify"],
        '[{"id":1},{"id":2}]',
    )
    assert code == 0
    assert json.loads(stdout) == {"valid": True, "records": 2, "error_count": 0, "errors": []}


def test_cli_invalid_exit_one_and_quiet():
    args = ["validate", "-r", "id", "-u", "id", "-f", "json"]
    code, stdout, _ = run_cli(args, '[{"id":1},{"id":1},{}]')
    assert code == 1
    assert json.loads(stdout)["error_count"] == 2
    code, stdout, _ = run_cli([*args, "-q"], '[{"id":1},{"id":1}]')
    assert code == 1 and stdout == ""


def test_cli_csv_coerce_and_errors_as_csv():
    data = "id,age\n1,30\nx,\n"
    code, _, _ = run_cli(["validate", "--type", "id=integer", "--coerce", "-f", "csv"], "id\n1\n2\n")
    assert code == 0
    code, stdout, _ = run_cli(
        ["validate", "--type", "id=integer", "--type", "age=integer|null", "--coerce",
         "-f", "csv", "-t", "csv"],
        data,
    )
    assert code == 1
    assert stdout.splitlines() == [
        "record,path,message",
        "1,id,\"expected integer, got string\"",
    ]


def test_cli_schema_file_merges_with_flags(tmp_path):
    schema = tmp_path / "users.schema.yaml"
    schema.write_text("required: [id]\ntypes:\n  id: integer\n", encoding="utf-8")
    data = tmp_path / "users.json"
    data.write_text('[{"id":1,"name":"Ada"},{"id":2}]', encoding="utf-8")
    code, _, _ = run_cli(["validate", "-s", str(schema), str(data), "-q"])
    assert code == 0
    code, stdout, _ = run_cli(["validate", "-s", str(schema), "-r", "name", str(data), "--minify"])
    assert code == 1
    assert json.loads(stdout)["errors"] == [
        {"record": 1, "path": "name", "message": "missing required value"}
    ]


def test_cli_usage_errors_exit_two(tmp_path):
    code, _, stderr = run_cli(["validate", "-f", "json"], "[]")
    assert code == 2 and "nothing to check" in stderr
    code, _, stderr = run_cli(["validate", "--type", "id=int", "-f", "json"], "[]")
    assert code == 2 and "Unknown type" in stderr
    code, _, stderr = run_cli(["validate", "-r", "id", "-f", "json"], "5")
    assert code == 2 and "root must be" in stderr
    code, _, stderr = run_cli(["validate", "-s", str(tmp_path / "nope.yaml"), "-f", "json"], "[]")
    assert code == 2 and "schema file not found" in stderr

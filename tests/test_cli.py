import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "fixtures"


def run_cli(args: list[str], stdin_text: str | None = None):
    env = os.environ.copy()
    # Prefer installed console script; fall back to python -m
    cmd = [sys.executable, "-m", "data_transform.cli", *args]
    # Also try data-transform if on PATH after editable install
    completed = subprocess.run(
        cmd,
        input=stdin_text,
        text=True,
        capture_output=True,
        cwd=ROOT,
        env=env,
    )
    return completed.returncode, completed.stdout, completed.stderr


def test_to_json_from_yaml_file():
    code, stdout, stderr = run_cli(["to-json", str(FIXTURE / "sample.yaml")])
    assert code == 0, stderr
    data = json.loads(stdout)
    assert data[0]["name"] == "alpha"


def test_to_yaml_from_json_file():
    code, stdout, stderr = run_cli(["to-yaml", str(FIXTURE / "sample.json")])
    assert code == 0, stderr
    assert "name:" in stdout and "alpha" in stdout


def test_to_csv_from_json_via_stdin():
    input_text = (FIXTURE / "sample.json").read_text(encoding="utf-8")
    code, stdout, stderr = run_cli(["to-csv", "-f", "json"], input_text)
    assert code == 0, stderr
    assert "id,name,note" in stdout.splitlines()[0]
    assert "hello, world" in stdout


def test_pretty_formats_compact_json_from_stdin():
    code, stdout, stderr = run_cli(["pretty", "-f", "json"], '{"a":1}')
    assert code == 0, stderr
    assert stdout == '{\n  "a": 1\n}\n'


def test_minify_collapses_json():
    code, stdout, stderr = run_cli(["minify", "-f", "json"], '{\n  "a": 1\n}\n')
    assert code == 0, stderr
    assert stdout == '{"a":1}'


def test_to_json_minify_emits_compact_output():
    code, stdout, stderr = run_cli(
        ["to-json", "--minify", str(FIXTURE / "sample.yaml")]
    )
    assert code == 0, stderr
    assert "\n  " not in stdout
    assert json.loads(stdout)


def test_to_ndjson_from_json_array():
    code, stdout, stderr = run_cli(
        ["to-ndjson", "-f", "json"], '[{"a":1},{"b":2}]'
    )
    assert code == 0, stderr
    lines = [ln for ln in stdout.splitlines() if ln]
    assert lines == ['{"a":1}', '{"b":2}']


def test_to_json_from_ndjson_stdin():
    code, stdout, stderr = run_cli(
        ["to-json", "-f", "ndjson", "--minify"], '{"a":1}\n{"b":2}\n'
    )
    assert code == 0, stderr
    assert json.loads(stdout) == [{"a": 1}, {"b": 2}]


def test_select_single_path():
    code, stdout, stderr = run_cli(
        ["select", "user.name", "-f", "json", "--minify"],
        '{"user":{"name":"Ada"}}',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == "Ada"


def test_select_multiple_paths_and_missing():
    code, stdout, stderr = run_cli(
        ["select", "a", "b", "-f", "json", "--minify"],
        '{"a":1}',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == {"a": 1, "b": None}


def test_select_list_index_path():
    code, stdout, stderr = run_cli(
        ["select", "items.0.id", "-f", "json", "--minify"],
        '{"items":[{"id":7},{"id":8}]}',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == 7


def test_select_invalid_path_exits_1():
    code, stdout, stderr = run_cli(
        ["select", "a..b", "-f", "json"],
        '{"a":{"b":1}}',
    )
    assert code == 1
    assert "error:" in stderr


def test_pick_keys_from_object():
    code, stdout, stderr = run_cli(
        ["pick", "id", "name", "-f", "json", "--minify"],
        '{"id":1,"name":"a","note":"x"}',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == {"id": 1, "name": "a"}


def test_omit_keys_from_array():
    code, stdout, stderr = run_cli(
        ["omit", "note", "-f", "json", "--minify"],
        '[{"id":1,"note":"x"},{"id":2,"note":"y"}]',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == [{"id": 1}, {"id": 2}]


def test_filter_ge_from_stdin():
    code, stdout, stderr = run_cli(
        ["filter", "age", "ge", "30", "-f", "json", "--minify"],
        '[{"name":"Ada","age":36},{"name":"Bob","age":22}]',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == [{"name": "Ada", "age": 36}]


def test_filter_exists_and_non_list_error():
    code, stdout, stderr = run_cli(
        ["filter", "note", "exists", "-f", "json", "--minify"],
        '[{"id":1,"note":"x"},{"id":2}]',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == [{"id": 1, "note": "x"}]

    code, stdout, stderr = run_cli(
        ["filter", "a", "eq", "1", "-f", "json"],
        '{"a":1}',
    )
    assert code == 1
    assert "error:" in stderr
    assert "list" in stderr.lower()


def test_sort_and_sort_desc():
    code, stdout, stderr = run_cli(
        ["sort", "id", "-f", "json", "--minify"],
        '[{"id":2},{"id":1},{"id":3}]',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == [{"id": 1}, {"id": 2}, {"id": 3}]

    code, stdout, stderr = run_cli(
        ["sort", "id", "--desc", "-f", "json", "--minify"],
        '[{"id":2},{"id":1}]',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == [{"id": 2}, {"id": 1}]


def test_unique_by_key_and_whole():
    code, stdout, stderr = run_cli(
        ["unique", "id", "-f", "json", "--minify"],
        '[{"id":1,"n":"a"},{"id":1,"n":"b"},{"id":2}]',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == [{"id": 1, "n": "a"}, {"id": 2}]

    code, stdout, stderr = run_cli(
        ["unique", "-f", "json", "--minify"],
        '[{"a":1},{"a":1},{"b":2}]',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == [{"a": 1}, {"b": 2}]


def test_rename_pairs_from_stdin():
    code, stdout, stderr = run_cli(
        ["rename", "name", "title", "note", "comment", "-f", "json", "--minify"],
        '{"id":1,"name":"Ada","note":"x"}',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == {"id": 1, "title": "Ada", "comment": "x"}


def test_rename_array_missing_key_and_file():
    code, stdout, stderr = run_cli(
        ["rename", "name", "title", "-f", "json", "--minify"],
        '[{"name":"Ada"},{"id":2},1]',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == [{"title": "Ada"}, {"id": 2}, 1]

    code, stdout, stderr = run_cli(
        ["rename", "name", "title", str(FIXTURE / "sample.json"), "--minify"]
    )
    assert code == 0, stderr
    data = json.loads(stdout)
    assert data[0]["title"] == "alpha"
    assert "name" not in data[0]
    assert data[0]["note"] == "hello, world"
    assert data[1]["title"] == "beta"


def test_rename_odd_pairs_and_duplicate_old():
    code, stdout, stderr = run_cli(
        ["rename", "only", "-f", "json"],
        '{"a":1}',
    )
    assert code == 1
    assert stdout == ""
    assert "error:" in stderr
    assert "OLD NEW" in stderr

    code, stdout, stderr = run_cli(
        ["rename", "a", "x", "a", "y", "-f", "json", "--minify"],
        '{"a":1,"b":2}',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == {"y": 1, "b": 2}


def test_flatten_nested_and_custom_sep():
    code, stdout, stderr = run_cli(
        ["flatten", "-f", "json", "--minify"],
        '{"user":{"name":"Ada","addr":{"city":"London"}},"tags":["a","b"]}',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == {
        "user.name": "Ada",
        "user.addr.city": "London",
        "tags": ["a", "b"],
    }

    code, stdout, stderr = run_cli(
        ["flatten", "--sep", "_", "-f", "json", "--minify"],
        '{"user":{"name":"Ada"}}',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == {"user_name": "Ada"}


def test_flatten_list_root_passthrough_and_empty_sep():
    code, stdout, stderr = run_cli(
        ["flatten", "-f", "json", "--minify"],
        '[{"user":{"name":"Ada"}},2]',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == [{"user.name": "Ada"}, 2]

    code, stdout, stderr = run_cli(["flatten", "-f", "json", "--minify"], "42")
    assert code == 0, stderr
    assert json.loads(stdout) == 42

    code, stdout, stderr = run_cli(
        ["flatten", "--sep", "", "-f", "json"],
        '{"a":{"b":1}}',
    )
    assert code == 1
    assert "error:" in stderr
    assert "separator" in stderr


def test_head_and_tail_from_stdin_and_file():
    code, stdout, stderr = run_cli(
        ["head", "2", "-f", "json", "--minify"],
        '[{"id":1},{"id":2},{"id":3}]',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == [{"id": 1}, {"id": 2}]

    code, stdout, stderr = run_cli(
        ["tail", "1", "-f", "json", "--minify"],
        '[{"id":1},{"id":2},{"id":3}]',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == [{"id": 3}]

    code, stdout, stderr = run_cli(
        ["head", "1", str(FIXTURE / "sample.json"), "--minify"]
    )
    assert code == 0, stderr
    data = json.loads(stdout)
    assert data == [
        {"id": 1, "name": "alpha", "note": "hello, world"},
    ]


def test_head_tail_clamp_zero_and_errors(tmp_path):
    code, stdout, stderr = run_cli(
        ["head", "0", "-f", "json", "--minify"],
        "[1,2,3]",
    )
    assert code == 0, stderr
    assert json.loads(stdout) == []

    code, stdout, stderr = run_cli(
        ["tail", "0", "-f", "json", "--minify"],
        "[1,2,3]",
    )
    assert code == 0, stderr
    assert json.loads(stdout) == []

    code, stdout, stderr = run_cli(
        ["head", "9", "-f", "json", "--minify"],
        "[1,2]",
    )
    assert code == 0, stderr
    assert json.loads(stdout) == [1, 2]

    code, stdout, stderr = run_cli(
        ["tail", "9", "-f", "json", "--minify"],
        "[1,2]",
    )
    assert code == 0, stderr
    assert json.loads(stdout) == [1, 2]

    dest = tmp_path / "out.json"
    code, stdout, stderr = run_cli(
        ["head", "1", "-f", "json", "--minify", "-o", str(dest)],
        "[1,2,3]",
    )
    assert code == 0, stderr
    assert stdout == ""
    assert json.loads(dest.read_text(encoding="utf-8")) == [1]

    code, stdout, stderr = run_cli(
        ["head", "1", "-f", "json"],
        '{"a":1}',
    )
    assert code == 1
    assert "error:" in stderr
    assert "list" in stderr.lower()

    code, stdout, stderr = run_cli(
        ["tail", "nope", "-f", "json"],
        "[1,2,3]",
    )
    assert code == 1
    assert "error:" in stderr
    assert "non-negative" in stderr

    code, stdout, stderr = run_cli(
        ["head", "-1", "-f", "json"],
        "[1,2,3]",
    )
    assert code == 1
    assert "error:" in stderr
    assert "non-negative" in stderr

    code, stdout, stderr = run_cli(
        ["head", "1", "2", "-f", "json"],
        "[1,2,3]",
    )
    assert code == 1
    assert "error:" in stderr
    assert "Usage:" in stderr


def test_group_by_from_stdin_and_file():
    code, stdout, stderr = run_cli(
        ["group-by", "team", "-f", "json", "--minify"],
        '[{"team":"a","id":1},{"team":"b","id":2},{"team":"a","id":3},{"id":4}]',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == {
        "a": [{"team": "a", "id": 1}, {"team": "a", "id": 3}],
        "b": [{"team": "b", "id": 2}],
    }

    code, stdout, stderr = run_cli(
        ["group-by", "id", str(FIXTURE / "sample.json"), "--minify"]
    )
    assert code == 0, stderr
    assert list(json.loads(stdout)) == ["1", "2"]


def test_group_by_errors():
    code, stdout, stderr = run_cli(["group-by", "k", "-f", "json"], '{"k":1}')
    assert code == 1
    assert stdout == ""
    assert "error:" in stderr
    assert "list" in stderr.lower()

    code, stdout, stderr = run_cli(["group-by", "a", "b", "-f", "json"], "[]")
    assert code == 1
    assert "Usage:" in stderr


def test_count_total_per_key_and_piped_groups():
    rows = '[{"t":"a"},{"t":"b"},{"t":"a"}]'
    code, stdout, stderr = run_cli(["count", "-f", "json"], rows)
    assert code == 0, stderr
    assert json.loads(stdout) == 3

    code, stdout, stderr = run_cli(["count", "t", "-f", "json", "--minify"], rows)
    assert code == 0, stderr
    assert stdout.strip() == '{"a":2,"b":1}'

    code, grouped, stderr = run_cli(["group-by", "t", "-f", "json"], rows)
    assert code == 0, stderr
    code, stdout, stderr = run_cli(["count", "-f", "json", "--minify"], grouped)
    assert code == 0, stderr
    assert json.loads(stdout) == {"a": 2, "b": 1}

    code, stdout, stderr = run_cli(["count", str(FIXTURE / "sample.json")])
    assert code == 0, stderr
    assert json.loads(stdout) == 2

    code, stdout, stderr = run_cli(
        ["count", "-f", "ndjson"], '{"id":1}\n{"id":2}\n'
    )
    assert code == 0, stderr
    assert json.loads(stdout) == 2


def test_count_errors():
    code, stdout, stderr = run_cli(["count", "-f", "json"], '{"a":1}')
    assert code == 1
    assert "error:" in stderr
    assert "list" in stderr.lower()

    code, stdout, stderr = run_cli(["count", "a", "b", "-f", "json"], "[]")
    assert code == 1
    assert "Usage:" in stderr


def test_unflatten_nested_custom_sep_and_round_trip(tmp_path):
    code, stdout, stderr = run_cli(
        ["unflatten", "-f", "json", "--minify"],
        '{"user.name":"Ada","user.addr.city":"London","tags":["a","b"]}',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == {
        "user": {"name": "Ada", "addr": {"city": "London"}},
        "tags": ["a", "b"],
    }

    code, stdout, stderr = run_cli(
        ["unflatten", "--sep", "_", "-f", "json", "--minify"],
        '[{"user_name":"Ada"},3]',
    )
    assert code == 0, stderr
    assert json.loads(stdout) == [{"user": {"name": "Ada"}}, 3]

    original = {"user": {"name": "Ada", "addr": {"city": "London"}}, "id": 1}
    flat_file = tmp_path / "flat.json"
    code, stdout, stderr = run_cli(
        ["flatten", "-f", "json", "-o", str(flat_file)], json.dumps(original)
    )
    assert code == 0, stderr
    code, stdout, stderr = run_cli(["unflatten", str(flat_file)])
    assert code == 0, stderr
    assert json.loads(stdout) == original

    code, stdout, stderr = run_cli(
        ["unflatten", "--sep", "", "-f", "json"], '{"a.b":1}'
    )
    assert code == 1
    assert "error:" in stderr
    assert "separator" in stderr

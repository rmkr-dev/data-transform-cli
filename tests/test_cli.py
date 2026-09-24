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

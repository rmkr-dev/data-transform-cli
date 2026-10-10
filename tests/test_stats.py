import json

import pytest

from data_transform import group_rows, stats_rows
from test_cli import run_cli


def test_stats_list_mixed_values():
    rows = [{"v": 1}, {"v": "2.5"}, {"v": True}, {"v": "x"}, {}, 3, {"v": 4}]
    assert stats_rows(rows, "v") == {
        "count": 3, "sum": 7.5, "min": 1, "max": 4, "avg": 2.5,
    }


def test_stats_empty_and_no_numbers():
    empty = {"count": 0, "sum": 0, "min": None, "max": None, "avg": None}
    assert stats_rows([], "v") == empty
    assert stats_rows([{"v": "a"}], "v") == empty


def test_stats_grouped():
    rows = [{"t": "a", "v": 2}, {"t": "b", "v": 5}, {"t": "a", "v": 4}]
    out = stats_rows(group_rows(rows, "t"), "v")
    assert out["a"] == {"count": 2, "sum": 6, "min": 2, "max": 4, "avg": 3}
    assert out["b"]["avg"] == 5


def test_stats_bad_root():
    with pytest.raises(ValueError, match="stats: root"):
        stats_rows({"a": 1}, "v")


def test_stats_cli_json_and_csv():
    code, stdout, _ = run_cli(
        ["stats", "ms", "-f", "json", "--minify"], '[{"ms":120},{"ms":80}]'
    )
    assert code == 0
    assert json.loads(stdout) == {"count": 2, "sum": 200, "min": 80, "max": 120, "avg": 100}
    code, stdout, _ = run_cli(["stats", "ms", "-f", "csv", "--minify"], "ms\n1\n2\n")
    assert code == 0 and json.loads(stdout)["avg"] == 1.5


def test_stats_cli_errors():
    code, _, stderr = run_cli(["stats", "-f", "json"], "[]")
    assert code != 0
    code, _, stderr = run_cli(["stats", "a", "b", "-f", "json"], "[]")
    assert code != 0 and "Usage" in stderr

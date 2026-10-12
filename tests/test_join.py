import json

import pytest

from data_transform import join_rows
from test_cli import run_cli

USERS = [
    {"id": 1, "name": "Ada"},
    {"id": 2, "name": "Bob"},
    {"id": 3, "name": "Cy"},
]
ORDERS = [
    {"id": 2, "total": 10},
    {"id": 1, "total": 5},
    {"id": 2, "total": 7},
]


def test_join_inner_keeps_left_order_and_emits_one_row_per_match():
    assert join_rows(USERS, ORDERS, "id") == [
        {"id": 1, "name": "Ada", "total": 5},
        {"id": 2, "name": "Bob", "total": 10},
        {"id": 2, "name": "Bob", "total": 7},
    ]


def test_join_left_keeps_unmatched_left_rows_unchanged():
    out = join_rows(USERS, ORDERS, "id", how="left")
    assert out[-1] == {"id": 3, "name": "Cy"}
    assert len(out) == 4


def test_join_right_wins_on_collision_and_key_appears_once():
    left = [{"id": 1, "name": "old", "a": 1}]
    right = [{"name": "new", "id": 1, "b": 2}]
    out = join_rows(left, right, "id")
    assert out == [{"id": 1, "name": "new", "a": 1, "b": 2}]
    assert list(out[0]) == ["id", "name", "a", "b"]


def test_join_missing_and_null_keys_never_match():
    left = [{"id": None, "v": "l0"}, {"v": "l1"}, {"id": 1, "v": "l2"}]
    right = [{"id": None, "r": 0}, {"r": 1}, {"id": 1, "r": 2}]
    assert join_rows(left, right, "id") == [{"id": 1, "v": "l2", "r": 2}]
    assert join_rows(left, right, "id", how="left") == [
        {"id": None, "v": "l0"},
        {"v": "l1"},
        {"id": 1, "v": "l2", "r": 2},
    ]


def test_join_matches_numbers_and_numeric_strings_keeping_left_value():
    out = join_rows([{"id": 1}], [{"id": "1", "x": "y"}], "id")
    assert out == [{"id": 1, "x": "y"}]


def test_join_empty_lists():
    assert join_rows([], ORDERS, "id") == []
    assert join_rows(USERS, [], "id") == []
    assert join_rows(USERS, [], "id", how="LEFT") == USERS


def test_join_does_not_mutate_inputs():
    left = [{"id": 1, "a": 1}]
    right = [{"id": 1, "a": 2}]
    join_rows(left, right, "id")
    assert left == [{"id": 1, "a": 1}] and right == [{"id": 1, "a": 2}]


@pytest.mark.parametrize(
    "left,right,message",
    [
        ({"id": 1}, [], "left root must be a list"),
        ([], "x", "right root must be a list"),
        ([{"id": 1}, 2], [], "left item 1 must be an object"),
        ([], [None], "right item 0 must be an object"),
    ],
)
def test_join_rejects_non_list_roots_and_non_object_items(left, right, message):
    with pytest.raises(ValueError, match=message):
        join_rows(left, right, "id")


def test_join_rejects_bad_how_and_empty_key():
    with pytest.raises(ValueError, match="unsupported join type"):
        join_rows([], [], "id", how="outer")
    with pytest.raises(ValueError, match="KEY must be"):
        join_rows([], [], "")


# CLI


@pytest.fixture
def right_csv(tmp_path):
    path = tmp_path / "teams.csv"
    path.write_text("id,team\n1,core\n2,web\n2,ops\n", encoding="utf-8")
    return path


def test_cli_join_inner_json_left_from_stdin_csv_right(right_csv):
    code, stdout, stderr = run_cli(
        ["join", "id", "--with", str(right_csv), "-f", "json", "--minify"],
        json.dumps(USERS),
    )
    assert code == 0, stderr
    assert json.loads(stdout) == [
        {"id": 1, "name": "Ada", "team": "core"},
        {"id": 2, "name": "Bob", "team": "web"},
        {"id": 2, "name": "Bob", "team": "ops"},
    ]


def test_cli_join_left_with_file_arg_and_yaml_right(tmp_path):
    left = tmp_path / "users.json"
    left.write_text(json.dumps(USERS), encoding="utf-8")
    right = tmp_path / "roles.yaml"
    right.write_text("- id: 3\n  role: admin\n", encoding="utf-8")
    code, stdout, stderr = run_cli(
        ["join", "id", "-w", str(right), str(left), "--how", "left"]
    )
    assert code == 0, stderr
    assert json.loads(stdout) == [
        {"id": 1, "name": "Ada"},
        {"id": 2, "name": "Bob"},
        {"id": 3, "name": "Cy", "role": "admin"},
    ]


def test_cli_join_right_from_forces_format_and_writes_output(tmp_path):
    right = tmp_path / "extra.txt"
    right.write_text('{"id":1,"x":true}\n{"id":9,"x":false}\n', encoding="utf-8")
    out = tmp_path / "out.json"
    code, _, stderr = run_cli(
        [
            "join", "id", "-w", str(right), "--right-from", "ndjson",
            "-f", "json", "-o", str(out), "--minify",
        ],
        '[{"id":1},{"id":2}]',
    )
    assert code == 0, stderr
    assert json.loads(out.read_text(encoding="utf-8")) == [{"id": 1, "x": True}]


def test_cli_join_requires_with_option():
    code, _, stderr = run_cli(["join", "id", "-f", "json"], "[]")
    assert code != 0
    assert "--with" in stderr


def test_cli_join_rejects_stdin_and_missing_right_file(tmp_path):
    code, _, stderr = run_cli(["join", "id", "-w", "-", "-f", "json"], "[]")
    assert code == 1
    assert "needs a file path" in stderr
    code, _, stderr = run_cli(
        ["join", "id", "-w", str(tmp_path / "nope.json"), "-f", "json"], "[]"
    )
    assert code == 1
    assert "right file not found" in stderr


def test_cli_join_reports_non_list_root(right_csv):
    code, _, stderr = run_cli(
        ["join", "id", "-w", str(right_csv), "-f", "json"], '{"id":1}'
    )
    assert code == 1
    assert "left root must be a list" in stderr

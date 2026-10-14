import json

import pytest
import yaml

from data_transform.cli import resolve_to
from data_transform.csv_io import parse_csv
from test_cli import run_cli

PEOPLE = '[{"name":"Ada","age":36,"team":"core"},{"name":"Bob","age":22,"team":"web"}]'


@pytest.mark.parametrize(
    "to_flag, output, expected",
    [
        (None, None, "json"),
        (None, "-", "json"),
        (None, "out.csv", "csv"),
        (None, "out.YML", "yaml"),
        (None, "dir/out.jsonl", "ndjson"),
        (None, "out.txt", "json"),
        ("yaml", "out.csv", "yaml"),
        ("CSV", None, "csv"),
    ],
)
def test_resolve_to_flag_then_extension_then_json(to_flag, output, expected):
    assert resolve_to(to_flag, output) == expected


def test_filter_to_csv():
    code, stdout, stderr = run_cli(
        ["filter", "age", "ge", "30", "-f", "json", "-t", "csv"], PEOPLE
    )
    assert code == 0, stderr
    assert stdout == "name,age,team\nAda,36,core\n"


def test_sort_to_yaml_keeps_key_order():
    code, stdout, stderr = run_cli(["sort", "age", "-f", "json", "--to", "yaml"], PEOPLE)
    assert code == 0, stderr
    assert yaml.safe_load(stdout) == [
        {"name": "Bob", "age": 22, "team": "web"},
        {"name": "Ada", "age": 36, "team": "core"},
    ]
    assert stdout.startswith("- name: Bob\n  age: 22\n")


def test_pick_to_ndjson_is_one_compact_line_per_item():
    code, stdout, stderr = run_cli(["pick", "name", "-f", "json", "-t", "ndjson"], PEOPLE)
    assert code == 0, stderr
    assert stdout == '{"name":"Ada"}\n{"name":"Bob"}\n'


def test_to_json_explicit_matches_default_and_respects_minify():
    _, default_out, _ = run_cli(["head", "1", "-f", "json"], PEOPLE)
    code, explicit_out, stderr = run_cli(["head", "1", "-f", "json", "-t", "json"], PEOPLE)
    assert code == 0, stderr
    assert explicit_out == default_out
    assert explicit_out.endswith("\n") and "\n  " in explicit_out
    _, compact, _ = run_cli(["head", "1", "-f", "json", "-t", "json", "--minify"], PEOPLE)
    assert compact == '[{"name":"Ada","age":36,"team":"core"}]'


def test_minify_is_ignored_for_non_json_output():
    code, stdout, stderr = run_cli(
        ["tail", "1", "-f", "json", "-t", "csv", "--minify"], PEOPLE
    )
    assert code == 0, stderr
    assert stdout == "name,age,team\nBob,22,web\n"


def test_output_extension_picks_format(tmp_path):
    out_csv = tmp_path / "flat.csv"
    code, stdout, stderr = run_cli(
        ["flatten", "-f", "json", "-o", str(out_csv)],
        '[{"id":1,"user":{"name":"Ada"}}]',
    )
    assert code == 0, stderr
    assert stdout == ""
    assert out_csv.read_text(encoding="utf-8") == "id,user.name\n1,Ada\n"

    out_yaml = tmp_path / "people.yaml"
    code, _, stderr = run_cli(["omit", "age", "-f", "json", "-o", str(out_yaml)], PEOPLE)
    assert code == 0, stderr
    assert yaml.safe_load(out_yaml.read_text(encoding="utf-8"))[0] == {
        "name": "Ada",
        "team": "core",
    }


def test_to_flag_overrides_output_extension(tmp_path):
    out = tmp_path / "data.csv"
    code, _, stderr = run_cli(
        ["rename", "name", "title", "-f", "json", "-t", "json", "--minify", "-o", str(out)],
        PEOPLE,
    )
    assert code == 0, stderr
    assert json.loads(out.read_text(encoding="utf-8"))[0]["title"] == "Ada"


def test_unknown_output_extension_stays_json(tmp_path):
    out = tmp_path / "result.out"
    code, _, stderr = run_cli(["unique", "team", "-f", "json", "-o", str(out)], PEOPLE)
    assert code == 0, stderr
    assert len(json.loads(out.read_text(encoding="utf-8"))) == 2


def test_csv_round_trip_through_filter():
    csv_in = "name,age\nAda,36\nBob,22\nCy,41\n"
    code, stdout, stderr = run_cli(
        ["filter", "age", "gt", "30", "-f", "csv", "-t", "csv"], csv_in
    )
    assert code == 0, stderr
    assert parse_csv(stdout) == [{"name": "Ada", "age": "36"}, {"name": "Cy", "age": "41"}]


def test_group_by_and_count_to_yaml():
    code, stdout, stderr = run_cli(["count", "team", "-f", "json", "-t", "yaml"], PEOPLE)
    assert code == 0, stderr
    assert stdout == "core: 1\nweb: 1\n"
    code, stdout, stderr = run_cli(["group-by", "team", "-f", "json", "-t", "yaml"], PEOPLE)
    assert code == 0, stderr
    assert list(yaml.safe_load(stdout)) == ["core", "web"]


def test_stats_and_select_to_yaml():
    code, stdout, stderr = run_cli(["stats", "age", "-f", "json", "-t", "yaml"], PEOPLE)
    assert code == 0, stderr
    assert yaml.safe_load(stdout) == {"count": 2, "sum": 58, "min": 22, "max": 36, "avg": 29}
    code, stdout, stderr = run_cli(["select", "0.name", "-f", "json", "-t", "yaml"], PEOPLE)
    assert code == 0, stderr
    assert yaml.safe_load(stdout) == "Ada"


def test_unflatten_to_ndjson():
    code, stdout, stderr = run_cli(
        ["unflatten", "-f", "json", "-t", "ndjson"], '[{"a.b":1},{"a.b":2}]'
    )
    assert code == 0, stderr
    assert stdout == '{"a":{"b":1}}\n{"a":{"b":2}}\n'


def test_join_to_csv(tmp_path):
    right = tmp_path / "teams.csv"
    right.write_text("id,team\n1,core\n", encoding="utf-8")
    code, stdout, stderr = run_cli(
        ["join", "id", "-w", str(right), "-f", "json", "-t", "csv"],
        '[{"id":1,"name":"Ada"},{"id":2,"name":"Bob"}]',
    )
    assert code == 0, stderr
    assert stdout == "id,name,team\n1,Ada,core\n"


def test_yaml_dates_survive_when_output_is_yaml():
    yaml_in = "- id: 1\n  day: 2026-10-14\n- id: 2\n  day: 2026-10-15\n"
    code, stdout, stderr = run_cli(["head", "1", "-f", "yaml", "-t", "yaml"], yaml_in)
    assert code == 0, stderr
    assert stdout == "- id: 1\n  day: 2026-10-14\n"


@pytest.mark.parametrize(
    "args, stdin",
    [
        (["count", "-f", "json", "-t", "csv"], PEOPLE),
        (["group-by", "team", "-f", "json", "-t", "csv"], PEOPLE),
        (["select", "0", "-f", "json", "-t", "csv"], PEOPLE),
    ],
)
def test_csv_output_of_non_list_result_is_a_clear_error(args, stdin):
    code, stdout, stderr = run_cli(args, stdin)
    assert code == 1
    assert stdout == ""
    assert "error: cannot write csv" in stderr
    assert "--to json or --to yaml" in stderr


def test_invalid_to_choice_is_usage_error():
    code, _, stderr = run_cli(["pick", "name", "-f", "json", "-t", "xml"], PEOPLE)
    assert code == 2
    assert "xml" in stderr


def test_conversion_commands_do_not_take_to():
    code, _, stderr = run_cli(["to-json", "-f", "json", "-t", "yaml"], "{}")
    assert code == 2
    assert "No such option" in stderr

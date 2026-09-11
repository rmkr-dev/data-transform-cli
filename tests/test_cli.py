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

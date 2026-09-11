"""Click CLI entry point for data-transform."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click

from . import __version__
from .convert import convert, detect_format, infer_format, parse, serialize


def load_input(file: Optional[str]) -> tuple[str, Optional[str]]:
    """Load input from file path or stdin when path is '-' / omitted."""
    if not file or file == "-":
        if sys.stdin.isatty():
            raise ValueError(
                "No input file and stdin is a TTY. Pass a file or pipe data."
            )
        return sys.stdin.read(), None
    return Path(file).read_text(encoding="utf-8"), file


def resolve_from(text: str, name: Optional[str], from_flag: Optional[str]) -> str:
    """Resolve source format from flag, filename, or content."""
    if from_flag:
        return from_flag.lower()
    detected = detect_format(name)
    if detected:
        return detected
    return infer_format(text)


def write_output(out: str, output_path: Optional[str]) -> None:
    """Write output to file or stdout."""
    if output_path and output_path != "-":
        Path(output_path).write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)


def _run_transform(
    file: Optional[str],
    output: Optional[str],
    from_format: Optional[str],
    to_format: str,
    *,
    pretty: bool | None = None,
    minify: bool = False,
) -> None:
    try:
        text, name = load_input(file)
        src = resolve_from(text, name, from_format)
        out = convert(text, src, to_format, pretty=pretty, minify=minify)  # type: ignore[arg-type]
        write_output(out, output)
    except Exception as err:  # noqa: BLE001 — CLI surface
        click.echo(f"error: {err}", err=True)
        sys.exit(1)


def _run_json_view(
    file: Optional[str],
    output: Optional[str],
    from_format: Optional[str],
    *,
    pretty: bool = False,
    minify: bool = False,
) -> None:
    try:
        text, name = load_input(file)
        src = resolve_from(text, name, from_format)
        data = parse(text, src)  # type: ignore[arg-type]
        write_output(serialize(data, "json", pretty=pretty, minify=minify), output)
    except Exception as err:  # noqa: BLE001
        click.echo(f"error: {err}", err=True)
        sys.exit(1)


@click.group()
@click.version_option(__version__, prog_name="data-transform")
def main() -> None:
    """YAML ↔ JSON ↔ CSV transforms for pipelines and shell use."""


@main.command("to-json")
@click.argument("file", required=False)
@click.option("-o", "--output", default=None, help="write to file instead of stdout")
@click.option(
    "-f",
    "--from",
    "from_format",
    type=click.Choice(["json", "yaml", "csv"], case_sensitive=False),
    default=None,
    help="input format: json | yaml | csv",
)
@click.option("--minify", is_flag=True, default=False, help="emit compact JSON")
def to_json(
    file: Optional[str],
    output: Optional[str],
    from_format: Optional[str],
    minify: bool,
) -> None:
    """Convert input to JSON."""
    _run_transform(
        file, output, from_format, "json", pretty=not minify, minify=minify
    )


@main.command("to-yaml")
@click.argument("file", required=False)
@click.option("-o", "--output", default=None, help="write to file instead of stdout")
@click.option(
    "-f",
    "--from",
    "from_format",
    type=click.Choice(["json", "yaml", "csv"], case_sensitive=False),
    default=None,
    help="input format: json | yaml | csv",
)
def to_yaml(
    file: Optional[str], output: Optional[str], from_format: Optional[str]
) -> None:
    """Convert input to YAML."""
    _run_transform(file, output, from_format, "yaml")


@main.command("to-csv")
@click.argument("file", required=False)
@click.option("-o", "--output", default=None, help="write to file instead of stdout")
@click.option(
    "-f",
    "--from",
    "from_format",
    type=click.Choice(["json", "yaml", "csv"], case_sensitive=False),
    default=None,
    help="input format: json | yaml | csv",
)
def to_csv(
    file: Optional[str], output: Optional[str], from_format: Optional[str]
) -> None:
    """Convert input to CSV (array of objects/rows)."""
    _run_transform(file, output, from_format, "csv")


@main.command("pretty")
@click.argument("file", required=False)
@click.option("-o", "--output", default=None, help="write to file instead of stdout")
@click.option(
    "-f",
    "--from",
    "from_format",
    type=click.Choice(["json", "yaml", "csv"], case_sensitive=False),
    default=None,
    help="input format: json | yaml | csv",
)
def pretty_cmd(
    file: Optional[str], output: Optional[str], from_format: Optional[str]
) -> None:
    """Pretty-print JSON (or convert to pretty JSON)."""
    _run_json_view(file, output, from_format, pretty=True)


@main.command("minify")
@click.argument("file", required=False)
@click.option("-o", "--output", default=None, help="write to file instead of stdout")
@click.option(
    "-f",
    "--from",
    "from_format",
    type=click.Choice(["json", "yaml", "csv"], case_sensitive=False),
    default=None,
    help="input format: json | yaml | csv",
)
def minify_cmd(
    file: Optional[str], output: Optional[str], from_format: Optional[str]
) -> None:
    """Minify JSON (or convert to compact JSON)."""
    _run_json_view(file, output, from_format, minify=True)


if __name__ == "__main__":
    main()

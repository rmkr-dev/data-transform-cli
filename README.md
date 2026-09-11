# data-transform-cli

Python CLI for **YAML ↔ JSON ↔ CSV** transforms. Built for shell pipelines and local scripts.
Streaming-friendly where practical (stdin/stdout; full documents buffered for parse safety).

Requires **Python 3.11+**.

## Install

```bash
pip install -e .
# or with test extras:
pip install -e ".[dev]"
```

After install, the `data-transform` console script is on your `PATH`.

## Commands

| Command | Description |
|--------|-------------|
| `to-json` | Convert input to JSON |
| `to-yaml` | Convert input to YAML |
| `to-csv` | Convert input to CSV (array of objects or rows) |
| `pretty` | Pretty-print as JSON |
| `minify` | Emit compact JSON |

### Options (most commands)

- `[file]` — input path; omit or use `-` for stdin
- `-o, --output <file>` — write to a file instead of stdout
- `-f, --from <format>` — force input format: `json` | `yaml` | `csv`
- `to-json --minify` — compact JSON output

Format is taken from `--from`, else the file extension, else simple content heuristics.

## Usage examples

```bash
# YAML to JSON
data-transform to-json config.yaml

# JSON to YAML (pipe)
cat payload.json | data-transform to-yaml

# JSON array to CSV
data-transform to-csv records.json -o records.csv

# CSV to pretty JSON
data-transform pretty table.csv -f csv

# Minify JSON
data-transform minify bulky.json

# Force format when using stdin
printf "a: 1\n" | data-transform to-json -f yaml
```

### Library use

```python
from data_transform import convert, parse, serialize

yaml_text = convert('{"a":1}', "json", "yaml")
data = parse("id,name\n1,x\n", "csv")
json_text = serialize(data, "json", pretty=True)
```

## CSV notes

CSV support is intentionally small and robust (RFC 4180-ish) via the Python standard library `csv` module: quoted fields, escaped quotes (`""`), and newlines inside quotes. Object arrays use a header row; all cell values are strings when parsed from CSV.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests use **pytest** with fixtures under `tests/fixtures/` for JSON/YAML/CSV round-trips and CLI smoke checks.

## License

MIT — see [LICENSE](./LICENSE).

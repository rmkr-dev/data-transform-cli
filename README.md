# data-transform-cli

Python CLI for **YAML ↔ JSON ↔ CSV ↔ NDJSON** transforms. Built for shell pipelines and local scripts.
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
| `to-ndjson` | Convert input to NDJSON (one JSON value per line) |
| `pretty` | Pretty-print as JSON |
| `minify` | Emit compact JSON |
| `select` | Extract dotted paths from parsed data |
| `pick` | Keep only listed top-level keys |
| `omit` | Drop listed top-level keys |

### Options (most commands)

- `[file]` — input path; omit or use `-` for stdin
- `-o, --output <file>` — write to a file instead of stdout
- `-f, --from <format>` — force input format: `json` | `yaml` | `csv` | `ndjson`
- `--minify` — compact JSON output (`to-json`, `select`, `pick`, `omit`)

Format is taken from `--from`, else the file extension (`.ndjson` / `.jsonl` → ndjson), else simple content heuristics.

## Usage examples

```bash
# YAML to JSON
data-transform to-json config.yaml

# JSON to YAML (pipe)
cat payload.json | data-transform to-yaml

# JSON array to CSV
data-transform to-csv records.json -o records.csv

# JSON array to NDJSON
data-transform to-ndjson records.json

# NDJSON to JSON array
data-transform to-json events.ndjson

# CSV to pretty JSON
data-transform pretty table.csv -f csv

# Minify JSON
data-transform minify bulky.json

# Force format when using stdin
printf "a: 1\n" | data-transform to-json -f yaml
```

### Select, pick, omit

```bash
# Single dotted path (list index supported)
echo '{"user":{"name":"Ada"},"items":[{"id":1}]}' \
  | data-transform select user.name -f json
# → "Ada"

echo '{"items":[{"id":1},{"id":2}]}' \
  | data-transform select items.0.id -f json
# → 1

# Multiple paths → object map (missing → null)
echo '{"a":1}' | data-transform select a b -f json --minify
# → {"a":1,"b":null}

# Keep / drop top-level keys (maps over arrays of objects)
echo '[{"id":1,"name":"a","note":"x"},{"id":2,"name":"b","note":"y"}]' \
  | data-transform pick id name -f json --minify
# → [{"id":1,"name":"a"},{"id":2,"name":"b"}]

echo '{"id":1,"secret":"x","name":"a"}' \
  | data-transform omit secret -f json --minify
# → {"id":1,"name":"a"}
```

### Library use

```python
from data_transform import convert, parse, serialize, get_path, pick_keys, omit_keys

yaml_text = convert('{"a":1}', "json", "yaml")
data = parse("id,name\n1,x\n", "csv")
json_text = serialize(data, "json", pretty=True)
name = get_path({"user": {"name": "Ada"}}, "user.name")
slim = pick_keys({"id": 1, "name": "a", "note": "x"}, ["id", "name"])
```

## NDJSON notes

NDJSON (also known as JSON Lines / `.jsonl`) is one JSON value per non-empty line. Parsing always yields a list. Serializing a list emits one compact JSON value per line; a non-list root becomes a single line.

## CSV notes

CSV support is intentionally small and robust (RFC 4180-ish) via the Python standard library `csv` module: quoted fields, escaped quotes (`""`), and newlines inside quotes. Object arrays use a header row; all cell values are strings when parsed from CSV.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests use **pytest** with fixtures under `tests/fixtures/` for JSON/YAML/CSV/NDJSON round-trips and CLI smoke checks.

## License

MIT — see [LICENSE](./LICENSE).

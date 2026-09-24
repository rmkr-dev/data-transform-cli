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
| `filter` | Keep array items matching KEY OP VALUE |
| `sort` | Sort array of objects by top-level KEY |
| `unique` | Deduplicate array (by KEY or whole item) |

### Options (most commands)

- `[file]` — input path; omit or use `-` for stdin
- `-o, --output <file>` — write to a file instead of stdout
- `-f, --from <format>` — force input format: `json` | `yaml` | `csv` | `ndjson`
- `--minify` — compact JSON output (`to-json`, `select`, `pick`, `omit`, `filter`, `sort`, `unique`)
- `--desc` — reverse sort order (`sort` only)

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

### Filter, sort, unique

These commands require a **list** root (JSON/YAML/CSV/NDJSON array). Non-object
items are dropped by `filter`. Missing keys sort last (first with `--desc`).

```bash
# Keep rows where age >= 30 (numeric when both sides look like numbers)
echo '[{"name":"Ada","age":36},{"name":"Bob","age":22}]' \
  | data-transform filter age ge 30 -f json --minify
# → [{"name":"Ada","age":36}]

# String contains / key exists (VALUE optional for exists)
echo '[{"role":"admin"},{"role":"user"}]' \
  | data-transform filter role contains adm -f json --minify
# → [{"role":"admin"}]

echo '[{"id":1,"note":"x"},{"id":2}]' \
  | data-transform filter note exists -f json --minify
# → [{"id":1,"note":"x"}]

# Sort by key (ascending / descending)
echo '[{"id":2},{"id":1},{"id":3}]' \
  | data-transform sort id -f json --minify
# → [{"id":1},{"id":2},{"id":3}]

echo '[{"id":2},{"id":1}]' \
  | data-transform sort id --desc -f json --minify
# → [{"id":2},{"id":1}]

# Deduplicate whole items, or by a key (first wins)
echo '[{"id":1},{"id":1},{"id":2}]' \
  | data-transform unique id -f json --minify
# → [{"id":1},{"id":2}]

echo '[{"a":1},{"a":1},{"b":2}]' \
  | data-transform unique -f json --minify
# → [{"a":1},{"b":2}]
```

### Library use

```python
from data_transform import (
    convert,
    parse,
    serialize,
    get_path,
    pick_keys,
    omit_keys,
    filter_rows,
    sort_rows,
    unique_rows,
)

yaml_text = convert('{"a":1}', "json", "yaml")
data = parse("id,name\n1,x\n", "csv")
json_text = serialize(data, "json", pretty=True)
name = get_path({"user": {"name": "Ada"}}, "user.name")
slim = pick_keys({"id": 1, "name": "a", "note": "x"}, ["id", "name"])
adults = filter_rows([{"age": 36}, {"age": 22}], "age", "ge", "30")
ordered = sort_rows([{"id": 2}, {"id": 1}], "id")
deduped = unique_rows([{"id": 1}, {"id": 1}], "id")
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

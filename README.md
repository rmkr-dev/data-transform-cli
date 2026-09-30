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
| `rename` | Rename top-level keys (`OLD NEW` pairs) |
| `flatten` | Flatten nested objects into joined keys |
| `unflatten` | Expand joined keys back into nested objects |
| `filter` | Keep array items matching KEY OP VALUE |
| `sort` | Sort array of objects by top-level KEY |
| `unique` | Deduplicate array (by KEY or whole item) |
| `head` | First N items of a list |
| `tail` | Last N items of a list |
| `group-by` | Group array of objects by top-level KEY |
| `count` | Count items, per KEY value, or per group |

### Options (most commands)

- `[file]` — input path; omit or use `-` for stdin
- `-o, --output <file>` — write to a file instead of stdout
- `-f, --from <format>` — force input format: `json` | `yaml` | `csv` | `ndjson`
- `--minify` — compact JSON output (`to-json`, `select`, `pick`, `omit`, `rename`, `flatten`, `unflatten`, `filter`, `sort`, `unique`, `head`, `tail`, `group-by`, `count`)
- `--desc` — reverse sort order (`sort` only)
- `--sep <text>` — separator between nested keys (`flatten` and `unflatten`, default `.`)

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

### Rename and flatten

`rename` takes pairs of `OLD NEW` and maps over an object or each object in an array, the same way `pick` and `omit` do. Missing old keys are left alone. A later pair wins when the same old key is given twice. Renames are one pass over the original keys: `a→b` together with `b→c` leaves the value of `a` under `b`.

`flatten` collapses nested objects into top-level keys joined by `--sep` (default `.`). A list root is flattened item by item. Nested lists stay as values. Empty objects stay empty. A number, string, or other non-object root is returned unchanged.

```bash
# Rename top-level keys (several pairs)
echo '{"id":1,"name":"Ada","note":"x"}' \
  | data-transform rename name title note comment -f json --minify
# → {"id":1,"title":"Ada","comment":"x"}

# Same mapping over an array; missing keys are a no-op
echo '[{"name":"Ada"},{"id":2},1]' \
  | data-transform rename name title -f json --minify
# → [{"title":"Ada"},{"id":2},1]

# Flatten nested objects; lists stay as values
echo '{"user":{"name":"Ada","city":"London"},"tags":["a","b"]}' \
  | data-transform flatten -f json --minify
# → {"user.name":"Ada","user.city":"London","tags":["a","b"]}

# Custom separator
echo '{"user":{"name":"Ada"}}' \
  | data-transform flatten --sep _ -f json --minify
# → {"user_name":"Ada"}
```

### Unflatten

`unflatten` is the inverse of `flatten`: it splits top-level keys on `--sep` (default `.`) and rebuilds nested objects. Like `flatten`, it maps over a list root and returns non-object roots and items unchanged. It does not rebuild lists, so a segment like `0` stays an object key. Keys are split literally, so an empty segment (`a..b`) becomes an empty key. If an object value and joined keys write to the same branch, they are merged. If a path runs into a non-object value, the later key wins. `unflatten` undoes `flatten` exactly as long as the original keys don't contain the separator.

```bash
echo '{"user.name":"Ada","user.addr.city":"London","tags":["a","b"]}' \
  | data-transform unflatten -f json --minify
# → {"user":{"name":"Ada","addr":{"city":"London"}},"tags":["a","b"]}

echo '[{"user_name":"Ada"},{"user_name":"Bob"}]' \
  | data-transform unflatten --sep _ -f json --minify
# → [{"user":{"name":"Ada"}},{"user":{"name":"Bob"}}]

# Round trip
data-transform flatten nested.json | data-transform unflatten
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

### Head and tail

`head` and `tail` require a **list** root, same as `filter`, `sort`, and `unique`. `N` is a non-negative integer. A count past the end returns the items that exist; `0` returns an empty list.

```bash
echo '[{"id":1},{"id":2},{"id":3}]' \
  | data-transform head 2 -f json --minify
# → [{"id":1},{"id":2}]

echo '[{"id":1},{"id":2},{"id":3}]' \
  | data-transform tail 1 -f json --minify
# → [{"id":3}]

echo '[1,2,3]' | data-transform head 0 -f json --minify
# → []
```

### Group-by and count

`group-by KEY` requires a **list** root. It returns an object that maps each value of top-level `KEY` to the list of items that have it. Groups appear in the order they are first seen, and items keep their input order. Group labels are the value itself for strings; any other value becomes compact JSON text (`1` → `"1"`, `true` → `"true"`, `null` → `"null"`). This means `1` and `"1"` end up in the same group, which suits CSV input where every value is a string. Non-object items and objects without `KEY` are dropped.

`count` counts records:

- `count` on a list prints its length as a number.
- `count KEY` on a list prints an object of per-value counts, using the same labels and dropping rules as `group-by`.
- `count` on the output of `group-by` (an object whose values are all lists) prints the size of each group.

Any other root is an error.

```bash
echo '[{"team":"a","id":1},{"team":"b","id":2},{"team":"a","id":3},{"id":4}]' \
  | data-transform group-by team -f json --minify
# → {"a":[{"team":"a","id":1},{"team":"a","id":3}],"b":[{"team":"b","id":2}]}

echo '[{"id":1},{"id":2},{"id":3}]' | data-transform count -f json
# → 3

echo '[{"team":"a"},{"team":"b"},{"team":"a"}]' \
  | data-transform count team -f json --minify
# → {"a":2,"b":1}

# Count per group from group-by output
data-transform group-by team people.json | data-transform count --minify
# → {"a":2,"b":1}

# Works with NDJSON / CSV too
data-transform count status events.ndjson
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
    rename_keys,
    flatten_object,
    unflatten_object,
    filter_rows,
    sort_rows,
    unique_rows,
    head_rows,
    tail_rows,
    group_rows,
    count_rows,
)

yaml_text = convert('{"a":1}', "json", "yaml")
data = parse("id,name\n1,x\n", "csv")
json_text = serialize(data, "json", pretty=True)
name = get_path({"user": {"name": "Ada"}}, "user.name")
slim = pick_keys({"id": 1, "name": "a", "note": "x"}, ["id", "name"])
renamed = rename_keys({"id": 1, "name": "a"}, {"name": "title"})
flat = flatten_object({"user": {"name": "Ada"}, "tags": ["x"]})
nested = unflatten_object({"user.name": "Ada"})
adults = filter_rows([{"age": 36}, {"age": 22}], "age", "ge", "30")
ordered = sort_rows([{"id": 2}, {"id": 1}], "id")
deduped = unique_rows([{"id": 1}, {"id": 1}], "id")
first = head_rows([{"id": 1}, {"id": 2}, {"id": 3}], 2)
last = tail_rows([{"id": 1}, {"id": 2}, {"id": 3}], 1)
by_team = group_rows([{"team": "a"}, {"team": "b"}], "team")
total = count_rows([{"id": 1}, {"id": 2}])
per_team = count_rows([{"team": "a"}, {"team": "a"}], "team")
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

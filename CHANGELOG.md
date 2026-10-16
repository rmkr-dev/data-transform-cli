# Changelog

All notable changes to this project are listed here. Versions follow [Semantic Versioning](https://semver.org/). From 1.0.0, documented commands, options, exit codes, and output shapes only break in a new major version.

## [1.0.0] - 2026-10-16

### Added

- `validate [file]` checks a list of records (or one object) and exits `0` when valid, `1` when not, and `2` when the check can't run.
  - `-r, --require PATH`, `--type PATH=TYPE[|TYPE...]`, and `-u, --unique PATH`, all repeatable and using dotted paths.
  - `-s, --schema FILE` reads `required`, `types`, and `unique` from a JSON or YAML file; command-line flags are added on top.
  - `--coerce` lets numeric, `true` / `false`, and empty strings satisfy `integer`, `number`, `boolean`, and `null`, for CSV input.
  - `--max-errors N` and `-q, --quiet`. `-t csv` / `-t ndjson` writes only the error rows.
- `validate_rows` and `load_schema` in the library API.
- CI now builds the sdist and wheel, installs the wheel in a clean virtual environment, and smoke-tests the `data-transform` command.
- A Stability section in the README describing what 1.0.0 commits to.

## [0.8.0] - 2026-10-14

### Added

- `-t, --to json|yaml|csv|ndjson` on every shaping command (`select`, `pick`, `omit`, `rename`, `flatten`, `unflatten`, `filter`, `sort`, `unique`, `head`, `tail`, `group-by`, `count`, `stats`, `join`), so results can be written as YAML, CSV, or NDJSON without a second `to-*` step.
- This changelog.

### Changed

- When `--to` is not given, shaping commands pick the output format from the `--output` file extension (for example `-o out.csv` writes CSV). Before, they always wrote JSON whatever the file name. Unknown extensions and stdout still get JSON.
- Writing a non-list result as CSV now fails with a message that points to `--to json` or `--to yaml`.

## [0.7.0] - 2026-10-12

### Added

- `join KEY --with RIGHT_FILE [file]` with `--how inner|left` and `--right-from` to join two arrays of objects on a top-level key.

## [0.6.0] - 2026-10-10

### Added

- `stats FIELD` for count / sum / min / max / avg of a numeric field, on a list or on `group-by` output.

## [0.5.0] - 2026-09-30

### Added

- `group-by KEY`, `count [KEY]`, and `unflatten` (with `--sep`).

## [0.4.0] - 2026-09-28

### Added

- `rename OLD NEW ...`, `flatten` (with `--sep`), `head N`, and `tail N`.

## [0.3.0] - 2026-09-24

### Added

- `filter KEY OP VALUE`, `sort KEY` (with `--desc`), and `unique [KEY]`.

## [0.2.0] - 2026-09-21

### Added

- NDJSON / JSON Lines input and output (`to-ndjson`, `.ndjson` / `.jsonl` detection).
- `select`, `pick`, and `omit`.

## [0.1.0] - 2026-09-11

### Added

- Python implementation of the CLI: `to-json`, `to-yaml`, `to-csv`, `pretty`, and `minify` with format detection for JSON, YAML, and CSV.

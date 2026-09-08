# data-transform-cli

Node.js ESM CLI for **YAML ↔ JSON ↔ CSV** transforms. Built for shell pipelines and local scripts.
Streaming-friendly where practical (stdin/stdout; full documents buffered for parse safety).

Requires **Node.js 20+**.

## Install

```bash
npm install -g .
# or run without installing:
npx --yes . to-json ./data.yaml
```

From a clone of this repo:

```bash
npm install
npm link   # optional: exposes data-transform on your PATH
```

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

```js
import { convert, parse, serialize } from "data-transform-cli";

const yaml = convert("{\"a\":1}", "json", "yaml");
const data = parse("id,name\n1,x\n", "csv");
const json = serialize(data, "json", { pretty: true });
```

## CSV notes

CSV support is intentionally small and robust (RFC 4180-ish): quoted fields, escaped quotes (`""`), and newlines inside quotes. Object arrays use a header row; all cell values are strings when parsed from CSV.

## Development

```bash
npm install
npm test
```

Tests use Node built-in `node:test` runner with fixtures under `test/fixtures/` for JSON/YAML/CSV round-trips and CLI smoke checks.

## Extending with coding agents

### GitHub Copilot

- Open this repo in VS Code / JetBrains with Copilot enabled.
- Prefer asking Copilot to follow existing modules (`src/convert.js`, `src/csv.js`) and to add `node:test` cases beside fixtures.
- Optional: add workspace guidance under `.github/copilot-instructions.md`.

### Claude Code

- From the repo root, open the folder in Claude Code (or its CLI).
- Point it at `CONTRIBUTING.md` and ask for a failing test first, then implementation.
- Keep changes ESM-compatible and avoid adding heavy CSV libraries unless needed.

### OpenAI Codex

- Open the project in Codex with this directory as the workspace.
- Ask for command-level changes (`to-json`, `to-csv`, ...) and matching CLI tests in `test/cli.test.js`.
- Remind the agent: no company names, no personal contacts, no generator authorship comments in committed files.

## License

MIT — see [LICENSE](./LICENSE).

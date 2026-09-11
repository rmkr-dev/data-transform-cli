# Contributing

## Setup

- Use Python 3.11 or newer
- Install with `pip install -e ".[dev]"`
- Run tests with `pytest`

## Guidelines

- Keep the public CLI entry as the `data-transform` console script.
- Prefer small, focused changes with tests for round-trips and edge cases.
- Do not add company names or personal contacts in committed files.
- Match existing style: errors on stderr as `error: …`, exit code 1 on failure, UTF-8 I/O.

## Pull requests

1. Fork and branch from main.
2. Add or update tests under `tests/`.
3. Ensure `pytest` passes.
4. Open a PR with a short summary of the change and why.

# Contributing

## Setup

- Use Node 20 or newer
- Install dependencies with the package manager
- Run the test script from package.json

## Guidelines

- Keep the CLI ESM-only (type module).
- Prefer small, focused changes with tests for round-trips and edge cases.
- Do not add company names or personal contacts in committed files.
- Match existing style: errors on stderr, exit code 1 on failure, UTF-8 I/O.

## Pull requests

1. Fork and branch from main.
2. Add or update tests under test/.
3. Ensure the test script passes.
4. Open a PR with a short summary of the change and why.

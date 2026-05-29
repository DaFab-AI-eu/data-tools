# pydafab

Python package providing utilities and tools for working with Copernicus data as
part of the DaFab (AI Factory for Copernicus Data at Scale) project.

## Features

- Search and ingest Copernicus products using STAC conventions
- Helpers to stage and archive products with Dasi/pydasi
- Small CLI and programmatic API for scripted workflows

## Installation

Install from PyPI:

```bash
pip install pydafab
```

Or install editable from source (recommended for development):

```bash
git clone <repo-url>
cd pydafab
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Quick usage

Example (programmatic):

```python
from pydafab import CopernicusIngestor, IngestTool

ingestor = CopernicusIngestor()
ingest_tool = IngestTool(ingestor)

params = {
	"max_items": 5,
	"collections": "sentinel-2-l2a",
	"bbox": [6.95, 50.65, 7.25, 50.85],
}

for product in ingestor.search(params):
	ingest_tool.archive_product(product)
```

For CLI-style helpers see the `ingest.py` and `search.py` modules in the
`copernicus/` directory.

## Development

This project provides `just` targets (see `Justfile`) to manage the development environment and common tasks. `just` and `uv` should be installed on your machine.

Common `just` targets:

- `just setup` — create the `.venv`, compile and sync requirements, and install the project in editable mode
- `just venv` — create a project virtualenv via `uv`
- `just compile` — compile dependencies into `requirements.txt`
- `just sync` — sync the locked requirements into `.venv`
- `just dev` — install the package in editable mode (`pip install -e .`)
- `just check` — run linting (uses `ruff`) and depends on `setup`
- `just test` — run the test suite (depends on `check`)
- `just clean` — remove build artifacts and virtualenv
- `just dist` — run tests and build distribution packages

Examples:

```bash
# one-time setup (creates .venv and installs editable package)
just setup

# run tests
just test

# run lint and quick checks
just check

# clean build artifacts
just clean

# build distributable packages
just dist
```

## Contributing

Please follow the repository Code of Conduct and open PRs against the main branch.

## License

This project is licensed under the Apache License 2.0.

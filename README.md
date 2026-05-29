# DaFab Data Tools

`pydafab` is a Python package that provides tools for accessing and archiving data from the Copernicus Data Space using STAC (SpatioTemporal Asset Catalog) standards. It leverages the Dasi data management tool (`pydasi`) for efficient data ingestion and management.

## Repository layout

- `copernicus/`: helper modules and ingest/search/stage scripts for Copernicus data.
- `pydafab/` and `src/pydafab/`: the Python package sources and project metadata.
- `tests/`: unit and integration tests.
- `rucio/`, `scripts/`, `volumes/`: deployment, storage and auxiliary scripts/configs.
- `Dockerfile`, `Justfile`, and CI-related files at the repository root.

## Installation (recommended: uv + just)

This project uses `uv` as the package manager and `just` for simple developer commands. `uv` provides fast resolution, a `.venv` workflow, and `pip`-compatible commands.

1. Clone the repository:

```bash
git clone https://github.com/yourusername/pydafab.git
cd pydafab
```

2. Install `uv` (one-time):

```bash
# via the installer
curl -LsSf https://astral.sh/uv/install.sh | sh
# or via pipx
pipx install uv
```

3. Install `just` (if not already installed).

```bash
# via the installer
curl -LsSf https://just.systems/install.sh | sh
# or via package manager, e.g. on Ubuntu
sudo apt install just
```

4. Set up the project environment and install dependencies:

```bash
# uses the Justfile to create .venv, compile/sync requirements, and install editable
just setup

# activate when needed
source .venv/bin/activate

# run tests
just test
```

## Alternative: plain venv + pip

If you prefer not to use `uv`, the repo also provides `requirements.txt` and `requirements-dev.txt` at the project root. Create a virtualenv and install with `pip`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # optional
pip install -e pydafab
```

## Configuration

Requires Copernicus credentials via environment variables.

**Local Development:**

Edit dev.env with your credentials

*vscode devcontainer is configured to use dev.env*

**Argo Workflows:**

create the secret:
```bash
kubectl create secret generic copernicus-creds \
  --from-literal=access-key=your_access_key \
  --from-literal=secret-key=your_secret_key
```

reference it in the workflow:
```yaml
templates:
- name: ingest
  container:
    image: your-registry/data-tools:latest
    env:
    - name: AWS_ACCESS_KEY_ID
      valueFrom:
        secretKeyRef:
          name: copernicus-creds
          key: access-key
    - name: AWS_SECRET_ACCESS_KEY
      valueFrom:
        secretKeyRef:
          name: copernicus-creds
          key: secret-key
```

## Usage

Example (after installing and activating `.venv`):

```python
from pydafab import CopernicusIngestor, IngestTool

ingestor = CopernicusIngestor()
ingest_tool = IngestTool(ingestor)

search_params = {
  "max_items": 10,
  "collections": "sentinel-2-l2a",
  "bbox": [6.95, 50.65, 7.25, 50.85],
  "datetime": "2025-01-21/2025-01-23",
  "cloud_cover_max": 100,
}

products = ingestor.search(search_params)

for product in products:
  ingest_tool.archive_product(product)
```

## Code of Conduct

Please note that the `pydafab` project is released with a
Code of Conduct. For more information, see the [CODE OF CONDUCT](CONDUCT.md) file.

## Acknowledgements

This work is funded by the Horizon 2020 programme, and is developed and maintained by ECMWF (European Centre for Medium-Range Weather Forecasts).
The grant number for the [DaFab (AI Factory for Copernicus Data at Scale)](https://www.dafab-ai.eu/) EU Horizon project is 101128693.

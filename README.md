# DaFab Data Tools

`pydafab` is a Python package that provides tools for accessing and archiving data from the Copernicus Data Space using STAC (SpatioTemporal Asset Catalog) standards. It leverages the Dasi data management tool (pydasi) for efficient data ingestion and management.

## Installation

Here's how to install and set up `pydafab`:

1. Download a copy of `pydafab` locally.

```console
$ git clone https://github.com/yourusername/pydafab.git
$ cd pydafab
```

2. Create and activate a virtual environment for `pydafab`:

    ```console
    $ python -m venv .venv
    $ source .venv/bin/activate
    ```

3. Install `pydafab`:

    ```console
    $ pip install pydafab
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
Here's a simple example of how to use `pydafab` to search for and archive products from the Copernicus Data Space:

```python
from pydafab import CopernicusIngestor, IngestTool

# Create an instance of the CopernicusIngestor
ingestor = CopernicusIngestor()

# Create an instance of the IngestTool
ingest_tool = IngestTool(ingestor)

# Define search parameters
search_params = {
    "max_items": 10,
    "collections": "sentinel-2-l2a",
    "bbox": [6.95, 50.65, 7.25, 50.85],
    "datetime": "2025-01-21/2025-01-23",
    "cloud_cover_max": 100,
}

# Search for products
products = ingestor.search(search_params)

# Archive each product
for product in products:
    ingest_tool.archive_product(product)
```

## Code of Conduct

Please note that the `pydafab` project is released with a
Code of Conduct. For more information, see the [CODE OF CONDUCT](CONDUCT.md) file.

## Acknowledgements

This work is funded by the Horizon 2020 programme, and is developed and maintained by ECMWF (European Centre for Medium-Range Weather Forecasts).
The grant number for the [DaFab (AI Factory for Copernicus Data at Scale)](https://www.dafab-ai.eu/) EU Horizon project is 101128693.

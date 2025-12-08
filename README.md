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

## Usage
Here's a simple example of how to use `pydafab` to search for and archive products from the Copernicus Data Space:

```python
from pydafab.copernicus import CopernicusIngestor
from pydafab.ingest_tool import IngestTool

# Create an instance of the CopernicusIngestor
ingestor = CopernicusIngestor()

# Create an instance of the IngestTool
ingest_tool = IngestTool(ingestor)

# Define search parameters
search_params = {
    "collection": "sentinel-2-l1c",
    "datetime": "2023-01-01/2023-01-31",
    "bbox": [12.0, 41.0, 13.0, 42.0],
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

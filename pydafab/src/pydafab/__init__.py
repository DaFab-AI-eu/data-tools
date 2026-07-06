# read version from installed Product
from importlib.metadata import version

__version__ = version("pydafab")

from .errors import (
    AssetFetchError,
    AssetNotFoundError,
    InvalidArgumentError,
    ProductFetchError,
    ProductNotFoundError,
)
from .copernicus import CopernicusIngestor
from .ingest_tool import DasiProductHandler

__all__ = [
    "AssetFetchError",
    "AssetNotFoundError",
    "InvalidArgumentError",
    "ProductFetchError",
    "ProductNotFoundError",
    "CopernicusIngestor",
    "DasiProductHandler",
]

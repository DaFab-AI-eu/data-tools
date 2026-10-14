# read version from installed Product
import logging
from importlib.metadata import version

from .errors import (
    AssetFetchError,
    AssetIntegrityError,
    AssetNotFoundError,
    InvalidArgumentError,
    ProductFetchError,
    ProductNotFoundError,
)
from .copernicus import CopernicusIngestor
from .ingest_tool import DasiProductHandler
from .helpers import media_subtype

__version__ = version("pydafab")

logging.getLogger("pydafab").addHandler(logging.NullHandler())

__all__ = [
    "AssetFetchError",
    "AssetIntegrityError",
    "AssetNotFoundError",
    "InvalidArgumentError",
    "ProductFetchError",
    "ProductNotFoundError",
    "CopernicusIngestor",
    "DasiProductHandler",
    "media_subtype",
]

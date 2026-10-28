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
from .planetary_computer import PlanetaryComputerIngestor
from .helpers import media_subtype
from .ingestor import StacIngestor

__version__ = version("pydafab")

INGESTORS: dict[str, type[StacIngestor]] = {
    "sentinel-2-l2a": CopernicusIngestor,
    "sentinel-1-grd": CopernicusIngestor,
    "sentinel-1-slc": CopernicusIngestor,
    "sentinel-1-rtc": PlanetaryComputerIngestor,
}

logging.getLogger("pydafab").addHandler(logging.NullHandler())

__all__ = [
    "INGESTORS",
    "AssetFetchError",
    "AssetIntegrityError",
    "AssetNotFoundError",
    "InvalidArgumentError",
    "ProductFetchError",
    "ProductNotFoundError",
    "CopernicusIngestor",
    "DasiProductHandler",
    "PlanetaryComputerIngestor",
    "StacIngestor",
    "media_subtype",
]

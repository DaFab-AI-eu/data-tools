# read version from installed Product
import logging
from importlib.metadata import version

from .errors import InvalidArgumentError, ProductNotFoundError
from .copernicus import CopernicusIngestor
from .ingest_tool import DasiProductHandler
from .helpers import media_subtype

__version__ = version("pydafab")

logging.getLogger("pydafab").addHandler(logging.NullHandler())

__all__ = [
    "InvalidArgumentError",
    "ProductNotFoundError",
    "CopernicusIngestor",
    "DasiProductHandler",
    "media_subtype",
]

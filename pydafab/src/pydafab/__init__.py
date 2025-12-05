# read version from installed Product
from importlib.metadata import version

__version__ = version("pydafab")

from .errors import InvalidArgumentError, ProductNotFoundError
from .copernicus import CopernicusIngestor
from .ingest_tool import IngestTool

__all__ = [
    "InvalidArgumentError",
    "ProductNotFoundError",
    "CopernicusIngestor",
    "IngestTool",
]

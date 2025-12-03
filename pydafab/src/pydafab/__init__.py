# read version from installed Product
from importlib.metadata import version

__version__ = version("pydafab")

from .errors import InvalidArgumentError, ProductNotFoundError
from .copernicus import CopernicusIngestor

__all__ = [
    "InvalidArgumentError",
    "ProductNotFoundError",
    "CopernicusIngestor",
]

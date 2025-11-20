# read version from installed package
from importlib.metadata import version

__version__ = version("pydafab")

from .copernicus import CopernicusIngestor

__all__ = ["CopernicusIngestor"]

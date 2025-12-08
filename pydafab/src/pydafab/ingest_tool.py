"""

DASI Ingest Tool

"""

import logging
import sys

from pydasi import Dasi

from .copernicus import StacIngestor
from .errors import AssetNotFoundError, ProductNotFoundError

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"
__version__ = "0.0.1"
__author__ = "Metin Cakircali"
__email__ = "metin.cakircali@ecmwf.int"


class IngestTool:

    def __init__(self, ingestor: StacIngestor):
        self.__ingestor = ingestor
        self.__verbose = ingestor.verbose

    def archive_product(self, product):
        """Ingest product from Copernicus STAC and archive using Dasi."""

        if self.__verbose:
            print(f"Archiving product: {product.id}")

        try:
            key, data = self.__ingestor.fetch_product(product)
        except ProductNotFoundError:
            sys.exit(f"Product [{product.id}] not found!")

        dasi = Dasi("/tools/copernicus/ingest/metadata.yml")
        dasi.archive(key, data)

        if self.__verbose:
            print(f"Finished archiving product: {product.id}")

    def archive_assets(self, product, asset_keys):
        """Given product, archive assets from Copernicus S3 using Dasi."""

        if self.__verbose:
            print(f"Archiving assets of product: {product.id}")

        dasi = Dasi("/tools/copernicus/ingest/assets.yml")

        for asset_key in asset_keys:
            try:
                key, data = self.__ingestor.fetch_asset(product, asset_key)
            except AssetNotFoundError:
                logging.warning(f"Asset [{asset_key}] not found in product [{product.id}]!")
                continue
            dasi.archive(key, data)

        if self.__verbose:
            print(f"Finished archiving assets of product: {product.id}")

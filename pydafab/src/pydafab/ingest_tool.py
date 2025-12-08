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
        """
        Archive a product using the ingestor and Dasi metadata tool

        :param self: Instance of IngestTool
        :param product: Product object to be archived
        """

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
        """
        Archive specified assets of a product using Dasi

        :param self: Instance of IngestTool
        :param product: Product whose assets will be archived
        :param asset_keys: List of asset keys to archive
        """

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

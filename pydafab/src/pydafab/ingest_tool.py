"""

DASI Ingest Tool

"""

import logging
import sys

from pydasi import Dasi

from .copernicus import StacIngestor
from .errors import AssetNotFoundError, ProductNotFoundError

logger = logging.getLogger(__name__)

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"
__version__ = "0.0.1"
__author__ = "Metin Cakircali"
__email__ = "metin.cakircali@ecmwf.int"


class IngestTool:

    def __init__(self, ingestor: StacIngestor):
        self.__ingestor = ingestor
        self.__verbose = ingestor.verbose
        
        if self.__verbose:
            logger.setLevel(logging.DEBUG)

    def archive_product(self, product):
        """
        Archive a product using the ingestor and Dasi metadata tool

        :param self: Instance of IngestTool
        :param product: Product object to be archived
        """

        try:
            key, data = self.__ingestor.fetch_product(product)
        except ProductNotFoundError:
            sys.exit(f"Product [{product.id}] not found!")

        logger.debug(f"Archiving product: {product.id} with key: {key}")

        # TODO: Make the path to the Dasi config file configurable
        dasi = Dasi("/tools/copernicus/ingest/metadata.yml")
        dasi.archive(key, data)

        logger.info(f"Archived product: {product.id}")

    def archive_assets(self, product, asset_keys):
        """
        Archive specified assets of a product using Dasi

        :param self: Instance of IngestTool
        :param product: Product whose assets will be archived
        :param asset_keys: List of asset keys to archive
        """

        logger.debug(f"Archiving assets of product: {product.id} with keys: {asset_keys}")

        if product is None:
            sys.exit(f"Product [{product.id}] not found!")

        dasi = Dasi("/tools/copernicus/ingest/assets.yml")

        for asset_key in asset_keys:
            try:
                key, data = self.__ingestor.fetch_asset(product, asset_key)
            except AssetNotFoundError:
                logger.warning(f"Asset [{asset_key}] not found in product [{product.id}]!")
                continue
            logger.debug(f"Archiving asset: {asset_key} with key: {key}")
            dasi.archive(key, data)
            logger.info(f"Archived asset: {asset_key}")

        logger.debug(f"Finished archiving assets of product: {product.id}")

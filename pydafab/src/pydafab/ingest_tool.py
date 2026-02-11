import logging
import sys

from pydasi import Dasi

from .copernicus import StacIngestor
from .errors import AssetNotFoundError, ProductNotFoundError

logger = logging.getLogger(__name__)

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"


class DasiProductHandler:

    def __init__(self, config_dir, ingestor: StacIngestor):
        """Initializes with a directory path to the Dasi configurations and an ingestor instance."""
        self.config_dir = config_dir
        if not config_dir.is_dir():
            raise NotADirectoryError(f"Config directory is not a directory: {config_dir}")
        self.ingestor = ingestor

    def archive_product(self, product, modifier=None):
        """
        Archive a product using the ingestor and Dasi metadata tool

        :param product: Product object to be archived
        """

        try:
            key, data = self.ingestor.fetch_product(product)
        except ProductNotFoundError:
            sys.exit(f"Product [{product.id}] not found!")

        logger.debug(f"Archiving product: {product.id} with key: {key}")

        if modifier:
            data = modifier.modify_product_metadata(data)

        dasi = Dasi(self.config_dir / "metadata.yml")
        dasi.archive(key, data)

        logger.info(f"Archived product: {product.id}")

    def archive_assets(self, product, asset_keys, modifier=None):
        """
        Archive specified assets of a product using Dasi

        :param product: Product whose assets will be archived
        :param asset_keys: List of asset keys to archive
        """

        logger.debug(f"Archiving assets of product: {product.id} with keys: {asset_keys}")

        for asset_key in asset_keys:
            try:
                key, data = self.ingestor.fetch_asset(product, asset_key)
            except AssetNotFoundError:
                logger.warning(f"Asset [{asset_key}] not found in product [{product.id}]!")
                continue
            except ProductNotFoundError:
                sys.exit(f"Product [{product.id}] not found!")

            logger.debug(f"Archiving asset: {asset_key} with DASI key: {key}")

            if modifier:
                data = modifier.modify_asset(asset_key, data)

            dasi = Dasi(self.config_dir / "assets.yml")
            dasi.archive(key, data)

            logger.info(f"Archived asset: {asset_key}")

        # logger.info(f"Archived assets of product: {product.id}")

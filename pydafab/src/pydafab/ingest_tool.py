import logging
import sys
from pathlib import Path

from pydasi import Dasi

from .copernicus import StacIngestor
from .errors import AssetNotFoundError, ProductNotFoundError

logger = logging.getLogger(__name__)

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"


class DasiProductHandler:

    def __init__(self, ingestor: StacIngestor, config_dir: str = "."):
        """Initializes with a directory path to the Dasi configurations and an ingestor instance."""
        self.config_dir = Path(config_dir)
        if not Path(self.config_dir).is_dir():
            raise NotADirectoryError(f"Parameter 'config_dir' is not a directory: {config_dir}")
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

        if modifier and hasattr(modifier, "modify_product_metadata"):
            data = modifier.modify_product_metadata(data)

        dasi = Dasi(str(Path(self.config_dir) / "metadata.yml"))
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

            if modifier and hasattr(modifier, "modify_asset"):
                data = modifier.modify_asset(asset_key, data)

            dasi = Dasi(str(self.config_dir / "assets.yml"))
            dasi.archive(key, data)

            logger.info(f"Archived asset: {asset_key}")

    def retrieve_metadata(self, product):
        """Retrieve metadata by product ID."""

        # Dasi query values must be lists
        query = {k: [v] for k, v in self.ingestor.make_key_from_product(product).items()}

        dasi = Dasi(str(self.config_dir / "metadata.yml"))

        retrieved = dasi.retrieve(query)

        if len(retrieved) == 1:
            logger.info(f"Retrieved product metadata for {product.id}")
            for item in retrieved:
                return item.data
        elif len(retrieved) == 0:
            logger.info(f"No product metadata found for Query={query}")
        else:
            sys.exit(f"Multiple results found for Query={query}")

    def retrieve_assets(self, product, asset_keys):

        assets: dict[str, bytearray] = {}
        dasi = Dasi(str(self.config_dir / "assets.yml"))

        for asset_key in asset_keys:
            # Dasi query values must be lists
            asset = product.assets[asset_key]
            query = {k: [v] for k, v in self.ingestor.make_asset_key_from_product(product, asset).items()}

            retrieved = dasi.retrieve(query)

            if len(retrieved) == 1:
                logger.info(f"Retrieved asset for {product.id}")
                for item in retrieved:
                    assets[asset_key] = item.data
            elif len(retrieved) == 0:
                logger.info(f"No asset found for Query={query}")
            else:
                sys.exit(f"Multiple results found for Query={query}")

        return assets

import logging
import sys
from pathlib import Path
from typing import Iterator, Any

from pystac import Item
from pydasi import Dasi, dasi

from pydafab.dasi_product import DasiProduct

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

    def archive_product(self, product: Item, modifier: Any = None) -> None:
        """
        Archive a product using the ingestor and Dasi metadata tool

        Args:
            product: Product object to be archived.
            modifier: Optional tool to modify the metadata before download.
        """

        try:
            data = self.ingestor.fetch_product(product)
            key = DasiProduct(source=self.ingestor.source, product=product).key
        except ProductNotFoundError as e:
            raise ProductNotFoundError(f"Product [{product.id}] not found!") from e

        logger.debug("Archiving product: %s with key: %s", product.id, key)

        if modifier and hasattr(modifier, "modify_product_metadata"):
            data = modifier.modify_product_metadata(key, data)

        dasi = Dasi(str(Path(self.config_dir) / "metadata.yml"))
        dasi.archive(key, data)

        logger.info("Archived product: %s", product.id)

    def archive_assets(self, product: Item, asset_keys: list[str], modifier: Any = None) -> None:
        """
        Archive specified assets of a product using Dasi

        Args:
            product: Product whose assets will be archived.
            asset_keys: List of asset keys to archive.
            modifier: Optional tool to modify the asset before download.
        """

        logger.debug("Archiving assets of product: %s with keys: %s", product.id, asset_keys)

        for asset_key in asset_keys:
            try:
                asset, data = self.ingestor.fetch_asset(product, asset_key)
                key = DasiProduct(source=self.ingestor.source, product=product).set_asset(asset)
            except AssetNotFoundError:
                logger.warning("Asset [%s] not found in product [%s]!", asset_key, product.id)
                continue
            except ProductNotFoundError as e:
                raise ProductNotFoundError(f"Product [{product.id}] not found!") from e

            logger.debug("Archiving asset: %s with DASI key: %s", asset_key, key)

            if modifier and hasattr(modifier, "modify_asset"):
                data = modifier.modify_asset(asset_key, data)

            dasi = Dasi(str(self.config_dir / "assets.yml"))
            dasi.archive(key, data)

            logger.info("Archived asset: %s", asset_key)

    def retrieve_metadata(self, product: Item) -> Any:
        """
        Retrieve metadata by product ID.

        Args:
            product: Product to retrieve metadata for.

        Returns:
            The retrieved metadata data.

        Raises:
            RuntimeError: If multiple results are found.
        """

        # Dasi query values must be lists
        query = {k: [v] for k, v in DasiProduct(source=self.ingestor.source, product=product).key.items()}

        dasi = Dasi(str(self.config_dir / "metadata.yml"))

        retrieved = dasi.retrieve(query)

        for item in retrieved:
            yield item.data

    def retrieve_assets(self, product: Item, asset_keys: list[str]):
        """
        Retrieve assets for a product as an iterator.

        Args:
            product: The product object containing asset definitions.
            asset_keys: A list of asset keys to retrieve.

        Yields:
            A tuple of (asset_key, asset_data).
        """

        for asset_key in asset_keys:
            # Dasi query values must be lists
            query = {
                k: [v]
                for k, v in DasiProduct(source=self.ingestor.source, product=product)
                .set_asset(product.assets[asset_key])
                .items()
            }

            dasi = Dasi(str(self.config_dir / "assets.yml"))
            retrieved = dasi.retrieve(query)

            for item in retrieved:
                yield asset_key, item.key, item.data

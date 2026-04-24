import logging
import sys
from pathlib import Path
from typing import Iterator, Any

from pystac import Item
from pydasi import Dasi, dasi

from pydafab.dasi_copernicus import CopernicusKey

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
            key = CopernicusKey.from_stac(self.ingestor.source, product)
        except ProductNotFoundError as e:
            raise ProductNotFoundError(f"Product [{product.id}] not found!") from e

        logger.debug("Archiving product: %s with key: %s", product.id, key)

        if modifier and hasattr(modifier, "modify_product_metadata"):
            data = modifier.modify_product_metadata(key, data)

        dasi = Dasi(str(Path(self.config_dir) / "metadata.yml"))
        dasi.archive(key, data)

        logger.info("Archived product: %s", product.id)

    def archive_assets(self, product: Item, asset_names: list[str], modifier: Any = None) -> None:
        """
        Archive specified assets of a product using Dasi

        Args:
            product: Product whose assets will be archived.
            asset_names: List of asset names to archive.
            modifier: Optional tool to modify the asset before download.
        """

        logger.debug("Archiving assets of product: %s with names: %s", product.id, asset_names)

        for asset_name in asset_names:
            try:
                _asset, data = self.ingestor.fetch_asset(product, asset_name)
                key = CopernicusKey.from_stac(self.ingestor.source, product, asset_name)
            except AssetNotFoundError:
                logger.warning("Asset [%s] not found in product [%s]!", asset_name, product.id)
                continue
            except ProductNotFoundError as e:
                raise ProductNotFoundError(f"Product [{product.id}] not found!") from e

            logger.debug("Archiving asset: %s with DASI key: %s", asset_name, key)

            if modifier and hasattr(modifier, "modify_asset"):
                data = modifier.modify_asset(key, data)

            dasi = Dasi(str(self.config_dir / "assets.yml"))
            dasi.archive(key, data)

            logger.info("Archived asset: %s", asset_name)

    def retrieve_metadata(self, product_id: str) -> Iterator[bytes]:
        """
        Retrieve product metadata from Dasi by product ID.

        Args:
            product_id: Sentinel product ID (S1 or S2 compact naming).

        Yields:
            The metadata bytes for each matching record.
        """

        key = CopernicusKey.from_product_id(self.ingestor.source, product_id)
        query = {k: [v] for k, v in key.items()}
        dasi = Dasi(str(self.config_dir / "metadata.yml"))
        for item in dasi.retrieve(query):
            yield item.data

    def retrieve_assets(
        self, product_id: str, asset_names: list[str]
    ) -> Iterator[tuple[str, dict, bytes]]:
        """
        Retrieve named assets for a product from Dasi.

        Args:
            product_id: Sentinel product ID (S1 or S2 compact naming).
            asset_names: Asset labels to retrieve (e.g. "WVP_10m"). Each name
                is queried independently against Dasi.

        Yields:
            Tuples of (asset_name, dasi_key, asset_data) per matching asset.
        """

        dasi = Dasi(str(self.config_dir / "assets.yml"))
        for asset_name in asset_names:
            key = CopernicusKey.from_product_id(self.ingestor.source, product_id, asset_name)
            query = {k: [v] for k, v in key.items()}
            for item in dasi.retrieve(query):
                yield asset_name, item.key, item.data

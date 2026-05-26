import logging
from pathlib import Path
from typing import Iterator, Any

from pystac import Item
from pydasi import Dasi

from pydafab.dasi_copernicus import CopernicusKey

from .copernicus import StacIngestor
from .errors import AssetNotFoundError

logger = logging.getLogger(__name__)

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"


class DasiProductHandler:

    def __init__(self, ingestor: StacIngestor, config_dir: str = "."):
        """Initializes with a directory path to the Dasi configurations and an ingestor instance."""
        self.config_dir = Path(config_dir)
        if not self.config_dir.is_dir():
            raise NotADirectoryError(f"Parameter 'config_dir' is not a directory: {config_dir}")
        self.ingestor = ingestor
        self.dasi_metadata = Dasi(str(self.config_dir / "metadata.yml"))
        self.dasi_assets = Dasi(str(self.config_dir / "assets.yml"))

    def _build_query(self, product_id: str, asset_name: str | None = None) -> dict:
        return CopernicusKey.from_product_id(self.ingestor.source, product_id, asset_name).to_dasi_query()

    def _product_archived(self, product_id: str) -> bool:
        found = False
        for _ in self.dasi_metadata.list(self._build_query(product_id)):
            found = True
        return found

    def _list_assets(self, product_id: str) -> set[str]:
        existing = set()
        for item in self.dasi_assets.list(self._build_query(product_id)):
            if item.key.has('asset_name'):
                existing.add(item.key['asset_name'])
        return existing

    def archive_product(self, product: Item, modifier: Any = None) -> None:
        """
        Archive a product using the ingestor and Dasi metadata tool

        Args:
            product: Product object to be archived.
            modifier: Optional tool to modify the metadata before download.
        """

        if self._product_archived(product.id):
            logger.info("Product %s already exists in DASI, skipping download", product.id)
            return

        data = self.ingestor.fetch_product(product)
        key = CopernicusKey.from_stac(self.ingestor.source, product)

        logger.debug("Archiving product: %s with key: %s", product.id, key)

        if modifier:
            data = modifier.modify_product_metadata(key, data)

        self.dasi_metadata.archive(key, data)
        self.dasi_metadata.flush()

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

        existing_assets = self._list_assets(product.id)
        existing_requested = existing_assets & set(asset_names)
        assets_to_fetch = [name for name in asset_names if name not in existing_assets]

        if existing_requested:
            logger.info(
                "Skipping %d existing asset(s) for product %s: %s",
                len(existing_requested),
                product.id,
                ", ".join(sorted(existing_requested))
            )

        archived_any = False
        for asset_name in assets_to_fetch:
            try:
                _asset, data = self.ingestor.fetch_asset(product, asset_name)
                key = CopernicusKey.from_stac(self.ingestor.source, product, asset_name)
            except AssetNotFoundError:
                logger.warning("Asset [%s] not found in product [%s]!", asset_name, product.id)
                continue

            logger.debug("Archiving asset: %s with DASI key: %s", asset_name, key)

            if modifier:
                data = modifier.modify_asset(key, data)

            self.dasi_assets.archive(key, data)
            archived_any = True

            logger.info("Archived asset: %s", asset_name)

        if archived_any:
            self.dasi_assets.flush()

    def retrieve_metadata(self, product_id: str) -> Iterator[bytes]:
        """
        Retrieve product metadata from Dasi by product ID.

        Args:
            product_id: Sentinel product ID (S1 or S2 compact naming).

        Yields:
            The metadata bytes for each matching record.
        """
        for item in self.dasi_metadata.retrieve(self._build_query(product_id)):
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
        base_query = self._build_query(product_id)

        available: dict[str, str] = {}
        for item in self.dasi_assets.list(base_query):
            name = item.key['asset_name']
            mediatype = item.key['mediatype']
            if name in available:
                assert available[name] == mediatype, (
                    f"Multiple mediatypes for {product_id}/{name}: {available[name]!r}, {mediatype!r}"
                )
            available[name] = mediatype

        missing = sorted(set(asset_names) - available.keys())
        if missing:
            logger.error(
                "Asset(s) not found in DASI for product %s: %s",
                product_id, ", ".join(missing)
            )

        wanted = {name: available[name] for name in asset_names if name in available}
        if not wanted:
            return

        full_query = {
            **base_query,
            'asset_name': list(wanted),
            'mediatype': sorted(set(wanted.values())),
        }
        for r in self.dasi_assets.retrieve(full_query):
            yield r.key['asset_name'], r.key, r.data

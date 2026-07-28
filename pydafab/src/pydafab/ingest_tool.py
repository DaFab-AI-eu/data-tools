import hashlib
import logging
from pathlib import Path
from typing import Iterator, Any

from pystac import Item
from pydasi import Dasi

from pydafab.dasi_copernicus import CopernicusKey

from .copernicus import StacIngestor
from .errors import AssetIntegrityError, AssetNotFoundError
from .integrity import validate_asset_data

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

    def _retrieve_asset_records(
        self, dasi: Dasi, product_id: str, asset_names: list[str]
    ) -> dict[str, tuple[dict, bytes]]:
        base_query = self._build_query(product_id)
        available: dict[str, set[str]] = {}
        for item in dasi.list(base_query):
            if item.key.has('asset_name'):
                available.setdefault(item.key['asset_name'], set()).add(item.key['mediatype'])

        missing = sorted(set(asset_names) - available.keys())
        if missing:
            raise AssetNotFoundError(", ".join(missing), product_id)

        records: dict[str, tuple[dict, bytes]] = {}
        for asset_name in dict.fromkeys(asset_names):
            mediatypes = available[asset_name]
            if len(mediatypes) != 1:
                raise AssetIntegrityError(
                    product_id,
                    asset_name,
                    f"expected one media type, found {len(mediatypes)}",
                )

            mediatype = next(iter(mediatypes))
            query = self._build_query(product_id, asset_name)
            query['mediatype'] = [mediatype]
            try:
                matches = list(dasi.retrieve(query))
            except Exception as e:
                raise AssetIntegrityError(product_id, asset_name, f"indexed payload is unreadable: {e}") from e

            if len(matches) != 1:
                raise AssetIntegrityError(
                    product_id,
                    asset_name,
                    f"expected one payload, found {len(matches)}",
                )

            match = matches[0]
            if match.key['asset_name'] != asset_name or match.key['mediatype'] != mediatype:
                raise AssetIntegrityError(product_id, asset_name, "retrieved payload key does not match request")
            if not match.data:
                raise AssetIntegrityError(product_id, asset_name, "retrieved payload is empty")
            records[asset_name] = (match.key, match.data)

        return records

    @staticmethod
    def _validate_asset_records(product: Item, records: dict[str, tuple[dict, bytes]]) -> None:
        for asset_name, (_key, data) in records.items():
            validate_asset_data(
                product.id,
                asset_name,
                product.assets[asset_name],
                data,
                "retrieved",
            )

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

        missing = sorted(name for name in asset_names if name not in product.assets)
        if missing:
            raise AssetNotFoundError(", ".join(missing), product.id)

        requested = list(dict.fromkeys(asset_names))
        existing_assets = self._list_assets(product.id)
        indexed = existing_assets & set(requested)
        skipped: set[str] = set()
        corrupt: set[str] = set()

        for asset_name in sorted(indexed):
            try:
                existing_record = self._retrieve_asset_records(
                    self.dasi_assets, product.id, [asset_name]
                )
                if modifier is None:
                    self._validate_asset_records(product, existing_record)
                skipped.add(asset_name)
            except (AssetIntegrityError, AssetNotFoundError) as e:
                logger.warning("Rearchiving corrupt indexed asset %s/%s: %s", product.id, asset_name, e)
                corrupt.add(asset_name)

        assets_to_fetch = [
            name for name in requested if name not in existing_assets or name in corrupt
        ]

        if skipped:
            logger.info(
                "Skipping %d existing asset(s) for product %s: %s",
                len(skipped),
                product.id,
                ", ".join(sorted(skipped)),
            )

        archived: dict[str, tuple[int, str]] = {}
        try:
            for asset_name in assets_to_fetch:
                _asset, data = self.ingestor.fetch_asset(product, asset_name)
                key = CopernicusKey.from_stac(self.ingestor.source, product, asset_name)

                logger.debug("Archiving asset: %s with DASI key: %s", asset_name, key)

                if modifier:
                    data = modifier.modify_asset(key, data)

                archived[asset_name] = (len(data), hashlib.sha256(data).hexdigest())
                self.dasi_assets.archive(key, data)
                logger.debug("Buffered asset for archive: %s", asset_name)
        finally:
            self.dasi_assets.flush()

        fresh_dasi = Dasi(str(self.config_dir / "assets.yml"))
        records = self._retrieve_asset_records(fresh_dasi, product.id, requested)
        if modifier is None:
            self._validate_asset_records(product, records)
        for asset_name, (expected_size, expected_digest) in archived.items():
            data = records[asset_name][1]
            actual_digest = hashlib.sha256(data).hexdigest()
            if len(data) != expected_size or actual_digest != expected_digest:
                raise AssetIntegrityError(product.id, asset_name, "post-flush readback differs from archived bytes")
            logger.info("Archived and verified asset: %s", asset_name)

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
        requested = list(dict.fromkeys(asset_names))
        if not requested:
            return

        records = self._retrieve_asset_records(self.dasi_assets, product_id, requested)
        for asset_name in requested:
            key, data = records[asset_name]
            yield asset_name, key, data

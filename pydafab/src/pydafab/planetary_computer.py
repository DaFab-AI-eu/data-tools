"""
Planetary Computer STAC Ingestor

This module provides the PlanetaryComputerIngestor class for querying and retrieving
Sentinel-1 Radiometrically Terrain Corrected products from the Microsoft Planetary Computer STAC API.

"""

import logging
from collections.abc import Iterator
from typing import Any

from pystac import Item
from requests import RequestException

from .errors import AssetFetchError
from .ingestor import PYSTAC_TIMEOUT, StacIngestor

logger = logging.getLogger(__name__)

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"

SAS_SIGN_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"
# Timeout in seconds for connecting to and reading from Azure Blob Storage
BLOB_TIMEOUT = (10, 60)
# Multihash prefix for a 16-byte MD5 digest
MD5_MULTIHASH_PREFIX = "d50110"


def _with_multihash_checksums(item: Item) -> Item:
    """Prefix the bare MD5 hex the Planetary Computer puts in file:checksum so it is a multihash.

    The STAC file extension requires file:checksum to be a self-describing multihash.
    The Planetary Computer breaks the spec here by publishing a bare MD5, which
    validate_asset_data would otherwise reject as malformed.
    """
    for asset in item.assets.values():
        checksum = asset.extra_fields.get("file:checksum")
        if checksum is not None and len(checksum) == 32:
            asset.extra_fields["file:checksum"] = MD5_MULTIHASH_PREFIX + checksum
    return item


class PlanetaryComputerIngestor(StacIngestor):
    """Ingests products and assets from the Microsoft Planetary Computer STAC catalog."""

    def __init__(
        self,
        stac_catalog: str = "https://planetarycomputer.microsoft.com/api/stac/v1",
        verbose: bool = False,
    ) -> None:
        super().__init__(stac_catalog=stac_catalog, verbose=verbose)
        self.source = "MPC"

    def __repr__(self) -> str:
        return f"<PlanetaryComputerIngestor:verbose={self.verbose}>"

    def _fetch(self, href: str) -> bytes:
        """Download an Azure Blob Storage Asset through a SAS-signed href."""

        logger.debug("Fetching blob from %s", href)

        try:
            response = self._session.get(SAS_SIGN_URL, params={"href": href}, timeout=PYSTAC_TIMEOUT)
            response.raise_for_status()
            response = self._session.get(response.json()["href"], timeout=BLOB_TIMEOUT)
            response.raise_for_status()
            return response.content
        except RequestException as e:
            raise AssetFetchError(href) from e

    def search_product(self, product_id: str, collections: list[str] | None = None) -> Item:
        return _with_multihash_checksums(super().search_product(product_id, collections))

    def search(self, params: dict[str, Any]) -> Iterator[Item]:
        """
        Search products matching the provided parameters.

        Sentinel-1 has no cloud cover, so ``cloud_cover_max`` is ignored.

        :param self: The PlanetaryComputerIngestor instance
        :param params: Dictionary of search parameters
        :return: An iterator over matching product items
        :rtype: Iterator[Item]
        """
        bbox = [float(v) for v in params["bbox"].split(",")]
        if len(bbox) != 4:
            raise ValueError(f"Invalid bbox[{params['bbox']}]! Expected format: 'min_lon,min_lat,max_lon,max_lat'")

        items = super().search(
            {
                "max_items": params["max_items"],
                "collections": params["collections"],
                "datetime": params["datetime"],
                "bbox": bbox,
            }
        )
        return map(_with_multihash_checksums, items)

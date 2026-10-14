"""
Planetary Computer STAC Ingestor

This module provides the PlanetaryComputerIngestor class for querying and retrieving
Sentinel-1 Radiometrically Terrain Corrected products from the Microsoft Planetary Computer STAC API.

"""

import logging
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit

from pystac import Asset, Item
from requests import RequestException

from .errors import AssetFetchError
from .ingestor import PYSTAC_TIMEOUT, StacIngestor

logger = logging.getLogger(__name__)

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"

SAS_SIGN_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"
# Only Azure Blob Storage hrefs need a SAS token; API assets such as rendered_preview do not
BLOB_STORAGE_DOMAIN = ".blob.core.windows.net"
# Timeout in seconds for connecting to and reading from Azure Blob Storage
BLOB_TIMEOUT = (10, 60)
# A SAS token is renewed this long before the Planetary Computer says it expires
SAS_EXPIRY_MARGIN = timedelta(minutes=5)
# Multihash prefix for a 16-byte MD5 digest
MD5_MULTIHASH_PREFIX = "d50110"


def _container_url(href: str) -> str:
    """The Azure Blob Storage container an href lives in, as a URL.

    https://account.blob.core.windows.net/container/path/to/blob.tiff
    -> https://account.blob.core.windows.net/container

    A SAS token is valid for its whole container, and a collection lives in one
    container, so one token serves every asset of every product in a run.
    """
    url = urlsplit(href)
    container = url.path.split("/", 2)[1]
    return f"{url.scheme}://{url.netloc}/{container}"


class PlanetaryComputerIngestor(StacIngestor):
    """Ingests products and assets from the Microsoft Planetary Computer STAC catalog."""

    source = "MPC"

    def __init__(
        self,
        stac_catalog: str = "https://planetarycomputer.microsoft.com/api/stac/v1",
        verbose: bool = False,
    ) -> None:
        super().__init__(stac_catalog=stac_catalog, verbose=verbose)
        self._sas_tokens: dict[str, tuple[str, datetime]] = {}

    def __repr__(self) -> str:
        return f"<PlanetaryComputerIngestor:verbose={self.verbose}>"

    def _sas_token(self, href: str) -> str:
        """A SAS query string valid for href, signed once per container and renewed before it expires."""
        container = _container_url(href)
        cached = self._sas_tokens.get(container)
        if cached and datetime.now(timezone.utc) + SAS_EXPIRY_MARGIN < cached[1]:
            return cached[0]

        response = self._session.get(SAS_SIGN_URL, params={"href": href}, timeout=PYSTAC_TIMEOUT)
        response.raise_for_status()
        signed = response.json()
        token = urlsplit(signed["href"]).query
        self._sas_tokens[container] = (token, datetime.fromisoformat(signed["msft:expiry"]))
        return token

    def _fetch(self, href: str) -> bytes:
        """Download an Asset, through a SAS-signed href when it is in Azure Blob Storage."""

        logger.debug("Fetching asset from %s", href)

        try:
            if urlsplit(href).netloc.endswith(BLOB_STORAGE_DOMAIN):
                href = f"{href}?{self._sas_token(href)}"
            response = self._session.get(href, timeout=BLOB_TIMEOUT)
            response.raise_for_status()
            return response.content
        except (RequestException, KeyError, ValueError) as e:
            raise AssetFetchError(href) from e

    def _checksum(self, asset: Asset) -> str | None:
        """The STAC file extension requires a multihash in file:checksum.

        The Planetary Computer breaks the spec here by publishing a bare MD5 hex,
        so prefix it to make it one.
        """
        checksum = super()._checksum(asset)
        if checksum is not None and len(checksum) == 32:
            return MD5_MULTIHASH_PREFIX + checksum
        return checksum

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

        return super().search(
            {
                "max_items": params["max_items"],
                "collections": params["collections"],
                "datetime": params["datetime"],
                "bbox": bbox,
            }
        )

"""
STAC Ingestor

This module provides the base class for retrieving products and their assets from a STAC API.

"""

import logging

from typing import Any, Iterator, Optional

from pystac import Item
from pystac_client import Client
from pystac_client.stac_api_io import StacApiIO
from urllib3.util import Retry

from .errors import AssetNotFoundError, ProductNotFoundError

logger = logging.getLogger(__name__)

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"

# Timeout in seconds for STAC API requests
PYSTAC_TIMEOUT = 60
# Timeout in seconds for S3 connect requests
S3_CONNECT_TIMEOUT = 10
# Timeout in seconds for S3 read requests
S3_READ_TIMEOUT = 60
# Number of retries for S3 requests
S3_RETRYS = 3


class StacIngestor:
    """Base class for data ingestion functionality."""

    def __init__(self, stac_catalog: str, s3_endpoint: str, verbose: bool = False):
        retry = Retry(
            total=5,
            backoff_factor=8,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods={"GET", "POST"},
            respect_retry_after_header=True,
            retry_after_max=300,
        )
        stac_io = StacApiIO(timeout=PYSTAC_TIMEOUT, max_retries=retry)
        self.catalog = Client.open(url=stac_catalog, stac_io=stac_io)
        self._session = stac_io.session
        self.s3_endpoint = s3_endpoint
        self.verbose = verbose
        self.source = "unknown"

    def __repr__(self) -> str:
        return f"<StacIngestor:verbose={self.verbose}>"

    def _fetch_s3(self, href: str) -> Optional[bytes]:
        import boto3
        from botocore.config import Config

        logger.debug("Fetching S3 object from %s using endpoint %s", href, self.s3_endpoint)

        s3_config = Config(
            connect_timeout=S3_CONNECT_TIMEOUT, read_timeout=S3_READ_TIMEOUT, retries={'max_attempts': S3_RETRYS}
        )

        try:
            s3 = boto3.resource(service_name="s3", endpoint_url=self.s3_endpoint, config=s3_config)
            bucket, key = href.lstrip("s3://").split("/", 1)
            response = s3.Object(bucket, key).get()["Body"]  # type: ignore
            return response.read()
        except Exception as e:
            logger.warning("Failed to fetch S3 object from %s: %s", href, e)

        return None

    def search(self, params: dict[str, Any]) -> Iterator[Item]:
        """
        Search products matching the provided parameters

        :param self: The StacIngestor instance
        :param params: Dictionary of search parameters for STAC API
        :return: An iterator over matching product items
        :rtype: Iterator[Item]
        """

        return self.catalog.search(**params).items()

    def search_product(self, product_id: str, collections: list[str] | None = None) -> Item:
        """Retrieve a product from the catalog by its product ID.

        Args:
            product_id: Unique identifier of the product to retrieve.
            collections: Collection IDs to search within. Required by some STAC APIs.

        Returns:
            The matching product.

        Raises:
            ProductNotFoundError: If no item with ``product_id`` exists in the catalog.
        """

        logger.debug("Finding product with ID: %s", product_id)

        search_params: dict[str, Any] = {"ids": [product_id]}
        if collections:
            search_params["collections"] = collections

        product = next(self.catalog.search(**search_params).items(), None)

        if product is None:
            raise ProductNotFoundError(product_id)

        logger.debug("Found product: %s", product.self_href)

        return product

    def fetch_product(self, product: Item) -> bytes:
        """
        Fetch a product and return its raw metadata bytes.

        :param self: The StacIngestor instance
        :param product: The product item to fetch
        :return: The downloaded product metadata
        :rtype: bytes
        """

        logger.debug("Fetching product: %s", product.id)

        response = self._session.get(product.self_href, timeout=PYSTAC_TIMEOUT)
        response.raise_for_status()
        data = response.content

        logger.debug("Fetched product: %s, size: %d bytes", product.id, len(data))

        return data

    def fetch_asset(self, product: Item, asset_key: str):
        """
        Fetch a specific asset from a product and return its metadata key and data

        :param self: The StacIngestor instance
        :param product: The product item containing the asset
        :param asset_key: The key identifying the asset to fetch
        :return: A tuple with the asset metadata key dictionary and the asset data
        :rtype: tuple[dict[str, str], bytes]
        """

        if asset_key not in product.assets:
            raise AssetNotFoundError(asset_key)

        logger.debug("Fetching asset: %s from product: %s", asset_key, product.id)

        asset = product.assets[asset_key]

        data = self._fetch_s3(asset.href)

        if data is None:
            raise AssetNotFoundError(asset_key)
        else:
            logger.debug("Fetched asset: %s from product: %s, size: %d bytes", asset_key, product.id, len(data))

        return asset, data

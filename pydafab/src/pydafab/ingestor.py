"""
STAC Ingestor

This module provides the base class for retrieving products and their assets from a STAC API.

"""

import logging

from typing import Any, Iterator, Optional

from pystac import Item
from pystac_client import Client

from .errors import ProductNotFoundError, AssetNotFoundError
from .helpers import setup_logging

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
        # from .helpers import log_request
        # self.catalog = Client.open(url=stac_catalog, timeout=PYSTAC_TIMEOUT, request_modifier=log_request)
        self.catalog = Client.open(url=stac_catalog, timeout=PYSTAC_TIMEOUT)
        self.s3_endpoint = s3_endpoint
        self.verbose = verbose
        self.source = "unknown"
        setup_logging(self.verbose)

    def __repr__(self) -> str:
        return f"<StacIngestor:verbose={self.verbose}>"

    def _fetch_s3(self, href: str) -> Optional[bytes]:
        import boto3
        from botocore.config import Config

        logger.debug(f"Fetching S3 object from {href} using endpoint {self.s3_endpoint}")

        s3_config = Config(
            connect_timeout=S3_CONNECT_TIMEOUT, read_timeout=S3_READ_TIMEOUT, retries={'max_attempts': S3_RETRYS}
        )

        try:
            s3 = boto3.resource(service_name="s3", endpoint_url=self.s3_endpoint, config=s3_config)
            bucket, key = href.lstrip("s3://").split("/", 1)
            response = s3.Object(bucket, key).get()["Body"]  # type: ignore
            return response.read()
        except Exception as e:
            logger.warning(f"Failed to fetch S3 object from {href}: {e}")

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

    def search_product(self, product_id: str, collections: list[str] | None = None) -> Optional[Item]:
        """Retrieve a product from the catalog by its product ID.

        Args:
            product_id: Unique identifier of the product to retrieve.
            collections: Collection IDs to search within. Required by some STAC APIs.

        Returns:
            The product if found, otherwise None.
        """

        logger.debug(f"Finding product with ID: {product_id}")

        search_params: dict[str, Any] = {"ids": [product_id]}
        if collections:
            search_params["collections"] = collections

        product = next(self.catalog.search(**search_params).items(), None)

        logger.debug(f"Found product: {product.self_href if product else 'None'}")

        return product

    def fetch_product(self, product: Item):
        """
        Fetch a product and return its metadata key and data content

        :param self: The StacIngestor instance
        :param product: The product item to fetch
        :return: A tuple containing the product metadata key and the downloaded data
        :rtype: tuple[dict[str, str], bytes]
        """

        logger.debug(f"Fetching product: {product.id}")

        if product is None:
            raise ProductNotFoundError

        from urllib.request import urlopen

        with urlopen(product.self_href) as response:
            data = response.read()

        logger.debug(f"Fetched product: {product.id}, size: {len(data)} bytes")

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

        if product is None:
            raise ProductNotFoundError

        if asset_key not in product.assets:
            raise AssetNotFoundError

        logger.debug(f"Fetching asset: {asset_key} from product: {product.id}")

        asset = product.assets[asset_key]

        data = self._fetch_s3(asset.href)

        if data is None:
            raise AssetNotFoundError
        else:
            logger.debug(f"Fetched asset: {asset_key} from product: {product.id}, size: {len(data)} bytes")

        return asset, data

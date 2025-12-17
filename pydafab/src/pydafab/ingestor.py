"""
STAC Ingestor

This module provides the base class for retrieving products and their assets from a STAC API.

"""

import logging
from typing import Any, Iterator, Optional

from pystac import Asset, Item
from pystac_client import Client

from .errors import ProductNotFoundError, AssetNotFoundError

logger = logging.getLogger(__name__)

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"
__version__ = "0.0.1"
__author__ = "Metin Cakircali"
__email__ = "metin.cakircali@ecmwf.int"


class StacIngestor:
    """
    Base class for data ingestion functionality
    """

    def __init__(self, stac_catalog: str, s3_endpoint: str, verbose: bool = False) -> None:
        self.catalog = Client.open(url=stac_catalog, timeout=5)
        self.endpoint = s3_endpoint
        self.verbose = verbose
        
        if self.verbose:
            logger.setLevel(logging.DEBUG)

    def __repr__(self) -> str:
        return f"<StacIngestor:verbose={self.verbose}>"

    def __fetch_s3(self, href: str) -> Optional[bytes]:
        import boto3

        logger.debug(f"Fetching S3 object from {href} using endpoint {self.endpoint}")

        try:
            s3 = boto3.resource(service_name="s3", endpoint_url=self.endpoint)
            bucket, key = href.lstrip("s3://").split("/", 1)
            response = s3.Object(bucket, key).get()["Body"]
            return response.read()
        except Exception as e:
            logger.warning(f"Failed to fetch S3 object from {href}: {e}")

        return None

    def _fix_key(self, key: dict[str, str]) -> dict[str, str]:
        for fix in [("/", "_"), (":", "_")]:
            for k, v in key.items():
                key[k] = str(v).replace(*fix)
        return key

    def make_key_from_product(self, product: Item) -> dict[str, str]:
        raise NotImplementedError

    def make_asset_key_from_product(self, product: Item, asset: Asset) -> dict[str, str]:
        raise NotImplementedError

    def search(self, params: dict[str, Any]) -> Iterator[Item]:
        """
        Search products matching the provided parameters

        :param self: The StacIngestor instance
        :param params: Dictionary of search parameters for STAC API
        :return: An iterator over matching product items
        :rtype: Iterator[Item]
        """

        return self.catalog.search(**params).items()

    def search_product(self, product_id: str) -> Optional[Item]:
        """
        Retrieve a product from the catalog by its product ID

        :param self: The StacIngestor instance
        :param product_id: Unique identifier of the product to retrieve
        :return: The product if found, otherwise None
        :rtype: Optional[Item]
        """

        logger.debug(f"Finding product with ID: {product_id}")

        return next(self.catalog.get_items(product_id), None)

    def fetch_product(self, product: Item) -> tuple[dict[str, str], bytes]:
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

        key = self.make_key_from_product(product)

        return key, data

    def fetch_asset(self, product: Item, asset_key: str) -> tuple[dict[str, str], bytes]:
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

        key = self.make_asset_key_from_product(product, asset)

        data = self.__fetch_s3(asset.href)

        if data is None:
            raise AssetNotFoundError
        else:
            logger.debug(f"Fetched asset: {asset_key} from product: {product.id}, size: {len(data)} bytes")

        return key, data

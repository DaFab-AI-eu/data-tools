"""
Copernicus STAC Ingestor

This module provides the CopernicusIngestor class for querying and retrieving products from the Copernicus Dataspace STAC API.

"""

import logging
from functools import cached_property
from typing import Any, Iterator

import boto3
from botocore.config import Config

from pystac import Asset

from .errors import AssetFetchError
from .ingestor import StacIngestor, Item
from .integrity import MD5_MULTIHASH_PREFIX

logger = logging.getLogger(__name__)

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"

# Timeout in seconds for S3 connect requests
S3_CONNECT_TIMEOUT = 10
# Timeout in seconds for S3 read requests
S3_READ_TIMEOUT = 60
# Number of retries for S3 requests
S3_RETRYS = 3
# Multihash prefix CDSE puts on the MD5 of Sentinel-1 COG assets: SHA3-256 truncated to 16 bytes
MISLABELLED_MD5_PREFIX = "1610"


class CopernicusIngestor(StacIngestor):
    """Ingests and manages Copernicus STAC catalog products and assets."""

    source = "CDSE"

    def __init__(
        self,
        stac_catalog: str = "https://stac.dataspace.copernicus.eu/v1",
        s3_endpoint: str = "https://eodata.dataspace.copernicus.eu",
        verbose: bool = False,
    ) -> None:
        super().__init__(stac_catalog=stac_catalog, verbose=verbose)
        self.s3_endpoint = s3_endpoint

        if s3_endpoint == "https://eodata.cloudferro.com":
            self.source = "CREODIAS"

        self.catalog.add_conforms_to("ITEM_SEARCH")

    def __repr__(self) -> str:
        return f"<CopernicusIngestor:catalog={self.catalog.id},verbose={self.verbose}>"

    @cached_property
    def _s3(self):
        s3_config = Config(
            connect_timeout=S3_CONNECT_TIMEOUT,
            read_timeout=S3_READ_TIMEOUT,
            retries={"max_attempts": S3_RETRYS, "mode": "standard"},
        )
        return boto3.resource(service_name="s3", endpoint_url=self.s3_endpoint, config=s3_config)

    def _fetch(self, href: str) -> bytes:
        logger.debug("Fetching S3 object from %s using endpoint %s", href, self.s3_endpoint)

        try:
            bucket, key = href.removeprefix("s3://").split("/", 1)
            return self._s3.Object(bucket, key).get()["Body"].read()
        except Exception as e:
            raise AssetFetchError(href) from e

    def _checksum(self, asset: Asset) -> str | None:
        """The STAC file extension requires a multihash in file:checksum.

        CDSE breaks the spec for Sentinel-1 COG assets by labelling their MD5 as a
        truncated SHA3-256, so relabel it as the MD5 it is.
        """
        checksum = super()._checksum(asset)
        if checksum is not None and checksum.startswith(MISLABELLED_MD5_PREFIX) and len(checksum) == 36:
            return MD5_MULTIHASH_PREFIX + checksum[len(MISLABELLED_MD5_PREFIX):]
        return checksum

    def __make_search_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Build search parameters for querying Copernicus STAC API based on instance attributes

        :param self: The CopernicusIngestor instance
        :param params: Dictionary containing search criteria
        :return: Dictionary of search parameters for the STAC API
        :rtype: dict[str, Any]
        """

        logger.debug("Max items: %s", params["max_items"])
        logger.debug("Collections: %s", params["collections"])
        logger.debug("Datetime: %s", params["datetime"])
        logger.debug("Bounding Box: %s", params["bbox"])
        logger.debug("Cloud cover max: %s", params["cloud_cover_max"])

        bbox = params["bbox"].split(",")
        if len(bbox) == 4:
            min_lon, min_lat, max_lon, max_lat = map(float, bbox)
            coordinates = [
                [min_lon, min_lat],
                [min_lon, max_lat],
                [max_lon, max_lat],
                [max_lon, min_lat],
                [min_lon, min_lat],
            ]
            logger.debug("Coordinates: %s", coordinates)
        else:
            raise ValueError(f"Invalid bbox[{params['bbox']}]! Expected format: 'min_lon,min_lat,max_lon,max_lat'")
            # sys.exit(
            #     f"Error: Invalid bbox[{self.bbox}]! Expected format: 'min_lon,min_lat,max_lon,max_lat'"
            # )

        aoi = {
            "type": "Polygon",
            "coordinates": [coordinates],
        }

        search = {
            "max_items": params["max_items"],
            "collections": params["collections"],
            "datetime": params["datetime"],
            "intersects": aoi,
            "fields": {"exclude": ["geometry"]},
        }
        # Sentinel-1 is radar: it has no cloud cover, and the catalogue rejects the filter.
        if not params["collections"].startswith("sentinel-1"):
            search["filter"] = {"op": "<", "args": [{"property": "eo:cloud_cover"}, params["cloud_cover_max"]]}
        return search

    def search(self, params: dict[str, Any]) -> Iterator[Item]:
        """
        Search products matching the provided parameters.

        :param self: The CopernicusIngestor instance
        :param params: Dictionary of search parameters
        :return: An iterator over matching product items
        :rtype: Iterator[Item]
        """
        search_params = self.__make_search_params(params)
        return super().search(search_params)

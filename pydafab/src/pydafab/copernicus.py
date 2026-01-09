"""
Copernicus STAC Ingestor

This module provides the CopernicusIngestor class for querying and retrieving products from the Copernicus Dataspace STAC API.

"""

import logging
from datetime import datetime
from typing import Any, Iterator

from .ingestor import StacIngestor, Asset, Item

logger = logging.getLogger(__name__)

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"


class CopernicusIngestor(StacIngestor):
    """Ingests and manages Copernicus STAC catalog products and assets."""

    def __init__(
        self,
        stac_catalog: str = "https://stac.dataspace.copernicus.eu/v1",
        s3_endpoint: str = "https://eodata.dataspace.copernicus.eu",
        verbose: bool = False,
    ) -> None:
        super().__init__(stac_catalog=stac_catalog, s3_endpoint=s3_endpoint, verbose=verbose)

        self.catalog.add_conforms_to("ITEM_SEARCH")

    def __repr__(self) -> str:
        return f"<CopernicusIngestor:catalog={self.catalog.id},verbose={self.verbose}>"

    def __make_search_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Build search parameters for querying Copernicus STAC API based on instance attributes

        :param self: The CopernicusIngestor instance
        :param params: Dictionary containing search criteria
        :return: Dictionary of search parameters for the STAC API
        :rtype: dict[str, Any]
        """

        logger.debug(f"Max items: {params['max_items']}")
        logger.debug(f"Collections: {params['collections']}")
        logger.debug(f"Datetime: {params['datetime']}")
        logger.debug(f"Bounding Box: {params['bbox']}")
        logger.debug(f"Cloud cover max: {params['cloud_cover_max']}")

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
            logger.debug(f"Coordinates: {coordinates}")
        else:
            raise ValueError(f"Invalid bbox[{params['bbox']}]! Expected format: 'min_lon,min_lat,max_lon,max_lat'")
            # sys.exit(
            #     f"Error: Invalid bbox[{self.bbox}]! Expected format: 'min_lon,min_lat,max_lon,max_lat'"
            # )

        aoi = {
            "type": "Polygon",
            "coordinates": [coordinates],
        }

        return {
            "max_items": params["max_items"],
            "collections": params["collections"],
            "datetime": params["datetime"],
            "intersects": aoi,
            "filter": {
                "op": "<",
                "args": [{"property": "eo:cloud_cover"}, params["cloud_cover_max"]],
            },
            "fields": {"exclude": ["geometry"]},
        }

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

    def make_key_from_product(self, product: Item) -> dict[str, str]:
        """
        Extract metadata key information from a Copernicus STAC product item.

        :param self: The CopernicusIngestor instance
        :param product: The product item from which to extract metadata
        :return: A dictionary containing extracted metadata key information
        :rtype: dict[str, str]
        """

        key = {
            "source": "CDSE",
            "collection": getattr(product, "collection_id", "null"),
            "platform": product.properties["platform"],
            "instruments": product.properties["instruments"][0],
            "procver": product.properties["processing:version"],
            "gridcode": product.properties["grid:code"],
            "orbit": product.properties["sat:relative_orbit"],
        }

        # Processing date and time format: YYYYMMDDTHHMMSS
        dt = datetime.fromisoformat(product.properties["processing:datetime"])
        key["procdate"] = dt.strftime("%Y%m%dT%H%M%S")

        # Acquisition date and time format: YYYY-MM-DD and HHMMSS
        dt = datetime.fromisoformat(product.properties["datetime"])
        key["takedate"] = dt.strftime("%Y-%m-%d")
        key["taketime"] = dt.strftime("%H%M%S")

        return super()._fix_key(key)

    def make_asset_key_from_product(self, product: Item, asset: Asset) -> dict[str, str]:
        """
        Generate a metadata key dictionary for a Copernicus product asset, combining product and asset details.

        :param self: The CopernicusIngestor instance
        :param product: The product item to extract metadata from
        :type product: Item
        :param asset: The asset whose metadata will be included
        :type asset: Asset
        :return: Dictionary containing combined product and asset metadata keys
        :rtype: dict[str, str]
        """

        key = self.make_key_from_product(product)

        key["gsd"] = asset.extra_fields.get("gsd", "0")
        key["project"] = getattr(asset.ext.proj, "code", "null")
        key["mediatype"] = getattr(asset, "media_type", "null")

        return super()._fix_key(key)

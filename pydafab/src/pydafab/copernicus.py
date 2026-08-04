"""
Copernicus STAC Ingestor

This module provides the CopernicusIngestor class for querying and retrieving products from the Copernicus Dataspace STAC API.

"""

import logging
from typing import Any, Iterator

from .ingestor import StacIngestor, Item

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

        if s3_endpoint == "https://eodata.dataspace.copernicus.eu":
            self.source = "CDSE"
        elif s3_endpoint == "https://eodata.cloudferro.com":
            self.source = "CREODIAS"

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

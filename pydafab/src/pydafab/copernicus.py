"""
Copernicus STAC Ingestor

This module provides the CopernicusIngestor class for querying and retrieving products from the Copernicus Dataspace STAC API.

"""

from datetime import datetime
from math import prod
from .ingestor import StacIngestor, Asset, Item

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"
__version__ = "0.0.1"
__author__ = "Metin Cakircali"
__email__ = "metin.cakircali@ecmwf.int"


class CopernicusIngestor(StacIngestor):
    """
    Ingests and manages Copernicus STAC catalog products and assets

    """

    def __init__(
        self,
        stac_catalog="https://stac.dataspace.copernicus.eu/v1",
        s3_endpoint="https://eodata.dataspace.copernicus.eu",
        verbose=False,
    ):
        super().__init__(stac_catalog=stac_catalog, s3_endpoint=s3_endpoint, verbose=verbose)

        self.catalog.add_conforms_to("ITEM_SEARCH")

    def __repr__(self) -> str:
        return f"<CopernicusIngestor:catalog={self.catalog.id},verbose={self.verbose}>"

    def __make_search_params(self, params):
        """
        Build search parameters for querying Copernicus STAC API based on instance attributes

        :param self: The CopernicusIngestor instance containing search criteria
        :return: Dictionary of search parameters for the STAC API
        :rtype: dict[str, Any]
        """

        if self.verbose:
            print(f"Max items: {params['max_items']}")
            print(f"Collections: {params['collections']}")
            print(f"Datetime: {params['datetime']}")
            print(f"Bounding Box: {params['bbox']}")
            print(f"Cloud cover max: {params['cloud_cover_max']}")

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
            if self.verbose:
                print(f"Coordinates: {coordinates}")
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

    def search(self, params):
        search_params = self.__make_search_params(params)
        return super().search(search_params)

    def make_key_from_product(self, product: Item) -> dict[str, str]:
        """
        Extract metadata key information from a Copernicus STAC product item

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

        dt = datetime.fromisoformat(product.properties["processing:datetime"])
        key["procdate"] = dt.strftime("%Y%m%dT%H%M%S")

        dt = datetime.fromisoformat(product.properties["datetime"])
        key["takedate"] = dt.strftime("%Y-%m-%d")
        key["taketime"] = dt.strftime("%H%M%S")

        key = super()._fix_key(key)

        return key

    def make_asset_key_from_product(self, product: Item, asset: Asset) -> dict[str, str]:

        key = self.make_key_from_product(product)

        key["gsd"] = asset.extra_fields.get("gsd", "0")
        key["project"] = getattr(asset.ext.proj, "code", "null")
        key["mediatype"] = getattr(asset, "media_type", "null")

        key = super()._fix_key(key)

        return key

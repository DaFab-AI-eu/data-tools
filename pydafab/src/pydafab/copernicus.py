"""
Copernicus STAC Ingestor

This module provides the CopernicusIngestor class for querying and retrieving products from the Copernicus Dataspace STAC API.

"""

from datetime import datetime
import sys

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"
__version__ = "0.0.1"
__author__ = "Metin Cakircali"
__email__ = "metin.cakircali@ecmwf.int"


class CopernicusIngestor:
    """
    Ingests and retrieves products from the Copernicus STAC API (https://stac.dataspace.copernicus.eu/v1).

    :param max_items: Maximum number of items to retrieve
    :param collections: Collections to search in
    :param datetime: Datetime range for the search
    :param bbox: Bounding box for the search
    :param cloud_cover_max: Maximum cloud cover percentage
    :param verbose: Enable verbose output
    """

    def __init__(
        self,
        max_items=None,
        collections=None,
        datetime=None,
        bbox=[],
        cloud_cover_max=None,
        verbose=False,
    ):
        from pystac_client import Client

        self.max_items = max_items
        self.collections = collections
        self.datetime = datetime
        self.bbox = bbox
        self.cloud_cover_max = cloud_cover_max
        self.verbose = verbose

        # Initialize the STAC client for Copernicus Dataspace
        self.catalog = Client.open("https://stac.dataspace.copernicus.eu/v1")
        self.catalog.add_conforms_to("ITEM_SEARCH")

    def _get_seach_params(self):
        """
        Build search parameters for querying Copernicus STAC API based on instance attributes

        :param self: The CopernicusIngestor instance containing search criteria
        :return: Dictionary of search parameters for the STAC API
        :rtype: dict[str, Any]
        """

        if self.verbose:
            print(f"Max items: {self.max_items}")
            print(f"Collections: {self.collections}")
            print(f"Datetime: {self.datetime}")
            print(f"Bounding Box: {self.bbox}")
            print(f"Cloud cover max: {self.cloud_cover_max}")

        bbox = self.bbox.split(",")
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
            sys.exit(
                "Error: Invalid bbox[%s]! Expected format: 'min_lon,min_lat,max_lon,max_lat'"
                % self.bbox,
            )

        aoi = {
            "type": "Polygon",
            "coordinates": [coordinates],
        }

        return {
            "max_items": self.max_items,
            "collections": self.collections,
            "datetime": self.datetime,
            "intersects": aoi,
            "filter": {
                "op": "<",
                "args": [{"property": "eo:cloud_cover"}, self.cloud_cover_max],
            },
            "fields": {"exclude": ["geometry"]},
        }

    def get_products(self):
        """
        Retrieve all Copernicus products matching the current search parameters

        :param self: The CopernicusIngestor instance
        :return: An iterator over matching product items
        :rtype: Iterator[Item]
        """

        params = self._get_seach_params()

        return self.catalog.search(**params).items()

    def get_product(self, product_id):
        """
        Retrieve a product item from the catalog by its product ID

        :param self: The CopernicusIngestor instance
        :param product_id: Unique identifier of the product to retrieve
        :return: The product item if found, otherwise None
        :rtype: Item | None
        """

        return next(self.catalog.get_items(product_id), None)

    def retrieve(self, product_id):
        """
        Retrieve a Copernicus STAC product and its metadata by product ID

        :param self: The CopernicusIngestor instance
        :param product_id: Unique identifier of the product to retrieve
        :return: A list containing product metadata as a dictionary and the raw product data
        """

        data = None
        key: dict[str, str] = {}

        product = self.get_product(product_id)

        if product is not None:
            from urllib.request import urlopen

            # get the STAC product's link
            href = next(link.href for link in product.links if link.rel == "self")

            with urlopen(href) as response:
                data = response.read()

            key = {
                "source": "copernicus_stac",
                "collection": getattr(product, "collection_id", "unknown"),
                "platform": product.properties["platform"],
                "instruments": product.properties["instruments"][0],
                "procversion": product.properties["processing:version"],
                "gridcode": product.properties["grid:code"],
                "orbit": product.properties["sat:relative_orbit"],
                "date": product.properties["datetime"],
                "gsd": product.properties["gsd"],
            }

        return [key, data]

    def dump_product_ids(self, target_file):
        """
        Export all product IDs from the current product list to a JSON file

        :param self: The CopernicusIngestor instance
        :param target_file: Path to the JSON file where product IDs will be saved
        """

        from json import dump

        product_ids = []

        # Collect product IDs
        for product in self.get_products():
            product_ids.append(product.id)

        # Save product IDs to a JSON file
        with open(target_file, mode="w") as f:
            dump(product_ids, f, indent=2)

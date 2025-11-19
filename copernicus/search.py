"""
Search Copernicus STAC for products based on user-defined parameters.

Example usage:
    python search.py --max_items 100 --collections sentinel-2-l2a --bbox "6.95,50.65,7.25,50.85" --datetime "2023-01-01/2023-12-31" --cloud_cover_max 20.0

"""

import json

from tifffile import product
from helpers import get_seach_params
from pystac_client import Client

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"
__version__ = "0.0.1"
__author__ = "Metin Cakircali"
__email__ = "metin.cakircali@ecmwf.int"


def main():
    """Search Copernicus STAC and print found item IDs."""

    products = []

    params = get_seach_params()

    catalog = Client.open("https://stac.dataspace.copernicus.eu/v1")
    catalog.add_conforms_to("ITEM_SEARCH")

    resp = catalog.search(**params)

    for item in resp.items():
        products.append(item.id)

    # Save product IDs to a JSON file
    with open("/tmp/product_ids.json", "w") as f:
        json.dump(products, f, indent=2)


if __name__ == "__main__":
    main()

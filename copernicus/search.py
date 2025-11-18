"""
Search Copernicus STAC for items based on user-defined parameters.

Example usage:
    Run this script with appropriate command line arguments to search the Copernicus STAC catalog and
    print the IDs of the retrieved items.

"""

from helpers import get_seach_params
from pystac_client import Client

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"
__version__ = "0.0.1"
__author__ = "Metin Cakircali"
__email__ = "metin.cakircali@ecmwf.int"


def main():
    """Search Copernicus STAC and print found item IDs."""

    catalog = Client.open("https://stac.dataspace.copernicus.eu/v1")
    catalog.add_conforms_to("ITEM_SEARCH")

    params = get_seach_params()

    results = catalog.search(**params)

    for item in results.items():
        print(item.id)


if __name__ == "__main__":
    main()

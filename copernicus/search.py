"""
Search Copernicus STAC for products based on user-defined parameters and
output the product IDs to a JSON file.

Example usage:
    python copernicus/search.py --max_items 100 --collections sentinel-2-l2a --bbox "6.95,50.65,7.25,50.85" --datetime "2025-01-21/2025-01-23" --cloud_cover_max 100.0

"""

import argparse
from json import dump

from pydafab import CopernicusIngestor

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"
__version__ = "0.0.1"
__author__ = "Metin Cakircali"
__email__ = "metin.cakircali@ecmwf.int"


def parse_arguments():
    """Parse command line arguments for searching Copernicus STAC."""

    arg_parses = argparse.ArgumentParser("search_copernicus_stac")

    arg_parses.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    arg_parses.add_argument(
        "--max_items",
        type=int,
        help="Maximum number of items to retrieve. default: 100",
        default=100,
    )
    arg_parses.add_argument(
        "--collections",
        type=str,
        help="Collections to search in. default: sentinel-2-l2a",
        default="sentinel-2-l2a",
    )
    arg_parses.add_argument(
        "--datetime",
        type=str,
        help="Datetime range for the search in the format 'start/end'. e.g., '2025-01-01/2025-01-31'",
        required=True,
    )
    arg_parses.add_argument(
        "--bbox",
        type=str,
        help="Bounding box for the search in the format 'min_lon,min_lat,max_lon,max_lat'. e.g., '6.95,50.65,7.25,50.85'",
        required=True,
    )
    arg_parses.add_argument(
        "--cloud_cover_max",
        type=float,
        help="Maximum cloud cover percentage. default: 100.0",
        default=100.0,
    )
    arg_parses.add_argument(
        "--output_file",
        type=str,
        help="Path to the output file (json format).",
        default="/tmp/product_ids.json",
    )

    argparse.Namespace(verbose=False)

    return arg_parses.parse_args()


def main():
    """Main function to search Copernicus STAC and dump product IDs."""

    args = parse_arguments()

    params = {
        "max_items": args.max_items,
        "collections": args.collections,
        "datetime": args.datetime,
        "bbox": args.bbox,
        "cloud_cover_max": args.cloud_cover_max
    }

    product_ids = []

    # Collect product IDs
    for product in CopernicusIngestor(verbose=args.verbose).search(params):
        product_ids.append(product.id)

    # Save product IDs to a JSON file
    with open(args.output_file, mode="w") as f:
        dump(product_ids, f, indent=2)


if __name__ == "__main__":
    main()

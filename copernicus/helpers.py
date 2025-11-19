"""
Helpers for parsing command line arguments and constructing search parameters for Copernicus STAC queries.

This module provides:
- Argument parsing for command line tools searching Copernicus STAC.
- Construction of search parameter dictionaries, including bounding box parsing and cloud cover filtering.

Functions:
    get_seach_params():
        Uses parsed arguments to construct and return a dictionary of search parameters suitable for Copernicus STAC queries, including AOI polygon and filter expressions.

"""

import argparse
import sys

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"
__version__ = "0.0.1"
__author__ = "Metin Cakircali"
__email__ = "metin.cakircali@ecmwf.int"


def _parse_arguments():
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

    argparse.Namespace(verbose=False)

    return arg_parses.parse_args()


def get_seach_params():
    """Get search parameters for Copernicus STAC."""

    args = _parse_arguments()

    if args.verbose:
        print(f"max items: {args.max_items}")

    bbox = args.bbox.split(",")
    if len(bbox) == 4:
        min_lon, min_lat, max_lon, max_lat = map(float, bbox)
        coordinates = [
            [min_lon, min_lat],
            [min_lon, max_lat],
            [max_lon, max_lat],
            [max_lon, min_lat],
            [min_lon, min_lat],
        ]
        if args.verbose:
            print(f"Coordinates: {coordinates}")
    else:
        sys.exit(
            "Error: Invalid bbox[%s]! Expected format: 'min_lon,min_lat,max_lon,max_lat'"
            % args.bbox,
        )

    aoi = {
        "type": "Polygon",
        "coordinates": [coordinates],
    }

    return {
        "max_items": args.max_items,
        "collections": args.collections,
        "datetime": args.datetime,
        "intersects": aoi,
        "filter": {
            "op": "<",
            "args": [{"property": "eo:cloud_cover"}, args.cloud_cover_max],
        },
        "fields": {"exclude": ["geometry"]},
    }

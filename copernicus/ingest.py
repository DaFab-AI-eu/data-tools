"""Ingest product and its assets from Copernicus STAC and archive using Dasi.

Example usage:
    python copernicus/ingest.py --product_id=S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809 --asset_keys=WVP_10m,TCI_20m

"""

import argparse
import sys

from pydafab import CopernicusIngestor, IngestTool

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"
__version__ = "0.0.1"
__author__ = "Metin Cakircali"
__email__ = "metin.cakircali@ecmwf.int"


def parse_arguments():
    arg_parser = argparse.ArgumentParser("ingest_metadata_copernicus_stac")
    arg_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    arg_parser.add_argument(
        "--product_id",
        type=str,
        help="Product ID to ingest from Copernicus STAC, e.g., S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809",
        required=True,
    )
    arg_parser.add_argument(
        "--asset_keys",
        type=str,
        help="Comma-separated list of assets to ingest, e.g., WVP_10m,TCI_20m",
        required=True,
    )
    argparse.Namespace(verbose=False)
    return arg_parser.parse_args()


def main():
    """Ingest product from Copernicus STAC and archive using Dasi."""

    args = parse_arguments()

    ingestor = CopernicusIngestor(verbose=args.verbose)

    product = ingestor.search_product(args.product_id)

    if product is None:
        sys.exit(f"Product [{args.product_id}] not found!")

    tool = IngestTool(ingestor)

    tool.archive_product(product)

    tool.archive_assets(product, args.asset_keys.split(","))


if __name__ == "__main__":
    main()
